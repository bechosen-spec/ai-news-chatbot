"""Authenticated, owner-scoped persistent RAG chat API."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.dependencies.chat_auth import (
    ChatPrincipal,
    configured_subjects,
    require_chat_principal,
)
from backend.app.db.models import ChatConversation, ChatMessage, RetrievalMetadata
from backend.app.db.session import get_db
from backend.app.schemas.chat import (
    ChatHealthResponse,
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ConversationDetail,
    ConversationSummary,
    DiversityResponse,
    MessageResponse,
)
from backend.app.services.llm import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from backend.app.services.rag import RAGService
from backend.app.services.retrieval import Retriever
from backend.app.services.retrieval.text import normalize_tokens

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
DBSession = Annotated[Session, Depends(get_db)]
Principal = Annotated[ChatPrincipal, Depends(require_chat_principal)]


def _owned_conversation(
    session: Session, conversation_id: str, subject: str, *, include_messages: bool = False
) -> ChatConversation:
    statement = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.owner_subject == subject,
        ChatConversation.deleted_at.is_(None),
    )
    if include_messages:
        statement = statement.options(selectinload(ChatConversation.messages))
    conversation = session.scalar(statement)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def _citation_payload(item) -> dict:
    return {
        "citation_id": item.citation_id,
        "article_id": item.article_id,
        "title": item.title,
        "publisher": item.publisher,
        "source_slug": item.source_slug,
        "url": item.url,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "excerpt": item.excerpt,
        "category": item.category,
    }


@router.get("/health", response_model=ChatHealthResponse)
def chat_health(request: Request, session: DBSession) -> ChatHealthResponse:
    provider = request.app.state.llm_provider
    indexed = session.scalar(select(func.count()).select_from(RetrievalMetadata)) or 0
    return ChatHealthResponse(
        status="ok" if provider.configured else "degraded",
        provider=provider.name,
        provider_configured=provider.configured,
        authentication_configured=bool(configured_subjects(request)),
        indexed_articles=indexed,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    session: DBSession,
    principal: Principal,
) -> ChatResponse:
    settings = request.app.state.settings
    if len(payload.question) > settings.rag_max_question_characters:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Question is too long")
    if payload.published_after and payload.published_before:
        if payload.published_after > payload.published_before:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="published_after must not be later than published_before",
            )
    if payload.conversation_id:
        conversation = _owned_conversation(
            session, payload.conversation_id, principal.subject, include_messages=True
        )
    else:
        conversation = ChatConversation(
            owner_subject=principal.subject,
            title=payload.question.strip()[:250],
        )
        session.add(conversation)
        session.flush()

    ordered_messages = sorted(conversation.messages, key=lambda message: message.created_at)
    history = [(message.role, message.content) for message in ordered_messages[-6:]]
    previous_user_question = next(
        (message.content for message in reversed(ordered_messages) if message.role == "user"), None
    )
    retrieval_query = payload.question
    if previous_user_question and len(normalize_tokens(payload.question)) <= 3:
        retrieval_query = f"{previous_user_question} {payload.question}"
    user_message = ChatMessage(
        conversation=conversation,
        role="user",
        content=payload.question.strip(),
        status="complete",
    )
    conversation.updated_at = datetime.now(UTC)
    session.add(user_message)
    session.commit()

    retrieval = Retriever(session).search(
        retrieval_query,
        limit=settings.rag_result_limit,
        category=payload.category,
        source=payload.source,
        published_after=payload.published_after,
        published_before=payload.published_before,
    )
    service = RAGService(request.app.state.llm_provider, settings)
    try:
        answer = await service.answer(
            question=payload.question,
            retrieval=retrieval,
            history=history,
        )
    except ProviderUnavailableError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except ProviderTimeoutError as error:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail=str(error)) from error
    except ProviderResponseError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    citation_payloads = [_citation_payload(item) for item in answer.citations]
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=answer.answer,
        citations=citation_payloads,
        status=answer.status,
        message_metadata={
            "limitations": answer.limitations,
            "retrieval_query_terms": retrieval.query_terms,
            "candidate_count": retrieval.candidate_count,
            "unique_sources": retrieval.unique_sources,
            "source_diversity_ratio": retrieval.source_diversity_ratio,
        },
    )
    conversation.updated_at = datetime.now(UTC)
    session.add(assistant_message)
    session.commit()
    session.refresh(assistant_message)
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        answer=answer.answer,
        citations=[CitationResponse.model_validate(item) for item in citation_payloads],
        limitations=answer.limitations,
        status=answer.status,
        diversity=DiversityResponse(
            unique_sources=retrieval.unique_sources,
            source_diversity_ratio=retrieval.source_diversity_ratio,
            candidate_count=retrieval.candidate_count,
        ),
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(session: DBSession, principal: Principal) -> list[ConversationSummary]:
    rows = session.scalars(
        select(ChatConversation)
        .where(
            ChatConversation.owner_subject == principal.subject,
            ChatConversation.deleted_at.is_(None),
        )
        .order_by(ChatConversation.updated_at.desc())
    ).all()
    return [ConversationSummary.model_validate(row, from_attributes=True) for row in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str, session: DBSession, principal: Principal
) -> ConversationDetail:
    conversation = _owned_conversation(
        session, conversation_id, principal.subject, include_messages=True
    )
    messages = sorted(conversation.messages, key=lambda message: message.created_at)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(item, from_attributes=True) for item in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, session: DBSession, principal: Principal) -> None:
    conversation = _owned_conversation(session, conversation_id, principal.subject)
    conversation.deleted_at = datetime.now(UTC)
    conversation.updated_at = conversation.deleted_at
    session.commit()
