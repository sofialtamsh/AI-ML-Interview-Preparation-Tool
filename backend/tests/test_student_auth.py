from sqlalchemy import select

from app.models import LoginEvent
from tests.helpers import STUDENT_PASSWORD, login_student, register_student


def test_register_creates_account_and_signs_in(client):
    student = register_student(client)

    assert student["email"] == "asha@example.com"
    assert student["student_code"].startswith("STU-")
    assert student["status"] == "active"
    assert "password_hash" not in student
    me = client.get("/api/student/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == student["id"]


def test_register_normalises_email_and_rejects_duplicates(client, make_client):
    student = register_student(client, email="  Asha@Example.COM ")
    assert student["email"] == "asha@example.com"

    duplicate = make_client().post(
        "/api/student/auth/register",
        json={
            "full_name": "Someone Else",
            "email": "asha@example.com",
            "password": "another-pass-1",
        },
    )
    assert duplicate.status_code == 409


def test_register_validates_input(client):
    too_short = client.post(
        "/api/student/auth/register",
        json={"full_name": "Asha Rao", "email": "asha@example.com", "password": "short"},
    )
    bad_email = client.post(
        "/api/student/auth/register",
        json={"full_name": "Asha Rao", "email": "not-an-email", "password": STUDENT_PASSWORD},
    )
    assert too_short.status_code == 422
    assert bad_email.status_code == 422


def test_student_numbers_are_unique_and_sequential(make_client):
    first = register_student(make_client(), email="a@example.com")
    second = register_student(make_client(), email="b@example.com")
    assert first["student_code"] != second["student_code"]


def test_login_logout_and_revoked_token_cannot_be_reused(client, make_client):
    register_student(client)
    device = make_client()
    login_student(device)
    token = device.cookies.get("ipp_student_session")
    assert token

    assert device.post("/api/student/auth/logout").status_code == 204
    assert device.get("/api/student/auth/me").status_code == 401

    replay = make_client()
    replay.cookies.set("ipp_student_session", token)
    assert replay.get("/api/student/auth/me").status_code == 401


def test_wrong_password_and_unknown_email_get_the_same_answer(client, make_client):
    register_student(client)
    wrong_password = make_client().post(
        "/api/student/auth/login", json={"email": "asha@example.com", "password": "wrong-pass-123"}
    )
    unknown_email = make_client().post(
        "/api/student/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-pass-123"},
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_account_locks_after_repeated_failures(client, make_client):
    register_student(client)
    attacker = make_client()
    for _ in range(5):
        attacker.post(
            "/api/student/auth/login", json={"email": "asha@example.com", "password": "guess-12345"}
        )

    still_wrong = attacker.post(
        "/api/student/auth/login", json={"email": "asha@example.com", "password": "guess-12345"}
    )
    correct = make_client().post(
        "/api/student/auth/login", json={"email": "asha@example.com", "password": STUDENT_PASSWORD}
    )
    assert still_wrong.status_code == 401
    assert correct.status_code == 429
    assert "Too many failed attempts" in correct.json()["detail"]


def test_login_attempts_are_recorded(client, make_client, db):
    register_student(client)
    make_client().post(
        "/api/student/auth/login", json={"email": "asha@example.com", "password": "wrong-pass-123"}
    )
    login_student(make_client())

    events = db.scalars(select(LoginEvent).order_by(LoginEvent.id)).all()
    # registration sign-in, failed attempt, successful login
    assert [(e.success, e.failure_reason) for e in events] == [
        (True, None),
        (False, "bad_password"),
        (True, None),
    ]
    # Every event, including the sign-in at registration, records the device.
    assert all(e.user_agent and e.ip_address for e in events)


def test_login_is_rate_limited_per_ip(client):
    statuses = [
        client.post(
            "/api/student/auth/login", json={"email": "x@example.com", "password": "whatever-123"}
        ).status_code
        for _ in range(21)
    ]
    assert statuses[:20] == [401] * 20
    assert statuses[20] == 429


def test_multiple_devices_and_sign_out_others(client, make_client):
    register_student(client)
    laptop, phone = make_client(), make_client()
    login_student(laptop)
    login_student(phone)

    sessions = laptop.get("/api/student/me/sessions").json()
    assert len(sessions) == 3
    assert sum(s["current"] for s in sessions) == 1

    assert laptop.post("/api/student/me/sessions/revoke-others").status_code == 200
    assert laptop.get("/api/student/auth/me").status_code == 200
    assert phone.get("/api/student/auth/me").status_code == 401
    assert client.get("/api/student/auth/me").status_code == 401


def test_change_password(client, make_client):
    register_student(client)
    other_device = make_client()
    login_student(other_device)

    wrong = client.post(
        "/api/student/me/password",
        json={"current_password": "not-my-password", "new_password": "brand-new-pass-1"},
    )
    assert wrong.status_code == 400

    ok = client.post(
        "/api/student/me/password",
        json={"current_password": STUDENT_PASSWORD, "new_password": "brand-new-pass-1"},
    )
    assert ok.status_code == 200
    assert other_device.get("/api/student/auth/me").status_code == 401
    login_student(make_client(), password="brand-new-pass-1")


def test_update_profile_name(client):
    register_student(client)
    response = client.patch("/api/student/me", json={"full_name": "  Asha R.  "})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha R."
