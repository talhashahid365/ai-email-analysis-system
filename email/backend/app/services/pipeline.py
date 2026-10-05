"""Email ingestion + AI processing pipeline.

    ingest_email()  -> validate, de-duplicate, upsert sender, group into a thread, store with status 'queued'
    enqueue()       -> run process_email() inline (sync), in a FastAPI background task, or via Celery
    process_email() -> text cleaning -> category/intent/priority/sentiment/summary/extraction/actions/deadlines
                       (LLM with validated output, heuristic fallback) -> persist -> notifications -> AI log

`process_email` opens its own DB session unless one is passed in, so it is safe to run after the HTTP response.
"""
import logging
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import SessionLocal
from app.services import ai_engine, notifications, threads
from app.services.bootstrap import active_category_names
from app.services.settings_store import llm_provider_override
from app.services.text_utils import sanitize
from app.timeutil import to_naive_utc, utcnow

log = logging.getLogger("app.pipeline")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class IngestError(ValueError):
    """The submitted email is unusable (missing sender/body...). Maps to HTTP 422."""


@dataclass
class IngestResult:
    email: models.Email
    duplicate: bool = False


# ------------------------------------------------------------------ ingestion
def _upsert_sender(db: Session, user_id: int, address: str, name: str) -> models.Sender:
    s = db.query(models.Sender).filter_by(user_id=user_id, email=address).first()
    if s is None:
        s = models.Sender(user_id=user_id, email=address, name=name, email_count=0)
        db.add(s)
        db.flush()
    s.email_count = (s.email_count or 0) + 1
    s.last_seen_at = utcnow()
    if name and (not s.name or s.name == "Unknown Sender"):
        s.name = name
    return s


def ingest_email(db: Session, user: models.User, data: Dict[str, Any], raw_eml_path: Optional[str] = None) -> IngestResult:
    """Store one email (status 'queued'). Returns the existing row with duplicate=True when it was already imported."""
    sender_email = str(data.get("sender_email") or "").strip().lower()
    if not _EMAIL_RE.match(sender_email):
        raise IngestError("A valid sender email address is required")
    subject = sanitize(str(data.get("subject") or ""), 500).strip() or "(no subject)"
    body = sanitize(str(data.get("body_plain") or ""), settings.MAX_BODY_CHARS).strip()
    if not body:
        raise IngestError("Email body is empty")
    sender_name = sanitize(str(data.get("sender_name") or ""), 200).strip() or sender_email.split("@")[0].replace(".", " ").title()
    recipient = str(data.get("recipient_email") or user.email).strip().lower() or user.email
    message_id = (str(data["message_id"]).strip()[:500] if data.get("message_id") else None) or None
    in_reply_to = (str(data["in_reply_to"]).strip()[:500] if data.get("in_reply_to") else None) or None
    now = utcnow()
    received_at = to_naive_utc(data["received_at"]) if data.get("received_at") else now
    if received_at > now + timedelta(days=1):  # a future timestamp would pin the mail to the top of the inbox forever
        received_at = now

    chash = threads.compute_content_hash(sender_email, subject, body)
    existing = threads.find_duplicate(db, user.id, message_id, chash)
    if existing:
        return IngestResult(existing, duplicate=True)

    try:
        thread = threads.find_or_create_thread(db, user.id, subject, message_id, in_reply_to, sender_email, received_at)
        sender = _upsert_sender(db, user.id, sender_email, sender_name)
        email = models.Email(
            user_id=user.id, thread_id=thread.id, sender_id=sender.id, sender_email=sender_email, sender_name=sender_name,
            recipient_email=recipient, subject=subject, body_plain=body, body_html=data.get("body_html"),
            received_at=received_at, message_id=message_id, in_reply_to=in_reply_to, content_hash=chash,
            processing_status="queued", reply_status="not_required", raw_eml_path=raw_eml_path)
        db.add(email)
        db.flush()
        threads.refresh_thread(db, thread.id)
        db.commit()
    except IntegrityError:
        db.rollback()  # lost a race with an identical import
        existing = threads.find_duplicate(db, user.id, message_id, chash)
        if existing:
            return IngestResult(existing, duplicate=True)
        raise
    db.refresh(email)
    return IngestResult(email, duplicate=False)


def record_outbound_reply(db: Session, user: models.User, original: models.Email, body: str,
                          reply: models.AIReply, message_id: Optional[str] = None) -> models.Email:
    """Approving a reply stores it as an outbound message in the same thread and closes the reply loop.
    (The app records the reply; delivering it over SMTP is a separate integration.) Does not commit."""
    now = utcnow()
    subject = original.subject if re.match(r"^\s*re\s*:", original.subject, re.I) else f"Re: {original.subject}"
    msg = models.Email(
        user_id=user.id, thread_id=original.thread_id, sender_email=user.email, sender_name=user.full_name,
        recipient_email=original.sender_email, subject=subject[:500], body_plain=body, received_at=now,
        message_id=message_id or f"<{uuid.uuid4().hex}@ai-mail.local>", in_reply_to=original.message_id, is_outbound=True,
        is_read=True, processing_status="completed", reply_status="not_required",
        content_hash=threads.compute_content_hash(user.email, subject, body + uuid.uuid4().hex))
    db.add(msg)
    db.flush()
    original.reply_status = "replied"
    original.replied_at = now
    reply.status = "approved"
    reply.approved_at = now
    reply.sent_email_id = msg.id
    threads.refresh_thread(db, original.thread_id)
    return msg


# ------------------------------------------------------------------ processing
def _replace_analysis(db: Session, email: models.Email, result: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Persist analysis, extraction, action items and deadlines (idempotent: safe for re-analysis)."""
    done_tasks = {a.task.strip().lower() for a in email.action_items if a.status == "completed"}
    done_deadlines = {(d.due_date, d.title.strip().lower()) for d in email.deadlines if d.is_completed}
    for old in (email.ai_analysis, email.extracted_info):
        if old is not None:
            db.delete(old)
    for old in list(email.action_items) + list(email.deadlines):
        db.delete(old)
    db.flush()

    uid = email.user_id
    db.add(models.AIAnalysis(
        email_id=email.id, user_id=uid, category=result["category"], intent=result["intent"], priority=result["priority"],
        priority_reason=result["priority_reason"], sentiment=result["sentiment"],
        sentiment_confidence=result.get("sentiment_confidence", 0.8), short_summary=result["short_summary"],
        detailed_summary=result["detailed_summary"], reply_required=bool(result["reply_required"]),
        action_required=bool(result["action_required"]), provider=meta["provider"], flags=result.get("flags") or None))
    info = result.get("extracted_info") or {}
    db.add(models.ExtractedInformation(email_id=email.id, user_id=uid, **{
        k: info.get(k) for k in ("customer_name", "company", "email_address", "phone_number", "order_number", "invoice_number",
                                 "product", "amount", "date", "deadline", "meeting_date", "location", "requested_action")}))
    for a in result.get("action_items", []):
        completed = a["task"].strip().lower() in done_tasks
        db.add(models.ActionItem(email_id=email.id, user_id=uid, task=a["task"], deadline_text=a.get("deadline_text"),
                                 due_date=a.get("due_date"), status="completed" if completed else "pending",
                                 completed_at=utcnow() if completed else None))
    for d in result.get("deadlines", []):
        db.add(models.Deadline(email_id=email.id, user_id=uid, title=d["title"], due_date=d["due_date"],
                               source_phrase=d.get("source_phrase"),
                               is_completed=(d["due_date"], d["title"].strip().lower()) in done_deadlines))

    # reply lifecycle: a reply already sent (or dismissed) is never re-opened by re-analysis
    if email.reply_status not in ("replied", "dismissed"):
        later_out = (db.query(models.Email).filter(models.Email.thread_id == email.thread_id, models.Email.is_outbound == True,  # noqa: E712
                                                   models.Email.received_at > email.received_at)
                     .order_by(models.Email.received_at.asc()).first()) if email.thread_id else None
        if later_out is not None and result["reply_required"]:
            email.reply_status, email.replied_at = "replied", later_out.received_at
        elif result["reply_required"]:
            email.reply_status = "pending"
        else:
            email.reply_status = "not_required"


def process_email(email_id: int, db: Optional[Session] = None, notify: bool = True) -> bool:
    """Analyse one email. Returns True on success. Failures are recorded on the row (status 'failed') and never raised."""
    own = db is None
    session = db or SessionLocal()
    try:
        email = session.get(models.Email, email_id)
        if email is None or email.is_outbound:
            return False
        email.processing_status = "processing"
        email.last_attempt_at = utcnow()
        email.retry_count = (email.retry_count or 0) + 1
        session.commit()

        categories = active_category_names(session)
        provider = llm_provider_override(session)
        context = threads.thread_context_text(session, email)
        result, meta = ai_engine.analyze_email(
            email.subject, email.body_plain, email.sender_email, email.sender_name, reference=email.received_at,
            categories=categories, thread_context=context, provider=provider)

        _replace_analysis(session, email, result, meta)
        email.processing_status, email.processing_error = "completed", None
        session.add(models.AILog(user_id=email.user_id, email_id=email.id, operation="analysis", provider=meta["provider"],
                                 model=meta.get("model"), success=True, fallback_used=bool(meta.get("fallback_used")),
                                 latency_ms=meta.get("latency_ms", 0), error=meta.get("error")))
        session.flush()
        if notify:
            notifications.notify_for_analysis(session, email, result)
        session.commit()
        return True
    except Exception as exc:
        log.exception("processing failed for email %s", email_id)
        session.rollback()
        try:
            email = session.get(models.Email, email_id)
            if email is not None:
                email.processing_status = "failed"
                email.processing_error = f"{type(exc).__name__}: {exc}"[:500]
                session.add(models.AILog(user_id=email.user_id, email_id=email.id, operation="analysis",
                                         provider="unknown", success=False, error=email.processing_error))
                session.commit()
        except Exception:
            session.rollback()
            log.exception("could not record failure for email %s", email_id)
        return False
    finally:
        if own:
            session.close()


def process_many(email_ids: Iterable[int], db: Optional[Session] = None, notify: bool = True) -> int:
    return sum(1 for i in list(email_ids) if process_email(i, db=db, notify=notify))


def enqueue(background_tasks, email_ids: List[int], db: Optional[Session] = None, notify: bool = True) -> str:
    """Schedule processing according to PROCESSING_MODE. Returns the mode actually used."""
    ids = list(email_ids)
    if not ids:
        return "none"
    mode = (settings.PROCESSING_MODE or "background").lower()
    if mode == "sync":
        process_many(ids, db=db, notify=notify)
        return "sync"
    if mode == "celery":
        try:
            from app.workers.tasks import process_email_task
            for i in ids:
                process_email_task.delay(i, notify)
            return "celery"
        except Exception:
            log.warning("Celery unavailable; falling back to in-process background task", exc_info=True)
    background_tasks.add_task(process_many, ids, None, notify)
    return "background"


def recover_interrupted(max_age_minutes: int = 2, session: Optional[Session] = None) -> int:
    """Called at startup: emails left 'queued'/'processing' by a crash/restart are processed again."""
    close_after = False
    if session is None:
        from app import database
        session_factory = getattr(database, "SessionLocal", SessionLocal)
        session = session_factory()
        close_after = True

    try:
        cutoff = utcnow() - timedelta(minutes=max_age_minutes)
        rows = (session.query(models.Email.id).filter(models.Email.is_outbound == False,  # noqa: E712
                                                      models.Email.processing_status.in_(["queued", "processing"]),
                                                      models.Email.retry_count < settings.MAX_PROCESSING_RETRIES,
                                                      (models.Email.last_attempt_at.is_(None)) | (models.Email.last_attempt_at <= cutoff))
                .limit(500).all())
        ids = [r[0] for r in rows]
    except Exception:
        ids = []
    finally:
        if close_after:
            session.close()
    if ids:
        threading.Thread(target=process_many, args=(ids, None, False), daemon=True, name="recover-emails").start()
    return len(ids)
