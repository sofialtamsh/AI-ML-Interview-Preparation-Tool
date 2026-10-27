from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import AdminUser, Role

STUDENT_PASSWORD = "correct-horse-42"
ADMIN_PASSWORD = "admin-password-42"


def register_student(
    client: TestClient,
    email: str = "asha@example.com",
    name: str = "Asha Rao",
    password: str = STUDENT_PASSWORD,
) -> dict[str, Any]:
    response = client.post(
        "/api/student/auth/register",
        json={"full_name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_student(
    client: TestClient, email: str = "asha@example.com", password: str = STUDENT_PASSWORD
) -> dict[str, Any]:
    response = client.post("/api/student/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def create_admin(
    email: str = "admin@example.com",
    roles: tuple[str, ...] = ("super_admin",),
    password: str = ADMIN_PASSWORD,
    must_change_password: bool = False,
    name: str = "Platform Admin",
) -> AdminUser:
    with SessionLocal() as db:
        role_rows = list(db.scalars(select(Role).where(Role.key.in_(roles))))
        assert len(role_rows) == len(roles), f"unknown role in {roles}"
        admin = AdminUser(
            email=email,
            full_name=name,
            password_hash=hash_password(password),
            roles=role_rows,
            must_change_password=must_change_password,
        )
        db.add(admin)
        db.commit()
        return admin


def login_admin(
    client: TestClient, email: str = "admin@example.com", password: str = ADMIN_PASSWORD
) -> dict[str, Any]:
    response = client.post("/api/admin/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def role_id(client: TestClient, key: str) -> str:
    roles = client.get("/api/admin/roles").json()
    return next(r["id"] for r in roles if r["key"] == key)
