"""JWT-based authentication for inter-agent communication.

BD-5: OAuth2 Client Credentials Grant pattern.
Each agent has its own identity with scoped permissions.
Local mode: JWT with shared secret. AWS mode: Cognito tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt  # type: ignore[import-untyped]
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.errors import AuthorizationError


class TokenPayload(BaseModel):
    sub: str  # Agent ID (e.g., "triage_agent")
    scopes: list[str]  # e.g., ["patient:read", "triage:write"]
    aud: str  # Audience
    exp: datetime
    iat: datetime


def create_access_token(
    subject: str,
    scopes: list[str],
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT for agent-to-agent authentication."""
    settings = get_settings()
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "scopes": scopes,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_token_lifetime_seconds),
    }
    if extra_claims:
        claims.update(extra_claims)
    return str(jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def verify_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )
        return TokenPayload(
            sub=payload["sub"],
            scopes=payload.get("scopes", []),
            aud=payload["aud"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        )
    except JWTError as e:
        raise AuthorizationError(f"Invalid token: {e}") from e


def require_scope(token_payload: TokenPayload, required_scope: str) -> None:
    """Check that a token has a required scope. Raises AuthorizationError if not."""
    if required_scope not in token_payload.scopes:
        raise AuthorizationError(
            f"Agent '{token_payload.sub}' lacks required scope: {required_scope}"
        )


def get_agent_token(agent_id: str) -> str:
    """Get a token for an agent (convenience for inter-agent calls)."""
    scope_map: dict[str, list[str]] = {
        "triage_agent": [
            "patient:read",
            "observation:read",
            "condition:read",
            "intake:write",
            "triage:write",
        ],
        "care_coordinator": [
            "patient:read",
            "appointment:read",
            "appointment:write",
            "triage:read",
        ],
        "clinical_data_agent": [
            "patient:read",
            "observation:read",
            "condition:read",
            "medication:read",
            "encounter:read",
        ],
        "pharmacy_agent": [
            "patient:read",
            "medication:read",
            "medication:write",
            "interaction:read",
        ],
    }
    scopes = scope_map.get(agent_id, [])
    return create_access_token(subject=agent_id, scopes=scopes)
