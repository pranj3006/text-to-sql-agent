"""
Azure AD (Entra ID) OIDC bearer-token validation.

Frontend obtains an access token via MSAL (auth code + PKCE flow) and sends
it as `Authorization: Bearer <token>`. This module validates the token's
signature against Azure's published JWKS, checks issuer/audience/expiry,
and exposes the decoded claims as a `CurrentUser`.

JWKS keys are cached in Redis (see cache_service) with a short TTL so we
don't hit Microsoft's discovery endpoint on every request.
"""
from dataclasses import dataclass, field

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.core.logging import get_logger
from text_to_sql_agent.app.services.cache_service import CacheService, get_cache_service

logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

JWKS_CACHE_KEY = "auth:azure:jwks"
JWKS_CACHE_TTL = 3600  # re-fetch signing keys hourly


@dataclass
class CurrentUser:
    """Decoded identity of the caller, threaded through the request via DI."""
    oid: str                       # Azure AD object id - stable user identifier
    email: str | None
    name: str | None
    roles: list[str] = field(default_factory=list)   # app roles from the AD token, feeds RBAC
    raw_claims: dict = field(default_factory=dict)


async def _get_jwks(cache: CacheService) -> dict:
    cached = await cache.get_json(JWKS_CACHE_KEY)
    if cached:
        return cached
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(settings.AZURE_JWKS_URL)
        resp.raise_for_status()
        jwks = resp.json()
    await cache.set_json(JWKS_CACHE_KEY, jwks, ttl=JWKS_CACHE_TTL)
    return jwks


async def validate_token(token: str, cache: CacheService) -> dict:
    jwks = await _get_jwks(cache)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token") from exc

    key = next((k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")), None)
    if key is None:
        # Key rotated on Azure's side - force a refresh once, then fail hard.
        await cache.delete(JWKS_CACHE_KEY)
        jwks = await _get_jwks(cache)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")), None)
        if key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.AZURE_AUDIENCE,
            issuer=settings.AZURE_ISSUER,
        )
    except JWTError as exc:
        logger.warning("token_validation_failed", extra={"error": str(exc)})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    return claims


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    cache: CacheService = Depends(get_cache_service),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    claims = await validate_token(creds.credentials, cache)
    return CurrentUser(
        oid=claims.get("oid") or claims.get("sub"),
        email=claims.get("preferred_username") or claims.get("email"),
        name=claims.get("name"),
        roles=claims.get("roles", []),
        raw_claims=claims,
    )
