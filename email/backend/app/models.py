from sqlalchemy import (Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database import Base
from app.timeutil import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # user | manager | admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)  # access tokens issued before this are rejected

    emails = relationship("Email", back_populates="owner", cascade="all, delete-orphan")
    threads = relationship("EmailThread", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="owner", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="owner", cascade="all, delete-orphan")


class RevokedToken(Base):
    """Denylist of logged-out access tokens (by jti)."""
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, default="#64748b")
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Sender(Base):
    __tablename__ = "senders"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_sender_user_email"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    email_count = Column(Integer, default=0)
    first_seen_at = Column(DateTime, default=utcnow)
    last_seen_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class EmailThread(Base):
    __tablename__ = "email_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    thread_key = Column(String, nullable=False, index=True)
    last_message_at = Column(DateTime, default=utcnow, index=True)
    snippet = Column(Text, nullable=True)
    unread_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="threads")
    messages = relationship("Email", back_populates="thread", cascade="all, delete-orphan",
                            order_by="Email.received_at")


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_email_user_message_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(Integer, ForeignKey("email_threads.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("senders.id"), nullable=True)

    sender_email = Column(String, nullable=False, index=True)
    sender_name = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False, index=True)
    body_plain = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)
    received_at = Column(DateTime, default=utcnow, index=True)
    message_id = Column(String, nullable=True, index=True)
    in_reply_to = Column(String, nullable=True)
    is_outbound = Column(Boolean, default=False, index=True)  # message written by the mailbox owner
    content_hash = Column(String, nullable=True, index=True)  # sender + normalised subject + body, for duplicate detection
    # Reply lifecycle: not_required | pending | replied | dismissed
    reply_status = Column(String, default="not_required", index=True)
    replied_at = Column(DateTime, nullable=True)

    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True, index=True)  # soft delete — set to delete, filter in queries

    processing_status = Column(String, default="queued", index=True)  # queued|processing|completed|failed
    processing_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    raw_eml_path = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="emails")
    thread = relationship("EmailThread", back_populates="messages")
    sender = relationship("Sender")
    ai_analysis = relationship("AIAnalysis", back_populates="email", uselist=False, cascade="all, delete-orphan")
    extracted_info = relationship("ExtractedInformation", back_populates="email", uselist=False,
                                  cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="email", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="email", cascade="all, delete-orphan")
    ai_replies = relationship("AIReply", back_populates="email", cascade="all, delete-orphan",
                              order_by="AIReply.id")


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    category = Column(String, nullable=False, index=True)
    intent = Column(String, nullable=False)
    priority = Column(String, nullable=False, index=True)
    priority_reason = Column(Text, nullable=False)
    sentiment = Column(String, nullable=False, index=True)
    sentiment_confidence = Column(Float, default=0.9)
    short_summary = Column(Text, nullable=False)
    detailed_summary = Column(Text, nullable=False)
    reply_required = Column(Boolean, default=False, index=True)
    action_required = Column(Boolean, default=False, index=True)
    provider = Column(String, default="heuristic")
    flags = Column(JSON, nullable=True)  # e.g. ["prompt_injection_suspected"]
    processed_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    email = relationship("Email", back_populates="ai_analysis")


class ExtractedInformation(Base):
    __tablename__ = "extracted_information"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    customer_name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    email_address = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    order_number = Column(String, nullable=True, index=True)
    invoice_number = Column(String, nullable=True, index=True)
    product = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    date = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    meeting_date = Column(String, nullable=True)
    location = Column(String, nullable=True)
    requested_action = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    email = relationship("Email", back_populates="extracted_info")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task = Column(Text, nullable=False)
    deadline_text = Column(String, nullable=True)
    due_date = Column(String, nullable=True)  # ISO date when the deadline phrase could be resolved
    status = Column(String, default="pending")  # pending | completed
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)

    email = relationship("Email", back_populates="action_items")


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_date = Column(String, nullable=False)  # ISO YYYY-MM-DD
    source_phrase = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    email = relationship("Email", back_populates="deadlines")


class AIReply(Base):
    __tablename__ = "ai_replies"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    selected_tone = Column(String, default="Professional")
    suggested_body = Column(Text, nullable=False)
    edited_body = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft | approved | rejected | superseded
    provider = Column(String, default="heuristic")
    model = Column(String, nullable=True)
    fallback_used = Column(Boolean, default=False)
    custom_instructions = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)
    sent_email_id = Column(Integer, nullable=True)  # outbound Email row created on approval

    email = relationship("Email", back_populates="ai_replies")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=True)
    type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    dedupe_key = Column(String, nullable=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    urgent_email = Column(Boolean, default=True)
    customer_complaint = Column(Boolean, default=True)
    reply_required = Column(Boolean, default=True)
    upcoming_deadline = Column(Boolean, default=True)
    action_item = Column(Boolean, default=True)
    ai_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="AIMessage.id")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False, index=True)
    sender = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    cited_email_ids = Column(JSON, nullable=True)
    filters = Column(JSON, nullable=True)  # structured filters the assistant applied (used for follow-up questions)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    conversation = relationship("AIConversation", back_populates="messages")


class AILog(Base):
    """One row per LLM / analysis call – powers the admin AI usage and logs screens."""
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email_id = Column(Integer, nullable=True, index=True)
    operation = Column(String, nullable=False)  # analysis | reply | assistant
    provider = Column(String, nullable=False)
    model = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    fallback_used = Column(Boolean, default=False)
    latency_ms = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    resource = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
