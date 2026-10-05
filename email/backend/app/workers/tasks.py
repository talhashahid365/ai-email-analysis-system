"""Optional Celery worker (PROCESSING_MODE=celery). Start with:  celery -A app.workers.tasks.celery_app worker

Importing this module raises ImportError when Celery is not installed; `pipeline.enqueue` then falls back to
FastAPI background tasks, so the API keeps working."""
from celery import Celery  # noqa: F401  (ImportError is intentional when celery is absent)

from app.config import settings

celery_app = Celery("email_intelligence", broker=settings.CELERY_BROKER_URL or "memory://",
                    backend=settings.CELERY_RESULT_BACKEND or None)
celery_app.conf.task_acks_late = True


@celery_app.task(name="process_email", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def process_email_task(email_id: int, notify: bool = True) -> bool:
    from app.services.pipeline import process_email
    return process_email(email_id, notify=notify)


@celery_app.task(name="check_deadlines")
def check_deadlines_task() -> int:
    """Scan every user's open deadlines and create 'upcoming_deadline' notifications (run by Celery beat)."""
    from app.database import SessionLocal
    from app.services import notifications
    db = SessionLocal()
    try:
        return notifications.check_all_deadlines(db)
    finally:
        db.close()


celery_app.conf.beat_schedule = {
    "check-deadlines-hourly": {"task": "check_deadlines", "schedule": 3600.0},
}
