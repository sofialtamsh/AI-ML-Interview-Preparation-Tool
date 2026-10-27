from unittest.mock import patch

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.cli import create_admin
from app.models import AdminUser
from tests.helpers import create_admin as create_admin_user
from tests.helpers import login_admin


@pytest.fixture
def admin_with_secret(make_client):
    create_admin_user()
    admin = make_client()
    login_admin(admin)
    source = admin.post(
        "/api/admin/sources",
        json={
            "name": "Rotated",
            "connector_type": "json_api",
            "base_url": "https://api.example.com",
            "auth_method": "bearer_token",
        },
    ).json()
    response = admin.put(
        f"/api/admin/sources/{source['id']}/credentials", json={"values": {"token": "rotate-me"}}
    )
    assert response.status_code == 200
    return admin


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


def test_credentials_can_be_rotated_to_a_new_key(monkeypatch, admin_with_secret, db):
    from cryptography.fernet import Fernet

    from app.cli import rotate_credentials
    from app.core.config import get_settings
    from app.core.vault import get_vault
    from app.models import SourceCredential

    old_key = get_settings().credentials_keys.get_secret_value()
    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(get_settings(), "credentials_keys", SecretStr(f"{new_key},{old_key}"))
    rotate_credentials()

    monkeypatch.setattr(get_settings(), "credentials_keys", SecretStr(new_key))  # old key gone
    stored = db.scalar(select(SourceCredential))
    assert get_vault().decrypt(stored.ciphertext) == {"token": "rotate-me"}
    assert stored.key_id == get_vault().current_key_id


def test_generated_credential_keys_are_valid(capsys):
    from cryptography.fernet import Fernet

    from app.cli import main

    with patch("sys.argv", ["app.cli", "generate-credentials-key"]):
        main()
    Fernet(capsys.readouterr().out.strip().encode())  # raises if invalid
