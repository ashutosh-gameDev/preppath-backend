"""
File storage for admin-uploaded question images.

Real path: uploads go to Supabase Storage (the bucket named by
`SUPABASE_STORAGE_BUCKET`), written via the Storage REST API using the
service role key - the backend never hands the service role key to a
browser, so this upload always goes through this endpoint rather than the
frontend talking to Supabase Storage directly.

Local dev without a Supabase project connected: falls back to saving the
file on local disk under `backend/uploads/` and serving it back via the
static mount in `main.py` - same "real integration, dev-mode local
fallback" pattern as Supabase Auth (`dev_auth.py`) and Razorpay
(`premium.py`). Whichever path is used, callers only ever see a public URL.
"""
import mimetypes
import uuid
from pathlib import Path

import httpx

from app.core.config import settings

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB


class UploadError(Exception):
    pass


def _supabase_storage_configured() -> bool:
    # Guards against the realistic footgun of copying .env.example to .env
    # and not editing it: those placeholders ("https://your-project...",
    # "your-service-role-key") are non-empty strings, so a plain truthiness
    # check would wrongly treat Supabase as configured and attempt a real
    # network call to a host that doesn't exist. Same reasoning applies
    # anywhere else in the codebase that gates on a credential being set.
    url, key = settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
    if not url or not key:
        return False
    if "your-project" in url or key == "your-service-role-key":
        return False
    return True


def _safe_filename(original_name: str) -> str:
    ext = Path(original_name).suffix.lower() or mimetypes.guess_extension("image/jpeg") or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def upload_question_image(content: bytes, filename: str, content_type: str) -> str:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadError(f"Unsupported image type: {content_type}")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError("Image must be 5MB or smaller")

    safe_name = _safe_filename(filename)
    object_path = f"questions/{safe_name}"

    if _supabase_storage_configured():
        url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"
        resp = httpx.post(
            url,
            content=content,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                # Required alongside Authorization - without it Supabase's
                # gateway can't identify the project and instead tries to
                # decode Authorization itself as an end-user JWT, which fails
                # with a confusing "Invalid Compact JWS" for the new-format
                # sb_secret_... key (it isn't JWT-shaped at all).
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=30,
        )
        if resp.status_code >= 400:
            raise UploadError(f"Supabase Storage upload failed: {resp.text}")
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"

    # Dev-mode local fallback.
    dest = UPLOAD_DIR / object_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return f"{settings.PUBLIC_BASE_URL}/uploads/{object_path}"
