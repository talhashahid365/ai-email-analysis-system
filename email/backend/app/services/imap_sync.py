"""Pull real incoming mail (e.g. a Gmail inbox) into the app through IMAP.

Messages already imported are skipped by the pipeline's duplicate check (Message-ID / content hash), so syncing
repeatedly is safe. Mail sent BY the mailbox owner is ignored so your own replies do not show up as new queries.
"""
import imaplib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services import mailnet, pipeline
from app.services.email_parser import parse_eml_content

log = logging.getLogger("app.imap_sync")


class ImapNotConfigured(RuntimeError):
    pass


class ImapError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASSWORD)


def fetch_raw_messages(limit: int) -> List[bytes]:
    """Newest `limit` messages of the configured folder, read without changing their read/unread flag in the mailbox."""
    if not configured():
        raise ImapNotConfigured("IMAP is not configured. Set IMAP_HOST, IMAP_USER and IMAP_PASSWORD in backend/.env")
    try:
        conn = mailnet.connect_imap()
        try:
            conn.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
            typ, _ = conn.select(settings.IMAP_FOLDER, readonly=True)
            if typ != "OK":
                raise ImapError(f"Could not open folder '{settings.IMAP_FOLDER}'")
            since = (datetime.now(timezone.utc) - timedelta(days=max(1, settings.IMAP_SINCE_DAYS))).strftime("%d-%b-%Y")
            typ, data = conn.search(None, "SINCE", since)
            ids = (data[0] or b"").split()[-limit:] if typ == "OK" else []
            out = []
            for mid in reversed(ids):  # newest first
                typ, msg_data = conn.fetch(mid, "(BODY.PEEK[])")
                if typ == "OK" and msg_data and isinstance(msg_data[0], tuple):
                    out.append(msg_data[0][1])
            return out
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    except imaplib.IMAP4.error as exc:
        raise ImapError(f"IMAP login/read failed: {str(exc)[:200]} (Gmail needs IMAP enabled and an App Password)") from exc
    except OSError as exc:
        raise ImapError(f"Could not reach {settings.IMAP_HOST}: {type(exc).__name__}") from exc


def sync_mailbox(db: Session, user: models.User, background_tasks) -> Dict[str, Any]:
    own = {settings.IMAP_USER.lower(), (user.email or "").lower()}
    stats = {"checked": 0, "imported": 0, "duplicates": 0, "skipped_own": 0, "errors": 0}
    new_ids: List[int] = []
    for raw in fetch_raw_messages(max(1, settings.IMAP_MAX_FETCH)):
        stats["checked"] += 1
        try:
            parsed = parse_eml_content(raw)
            if (parsed.get("sender_email") or "").lower() in own:
                stats["skipped_own"] += 1
                continue
            res = pipeline.ingest_email(db, user, parsed)
        except pipeline.IngestError:
            stats["errors"] += 1
            continue
        except Exception:
            log.exception("could not import one message")
            db.rollback()
            stats["errors"] += 1
            continue
        if res.duplicate:
            stats["duplicates"] += 1
        else:
            stats["imported"] += 1
            new_ids.append(res.email.id)
    pipeline.enqueue(background_tasks, new_ids, db=db)
    return stats


def find_owner(db: Session):
    """Website account that automatic sync files the incoming mail under."""
    q = db.query(models.User).filter(models.User.is_active == True)  # noqa: E712
    for addr in (settings.IMAP_OWNER_EMAIL, settings.IMAP_USER):
        if addr:
            u = q.filter(models.User.email == addr.strip().lower()).first()
            if u:
                return u
    return q.filter(models.User.role == "admin").order_by(models.User.id).first()


def poll_once() -> Dict[str, Any]:
    """One automatic sync run (called by the background poller). New mail is analysed right away."""
    from app import database
    if not configured():
        return {}
    db = getattr(database, "SessionLocal")()
    try:
        owner = find_owner(db)
        if owner is None:
            log.warning("IMAP auto-sync: no admin account exists yet; sign up on the website first")
            return {}

        class _Inline:  # analyse immediately in this thread instead of scheduling a request background task
            def add_task(self, fn, *a, **k):
                fn(*a, **k)

        return sync_mailbox(db, owner, _Inline())
    finally:
        db.close()
