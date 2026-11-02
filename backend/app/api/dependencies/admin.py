"""Transitional server-side admin protection for Milestone 2A."""

import hmac

from fastapi import Header, HTTPException, Request, status


def require_admin_key(request: Request, x_admin_key: str | None = Header(default=None)) -> str:
    configured = request.app.state.settings.admin_api_key
    if configured is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrative access is not configured",
        )
    if x_admin_key is None or not hmac.compare_digest(x_admin_key, configured.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid administrator credential")
    return "admin_api_key"
