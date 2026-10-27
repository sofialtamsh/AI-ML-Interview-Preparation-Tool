import pytest
from sqlalchemy import select

from app.cli import create_admin
from app.models import AdminUser
from tests.helpers import login_admin


def test_create_admin_rejects_emails_the_login_form_would_refuse(monkeypatch):
    monkeypatch.setenv("IPP_BOOTSTRAP_ADMIN_PASSWORD", "bootstrap-pass-1")
    with pytest.raises(SystemExit, match="Invalid email"):
        create_admin("admin@ipp.local", "Admin", "super_admin")


def test_created_admin_can_sign_in(monkeypatch, client, db):
    monkeypatch.setenv("IPP_BOOTSTRAP_ADMIN_PASSWORD", "bootstrap-pass-1")
    create_admin("  Ops@Example.com ", "Ops Lead", "super_admin")

    assert db.scalar(select(AdminUser.email)) == "ops@example.com"
    me = login_admin(client, email="ops@example.com", password="bootstrap-pass-1")
    assert [r["key"] for r in me["roles"]] == ["super_admin"]
