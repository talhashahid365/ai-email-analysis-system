from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-insecure-secret-change-me-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "MailNexa AI"
    VERSION: str = "2.1.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"  # development | staging | production | test

    # --- Security ---
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    VERIFY_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 3
    CORS_ORIGINS: str = "http://localhost:3000"
    REQUIRE_EMAIL_VERIFICATION: bool = False
    # Returns reset/verify tokens in API responses (dev/testing only, never in production)
    EXPOSE_DEV_TOKENS: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    ALLOW_REGISTRATION: bool = True
    FIRST_USER_IS_ADMIN: bool = True  # bootstrap only; ignored in production
    ADMIN_EMAILS: str = ""  # comma-separated; accounts registered with these addresses become admins
    PASSWORD_MIN_LENGTH: int = 8

    # --- Rate limiting ---
    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_PER_MIN: int = 10
    AI_RATE_LIMIT_PER_MIN: int = 30
    UPLOAD_RATE_LIMIT_PER_MIN: int = 20

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./email_intelligence.db"
    # Set AUTO_CREATE_TABLES=False in production and use `alembic upgrade head` instead
    AUTO_CREATE_TABLES: bool = True

    # --- Redis ---
    REDIS_URL: Optional[str] = None  # e.g. redis://localhost:6379/0

    # --- Error Tracking ---
    SENTRY_DSN: Optional[str] = None  # Set in production for error tracking

    # --- Logging ---
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR

    # --- LLM (keys stay on the backend only) ---
    LLM_PROVIDER: str = "auto"  # auto | gemini | openai | anthropic | heuristic
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-2.5-flash,gemini-2.5-flash-lite"  # tried in order if the main model is retired
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 2
    AI_FALLBACK_TO_HEURISTIC: bool = True

    # --- Background processing ---
    DEADLINE_CHECK_INTERVAL_SECONDS: int = 3600  # how often the API process scans for approaching deadlines (0 = off)
    PROCESSING_MODE: str = "background"  # sync | background | celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # --- Email handling ---
    THREAD_MATCH_DAYS: int = 90
    REPLY_OVERDUE_HOURS: int = 24
    DEADLINE_NOTICE_DAYS: int = 2
    MAX_PAGE_SIZE: int = 200
    MAX_PROCESSING_RETRIES: int = 3

    # --- Uploads ---
    MAX_UPLOAD_BYTES: int = 2_000_000
    MAX_IMPORT_ROWS: int = 500
    MAX_BODY_CHARS: int = 50_000

    # --- SMTP (optional; used for verification / reset emails) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@mailnexa.ai"
    # Approving a reply in the app also e-mails it to the original sender through the SMTP account above.
    SEND_REPLIES_VIA_SMTP: bool = True

    # --- Mail network (Gmail IMAP / SMTP connections) ---
    MAIL_TLS_MODE: str = "auto"  # auto = normal TLS, then TLS 1.2 only if the handshake hangs | default | tls12
    MAIL_NET_TIMEOUT_SECONDS: float = 15.0

    # --- IMAP (optional; "Sync mailbox" button pulls real incoming mail, e.g. Gmail) ---
    IMAP_HOST: str = ""  # e.g. imap.gmail.com
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""  # Gmail: use an App Password
    IMAP_FOLDER: str = "INBOX"
    IMAP_MAX_FETCH: int = 25  # newest N messages checked per sync (already-imported mail is skipped automatically)
    IMAP_SINCE_DAYS: int = 3  # only mail from the last N days is imported, so an old mailbox does not flood the website
    IMAP_SYNC_INTERVAL_SECONDS: int = 30  # automatic mailbox check; 0 = only the manual "Sync Mailbox" button
    IMAP_OWNER_EMAIL: str = ""  # website account that receives the mail; empty = account with IMAP_USER's address, else first admin

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def admin_emails_list(self) -> List[str]:
        return [o.strip().lower() for o in self.ADMIN_EMAILS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT.lower() == "test"


settings = Settings()

if settings.is_production:
    if settings.SECRET_KEY == INSECURE_DEFAULT_SECRET or len(settings.SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be set to a random string of 32+ characters in production")
    if settings.EXPOSE_DEV_TOKENS:
        raise RuntimeError("EXPOSE_DEV_TOKENS must be False in production")
    if settings.DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("SQLite is not supported in production. Set DATABASE_URL to a PostgreSQL connection string.")
