"""Initial schema migration — creates all tables.

Revision ID: 001
Revises:
Create Date: 2026-09-30

Generated from models.py. To regenerate after model changes, run:
    alembic revision --autogenerate -m "describe your change"
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("job_title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    # ── revoked_tokens ─────────────────────────────────────────────────────────
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"], unique=True)

    # ── categories ────────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True, server_default="#64748b"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── system_settings ───────────────────────────────────────────────────────
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    # ── senders ───────────────────────────────────────────────────────────────
    op.create_table(
        "senders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("email_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "email", name="uq_sender_user_email"),
    )
    op.create_index("ix_senders_email", "senders", ["email"])
    op.create_index("ix_senders_user_id", "senders", ["user_id"])

    # ── email_threads ─────────────────────────────────────────────────────────
    op.create_table(
        "email_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("thread_key", sa.String(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("unread_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_threads_id", "email_threads", ["id"])
    op.create_index("ix_email_threads_last_message_at", "email_threads", ["last_message_at"])
    op.create_index("ix_email_threads_thread_key", "email_threads", ["thread_key"])
    op.create_index("ix_email_threads_user_id", "email_threads", ["user_id"])

    # ── emails ────────────────────────────────────────────────────────────────
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("sender_email", sa.String(), nullable=False),
        sa.Column("sender_name", sa.String(), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body_plain", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("in_reply_to", sa.String(), nullable=True),
        sa.Column("is_outbound", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("reply_status", sa.String(), nullable=True, server_default="not_required"),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("is_starred", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("is_archived", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("processing_status", sa.String(), nullable=True, server_default="queued"),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("raw_eml_path", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["senders.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "message_id", name="uq_email_user_message_id"),
    )
    op.create_index("ix_emails_content_hash", "emails", ["content_hash"])
    op.create_index("ix_emails_id", "emails", ["id"])
    op.create_index("ix_emails_is_outbound", "emails", ["is_outbound"])
    op.create_index("ix_emails_message_id", "emails", ["message_id"])
    op.create_index("ix_emails_processing_status", "emails", ["processing_status"])
    op.create_index("ix_emails_received_at", "emails", ["received_at"])
    op.create_index("ix_emails_reply_status", "emails", ["reply_status"])
    op.create_index("ix_emails_sender_email", "emails", ["sender_email"])
    op.create_index("ix_emails_subject", "emails", ["subject"])
    op.create_index("ix_emails_user_id", "emails", ["user_id"])

    # ── ai_analyses ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("priority_reason", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("sentiment_confidence", sa.Float(), nullable=True, server_default="0.9"),
        sa.Column("short_summary", sa.Text(), nullable=False),
        sa.Column("detailed_summary", sa.Text(), nullable=False),
        sa.Column("reply_required", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("action_required", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("provider", sa.String(), nullable=True, server_default="heuristic"),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_id"),
    )
    op.create_index("ix_ai_analyses_action_required", "ai_analyses", ["action_required"])
    op.create_index("ix_ai_analyses_category", "ai_analyses", ["category"])
    op.create_index("ix_ai_analyses_email_id", "ai_analyses", ["email_id"])
    op.create_index("ix_ai_analyses_id", "ai_analyses", ["id"])
    op.create_index("ix_ai_analyses_priority", "ai_analyses", ["priority"])
    op.create_index("ix_ai_analyses_reply_required", "ai_analyses", ["reply_required"])
    op.create_index("ix_ai_analyses_sentiment", "ai_analyses", ["sentiment"])
    op.create_index("ix_ai_analyses_user_id", "ai_analyses", ["user_id"])

    # ── extracted_information ─────────────────────────────────────────────────
    op.create_table(
        "extracted_information",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("email_address", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("order_number", sa.String(), nullable=True),
        sa.Column("invoice_number", sa.String(), nullable=True),
        sa.Column("product", sa.String(), nullable=True),
        sa.Column("amount", sa.String(), nullable=True),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("deadline", sa.String(), nullable=True),
        sa.Column("meeting_date", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("requested_action", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_id"),
    )
    op.create_index("ix_extracted_information_email_id", "extracted_information", ["email_id"])
    op.create_index("ix_extracted_information_id", "extracted_information", ["id"])
    op.create_index("ix_extracted_information_invoice_number", "extracted_information", ["invoice_number"])
    op.create_index("ix_extracted_information_order_number", "extracted_information", ["order_number"])
    op.create_index("ix_extracted_information_user_id", "extracted_information", ["user_id"])

    # ── action_items ──────────────────────────────────────────────────────────
    op.create_table(
        "action_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("deadline_text", sa.String(), nullable=True),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_items_email_id", "action_items", ["email_id"])
    op.create_index("ix_action_items_id", "action_items", ["id"])
    op.create_index("ix_action_items_user_id", "action_items", ["user_id"])

    # ── deadlines ─────────────────────────────────────────────────────────────
    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_date", sa.String(), nullable=False),
        sa.Column("source_phrase", sa.String(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deadlines_email_id", "deadlines", ["email_id"])
    op.create_index("ix_deadlines_id", "deadlines", ["id"])
    op.create_index("ix_deadlines_user_id", "deadlines", ["user_id"])

    # ── ai_replies ────────────────────────────────────────────────────────────
    op.create_table(
        "ai_replies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("selected_tone", sa.String(), nullable=True, server_default="Professional"),
        sa.Column("suggested_body", sa.Text(), nullable=False),
        sa.Column("edited_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="draft"),
        sa.Column("provider", sa.String(), nullable=True, server_default="heuristic"),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("sent_email_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_replies_email_id", "ai_replies", ["email_id"])
    op.create_index("ix_ai_replies_id", "ai_replies", ["id"])
    op.create_index("ix_ai_replies_user_id", "ai_replies", ["user_id"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_dedupe_key", "notifications", ["dedupe_key"])
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # ── notification_preferences ──────────────────────────────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("urgent_email", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("customer_complaint", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("reply_required", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("upcoming_deadline", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("action_item", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("ai_completed", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── ai_conversations ──────────────────────────────────────────────────────
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True, server_default="New Conversation"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_id", "ai_conversations", ["id"])
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    # ── ai_messages ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("cited_email_ids", sa.JSON(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_index("ix_ai_messages_id", "ai_messages", ["id"])

    # ── ai_logs ───────────────────────────────────────────────────────────────
    op.create_table(
        "ai_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("fallback_used", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("latency_ms", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_logs_created_at", "ai_logs", ["created_at"])
    op.create_index("ix_ai_logs_email_id", "ai_logs", ["email_id"])
    op.create_index("ix_ai_logs_user_id", "ai_logs", ["user_id"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ai_logs")
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
    op.drop_table("ai_replies")
    op.drop_table("deadlines")
    op.drop_table("action_items")
    op.drop_table("extracted_information")
    op.drop_table("ai_analyses")
    op.drop_table("emails")
    op.drop_table("email_threads")
    op.drop_table("senders")
    op.drop_table("system_settings")
    op.drop_table("categories")
    op.drop_table("revoked_tokens")
    op.drop_table("users")
