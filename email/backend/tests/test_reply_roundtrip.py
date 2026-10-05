"""End-to-end: customer query arrives -> AI analyses it -> admin approves a reply -> every record on the website updates.

The real SMTP/IMAP servers are replaced by fakes so the test is offline and repeatable.
"""
import pytest

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from app.config import settings
from app.services import imap_sync, mailer

QUERY = {"sender_name": "Sara Khan", "sender_email": "sara@acme.com", "message_id": "<q1@acme.com>",
         "subject": "Refund for order #1029",
         "body_plain": "The product arrived damaged. Please refund order #1029 as soon as possible."}


def _hdr(u):
    return {"Authorization": f"Bearer {u['token']}"}


@pytest.fixture(autouse=True)
def offline_sync_processing(monkeypatch):
    """Analyse inside the request's own (test) DB session and never call a real LLM, whatever backend/.env says."""
    monkeypatch.setattr(settings, "PROCESSING_MODE", "sync")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "heuristic")


@pytest.fixture
def fake_smtp(monkeypatch):
    sent = []

    def fake_send(to, subject, body, from_name="", in_reply_to=None, message_id=None):
        sent.append({"to": to, "subject": subject, "body": body, "in_reply_to": in_reply_to, "message_id": message_id})
        return True, f"Reply e-mailed to {to}."

    monkeypatch.setattr(mailer, "send_reply_email", fake_send)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USER", "admin@company.test")
    return sent


def _overview(client, admin):
    return client.get("/api/analytics/overview", headers=_hdr(admin)).json()


def test_query_to_reply_updates_every_record(client, admin_user, fake_smtp):
    before = _overview(client, admin_user)

    # 1. a customer query arrives and is analysed
    created = client.post("/api/emails", json=QUERY, headers=_hdr(admin_user))
    assert created.status_code == 201
    eid = created.json()["id"]
    detail = client.get(f"/api/emails/{eid}", headers=_hdr(admin_user)).json()
    assert detail["processing_status"] == "completed"
    assert detail["ai_analysis"]["category"] and detail["ai_analysis"]["priority"] and detail["ai_analysis"]["sentiment"]

    mid = _overview(client, admin_user)
    assert mid["total_emails"] == before["total_emails"] + 1
    assert mid["daily_activity"][-1]["total"] == before["daily_activity"][-1]["total"] + 1

    # 2. admin generates a draft, edits it and approves
    draft = client.post(f"/api/emails/{eid}/reply", json={"tone": "Professional"}, headers=_hdr(admin_user))
    assert draft.status_code == 200 and draft.json()["status"] == "draft"
    final = "Hi Sara, your refund for order #1029 has been issued."
    ok = client.post(f"/api/emails/{eid}/reply/{draft.json()['id']}/approve", json={"edited_body": final},
                     headers=_hdr(admin_user))
    assert ok.status_code == 200
    assert ok.json()["status"] == "approved" and ok.json()["delivered"] is True and ok.json()["sent_email_id"]

    # 3. the real e-mail went to the customer, in the same conversation
    assert len(fake_smtp) == 1
    assert fake_smtp[0]["to"] == "sara@acme.com" and fake_smtp[0]["body"] == final
    assert fake_smtp[0]["subject"].lower().startswith("re:") and fake_smtp[0]["in_reply_to"] == "<q1@acme.com>"

    # 4. website records are updated
    item = next(e for e in client.get("/api/emails", headers=_hdr(admin_user)).json() if e["id"] == eid)
    assert item["reply_status"] == "replied"
    after = _overview(client, admin_user)
    assert after["daily_activity"][-1]["replied"] == before["daily_activity"][-1]["replied"] + 1
    assert after["sla"]["responded"] == before["sla"]["responded"] + 1
    assert after["replied_count"] == before["replied_count"] + 1
    outbound = client.get(f"/api/emails/{ok.json()['sent_email_id']}", headers=_hdr(admin_user)).json()
    assert outbound["is_outbound"] is True and outbound["body_plain"] == final and outbound["thread_id"] == detail["thread_id"]


def test_failed_delivery_records_nothing(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USER", "admin@company.test")
    monkeypatch.setattr(mailer, "send_reply_email", lambda *a, **k: (False, "SMTP login rejected."))
    q = dict(QUERY, message_id="<q2@acme.com>", subject="Where is my invoice?", body_plain="Please send invoice #55 today.")
    eid = client.post("/api/emails", json=q, headers=_hdr(admin_user)).json()["id"]
    d = client.post(f"/api/emails/{eid}/reply", json={"tone": "Short"}, headers=_hdr(admin_user)).json()
    r = client.post(f"/api/emails/{eid}/reply/{d['id']}/approve", json={"edited_body": "On it."}, headers=_hdr(admin_user))
    assert r.status_code == 502 and "SMTP" in r.json()["detail"]
    item = next(e for e in client.get("/api/emails", headers=_hdr(admin_user)).json() if e["id"] == eid)
    assert item["reply_status"] != "replied"  # not marked replied when nothing was delivered


def test_without_smtp_reply_is_recorded_but_flagged_not_sent(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    q = dict(QUERY, message_id="<q3@acme.com>", subject="Demo request", body_plain="Can we schedule a demo next week?")
    eid = client.post("/api/emails", json=q, headers=_hdr(admin_user)).json()["id"]
    d = client.post(f"/api/emails/{eid}/reply", json={"tone": "Friendly"}, headers=_hdr(admin_user)).json()
    r = client.post(f"/api/emails/{eid}/reply/{d['id']}/approve", json={"edited_body": "Sure!"}, headers=_hdr(admin_user))
    assert r.status_code == 200 and r.json()["delivered"] is False and "NOT" in r.json()["delivery_note"]


def test_mailbox_sync_imports_real_mail_once(client, admin_user, monkeypatch):
    def raw(frm, subj, body, mid):
        return (f"From: {frm}\nTo: admin@company.test\nSubject: {subj}\nMessage-ID: {mid}\n"
                f"Date: Fri, 02 Oct 2026 09:00:00 +0000\n\n{body}\n").encode()

    msgs = [raw("Ali Raza <ali@client.com>", "Quote needed", "Please send a quote for 50 licences.", "<m1@client.com>"),
            raw("Admin <admin@company.test>", "Re: Quote needed", "Sent.", "<m2@company.test>")]
    monkeypatch.setattr(settings, "IMAP_HOST", "imap.test")
    monkeypatch.setattr(settings, "IMAP_USER", "admin@company.test")
    monkeypatch.setattr(settings, "IMAP_PASSWORD", "x")
    monkeypatch.setattr(imap_sync, "fetch_raw_messages", lambda limit: msgs)

    first = client.post("/api/emails/sync-inbox", headers=_hdr(admin_user)).json()
    assert first["imported"] == 1 and first["skipped_own"] == 1
    second = client.post("/api/emails/sync-inbox", headers=_hdr(admin_user)).json()
    assert second["imported"] == 0 and second["duplicates"] == 1
    assert any(e["sender_email"] == "ali@client.com" for e in client.get("/api/emails", headers=_hdr(admin_user)).json())


def test_sync_without_imap_config_gives_clear_error(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "IMAP_HOST", "")
    r = client.post("/api/emails/sync-inbox", headers=_hdr(admin_user))
    assert r.status_code == 400 and "IMAP" in r.json()["detail"]


# ---------------------------------------------------------------- full real-mail lifecycle (IMAP in, SMTP out)
def _raw(frm, subj, body, mid, minutes_ago, in_reply_to=None):
    when = format_datetime(datetime.now(timezone.utc) - timedelta(minutes=minutes_ago))
    irt = f"In-Reply-To: {in_reply_to}\nReferences: {in_reply_to}\n" if in_reply_to else ""
    return (f"From: {frm}\nTo: admin@company.test\nSubject: {subj}\nMessage-ID: {mid}\nDate: {when}\n{irt}\n{body}\n").encode()


def _use_mailbox(monkeypatch, box):
    monkeypatch.setattr(settings, "IMAP_HOST", "imap.test")
    monkeypatch.setattr(settings, "IMAP_USER", "admin@company.test")
    monkeypatch.setattr(settings, "IMAP_PASSWORD", "x")
    monkeypatch.setattr(imap_sync, "fetch_raw_messages", lambda limit: list(box))


@pytest.mark.parametrize("known_id", [True, False])
def test_customer_followup_shows_in_same_conversation(client, admin_user, fake_smtp, monkeypatch, known_id):
    tag = "known" if known_id else "rewritten"
    box = [_raw("Bilal <bilal@shop.com>", f"Broken charger {tag}", "My charger stopped working. Can you replace it?",
                f"<first-{tag}@shop.com>", 30)]
    _use_mailbox(monkeypatch, box)

    # 1. the customer's real mail is picked up from the mailbox and analysed
    assert client.post("/api/emails/sync-inbox", headers=_hdr(admin_user)).json()["imported"] == 1
    first = next(e for e in client.get("/api/emails", headers=_hdr(admin_user)).json()
                 if e["sender_email"] == "bilal@shop.com" and tag in e["subject"])
    assert first["reply_status"] == "pending"
    thread_id = client.get(f"/api/emails/{first['id']}", headers=_hdr(admin_user)).json()["thread_id"]

    # 2. admin replies from the website; the e-mail carries our own Message-ID and the same id is stored
    d = client.post(f"/api/emails/{first['id']}/reply", json={"tone": "Professional"}, headers=_hdr(admin_user)).json()
    ok = client.post(f"/api/emails/{first['id']}/reply/{d['id']}/approve",
                     json={"edited_body": "We will ship a new charger today."}, headers=_hdr(admin_user))
    assert ok.status_code == 200 and ok.json()["delivered"] is True
    out_id = fake_smtp[-1]["message_id"]
    assert out_id.startswith("<") and "@" in out_id
    outbound = client.get(f"/api/emails/{ok.json()['sent_email_id']}", headers=_hdr(admin_user)).json()
    assert outbound["message_id"] == out_id

    # 3. the customer answers again (some providers rewrite In-Reply-To, so both cases must work)
    parent = out_id if known_id else "<rewritten-by-provider@mx.example.com>"
    box.append(_raw("Bilal <bilal@shop.com>", f"Re: Broken charger {tag}", "Thanks. When will it arrive? I need it this week.",
                    f"<second-{tag}@shop.com>", -2, in_reply_to=parent))  # dated after our reply
    assert client.post("/api/emails/sync-inbox", headers=_hdr(admin_user)).json()["imported"] == 1

    # 4. the follow-up is on the website, in the SAME conversation, and waits for the admin's next reply
    msgs = client.get(f"/api/emails/threads/{thread_id}", headers=_hdr(admin_user)).json()["messages"]
    assert [m["is_outbound"] for m in msgs] == [False, True, False]
    assert msgs[-1]["reply_status"] == "pending"
    assert msgs[0]["reply_status"] == "replied"  # the first question stays answered
    assert any(e["id"] == msgs[-1]["id"] for e in client.get("/api/emails", headers=_hdr(admin_user)).json())


def test_auto_sync_files_mail_under_the_admin_account(db, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "IMAP_OWNER_EMAIL", "")
    monkeypatch.setattr(settings, "IMAP_USER", admin_user["user"].email)
    assert imap_sync.find_owner(db).id == admin_user["user"].id


def test_approving_twice_does_not_send_twice(client, admin_user, fake_smtp):
    q = dict(QUERY, message_id="<q-twice@acme.com>", subject="Double click test", body_plain="Please confirm my booking today.")
    eid = client.post("/api/emails", json=q, headers=_hdr(admin_user)).json()["id"]
    d = client.post(f"/api/emails/{eid}/reply", json={"tone": "Short"}, headers=_hdr(admin_user)).json()
    url = f"/api/emails/{eid}/reply/{d['id']}/approve"
    assert client.post(url, json={"edited_body": "Confirmed."}, headers=_hdr(admin_user)).status_code == 200
    assert client.post(url, json={"edited_body": "Confirmed."}, headers=_hdr(admin_user)).status_code == 409
    assert len(fake_smtp) == 1
