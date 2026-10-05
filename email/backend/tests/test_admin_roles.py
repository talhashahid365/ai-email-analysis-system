"""Admins can promote/demote anyone, but the system always keeps at least one active admin."""


def _role(client, headers, user_id, role):
    return client.patch(f"/api/admin/users/{user_id}/role", json={"role": role}, headers=headers)


def test_admin_can_set_any_role(client, admin_user, user_a):
    h = {"Authorization": f"Bearer {admin_user['token']}"}
    uid = user_a["user"].id
    for role in ("manager", "admin", "user"):
        r = _role(client, h, uid, role)
        assert r.status_code == 200 and r.json()["role"] == role
    assert _role(client, h, uid, "superuser").status_code == 400


def test_last_admin_cannot_be_removed(client, admin_user, user_a):
    h_admin = {"Authorization": f"Bearer {admin_user['token']}"}
    admin_id, other_id = admin_user["user"].id, user_a["user"].id

    # the only admin cannot demote or suspend themselves
    r = _role(client, h_admin, admin_id, "user")
    assert r.status_code == 400 and "last admin" in r.json()["detail"].lower()
    assert client.patch(f"/api/admin/users/{admin_id}/status", json={"is_active": False}, headers=h_admin).status_code == 400

    # once a second admin exists, the first one may step down
    assert _role(client, h_admin, other_id, "admin").status_code == 200
    assert _role(client, h_admin, admin_id, "user").status_code == 200

    # ...and now user_a is the last admin and is protected
    h_other = {"Authorization": f"Bearer {user_a['token']}"}
    r = _role(client, h_other, other_id, "manager")
    assert r.status_code == 400 and "last admin" in r.json()["detail"].lower()

    # a non-admin can no longer manage roles
    assert _role(client, h_admin, other_id, "user").status_code == 403
