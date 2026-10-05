from app import models
from app.timeutil import utcnow


def _h(u):
    return {"Authorization": f"Bearer {u['token']}"}


def _seed(db, owner):
    db.add_all([
        models.Email(user_id=owner.id, sender_name="S", sender_email="s@x.com", recipient_email="r@x.com",
                     subject="secret subject", body_plain="b", processing_status="failed",
                     processing_error="provider timeout", retry_count=2, received_at=utcnow()),
        models.Email(user_id=owner.id, sender_name="S", sender_email="s@x.com", recipient_email="r@x.com",
                     subject="ok", body_plain="b", processing_status="completed", received_at=utcnow()),
    ])
    db.add_all([
        models.AILog(operation="analysis", provider="heuristic", success=True, fallback_used=False, latency_ms=10),
        models.AILog(operation="analysis", provider="openai", success=False, fallback_used=True, latency_ms=30, error="boom"),
        models.AILog(operation="reply", provider="openai", success=True, fallback_used=False, latency_ms=50),
    ])
    db.commit()


def test_processing_overview(client, db, admin_user, user_a):
    _seed(db, user_a["user"])
    r = client.get("/api/admin/processing", headers=_h(admin_user))
    assert r.status_code == 200
    body = r.json()
    assert body["by_status"].get("failed", 0) >= 1 and body["by_status"].get("completed", 0) >= 1
    failed = body["failed"]
    assert any(f["processing_error"] == "provider timeout" and f["retry_count"] == 2 for f in failed)
    # admins must not see other users' email content
    assert "secret subject" not in r.text and all("subject" not in f for f in failed)


def test_usage_stats(client, db, admin_user):
    r = client.get("/api/admin/usage", headers=_h(admin_user))
    assert r.status_code == 200
    body = r.json()
    assert body["total_calls"] >= 3 and body["failed_calls"] >= 1
    assert 0 < body["error_rate"] <= 1
    ops = {row["name"]: row for row in body["by_operation"]}
    assert ops["analysis"]["calls"] >= 2 and ops["analysis"]["fallbacks"] >= 1
    assert {row["name"] for row in body["by_provider"]} >= {"heuristic", "openai"}


def test_admin_views_forbidden_for_regular_users(client, user_a):
    for path in ("/api/admin/processing", "/api/admin/usage", "/api/admin/ai-errors"):
        assert client.get(path, headers=_h(user_a)).status_code == 403


def test_ai_errors_lists_only_failures(client, admin_user):
    r = client.get("/api/admin/ai-errors", headers=_h(admin_user))
    assert r.status_code == 200
    assert r.json() and all(row["success"] is False for row in r.json())


def test_retry_failed_requires_admin_and_requeues(client, db, admin_user, manager_user):
    assert client.post("/api/admin/emails/retry-failed", headers=_h(manager_user)).status_code == 403
    r = client.post("/api/admin/emails/retry-failed", headers=_h(admin_user))
    assert r.status_code == 200 and r.json()["queued"] >= 1
