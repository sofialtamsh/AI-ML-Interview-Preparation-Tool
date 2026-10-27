from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import update

from app.core.security import utcnow
from app.models import PasswordResetToken
from tests.helpers import STUDENT_PASSWORD, login_student, register_student


def _token_from(outbox) -> str:
    body = outbox.messages[-1].body
    link = next(word for word in body.split() if "reset-password?token=" in word)
    return parse_qs(urlparse(link).query)["token"][0]


def _request_reset(client, email="asha@example.com"):
    return client.post("/api/student/auth/password-reset/request", json={"email": email})


def test_unknown_email_gets_same_response_and_no_email(client, outbox):
    register_student(client)
    known = _request_reset(client)
    unknown = _request_reset(client, "nobody@example.com")

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox.messages) == 1
    assert outbox.messages[0].to == "asha@example.com"


def test_reset_flow_changes_password_and_signs_out_everywhere(client, make_client, outbox):
    register_student(client)
    _request_reset(client)
    token = _token_from(outbox)

    confirm = make_client().post(
        "/api/student/auth/password-reset/confirm",
        json={"token": token, "new_password": "fresh-password-9"},
    )
    assert confirm.status_code == 200
    assert client.get("/api/student/auth/me").status_code == 401

    old = make_client().post(
        "/api/student/auth/login", json={"email": "asha@example.com", "password": STUDENT_PASSWORD}
    )
    assert old.status_code == 401
    login_student(make_client(), password="fresh-password-9")

    reuse = make_client().post(
        "/api/student/auth/password-reset/confirm",
        json={"token": token, "new_password": "another-password-9"},
    )
    assert reuse.status_code == 400


def test_only_the_newest_reset_link_works(client, outbox):
    register_student(client)
    _request_reset(client)
    first = _token_from(outbox)
    _request_reset(client)
    second = _token_from(outbox)

    stale = client.post(
        "/api/student/auth/password-reset/confirm",
        json={"token": first, "new_password": "fresh-password-9"},
    )
    fresh = client.post(
        "/api/student/auth/password-reset/confirm",
        json={"token": second, "new_password": "fresh-password-9"},
    )
    assert stale.status_code == 400
    assert fresh.status_code == 200


def test_expired_reset_link_is_rejected(client, outbox, db):
    register_student(client)
    _request_reset(client)
    db.execute(update(PasswordResetToken).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()

    response = client.post(
        "/api/student/auth/password-reset/confirm",
        json={"token": _token_from(outbox), "new_password": "fresh-password-9"},
    )
    assert response.status_code == 400


def test_reset_clears_lockout(client, make_client, outbox):
    register_student(client)
    for _ in range(5):
        make_client().post(
            "/api/student/auth/login", json={"email": "asha@example.com", "password": "guess-12345"}
        )
    _request_reset(client)
    client.post(
        "/api/student/auth/password-reset/confirm",
        json={"token": _token_from(outbox), "new_password": "fresh-password-9"},
    )
    login_student(make_client(), password="fresh-password-9")
