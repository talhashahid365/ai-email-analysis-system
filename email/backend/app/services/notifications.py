"""Notification creation. Respects each user's NotificationPreference; one 'attention' notification per email."""
from datetime import date, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models
from app.config import settings

# type -> NotificationPreference column (None = always delivered)
TYPE_PREFERENCE = {
    "urgent_email": "urgent_email",
    "customer_complaint": "customer_complaint",
    "reply_required": "reply_required",
    "upcoming_deadline": "upcoming_deadline",
    "action_item": "action_item",
    "ai_completed": "ai_completed",
    "system": None,
}
NOTIFICATION_TYPES = list(TYPE_PREFERENCE)
PREFERENCE_FIELDS = [v for v in TYPE_PREFERENCE.values() if v]


def get_preferences(db: Session, user_id: int) -> models.NotificationPreference:
    prefs = db.query(models.NotificationPreference).filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = models.NotificationPreference(user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


def preferences_dict(prefs: models.NotificationPreference) -> Dict[str, bool]:
    return {f: bool(getattr(prefs, f)) for f in PREFERENCE_FIELDS}


def notify(db: Session, user_id: int, type_: str, title: str, message: str, email_id: Optional[int] = None,
           dedupe_key: Optional[str] = None) -> Optional[models.Notification]:
    """Create a notification unless the user disabled this type or the dedupe key already exists. Does not commit."""
    if type_ not in TYPE_PREFERENCE:
        raise ValueError(f"Unknown notification type {type_}")
    pref_field = TYPE_PREFERENCE[type_]
    if pref_field and not getattr(get_preferences(db, user_id), pref_field):
        return None
    if dedupe_key and db.query(models.Notification.id).filter_by(user_id=user_id, dedupe_key=dedupe_key).first():
        return None
    n = models.Notification(user_id=user_id, email_id=email_id, type=type_, title=title[:200], message=message[:1000],
                            dedupe_key=dedupe_key)
    db.add(n)
    db.flush()
    return n


def notify_for_analysis(db: Session, email: models.Email, analysis: Dict[str, Any]) -> None:
    """Pick the single most relevant alert for a freshly analysed email, then the optional 'AI completed' note."""
    if email.is_outbound or analysis["category"] == "Spam":
        return
    summary = f"From {email.sender_name}: {analysis['short_summary']}"
    key = f"analysis:{email.id}"
    if analysis["priority"] in ("HIGH", "CRITICAL"):
        label = "Critical" if analysis["priority"] == "CRITICAL" else "High-priority"
        notify(db, email.user_id, "urgent_email", f"{label} email: {email.subject}", summary, email.id, key)
    elif analysis["category"] == "Customer Complaint":
        notify(db, email.user_id, "customer_complaint", f"Customer complaint: {email.subject}", summary, email.id, key)
    elif analysis["reply_required"]:
        notify(db, email.user_id, "reply_required", f"Reply needed: {email.subject}", summary, email.id, key)
    elif analysis["action_items"]:
        notify(db, email.user_id, "action_item", f"New action item: {email.subject}",
               analysis["action_items"][0]["task"], email.id, key)
    notify(db, email.user_id, "ai_completed", f"Analysis complete: {email.subject}",
           f"{analysis['category']} · {analysis['priority']} priority · {analysis['sentiment']}", email.id,
           f"done:{email.id}:{email.retry_count or 0}")


def check_upcoming_deadlines(db: Session, user_id: int, today: Optional[date] = None) -> int:
    """Create 'upcoming_deadline' notifications for open deadlines due within DEADLINE_NOTICE_DAYS (or overdue)."""
    today = today or date.today()
    horizon = (today + timedelta(days=settings.DEADLINE_NOTICE_DAYS)).isoformat()
    rows = (db.query(models.Deadline).filter(models.Deadline.user_id == user_id, models.Deadline.is_completed == False,  # noqa: E712
                                             models.Deadline.due_date <= horizon).all())
    created = 0
    for d in rows:
        overdue = d.due_date < today.isoformat()
        when = "was due" if overdue else ("is due today" if d.due_date == today.isoformat() else "is due")
        n = notify(db, user_id, "upcoming_deadline", f"Deadline {'overdue' if overdue else 'approaching'}: {d.title[:80]}",
                   f"{d.title} {when} {d.due_date}" if when != "is due today" else f"{d.title} is due today ({d.due_date})",
                   d.email_id, f"deadline:{d.id}:{d.due_date}")
        created += 1 if n else 0
    if created:
        db.commit()
    return created


def check_all_deadlines(db: Session, today: Optional[date] = None) -> int:
    """Run check_upcoming_deadlines for every user that has an open deadline. Safe to call repeatedly (deduplicated)."""
    user_ids = [r[0] for r in db.query(models.Deadline.user_id).filter(models.Deadline.is_completed == False).distinct().all()]  # noqa: E712
    return sum(check_upcoming_deadlines(db, uid, today) for uid in user_ids)
