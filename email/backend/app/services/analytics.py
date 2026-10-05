"""Dashboard / analytics aggregation. Everything is computed from the signed-in user's own rows only."""
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.timeutil import utcnow

HEATMAP_SLOTS = [("12 AM", 0), ("4 AM", 4), ("8 AM", 8), ("12 PM", 12), ("4 PM", 16), ("8 PM", 20)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
URGENT_LEVELS = ("HIGH", "CRITICAL")


def _inbound(db: Session, user_id: int):
    """Base query: this user's received (not sent), non-deleted emails."""
    return db.query(models.Email).filter(
        models.Email.user_id == user_id,
        models.Email.is_outbound == False,  # noqa: E712
        models.Email.deleted_at.is_(None),
    )


def _analysed(db: Session, user_id: int):
    return _inbound(db, user_id).join(models.AIAnalysis, models.AIAnalysis.email_id == models.Email.id)


def _count(q) -> int:
    return q.count()


def _grouped(db: Session, user_id: int, column) -> Dict[str, int]:
    rows = (
        db.query(column, func.count(models.Email.id))
        .select_from(models.Email)
        .join(models.AIAnalysis, models.AIAnalysis.email_id == models.Email.id)
        .filter(models.Email.user_id == user_id, models.Email.is_outbound == False,  # noqa: E712
                models.Email.deleted_at.is_(None))
        .group_by(column)
        .all()
    )
    return {str(k): int(v) for k, v in rows}


def get_dashboard_metrics(db: Session, user_id: int) -> Dict[str, Any]:
    total = _count(_inbound(db, user_id))
    unread = _count(_inbound(db, user_id).filter(models.Email.is_read == False))  # noqa: E712
    category_dist = _grouped(db, user_id, models.AIAnalysis.category)

    replied_rows = (
        _inbound(db, user_id).filter(models.Email.replied_at.isnot(None))
        .with_entities(models.Email.received_at, models.Email.replied_at).all()
    )
    secs = [(rep - rec).total_seconds() for rec, rep in replied_rows if rec and rep and rep >= rec]
    avg_hours = round(sum(secs) / len(secs) / 3600.0, 2) if secs else 0.0

    now = utcnow()
    since = now - timedelta(days=30)
    day_counts: Counter = Counter()
    for (rec,) in _inbound(db, user_id).filter(models.Email.received_at >= since).with_entities(models.Email.received_at).all():
        if rec:
            day_counts[rec.date().isoformat()] += 1

    return {
        "total_emails": total,
        "unread_emails": unread,
        "urgent_emails": _count(_analysed(db, user_id).filter(models.AIAnalysis.priority.in_(URGENT_LEVELS))),
        "reply_required_emails": _count(_analysed(db, user_id).filter(
            models.AIAnalysis.reply_required == True,  # noqa: E712
            models.Email.reply_status != "replied")),
        "customer_emails": category_dist.get("Customer Complaint", 0),
        "sales_emails": category_dist.get("Sales Inquiry", 0),
        "support_emails": category_dist.get("Support Request", 0),
        "pending_actions": db.query(models.ActionItem).filter(
            models.ActionItem.user_id == user_id, models.ActionItem.status == "pending").count(),
        "avg_response_time_hours": avg_hours,
        "replied_count": len(secs),
        "complaint_count": category_dist.get("Customer Complaint", 0),
        "category_distribution": category_dist,
        "sentiment_distribution": _grouped(db, user_id, models.AIAnalysis.sentiment),
        "priority_distribution": _grouped(db, user_id, models.AIAnalysis.priority),
        "daily_volume": [{"date": d, "count": c} for d, c in sorted(day_counts.items())],
    }


def get_dashboard_extras(db: Session, user_id: int, days: int = 14) -> Dict[str, Any]:
    """Chart data: per-day activity, sentiment trend, weekday x time-of-day heatmap, SLA split."""
    now = utcnow()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    labels = [(start + timedelta(days=i)).date().isoformat() for i in range(days)]
    activity = {d: {"date": d, "total": 0, "critical": 0, "replied": 0} for d in labels}
    sentiment: Dict[str, Dict[str, int]] = {d: defaultdict(int) for d in labels}

    rows = (
        _inbound(db, user_id)
        .outerjoin(models.AIAnalysis, models.AIAnalysis.email_id == models.Email.id)
        .filter(models.Email.received_at >= start)
        .with_entities(models.Email.received_at, models.Email.reply_status,
                       models.AIAnalysis.priority, models.AIAnalysis.sentiment)
        .all()
    )
    for rec, reply_status, prio, sent in rows:
        key = rec.date().isoformat()
        if key not in activity:
            continue
        activity[key]["total"] += 1
        activity[key]["critical"] += 1 if prio in URGENT_LEVELS else 0
        activity[key]["replied"] += 1 if reply_status == "replied" else 0
        if sent:
            sentiment[key][sent] += 1

    heat_start = now - timedelta(days=90)
    grid = [[0] * len(HEATMAP_SLOTS) for _ in WEEKDAYS]
    for (rec,) in _inbound(db, user_id).filter(models.Email.received_at >= heat_start).with_entities(models.Email.received_at).all():
        if rec:
            slot = max(i for i, (_, h) in enumerate(HEATMAP_SLOTS) if rec.hour >= h)
            grid[rec.weekday()][slot] += 1

    pending_cut = now - timedelta(hours=24)
    sla = {
        "responded": _count(_inbound(db, user_id).filter(models.Email.reply_status == "replied")),
        "pending": _count(_inbound(db, user_id).filter(models.Email.reply_status == "pending", models.Email.received_at >= pending_cut)),
        "overdue": _count(_inbound(db, user_id).filter(models.Email.reply_status == "pending", models.Email.received_at < pending_cut)),
    }
    return {
        "daily_activity": [activity[d] for d in labels],
        "sentiment_trend": [{"date": d, **{k: sentiment[d].get(k, 0) for k in ("Positive", "Neutral", "Negative", "Angry", "Urgent")}} for d in labels],
        "activity_heatmap": {"days": WEEKDAYS, "slots": [s for s, _ in HEATMAP_SLOTS], "grid": grid},
        "sla": sla,
    }


def get_critical_queue(db: Session, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    rows = (
        _analysed(db, user_id)
        .filter(models.AIAnalysis.priority.in_(URGENT_LEVELS), models.Email.reply_status != "replied")
        .order_by(models.Email.received_at.desc()).limit(limit).all()
    )
    return [{
        "id": e.id, "subject": e.subject, "sender_name": e.sender_name, "received_at": e.received_at,
        "category": e.ai_analysis.category, "priority": e.ai_analysis.priority, "sentiment": e.ai_analysis.sentiment,
        "confidence": round(float(e.ai_analysis.sentiment_confidence or 0) * 100),
        "summary": e.ai_analysis.short_summary,
    } for e in rows]


def get_recent_ai_actions(db: Session, user_id: int, limit: int = 8) -> List[Dict[str, Any]]:
    logs = db.query(models.AILog).filter(models.AILog.user_id == user_id).order_by(models.AILog.created_at.desc()).limit(limit).all()
    subjects = {e.id: e.subject for e in db.query(models.Email.id, models.Email.subject).filter(
        models.Email.user_id == user_id, models.Email.id.in_([l.email_id for l in logs if l.email_id] or [0])).all()}
    return [{
        "id": l.id, "operation": l.operation, "provider": l.provider, "success": bool(l.success),
        "fallback_used": bool(l.fallback_used), "email_id": l.email_id,
        "subject": subjects.get(l.email_id), "created_at": l.created_at,
    } for l in logs]
