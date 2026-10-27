from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import PERMISSION_DESCRIPTIONS, SYSTEM_ROLES
from app.models import Permission, Role


def sync_rbac(db: Session) -> None:
    """Idempotently mirror the code-defined permissions and system roles into the database."""
    existing = {p.key: p for p in db.scalars(select(Permission))}
    for perm, description in PERMISSION_DESCRIPTIONS.items():
        if perm.value in existing:
            existing[perm.value].description = description
        else:
            existing[perm.value] = Permission(key=perm.value, description=description)
            db.add(existing[perm.value])
    for stale_key in set(existing) - {p.value for p in PERMISSION_DESCRIPTIONS}:
        db.delete(existing.pop(stale_key))
    db.flush()

    roles = {r.key: r for r in db.scalars(select(Role).where(Role.key.in_(SYSTEM_ROLES)))}
    for key, definition in SYSTEM_ROLES.items():
        role = roles.get(key) or Role(key=key, is_system=True)
        role.name = definition.name
        role.description = definition.description
        role.is_system = True
        role.permissions = [existing[p.value] for p in sorted(definition.permissions)]
        db.add(role)
    db.commit()
