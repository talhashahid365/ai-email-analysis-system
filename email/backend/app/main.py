import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import actions, admin, ai, analysis, analytics, auth, emails, notifications, search
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.services import bootstrap, notifications as notification_service, pipeline
from app.services.settings_store import SettingError

# ── Logging ─────────────────────────────────────────────────────────────────
setup_logging(debug=(settings.LOG_LEVEL.upper() == 'DEBUG'))
log = logging.getLogger('mailnexa.main')

# ── Sentry (optional, enabled when SENTRY_DSN is set) ────────────────────────
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
            send_default_pii=False,  # Never send PII to Sentry
        )
        log.info("Sentry error tracking enabled (env=%s)", settings.ENVIRONMENT)
    except ImportError:
        log.warning("sentry-sdk not installed — run: pip install sentry-sdk[fastapi]")


def _ensure_sqlite_columns(bind_engine):
    """Auto-migrate missing columns for SQLite in development mode."""
    if "sqlite" not in str(bind_engine.url):
        return
    from sqlalchemy import inspect, text

    inspector = inspect(bind_engine)
    with bind_engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(bind_engine.dialect)
                        try:
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))
                            log.info("Auto-migrated SQLite: added column %s.%s", table_name, col.name)
                        except Exception as exc:
                            log.warning("Could not add column %s.%s: %s", table_name, col.name, exc)
        conn.commit()


async def _deadline_scheduler(interval: int):
    """Periodically create 'upcoming_deadline' notifications (deduplicated, so repeated scans are harmless)."""
    while True:
        def _scan() -> int:
            db = SessionLocal()
            try:
                return notification_service.check_all_deadlines(db)
            finally:
                db.close()
        try:
            created = await asyncio.to_thread(_scan)
            if created:
                log.info("Deadline scan created %d notifications", created)
        except Exception:
            log.exception("Deadline scan failed")
        await asyncio.sleep(interval)


async def _imap_poller(interval: int):
    """Checks the real mailbox every `interval` seconds so new customer mail (and follow-ups) appear on the website."""
    from app.services import imap_sync
    while True:
        try:
            stats = await asyncio.to_thread(imap_sync.poll_once)
            if stats and stats.get("imported"):
                log.info("Mailbox sync imported %d new e-mail(s)", stats["imported"])
        except imap_sync.ImapError as exc:
            log.warning("Mailbox sync: %s", exc)
        except Exception:
            log.exception("Mailbox sync failed")
        await asyncio.sleep(interval)


# ── Application lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s v%s [%s]", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)

    from app import database
    current_engine = getattr(database, "engine", engine)
    current_session = getattr(database, "SessionLocal", SessionLocal)

    if settings.AUTO_CREATE_TABLES:
        if settings.is_production:
            log.warning(
                "AUTO_CREATE_TABLES is True in production — "
                "use `alembic upgrade head` and set AUTO_CREATE_TABLES=False"
            )
        _ensure_sqlite_columns(current_engine)
        Base.metadata.create_all(bind=current_engine)

    db = current_session()
    try:
        bootstrap.seed_defaults(db)
    finally:
        db.close()

    recovered = pipeline.recover_interrupted(session=db)
    if recovered:
        log.info("Recovered %d interrupted email processing tasks", recovered)

    scheduler = None
    if settings.DEADLINE_CHECK_INTERVAL_SECONDS > 0:
        scheduler = asyncio.create_task(_deadline_scheduler(settings.DEADLINE_CHECK_INTERVAL_SECONDS))

    poller = None
    from app.services import imap_sync as _imap
    if settings.IMAP_SYNC_INTERVAL_SECONDS > 0 and _imap.configured():
        poller = asyncio.create_task(_imap_poller(settings.IMAP_SYNC_INTERVAL_SECONDS))
        log.info("Automatic mailbox sync every %ss for %s", settings.IMAP_SYNC_INTERVAL_SECONDS, settings.IMAP_USER)

    yield

    if scheduler:
        scheduler.cancel()
    if poller:
        poller.cancel()
    log.info("Shutting down %s", settings.PROJECT_NAME)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json" if not settings.is_production else None,
    docs_url=f"{settings.API_PREFIX}/docs" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost first) ──────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(pipeline.IngestError)
async def ingest_error_handler(request: Request, exc: pipeline.IngestError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(SettingError)
async def setting_error_handler(request: Request, exc: SettingError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(emails.router, prefix=settings.API_PREFIX)
app.include_router(ai.router, prefix=settings.API_PREFIX)
app.include_router(analysis.router, prefix=settings.API_PREFIX)
app.include_router(actions.router, prefix=settings.API_PREFIX)
app.include_router(search.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(notifications.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)


# ── Health checks ─────────────────────────────────────────────────────────────
@app.get("/api/health/live", tags=["health"], include_in_schema=False)
def health_live():
    """Lightweight liveness probe — just confirms process is running."""
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
def health():
    """Deep health check — verifies DB and key services."""
    checks: dict = {}

    # Check database
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        checks["database"] = "ok"
    except Exception as exc:
        log.error("Health check: database error", exc_info=exc)
        checks["database"] = f"error: {type(exc).__name__}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": f"{settings.API_PREFIX}/docs" if not settings.is_production else "disabled in production",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
