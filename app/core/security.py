"""
Verification of Supabase-issued JWTs.

Supabase Auth issues a JWT on the frontend after login; the frontend sends it
as `Authorization: Bearer <token>` on every API call. The backend NEVER trusts
any role/user info the frontend sends outside of this token - `sub` (the
Supabase auth user id) is the only identity signal we accept.

Two verification paths, tried in order:
1. Local dev-mode tokens (see dev_auth.py) - HS256, signed with APP_SECRET_KEY.
   Only attempted when ENVIRONMENT=development, since these are never real
   Supabase tokens; a mismatch here just falls through to path 2 rather than
   failing outright.
2. Real Supabase-issued tokens. Modern Supabase projects sign access tokens
   with an asymmetric key (ES256/RS256) and publish the public half at
   `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` - nothing secret to
   configure on our side, so this is the default path. Older projects still
   on a shared HS256 "Legacy JWT Secret" are supported too: if
   SUPABASE_JWT_SECRET is set, that's verified against directly instead of
   hitting the JWKS endpoint.
"""
import jwt
from fastapi import HTTPException, status

from app.core.config import settings

_jwks_client: "jwt.PyJWKClient | None" = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(
            f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True
        )
    return _jwks_client


class TokenPayload:
    def __init__(self, sub: str, email: str | None, raw: dict):
        self.sub = sub
        self.email = email
        self.raw = raw


def _decode_dev_token(token: str) -> dict | None:
    """Locally-minted dev-login tokens (see dev_auth.py). Returns None (not
    raised) on any mismatch so the caller falls through to real-token
    verification instead of failing outright."""
    if settings.ENVIRONMENT.lower() != "development":
        return None
    try:
        return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=["HS256"], audience="authenticated")
    except jwt.InvalidTokenError:
        return None


def _decode_real_token(token: str) -> dict:
    if settings.SUPABASE_JWT_SECRET:
        return jwt.decode(
            token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    if not settings.SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured on the backend.",
        )
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")


def decode_supabase_token(token: str) -> TokenPayload:
    payload = _decode_dev_token(token)
    if payload is None:
        try:
            payload = _decode_real_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except (jwt.InvalidTokenError, jwt.PyJWKClientError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    return TokenPayload(sub=sub, email=payload.get("email"), raw=payload)
