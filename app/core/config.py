"""
Centralized application settings, loaded from environment variables / .env.

Everything that varies between environments (dev/staging/prod) lives here so
the rest of the codebase never reads `os.environ` directly.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/examprep"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_STORAGE_BUCKET: str = "exam-platform-media"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    # The student-web app's own public URL - used to build the referral
    # share link (STUDENT_WEB_URL + "/signup?ref=CODE"). MUST be set to the
    # real production domain via Render's env vars; this default is only
    # ever correct for local dev.
    STUDENT_WEB_URL: str = "http://localhost:3001"
    # This backend's own publicly-reachable base URL - only used to build
    # URLs for the local dev-mode upload fallback (see storage_service.py);
    # irrelevant once SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY are set, since
    # Supabase Storage URLs are already absolute.
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    APP_SECRET_KEY: str = "change-me-in-production"
    BOOTSTRAP_ADMIN_EMAIL: str = ""

    # Razorpay (premium subscriptions). Get test-mode keys free from the
    # Razorpay dashboard - no business verification needed to start testing.
    # Leave blank in development to use the dev-only mock checkout instead
    # (see services/premium_service.py) - real payments are impossible
    # without real keys either way, so this only ever affects local dev.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Google Play Billing (Android app purchases - Play policy requires this
    # for any in-app digital-goods purchase, Razorpay can't be used there).
    # GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is the raw JSON content of a service
    # account key with access to this app in Play Console (Setup -> API
    # access -> create/link a service account, grant it "View financial
    # data" + release permissions, download its key). Leave both blank to
    # hard-disable the /premium/google-play/verify route - there's no
    # dev-mode mock for this one, it only matters once a real Play Store
    # build is being tested (see services/google_play_service.py).
    GOOGLE_PLAY_PACKAGE_NAME: str = ""
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
