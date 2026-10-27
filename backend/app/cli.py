"""Operational commands.

    uv run python -m app.cli sync-rbac
    uv run python -m app.cli create-admin --email ops@example.com --name "Ops Lead"
    uv run python -m app.cli generate-credentials-key
    uv run python -m app.cli rotate-credentials
    uv run python -m app.cli run-worker

`create-admin` reads the password from IPP_BOOTSTRAP_ADMIN_PASSWORD if set, otherwise prompts.

Rotating the credential key: put a new key in front of the old one in IPP_CREDENTIALS_KEYS
("new,old"), restart, run `rotate-credentials`, then remove the old key.
"""

import argparse
import getpass
import os
import sys

from cryptography.fernet import Fernet
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from app.auth.permissions import SUPER_ADMIN, SYSTEM_ROLES
from app.auth.rbac import sync_rbac
from app.core.db import SessionLocal
from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, hash_password
from app.core.vault import VaultError, get_vault
from app.models import AdminUser, Role, SourceCredential
from app.schemas.common import NormalizedEmail


def _read_password() -> str:
    password = os.environ.get("IPP_BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords do not match.")
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        sys.exit(f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters.")
    return password


def create_admin(email: str, name: str, role_key: str) -> None:
    # Validate exactly as the login endpoint does, or the account could never sign in
    # (e.g. special-use domains such as .local are rejected there).
    try:
        email = TypeAdapter(NormalizedEmail).validate_python(email)
    except ValidationError as exc:
        sys.exit(f"Invalid email address: {exc.errors()[0]['msg']}")
    with SessionLocal() as db:
        sync_rbac(db)
        if db.scalar(select(AdminUser.id).where(AdminUser.email == email)):
            sys.exit(f"An admin with email {email} already exists.")
        role = db.scalar(select(Role).where(Role.key == role_key))
        if role is None:
            sys.exit(f"Unknown role {role_key!r}.")
        db.add(
            AdminUser(
                email=email,
                full_name=name.strip(),
                password_hash=hash_password(_read_password()),
                roles=[role],
            )
        )
        db.commit()
    print(f"Created admin {email} with role {role.name}.")


def rotate_credentials() -> None:
    vault = get_vault()
    if vault is None:
        sys.exit("IPP_CREDENTIALS_KEYS is not set.")
    rotated = 0
    with SessionLocal() as db:
        for credential in db.scalars(select(SourceCredential)):
            if credential.key_id == vault.current_key_id:
                continue
            try:
                credential.ciphertext = vault.rotate(credential.ciphertext)
            except VaultError as exc:
                sys.exit(f"Source {credential.source_id}: {exc}")
            credential.key_id = vault.current_key_id
            rotated += 1
        db.commit()
    print(f"Re-encrypted {rotated} credential set(s) with the newest key.")


def run_worker() -> None:
    import signal
    import threading

    from app.core.config import get_settings
    from app.core.logging import configure_logging
    from app.jobs.runner import start_worker, stop_worker

    configure_logging(get_settings().log_level)
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    start_worker()
    print("Job worker running. Press Ctrl+C to stop.")
    stopped.wait()
    stop_worker()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync-rbac", help="Sync permissions and system roles into the database")
    create = commands.add_parser("create-admin", help="Create an admin account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", default=SUPER_ADMIN, choices=sorted(SYSTEM_ROLES))
    commands.add_parser("generate-credentials-key", help="Print a new key for IPP_CREDENTIALS_KEYS")
    commands.add_parser(
        "rotate-credentials", help="Re-encrypt stored source credentials with the newest key"
    )
    commands.add_parser("run-worker", help="Run background jobs in this process")
    args = parser.parse_args()

    if args.command == "sync-rbac":
        with SessionLocal() as db:
            sync_rbac(db)
        print("Permissions and system roles are in sync.")
    elif args.command == "create-admin":
        create_admin(args.email, args.name, args.role)
    elif args.command == "generate-credentials-key":
        print(Fernet.generate_key().decode())
    elif args.command == "rotate-credentials":
        rotate_credentials()
    elif args.command == "run-worker":
        run_worker()


if __name__ == "__main__":
    main()
