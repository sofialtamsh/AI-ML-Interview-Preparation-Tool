"""Operational commands.

    uv run python -m app.cli sync-rbac
    uv run python -m app.cli create-admin --email ops@example.com --name "Ops Lead"

`create-admin` reads the password from IPP_BOOTSTRAP_ADMIN_PASSWORD if set, otherwise prompts.
"""

import argparse
import getpass
import os
import sys

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from app.auth.permissions import SUPER_ADMIN, SYSTEM_ROLES
from app.auth.rbac import sync_rbac
from app.core.db import SessionLocal
from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, hash_password
from app.models import AdminUser, Role
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync-rbac", help="Sync permissions and system roles into the database")
    create = commands.add_parser("create-admin", help="Create an admin account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", default=SUPER_ADMIN, choices=sorted(SYSTEM_ROLES))
    args = parser.parse_args()

    if args.command == "sync-rbac":
        with SessionLocal() as db:
            sync_rbac(db)
        print("Permissions and system roles are in sync.")
    elif args.command == "create-admin":
        create_admin(args.email, args.name, args.role)


if __name__ == "__main__":
    main()
