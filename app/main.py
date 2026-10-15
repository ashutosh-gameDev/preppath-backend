import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger("app")

app = FastAPI(
    title="Exam Prep Platform API",
    description="Generic competitive-exam practice/mock-test/PYQ/leaderboard platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches anything an endpoint didn't (a raw DB error, etc.) so the
    client gets a clean JSON body instead of a bare crash, and the real
    traceback still reaches Render's logs via `logger.exception` instead of
    only ever being visible by guessing. Note this does NOT fix a missing
    CORS header on this response - Starlette wires an Exception-class
    handler into ServerErrorMiddleware, which sits OUTSIDE CORSMiddleware
    (confirmed: still no Access-Control-Allow-Origin header here even with
    this handler in place) - a crash that reaches this point will still
    look like a CORS error in the browser. The real fix for that is making
    sure risky endpoints catch their own exceptions and raise HTTPException
    instead (see bulk_import_job_postings for why that path DOES keep its
    CORS header - it's handled by ExceptionMiddleware, which IS inside
    CORSMiddleware)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Serves files written by the local dev-mode upload fallback (see
# services/storage_service.py). Irrelevant in production once Supabase
# Storage is configured - uploads go straight there instead and this
# directory stays empty.
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
