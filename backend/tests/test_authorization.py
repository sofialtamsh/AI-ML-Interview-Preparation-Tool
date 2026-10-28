"""The admin/student boundary and cross-account isolation, tested explicitly."""

import re
import uuid
from typing import Any

import pytest

from app.main import app
from tests.helpers import create_admin, login_admin, login_student, register_student

PUBLIC_ADMIN_ROUTES = {"/api/admin/auth/login", "/api/admin/auth/logout"}


def _api_operations(prefix: str) -> list[tuple[str, str]]:
    """Every (METHOD, path template) under a prefix, read from the OpenAPI schema so that new
    endpoints are automatically covered by the sweeps below."""
    return [
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(prefix)
        for method in operations
    ]


ADMIN_ROUTES = [
    (method, re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path))
    for method, path in _api_operations("/api/admin")
    if path not in PUBLIC_ADMIN_ROUTES
]


def test_admin_route_inventory_is_complete():
    # Guards against the sweeps silently running zero cases if route discovery breaks.
    assert len(ADMIN_ROUTES) >= 19


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_students_cannot_reach_any_admin_endpoint(method, path, make_client):
    student = make_client()
    register_student(student)
    # Even if a student's token is presented under the admin cookie name, it is rejected.
    student.cookies.set("ipp_admin_session", student.cookies.get("ipp_student_session"))

    response = student.request(method, path, json={})
    assert response.status_code == 401, response.text


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_anonymous_requests_to_admin_endpoints_are_rejected(method, path, client):
    assert client.request(method, path, json={}).status_code == 401


def test_admin_token_cannot_be_used_as_student_session(client, make_client):
    create_admin()
    login_admin(client)
    impostor = make_client()
    impostor.cookies.set("ipp_student_session", client.cookies.get("ipp_admin_session"))
    assert impostor.get("/api/student/auth/me").status_code == 401


def test_admin_permissions_are_enforced_by_the_backend(make_client):
    create_admin(email="publisher@example.com", roles=("content_publisher",))
    create_admin(email="success@example.com", roles=("student_success",))
    publisher, success = make_client(), make_client()
    login_admin(publisher, email="publisher@example.com")
    login_admin(success, email="success@example.com")

    assert publisher.get("/api/admin/students").status_code == 403
    assert publisher.get("/api/admin/admin-users").status_code == 403
    assert publisher.get("/api/admin/audit-logs").status_code == 403
    assert publisher.get("/api/admin/overview").json() == {"students": None, "active_admins": None}

    assert success.get("/api/admin/students").status_code == 200
    assert success.get("/api/admin/overview").json()["students"] is not None
    assert success.get("/api/admin/admin-users").status_code == 403


def test_state_changing_requests_require_the_csrf_header(make_client):
    bare = make_client(csrf_header=False)
    response = bare.post(
        "/api/student/auth/register",
        json={"full_name": "Asha Rao", "email": "asha@example.com", "password": "long-enough-1"},
    )
    assert response.status_code == 403
    assert bare.post("/api/admin/auth/login", json={}).status_code == 403


def test_student_cannot_touch_another_students_sessions(make_client):
    alice, bob = make_client(), make_client()
    register_student(alice, email="alice@example.com", name="Alice")
    register_student(bob, email="bob@example.com", name="Bob")
    bobs_session = bob.get("/api/student/me/sessions").json()[0]["id"]

    assert alice.delete(f"/api/student/me/sessions/{bobs_session}").status_code == 404
    assert bob.get("/api/student/auth/me").status_code == 200
    alice_ids = {s["id"] for s in alice.get("/api/student/me/sessions").json()}
    assert bobs_session not in alice_ids


def test_student_api_never_takes_another_principals_id():
    """Student endpoints act on the session's own account only. Path parameters are limited to
    the student's own session id (ownership-checked above) and identifiers of *published*
    learning content; never a student, admin or other account id."""
    student_paths = {path for _, path in _api_operations("/api/student")}
    assert len(student_paths) >= 8
    params = {p for path in student_paths for p in re.findall(r"\{([^}]+)\}", path)}
    assert params == {"session_id", "slug", "media_id"}


def _walk(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [k for k in value] + [s for v in value.values() for s in _walk(v)]
    if isinstance(value, list):
        return [s for v in value for s in _walk(v)]
    return []


def test_no_password_hashes_or_tokens_are_ever_returned(client, make_client):
    create_admin()
    admin = make_client()
    responses = [login_admin(admin)]
    responses.append(register_student(client))
    responses.append(login_student(make_client()))
    for path in (
        "/api/admin/auth/me",
        "/api/admin/admin-users",
        "/api/admin/students",
        "/api/admin/overview",
        "/api/admin/roles",
    ):
        response = admin.get(path)
        assert response.status_code == 200, path
        responses.append(response.json())
        assert "$argon2" not in response.text
    responses.append(client.get("/api/student/me/sessions").json())

    keys = {k.lower() for body in responses for k in _walk(body)}
    assert not {k for k in keys if "password_hash" in k or "token" in k}


def test_suspending_a_student_signs_them_out_everywhere(make_client):
    create_admin(roles=("student_success",))
    admin, student = make_client(), make_client()
    login_admin(admin)
    me = register_student(student)

    response = admin.patch(f"/api/admin/students/{me['id']}", json={"status": "suspended"})
    assert response.status_code == 200
    assert student.get("/api/student/auth/me").status_code == 401

    retry = make_client().post(
        "/api/student/auth/login",
        json={"email": "asha@example.com", "password": "correct-horse-42"},
    )
    assert retry.status_code == 403
