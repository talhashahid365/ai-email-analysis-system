"""The dashboard must show only the signed-in user's own data - nothing pre-filled, nothing shared."""

BODY = {"sender_name": "Sara Khan", "sender_email": "sara@acme.com", "subject": "Refund for order #1029",
        "body_plain": "The product arrived damaged. Please refund order #1029 as soon as possible."}


def _hdr(u):
    return {"Authorization": f"Bearer {u['token']}"}


def test_new_user_dashboard_is_empty(client, user_a):
    r = client.get("/api/analytics/overview", headers=_hdr(user_a))
    assert r.status_code == 200
    d = r.json()
    assert d["total_emails"] == 0 and d["unread_emails"] == 0 and d["pending_actions"] == 0
    assert d["category_distribution"] == {} and d["recent_emails"] == [] and d["critical_queue"] == []
    assert len(d["daily_activity"]) == 14 and all(day["total"] == 0 for day in d["daily_activity"])
    heat = d["activity_heatmap"]
    assert len(heat["grid"]) == 7 and all(sum(row) == 0 for row in heat["grid"])


def test_dashboard_reflects_own_emails_only(client, user_a, user_b):
    assert client.post("/api/emails", json=BODY, headers=_hdr(user_a)).status_code == 201
    a = client.get("/api/analytics/overview", headers=_hdr(user_a)).json()
    b = client.get("/api/analytics/overview", headers=_hdr(user_b)).json()
    assert a["total_emails"] == 1 and len(a["recent_emails"]) == 1
    assert a["daily_activity"][-1]["total"] == 1
    assert sum(sum(row) for row in a["activity_heatmap"]["grid"]) == 1
    assert b["total_emails"] == 0 and b["recent_emails"] == []
