"""Server-side bearer-token authentication for the Phase 2B chat boundary."""

import hmac
import json
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ChatPrincipal:
    subject: str


def configured_subjects(request: Request) -> dict[str, str]:
    secret = request.app.state.settings.chat_access_tokens
    if secret is None:
        return {}
    try:
        value = json.loads(secret.get_secret_value())
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        token: subject
        for token, subject in value.items()
        if isinstance(token, str) and token and isinstance(subject, str) and subject
    }


async def require_chat_principal(request: Request) -> ChatPrincipal:
    credentials: HTTPAuthorizationCredentials | None = await bearer(request)
    subjects = configured_subjects(request)
    if not subjects:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat authentication is not configured",
        )
    supplied = credentials.credentials if credentials else ""
    matched_subject = None
    for token, subject in subjects.items():
        if hmac.compare_digest(supplied, token):
            matched_subject = subject
    if matched_subject is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid chat credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ChatPrincipal(subject=matched_subject)
