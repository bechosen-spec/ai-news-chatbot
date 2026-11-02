from dataclasses import dataclass

from backend.app.core.config import Settings
from backend.app.services.llm import GeneratedAnswer, LLMProvider
from backend.app.services.rag.citations import validate_citations
from backend.app.services.rag.prompt import SYSTEM_PROMPT, build_user_prompt
from backend.app.services.retrieval import Evidence, RetrievalResult


@dataclass(frozen=True)
class RAGAnswer:
    answer: str
    citations: list[Evidence]
    limitations: list[str]
    status: str


class RAGService:
    def __init__(self, provider: LLMProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    async def answer(
        self,
        *,
        question: str,
        retrieval: RetrievalResult,
        history: list[tuple[str, str]],
    ) -> RAGAnswer:
        if not retrieval.evidence:
            return RAGAnswer(
                answer=(
                    "I could not find relevant indexed news evidence for that question. "
                    "Try different terms or broader filters."
                ),
                citations=[],
                limitations=retrieval.limitations,
                status="insufficient_evidence",
            )
        prompt = build_user_prompt(
            question,
            retrieval.evidence,
            history=history,
            max_characters=self.settings.rag_max_context_characters,
        )
        generated: GeneratedAnswer = await self.provider.generate(
            system_prompt=SYSTEM_PROMPT, user_prompt=prompt
        )
        valid, citation_errors = validate_citations(generated, retrieval.evidence)
        if not valid:
            return RAGAnswer(
                answer=(
                    "I found relevant evidence, but could not produce an answer with valid "
                    "source citations. No unsupported answer has been returned."
                ),
                citations=[],
                limitations=retrieval.limitations + citation_errors,
                status="citation_validation_failed",
            )
        cited = {citation for citation in generated.citation_ids}
        citations = [item for item in retrieval.evidence if item.citation_id in cited]
        return RAGAnswer(
            answer=generated.answer,
            citations=citations,
            limitations=list(dict.fromkeys(retrieval.limitations + generated.limitations)),
            status="complete",
        )
