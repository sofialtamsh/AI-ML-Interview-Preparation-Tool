from alembic import command

from app.auth.permissions import PERMISSION_DESCRIPTIONS, SYSTEM_ROLES
from tests.conftest import alembic_config


def test_models_and_migrations_are_in_sync():
    """Fails if a model changed without a matching Alembic migration."""
    command.check(alembic_config())


def test_health_and_security_headers(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_session_cookies_are_httponly_and_path_scoped(client):
    response = client.post(
        "/api/student/auth/register",
        json={"full_name": "Asha Rao", "email": "asha@example.com", "password": "long-enough-1"},
    )
    cookie = response.headers["set-cookie"]
    assert "ipp_student_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/student" in cookie
    assert "SameSite=lax" in cookie


def test_super_admin_holds_every_permission_and_others_do_not():
    everything = set(PERMISSION_DESCRIPTIONS)
    assert SYSTEM_ROLES["super_admin"].permissions == everything
    for key, role in SYSTEM_ROLES.items():
        if key != "super_admin":
            assert role.permissions < everything, key
