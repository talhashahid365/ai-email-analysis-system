"""Password reset must be possible ONLY through the emailed link."""
from app import models, security
from app.ratelimit import reset_rate_limits
from app.services import mailer


def test_reset_link_only_sent_by_email(client, db, monkeypatch):
    reset_rate_limits()  # this test makes several auth calls; keep it independent of other tests
    user = models.User(email="resetme@example.com", hashed_password=security.hash_password("oldPassword123"),
                       full_name="Reset Me", role="user", is_active=True, is_verified=True)
    db.add(user)
    db.commit()

    sent = []
    monkeypatch.setattr("app.api.auth.send_system_email",
                        lambda to, subject, body, sensitive=False: sent.append((to, body, sensitive)) or True)

    r = client.post("/api/auth/forgot-password", json={"email": "resetme@example.com"})
    assert r.status_code == 200
    assert "reset_token" not in r.json()          # the API never hands out the token
    assert len(sent) == 1 and sent[0][2] is True   # the email is flagged sensitive
    assert "/reset-password?token=" in sent[0][1]

    # Unknown address gets the same answer and no email
    r2 = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r2.status_code == 200 and r2.json() == r.json() and len(sent) == 1

    # The emailed link works exactly once
    token = sent[0][1].split("token=")[1].split()[0]
    ok = client.post("/api/auth/reset-password", json={"token": token, "new_password": "newPassword123"})
    assert ok.status_code == 200
    again = client.post("/api/auth/reset-password", json={"token": token, "new_password": "anotherPass123"})
    assert again.status_code == 400
    login = client.post("/api/auth/login", json={"email": "resetme@example.com", "password": "newPassword123"})
    assert login.status_code == 200


def test_sensitive_mail_is_never_printed(capsys, monkeypatch):
    monkeypatch.setattr(mailer.settings, "SMTP_HOST", "")  # never attempt a real send from a test
    mailer.send_system_email("a@example.com", "Reset", "SECRET-LINK-123", sensitive=True)
    out = capsys.readouterr().out
    assert "SECRET-LINK-123" not in out
