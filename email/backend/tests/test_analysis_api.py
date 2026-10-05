"""Per-email AI endpoints, admin retry, deadline notifications and the greeting-in-action-item fix."""
from datetime import date, timedelta

from app import models
from app.services import ai_engine, notifications

BODY = {"sender_name": "Sara Khan", "sender_email": "sara@acme.com", "subject": "Updated quotation",
        "body_plain": "Hi Sara, please send the updated quotation by Friday. Order #4521 is waiting."}


def _hdr(u):
    return {"Authorization": f"Bearer {u['token']}"}


def _create(client, user):
    r = client.post("/api/emails", json=BODY, headers=_hdr(user))
    assert r.status_code == 201
    return r.json()["id"]


def test_reprocess_classify_summarize_extract(client, user_a):
    eid = _create(client, user_a)
    assert client.post(f"/api/emails/{eid}/reprocess", headers=_hdr(user_a)).status_code == 200
    c = client.post(f"/api/emails/{eid}/classify", headers=_hdr(user_a))
    assert c.status_code == 200 and c.json()["category"]
    s = client.post(f"/api/emails/{eid}/summarize?mode=detailed", headers=_hdr(user_a))
    assert s.status_code == 200 and s.json()["mode"] == "detailed" and s.json()["summary"]
    assert client.post(f"/api/emails/{eid}/summarize?mode=bogus", headers=_hdr(user_a)).status_code == 422
    x = client.post(f"/api/emails/{eid}/extract", headers=_hdr(user_a))
    assert x.status_code == 200 and "order_number" in x.json()


def test_analysis_endpoints_are_owner_scoped(client, user_a, user_b):
    eid = _create(client, user_a)
    for path in ("reprocess", "classify", "summarize", "extract"):
        assert client.post(f"/api/emails/{eid}/{path}", headers=_hdr(user_b)).status_code == 404
        assert client.post(f"/api/emails/{eid}/{path}").status_code in (401, 403)


def test_admin_retry_failed_requires_admin(client, user_a, admin_user, db):
    assert client.post("/api/admin/emails/retry-failed", headers=_hdr(user_a)).status_code == 403
    eid = _create(client, user_a)
    email = db.get(models.Email, eid)
    email.processing_status = "failed"
    db.commit()
    r = client.post("/api/admin/emails/retry-failed", headers=_hdr(admin_user))
    assert r.status_code == 200 and r.json()["queued"] >= 1
    assert client.post(f"/api/admin/emails/{eid}/reprocess", headers=_hdr(user_a)).status_code == 403
    assert client.post(f"/api/admin/emails/{eid}/reprocess", headers=_hdr(admin_user)).status_code == 200


def test_check_all_deadlines_creates_notifications_once(db, user_a):
    uid = user_a["user"].id
    email = models.Email(user_id=uid, sender_email="x@y.com", sender_name="X", recipient_email="a@b.com", subject="s",
                         body_plain="b", processing_status="completed", content_hash="dl-test-hash")
    db.add(email)
    db.flush()
    db.add(models.Deadline(email_id=email.id, user_id=uid, title="Send quotation",
                           due_date=(date.today() + timedelta(days=1)).isoformat(), is_completed=False))
    db.commit()
    assert notifications.check_all_deadlines(db) >= 1
    assert notifications.check_all_deadlines(db) == 0  # deduplicated


def test_greeting_not_part_of_action_item():
    actions, _ = ai_engine.extract_actions("Hi Sara, please send the updated quotation by Friday.\n\nThanks,\nAli",
                                           "Ali", "Quote", "Sales Inquiry", date(2026, 10, 1), True)
    assert actions[0]["task"] == "Send the updated quotation"
    assert actions[0]["due_date"] == "2026-10-02"
