"""Duplicate detection and thread grouping.

Thread matching order:
 1. `In-Reply-To` points at a stored message  -> that message's thread
 2. a stored message names *this* message in its In-Reply-To (out-of-order arrival)
 3. same normalised subject, within THREAD_MATCH_DAYS, and the same counterpart address (never merge strangers
    who merely share a generic subject like "Hello")
 otherwise a new thread is created.
"""
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.search import preview
from app.services.text_utils import normalize_subject, split_quoted
from app.timeutil import utcnow

Email, EmailThread = models.Email, models.EmailThread


def compute_content_hash(sender_email: str, subject: str, body: str) -> str:
    norm_body = re.sub(r"\s+", " ", split_quoted(body or "")[0]).strip().lower()[:5000]
    raw = f"{(sender_email or '').strip().lower()}|{normalize_subject(subject)}|{norm_body}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def find_duplicate(db: Session, user_id: int, message_id: Optional[str], content_hash: str) -> Optional[models.Email]:
    if message_id:
        hit = db.query(Email).filter(Email.user_id == user_id, Email.message_id == message_id).first()
        if hit:
            return hit
    return db.query(Email).filter(Email.user_id == user_id, Email.content_hash == content_hash).first()


def find_thread(db: Session, user_id: int, subject: str, message_id: Optional[str], in_reply_to: Optional[str],
                counterpart: str, received_at: datetime) -> Optional[models.EmailThread]:
    if in_reply_to:
        parent = db.query(Email).filter(Email.user_id == user_id, Email.message_id == in_reply_to,
                                        Email.thread_id.isnot(None)).first()
        if parent:
            return db.get(EmailThread, parent.thread_id)
    if message_id:
        child = db.query(Email).filter(Email.user_id == user_id, Email.in_reply_to == message_id,
                                       Email.thread_id.isnot(None)).first()
        if child:
            return db.get(EmailThread, child.thread_id)
    key = normalize_subject(subject)
    if not key:
        return None
    since = received_at - timedelta(days=settings.THREAD_MATCH_DAYS)
    candidates = (db.query(EmailThread).filter(EmailThread.user_id == user_id, EmailThread.thread_key == key,
                                               EmailThread.last_message_at >= since)
                  .order_by(EmailThread.last_message_at.desc()).limit(10).all())
    for t in candidates:
        hit = db.query(Email.id).filter(Email.thread_id == t.id,
                                        or_(Email.sender_email == counterpart, Email.recipient_email == counterpart)).first()
        if hit:
            return t
    return None


def find_or_create_thread(db: Session, user_id: int, subject: str, message_id: Optional[str], in_reply_to: Optional[str],
                          counterpart: str, received_at: datetime) -> models.EmailThread:
    thread = find_thread(db, user_id, subject, message_id, in_reply_to, counterpart, received_at)
    if thread is None:
        thread = EmailThread(user_id=user_id, subject=(subject or "(no subject)")[:500],
                             thread_key=normalize_subject(subject) or "(no subject)", last_message_at=received_at)
        db.add(thread)
        db.flush()
    return thread


def refresh_thread(db: Session, thread_id: Optional[int]) -> None:
    """Recompute last_message_at / snippet / unread_count from the messages. Does not commit."""
    if thread_id is None:
        return
    thread = db.get(EmailThread, thread_id)
    if thread is None:
        return
    msgs = db.query(Email).filter(Email.thread_id == thread_id).order_by(Email.received_at.desc(), Email.id.desc()).all()
    if not msgs:
        db.delete(thread)
        return
    thread.last_message_at = msgs[0].received_at
    thread.snippet = preview(split_quoted(msgs[0].body_plain)[0], 160)
    thread.unread_count = sum(1 for m in msgs if not m.is_outbound and not m.is_read)


def thread_history(db: Session, email: models.Email, limit: int = 6, per_message_chars: int = 700) -> List[Dict[str, str]]:
    """Messages that precede `email` in its thread, oldest first, quoted text stripped.
    role is 'you' for messages the mailbox owner sent, else 'them'."""
    if not email.thread_id:
        return []
    prior = (db.query(Email).filter(Email.thread_id == email.thread_id, Email.user_id == email.user_id, Email.id != email.id,
                                    or_(Email.received_at < email.received_at,
                                        (Email.received_at == email.received_at) & (Email.id < email.id)))
             .order_by(Email.received_at.desc(), Email.id.desc()).limit(limit).all())
    out = []
    for m in reversed(prior):
        body = re.sub(r"\n{3,}", "\n\n", split_quoted(m.body_plain)[0]).strip()
        out.append({"role": "you" if m.is_outbound else "them", "name": m.sender_name,
                    "date": (m.received_at or utcnow()).strftime("%Y-%m-%d %H:%M"), "subject": m.subject,
                    "body": body[:per_message_chars]})
    return out


def thread_context_text(db: Session, email: models.Email, limit: int = 5, max_chars: int = 3000) -> str:
    lines = [f"[{m['date']}] {'You' if m['role'] == 'you' else m['name']}: {m['body']}" for m in thread_history(db, email, limit)]
    return "\n\n".join(lines)[:max_chars]
