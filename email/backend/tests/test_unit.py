import pytest
from unittest.mock import patch
from app.services.email_parser import clean_html_text, parse_eml_content
from app.services import ai_engine, pipeline, smart_reply, rag_assistant, threads, llm


def test_clean_html_text():
    html = "<html><body><h1>Refund Request</h1><p>Product arrived damaged.<br>Please replace it!</p></body></html>"
    cleaned = clean_html_text(html)
    assert "Refund Request" in cleaned
    assert "Product arrived damaged." in cleaned


def test_parse_eml_content():
    raw_eml = (
        b"From: John Doe <john@example.com>\n"
        b"To: support@company.com\n"
        b"Subject: Test Subject\n"
        b"Content-Type: text/plain; charset=utf-8\n\n"
        b"This is a test email body."
    )
    parsed = parse_eml_content(raw_eml)
    assert parsed["sender_email"] == "john@example.com"
    assert parsed["sender_name"] == "John Doe"
    assert parsed["subject"] == "Test Subject"
    assert "test email body" in parsed["body_plain"]


def test_heuristic_classification():
    subject = "Refund request for order #1029"
    body = "The product arrived damaged. I want a refund within 24 hours."
    analysis, meta = ai_engine.analyze_email(subject, body, "sarah@example.com", "Sarah Ahmed")

    assert analysis["category"] == "Customer Complaint"
    assert analysis["priority"] in ["HIGH", "CRITICAL"]
    assert analysis["sentiment"] in ["Negative", "Angry", "Urgent"]
    assert analysis["reply_required"] is True
    assert meta["provider"] == "heuristic"


def test_llm_provider_resolution_and_mock_complete():
    # Test fallback when no key is set
    assert llm.resolve_provider("heuristic") is None

    # Test LLM complete path using mock API response
    mock_json = '{"category": "Customer Complaint", "priority": "HIGH", "sentiment": "Angry", "short_summary": "Refund requested.", "detailed_summary": "Customer requested full refund.", "reply_required": true, "action_required": true}'
    with patch("app.services.llm._post", return_value={"candidates": [{"content": {"parts": [{"text": mock_json}]}}]}):
        with patch("app.services.llm._key_for", return_value="mock_key_xyz"):
            res, info = llm.complete_json("system prompt", "user prompt", provider="gemini")
            assert res["category"] == "Customer Complaint"
            assert info.provider == "gemini"


def test_smart_reply_generation(db):
    draft, meta = smart_reply.generate_smart_reply(
        db=db,
        tone="Professional",
        subject="Refund request for order #1029",
        body="I received the wrong item.",
        sender_name="Sarah",
        sender_email="sarah@example.com",
        thread_history=[],
        category="Customer Complaint",
        extracted={"order_number": "1029"},
    )
    assert "Sarah" in draft
    assert len(draft) > 20
    assert meta["provider"] in ["heuristic", "gemini", "openai", "anthropic"]


def test_rag_query_filter_extraction():
    filters = rag_assistant.extract_query_filters("Show all urgent customer complaints")
    assert "HIGH" in filters.priorities or "CRITICAL" in filters.priorities
    assert "Customer Complaint" in filters.categories


# ── Permissions module tests ──────────────────────────────────────────────────
class TestPermissions:
    """Verify the central permissions module works correctly."""

    def _user(self, role: str):
        from unittest.mock import MagicMock
        u = MagicMock()
        u.role = role
        u.id = 1
        return u

    def test_user_can_read_email(self):
        from app.permissions import can, Action
        assert can(self._user('user'), Action.EMAIL_READ) is True

    def test_user_cannot_admin(self):
        from app.permissions import can, Action
        assert can(self._user('user'), Action.ADMIN_USERS) is False

    def test_manager_gets_advanced_analytics(self):
        from app.permissions import can, Action
        assert can(self._user('manager'), Action.ANALYTICS_ADVANCED) is True

    def test_manager_cannot_admin_settings(self):
        from app.permissions import can, Action
        assert can(self._user('manager'), Action.ADMIN_SETTINGS) is False

    def test_admin_can_do_everything(self):
        from app.permissions import can, Action
        admin = self._user('admin')
        for action in Action:
            assert can(admin, action) is True, f'Admin must be able to: {action}'

    def test_require_raises_403(self):
        from app.permissions import require, Action
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            require(self._user('user'), Action.ADMIN_USERS)
        assert exc.value.status_code == 403

    def test_assert_owns_resource_raises_404_for_other_user(self):
        from app.permissions import assert_owns_resource
        from fastapi import HTTPException
        user = self._user('user')
        user.id = 1
        with pytest.raises(HTTPException) as exc:
            assert_owns_resource(resource_user_id=99, current_user=user)
        assert exc.value.status_code == 404

    def test_admin_bypasses_ownership_check(self):
        from app.permissions import assert_owns_resource
        admin = self._user('admin')
        admin.id = 1
        # Must not raise — admin can access any resource
        assert_owns_resource(resource_user_id=999, current_user=admin)


# ── Rate limiter tests ────────────────────────────────────────────────────────
class TestRateLimiter:
    def setup_method(self):
        from app.ratelimit import reset_rate_limits
        reset_rate_limits()

    def test_reset_does_not_raise(self):
        from app.ratelimit import reset_rate_limits
        reset_rate_limits()

    def test_memory_allows_under_limit(self):
        from app.ratelimit import _check_memory
        allowed, retry = _check_memory(('scope_a', '1.2.3.4'), limit=5, window_seconds=60)
        assert allowed is True
        assert retry == 0

    def test_memory_blocks_over_limit(self):
        from app.ratelimit import _check_memory
        key = ('scope_b', '5.6.7.8')
        for _ in range(3):
            _check_memory(key, limit=3, window_seconds=60)
        allowed, retry = _check_memory(key, limit=3, window_seconds=60)
        assert allowed is False
        assert retry > 0
