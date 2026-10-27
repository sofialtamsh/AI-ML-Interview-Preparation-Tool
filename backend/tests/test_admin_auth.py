from datetime import timedelta

from sqlalchemy import update

from app.core.security import utcnow
from app.models import AuthSession
from tests.helpers import ADMIN_PASSWORD, create_admin, login_admin


def test_admin_login_returns_roles_and_permissions(client):
    create_admin(roles=("student_success",))
    me = login_admin(client)

    assert [r["key"] for r in me["roles"]] == ["student_success"]
    assert set(me["permissions"]) == {
        "students.view",
        "students.manage",
        "analytics.view",
        "rankings.view",
    }
    assert client.get("/api/admin/auth/me").json()["email"] == "admin@example.com"


def test_admin_logout(client):
    create_admin()
    login_admin(client)
    assert client.post("/api/admin/auth/logout").status_code == 204
    assert client.get("/api/admin/auth/me").status_code == 401


def test_admin_login_failure_is_generic(client):
    create_admin()
    response = client.post(
        "/api/admin/auth/login", json={"email": "admin@example.com", "password": "nope-nope-1"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_temporary_password_must_be_changed_before_anything_else(client):
    create_admin(must_change_password=True)
    me = login_admin(client)
    assert me["must_change_password"] is True
    assert client.get("/api/admin/overview").status_code == 403

    changed = client.post(
        "/api/admin/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "my-own-password-1"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert client.get("/api/admin/overview").status_code == 200


def test_idle_admin_session_expires(client, db):
    create_admin()
    login_admin(client)
    db.execute(update(AuthSession).values(last_seen_at=utcnow() - timedelta(hours=3)))
    db.commit()
    assert client.get("/api/admin/auth/me").status_code == 401


def test_disabled_admin_cannot_log_in(client, make_client):
    create_admin()
    target = create_admin(email="ops@example.com", roles=("analyst",))
    login_admin(client)
    ops_device = make_client()
    login_admin(ops_device, email="ops@example.com")

    response = client.patch(f"/api/admin/admin-users/{target.id}", json={"status": "disabled"})
    assert response.status_code == 200
    assert ops_device.get("/api/admin/auth/me").status_code == 401

    retry = make_client().post(
        "/api/admin/auth/login", json={"email": "ops@example.com", "password": ADMIN_PASSWORD}
    )
    assert retry.status_code == 403
