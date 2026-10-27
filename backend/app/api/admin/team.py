"""Admin accounts and roles. Guards ensure the platform can never be left without a
working Super Admin, and an admin cannot lock themselves out."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import SUPER_ADMIN, Perm
from app.auth.sessions import revoke_sessions
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import hash_password
from app.models import AdminStatus, AdminUser, Permission, Role
from app.models.admin import admin_user_roles
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)

router = APIRouter(tags=["admin-team"])

can_manage_admins = require_permission(Perm.ADMINS_MANAGE)
can_manage_roles = require_permission(Perm.ROLES_MANAGE)
can_read_roles = require_any_permission(Perm.ADMINS_MANAGE, Perm.ROLES_MANAGE)


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def _load_roles(db: Session, role_ids: list[uuid.UUID]) -> list[Role]:
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids))).all()
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown role selected.")
    return list(roles)


def _ensure_active_super_admin_remains(db: Session) -> None:
    db.flush()
    remaining = db.scalar(
        select(func.count(func.distinct(AdminUser.id)))
        .join(admin_user_roles, admin_user_roles.c.admin_user_id == AdminUser.id)
        .join(Role, Role.id == admin_user_roles.c.role_id)
        .where(Role.key == SUPER_ADMIN, AdminUser.status == AdminStatus.ACTIVE)
    )
    if not remaining:
        db.rollback()
        raise _conflict("At least one active Super Admin must remain.")


# --- Admin users ------------------------------------------------------------------------


@router.get(
    "/admin-users", response_model=list[AdminUserOut], dependencies=[Depends(can_manage_admins)]
)
def list_admin_users(db: Session = Depends(get_db)) -> list[AdminUser]:
    return list(db.scalars(select(AdminUser).order_by(AdminUser.full_name)))


@router.post("/admin-users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    body: AdminUserCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage_admins),
    db: Session = Depends(get_db),
) -> AdminUser:
    if db.scalar(select(AdminUser.id).where(AdminUser.email == body.email)):
        raise _conflict("An admin with this email already exists.")
    admin = AdminUser(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.temporary_password),
        must_change_password=True,
        roles=_load_roles(db, body.role_ids),
    )
    db.add(admin)
    db.flush()
    record_audit(
        db,
        request,
        ctx,
        "admin_user.created",
        "admin_user",
        admin.id,
        {"email": admin.email, "roles": [r.key for r in admin.roles]},
    )
    db.commit()
    return admin


@router.patch("/admin-users/{admin_id}", response_model=AdminUserOut)
def update_admin_user(
    admin_id: uuid.UUID,
    body: AdminUserUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage_admins),
    db: Session = Depends(get_db),
) -> AdminUser:
    admin = db.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Admin not found.")
    is_self = admin.id == ctx.admin.id
    changes: dict[str, object] = {}

    if body.full_name is not None and body.full_name != admin.full_name:
        changes["full_name"] = {"from": admin.full_name, "to": body.full_name}
        admin.full_name = body.full_name

    if body.status is not None and body.status != admin.status:
        if is_self:
            raise _conflict("You cannot change the status of your own account.")
        changes["status"] = {"from": admin.status.value, "to": body.status.value}
        admin.status = body.status
        if body.status is AdminStatus.DISABLED:
            revoke_sessions(db, admin_user_id=admin.id)

    if body.role_ids is not None:
        roles = _load_roles(db, body.role_ids)
        before, after = sorted(r.key for r in admin.roles), sorted(r.key for r in roles)
        if before != after:
            granted = {p.key for r in roles for p in r.permissions}
            if is_self and Perm.ADMINS_MANAGE.value not in granted:
                raise _conflict("You cannot remove your own admin-management access.")
            changes["roles"] = {"from": before, "to": after}
            admin.roles = roles

    if body.temporary_password is not None:
        if is_self:
            raise _conflict("Use 'Change password' to change your own password.")
        admin.password_hash = hash_password(body.temporary_password)
        admin.must_change_password = True
        admin.failed_login_count = 0
        admin.locked_until = None
        revoke_sessions(db, admin_user_id=admin.id)
        changes["password"] = "reset_by_admin"  # noqa: S105 (a marker; never the password)

    if changes:
        _ensure_active_super_admin_remains(db)
        record_audit(db, request, ctx, "admin_user.updated", "admin_user", admin.id, changes)
        db.commit()
    return admin


# --- Roles & permissions ----------------------------------------------------------------


def _role_counts(db: Session) -> dict[uuid.UUID, int]:
    return dict(
        db.execute(
            select(admin_user_roles.c.role_id, func.count()).group_by(admin_user_roles.c.role_id)
        ).all()
    )


def _custom_role(db: Session, role_id: uuid.UUID) -> Role:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found.")
    if role.is_system:
        raise _conflict("System roles are defined by the platform and cannot be modified.")
    return role


def _permissions(db: Session, keys: list[Perm]) -> list[Permission]:
    return list(db.scalars(select(Permission).where(Permission.key.in_([k.value for k in keys]))))


@router.get(
    "/permissions", response_model=list[PermissionOut], dependencies=[Depends(can_read_roles)]
)
def list_permissions(db: Session = Depends(get_db)) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.key)))


@router.get("/roles", response_model=list[RoleOut], dependencies=[Depends(can_read_roles)])
def list_roles(db: Session = Depends(get_db)) -> list[RoleOut]:
    counts = _role_counts(db)
    roles = db.scalars(select(Role).order_by(Role.is_system.desc(), Role.name))
    return [RoleOut.of(r, counts.get(r.id, 0)) for r in roles]


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    body: RoleCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage_roles),
    db: Session = Depends(get_db),
) -> RoleOut:
    key = "custom_" + re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_")
    if db.scalar(select(Role.id).where((Role.key == key) | (Role.name == body.name))):
        raise _conflict("A role with this name already exists.")
    role = Role(
        key=key,
        name=body.name,
        description=body.description,
        is_system=False,
        permissions=_permissions(db, body.permissions),
    )
    db.add(role)
    db.flush()
    record_audit(
        db,
        request,
        ctx,
        "role.created",
        "role",
        role.id,
        {"name": role.name, "permissions": [p.key for p in role.permissions]},
    )
    db.commit()
    return RoleOut.of(role, 0)


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage_roles),
    db: Session = Depends(get_db),
) -> RoleOut:
    role = _custom_role(db, role_id)
    changes: dict[str, object] = {}
    if body.name is not None and body.name != role.name:
        if db.scalar(select(Role.id).where(Role.name == body.name, Role.id != role.id)):
            raise _conflict("A role with this name already exists.")
        changes["name"] = {"from": role.name, "to": body.name}
        role.name = body.name
    if body.description is not None and body.description != role.description:
        changes["description"] = "updated"
        role.description = body.description
    if body.permissions is not None:
        before = sorted(p.key for p in role.permissions)
        after = sorted({p.value for p in body.permissions})
        if before != after:
            changes["permissions"] = {"from": before, "to": after}
            role.permissions = _permissions(db, body.permissions)
    if changes:
        record_audit(db, request, ctx, "role.updated", "role", role.id, changes)
        db.commit()
    return RoleOut.of(role, _role_counts(db).get(role.id, 0))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_manage_roles),
    db: Session = Depends(get_db),
) -> None:
    role = _custom_role(db, role_id)
    if _role_counts(db).get(role.id, 0):
        raise _conflict("Unassign this role from all admins before deleting it.")
    record_audit(db, request, ctx, "role.deleted", "role", role.id, {"name": role.name})
    db.delete(role)
    db.commit()
