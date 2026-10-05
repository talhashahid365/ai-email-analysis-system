import pytest
from app import models, security


def test_multi_tenant_data_isolation(client, user_a, user_b, db):
    """Verify that User B cannot access, read, or modify User A's emails, threads, or notifications."""
    headers_a = {"Authorization": f"Bearer {user_a['token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['token']}"}

    # User A creates an email
    create_resp = client.post(
        "/api/emails",
        json={
            "sender_name": "Confidential Sender",
            "sender_email": "private@confidential.com",
            "subject": "Confidential Project Strategy",
            "body_plain": "Top secret data for User A only.",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 201
    email_id = create_resp.json()["id"]
    thread_id = create_resp.json()["thread_id"]

    # User A can fetch email details
    get_a = client.get(f"/api/emails/{email_id}", headers=headers_a)
    assert get_a.status_code == 200

    # User B tries to fetch User A's email -> Expect 404
    get_b = client.get(f"/api/emails/{email_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B tries to list emails -> Should not see User A's email
    list_b = client.get("/api/emails", headers=headers_b)
    assert list_b.status_code == 200
    b_email_ids = [e["id"] for e in list_b.json()]
    assert email_id not in b_email_ids

    # User B tries to fetch User A's thread -> Expect 404
    thread_b = client.get(f"/api/emails/threads/{thread_id}", headers=headers_b)
    assert thread_b.status_code == 404

    # User B tries to delete User A's email -> Expect 404
    del_b = client.delete(f"/api/emails/{email_id}", headers=headers_b)
    assert del_b.status_code == 404


def test_token_revocation_logout(client, db):
    """Verify token revocation on logout."""
    # Register temporary user
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "logout.test@example.com",
            "password": "Password123!",
            "full_name": "Logout User",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    me_before = client.get("/api/auth/me", headers=headers)
    assert me_before.status_code == 200

    # Perform logout
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    # Verify token is now rejected
    me_after = client.get("/api/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_role_based_access_control(client, admin_user, manager_user, user_a):
    """Verify RBAC rules for admin, manager, and regular user roles."""
    headers_user = {"Authorization": f"Bearer {user_a['token']}"}
    headers_mgr = {"Authorization": f"Bearer {manager_user['token']}"}
    headers_admin = {"Authorization": f"Bearer {admin_user['token']}"}

    # Regular user tries admin endpoint -> Expect 403
    usr_admin_resp = client.get("/api/admin/users", headers=headers_user)
    assert usr_admin_resp.status_code == 403

    # Manager user reads stats -> Expect 200
    mgr_stats_resp = client.get("/api/admin/stats", headers=headers_mgr)
    assert mgr_stats_resp.status_code == 200

    # Manager user tries write action (modifying system setting) -> Expect 403
    mgr_setting_resp = client.put(
        "/api/admin/settings/allow_registration",
        json={"value": False},
        headers=headers_mgr,
    )
    assert mgr_setting_resp.status_code == 403

    # Admin user modifies system setting -> Expect 200
    adm_setting_resp = client.put(
        "/api/admin/settings/allow_registration",
        json={"value": True},
        headers=headers_admin,
    )
    assert adm_setting_resp.status_code == 200
