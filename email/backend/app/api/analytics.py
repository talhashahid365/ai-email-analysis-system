from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.api.emails import _format_email_item
from app.database import get_db
from app.services.analytics import (get_critical_queue, get_dashboard_extras, get_dashboard_metrics,
                                    get_recent_ai_actions)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=schemas.DashboardOverview)
def get_analytics_overview(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = get_dashboard_metrics(db, current_user.id)
    extras = get_dashboard_extras(db, current_user.id)
    recent_raw = (
        db.query(models.Email)
        .filter(models.Email.user_id == current_user.id, models.Email.is_outbound == False,  # noqa: E712
                models.Email.deleted_at.is_(None))
        .order_by(models.Email.received_at.desc()).limit(8).all()
    )

    urgent_raw = (
        db.query(models.Email)
        .join(models.AIAnalysis)
        .filter(
            models.Email.user_id == current_user.id,
            models.Email.is_outbound == False,
            models.Email.deleted_at.is_(None),
            models.AIAnalysis.priority.in_(["HIGH", "CRITICAL"]),
        )
        .order_by(models.Email.received_at.desc())
        .limit(5)
        .all()
    )

    recent_urgent = [_format_email_item(e) for e in urgent_raw]

    recent_actions = (
        db.query(models.ActionItem)
        .filter(models.ActionItem.user_id == current_user.id, models.ActionItem.status == "pending")
        .order_by(models.ActionItem.created_at.desc())
        .limit(5)
        .all()
    )

    upcoming_deadlines = (
        db.query(models.Deadline)
        .filter(models.Deadline.user_id == current_user.id, models.Deadline.is_completed == False)
        .order_by(models.Deadline.due_date.asc())
        .limit(5)
        .all()
    )

    return {
        "total_emails": stats["total_emails"],
        "unread_emails": stats["unread_emails"],
        "urgent_emails": stats["urgent_emails"],
        "reply_required_emails": stats["reply_required_emails"],
        "customer_emails": stats["customer_emails"],
        "sales_emails": stats["sales_emails"],
        "support_emails": stats["support_emails"],
        "pending_actions": stats["pending_actions"],
        "avg_response_time_hours": stats["avg_response_time_hours"],
        "category_distribution": stats["category_distribution"],
        "sentiment_distribution": stats["sentiment_distribution"],
        "priority_distribution": stats["priority_distribution"],
        "daily_volume": stats["daily_volume"],
        "replied_count": stats["replied_count"],
        "complaint_count": stats["complaint_count"],
        **extras,
        "critical_queue": get_critical_queue(db, current_user.id),
        "recent_emails": [_format_email_item(e) for e in recent_raw],
        "recent_ai_actions": get_recent_ai_actions(db, current_user.id),
        "recent_urgent_emails": recent_urgent,
        "recent_actions": recent_actions,
        "upcoming_deadlines": upcoming_deadlines,
    }
