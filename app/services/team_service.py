"""
Content-editor (intern) account management.

These are real Supabase Auth users - not a parallel auth system - so
everything downstream (JWT verification, get_current_user, require_content_access)
just works unchanged. The only twist is they log in with a username instead of
an email: we synthesize `{username}@INTERN_EMAIL_DOMAIN` as their Supabase
email (created with email_confirm=True so no confirmation step is needed),
and the admin-web login page does the same substitution client-side before
calling supabase.auth.signInWithPassword - see apps/admin-web login page.
"""
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.models.enums import UserRole

INTERN_EMAIL_DOMAIN = "interns.preppath.internal"


def username_to_email(username: str) -> str:
    return f"{username}@{INTERN_EMAIL_DOMAIN}"


def _require_supabase_configured() -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=400,
            detail="Connect a real Supabase project first (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY) - "
            "content-editor accounts are real Supabase Auth users, so there's nothing to create without one.",
        )


def _admin_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
    }


def create_intern_auth_user(username: str, password: str) -> str:
    """Creates the Supabase Auth user for a new intern account. Returns the
    new user's id (== our local users.id, same convention as every other
    account). Raises HTTPException on failure (e.g. username already taken)."""
    _require_supabase_configured()
    email = username_to_email(username)
    resp = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users",
        headers=_admin_headers(),
        json={"email": email, "password": password, "email_confirm": True, "user_metadata": {"username": username}},
        timeout=20,
    )
    if resp.status_code >= 400:
        detail = resp.json().get("msg") or resp.json().get("message") or resp.text
        if "already been registered" in str(detail).lower() or resp.status_code == 422:
            raise HTTPException(status_code=409, detail=f"Username '{username}' is already taken")
        raise HTTPException(status_code=400, detail=f"Failed to create account: {detail}")
    return resp.json()["id"]


def reset_intern_password(auth_user_id: str, new_password: str) -> None:
    _require_supabase_configured()
    resp = httpx.put(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users/{auth_user_id}",
        headers=_admin_headers(),
        json={"password": new_password},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Failed to reset password: {resp.text}")


def delete_intern_auth_user(auth_user_id: str) -> None:
    """Best-effort: the local `users` row is what actually gates access
    (role check + is_active), so a failure here (e.g. Supabase not configured
    in a dev environment that never really created the auth user) is not
    fatal to removing the local account."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return
    httpx.delete(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users/{auth_user_id}", headers=_admin_headers(), timeout=20
    )


ALLOWED_TEAM_ROLES = (UserRole.CONTENT_EDITOR,)
