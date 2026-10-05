"""Startup helpers: default categories and recovery of emails whose processing was interrupted."""
from sqlalchemy.orm import Session

from app import models
from app.services.ai_engine import DEFAULT_CATEGORIES

CATEGORY_META = {
    "Sales Inquiry": ("Prospects asking about pricing, demos or partnerships", "#2563eb"),
    "Customer Complaint": ("Unhappy customers: refunds, damaged goods, poor service", "#dc2626"),
    "Support Request": ("Technical help, bugs, how-to questions", "#7c3aed"),
    "Meeting Request": ("Scheduling and rescheduling", "#0891b2"),
    "Invoice / Payment": ("Invoices, payment notices, receipts", "#d97706"),
    "Job Application": ("Candidates applying for roles", "#059669"),
    "General Information": ("Newsletters, announcements, FYI messages", "#64748b"),
    "Spam": ("Unsolicited promotions and phishing", "#9ca3af"),
    "Urgent": ("Time-critical escalations and incidents", "#b91c1c"),
    "Other": ("Anything that fits no other category", "#475569"),
}


def seed_defaults(db: Session) -> int:
    """Insert missing system categories. Idempotent. Returns number created."""
    existing = {c.name for c in db.query(models.Category).all()}
    created = 0
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            desc, color = CATEGORY_META.get(name, (None, "#64748b"))
            db.add(models.Category(name=name, description=desc, color=color, is_system=True, is_active=True))
            created += 1
    if created:
        db.commit()
    return created


def active_category_names(db: Session):
    names = [c.name for c in db.query(models.Category).filter(models.Category.is_active == True).order_by(models.Category.id)]  # noqa: E712
    if "Other" not in names:
        names.append("Other")  # the engine always needs a catch-all
    return names or list(DEFAULT_CATEGORIES)
