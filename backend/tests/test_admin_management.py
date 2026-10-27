from sqlalchemy import select

from app.models import AuditLog
from tests.helpers import ADMIN_PASSWORD, create_admin, login_admin, role_id


def _super_admin_client(make_client):
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def test_create_admin_requires_password_change_and_is_audited(make_client, db):
    client = _super_admin_client(make_client)
    response = client.post(
        "/api/admin/admin-users",
        json={
            "email": "Reviewer@Example.com",
            "full_name": "Content Reviewer",
            "temporary_password": "temporary-pass-1",
            "role_ids": [role_id(client, "content_publisher")],
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["email"] == "reviewer@example.com"
    assert created["must_change_password"] is True

    new_admin = make_client()
    me = login_admin(new_admin, email="reviewer@example.com", password="temporary-pass-1")
    assert me["must_change_password"] is True

    log = db.scalar(select(AuditLog).where(AuditLog.action == "admin_user.created"))
    assert log.details == {"email": "reviewer@example.com", "roles": ["content_publisher"]}
    assert "temporary-pass-1" not in str(log.details)


def test_duplicate_admin_email_conflicts(make_client):
    client = _super_admin_client(make_client)
    body = {
        "email": "admin@example.com",
        "full_name": "Dup",
        "temporary_password": "temporary-pass-1",
        "role_ids": [role_id(client, "analyst")],
    }
    assert client.post("/api/admin/admin-users", json=body).status_code == 409


def test_admin_cannot_lock_themselves_out(make_client):
    client = _super_admin_client(make_client)
    me = client.get("/api/admin/auth/me").json()

    disable_self = client.patch(f"/api/admin/admin-users/{me['id']}", json={"status": "disabled"})
    demote_self = client.patch(
        f"/api/admin/admin-users/{me['id']}", json={"role_ids": [role_id(client, "analyst")]}
    )
    assert disable_self.status_code == 409
    assert demote_self.status_code == 409


def test_last_active_super_admin_cannot_be_removed(make_client):
    super_admin = create_admin()
    create_admin(email="team-lead@example.com", roles=("analyst",))
    owner = make_client()
    login_admin(owner)
    # Give a second admin a custom role that can manage admins, but is not Super Admin.
    custom = owner.post(
        "/api/admin/roles",
        json={"name": "Team Lead", "permissions": ["admins.manage", "roles.manage"]},
    ).json()
    lead_id = next(
        a["id"]
        for a in owner.get("/api/admin/admin-users").json()
        if a["email"] == "team-lead@example.com"
    )
    owner.patch(f"/api/admin/admin-users/{lead_id}", json={"role_ids": [custom["id"]]})

    lead = make_client()
    login_admin(lead, email="team-lead@example.com")
    demote = lead.patch(
        f"/api/admin/admin-users/{super_admin.id}", json={"role_ids": [custom["id"]]}
    )
    disable = lead.patch(f"/api/admin/admin-users/{super_admin.id}", json={"status": "disabled"})
    assert demote.status_code == 409
    assert disable.status_code == 409
    assert owner.get("/api/admin/auth/me").status_code == 200


def test_resetting_another_admins_password(make_client):
    client = _super_admin_client(make_client)
    target = create_admin(email="ops@example.com", roles=("analyst",))
    ops = make_client()
    login_admin(ops, email="ops@example.com")

    response = client.patch(
        f"/api/admin/admin-users/{target.id}", json={"temporary_password": "issued-by-admin-1"}
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    assert ops.get("/api/admin/auth/me").status_code == 401
    old = make_client().post(
        "/api/admin/auth/login", json={"email": "ops@example.com", "password": ADMIN_PASSWORD}
    )
    assert old.status_code == 401


def test_custom_role_lifecycle(make_client):
    client = _super_admin_client(make_client)
    created = client.post(
        "/api/admin/roles",
        json={"name": "Cohort Mentor", "description": "Mentors", "permissions": ["students.view"]},
    )
    assert created.status_code == 201
    role = created.json()
    assert role["key"] == "custom_cohort_mentor"
    assert role["is_system"] is False

    updated = client.patch(
        f"/api/admin/roles/{role['id']}",
        json={"permissions": ["students.view", "analytics.view"]},
    )
    assert updated.json()["permissions"] == ["analytics.view", "students.view"]

    invalid = client.post(
        "/api/admin/roles", json={"name": "Bad", "permissions": ["not.a.permission"]}
    )
    assert invalid.status_code == 422

    mentor = create_admin(email="mentor@example.com", roles=("analyst",))
    client.patch(f"/api/admin/admin-users/{mentor.id}", json={"role_ids": [role["id"]]})
    assert client.delete(f"/api/admin/roles/{role['id']}").status_code == 409

    client.patch(
        f"/api/admin/admin-users/{mentor.id}", json={"role_ids": [role_id(client, "analyst")]}
    )
    assert client.delete(f"/api/admin/roles/{role['id']}").status_code == 204


def test_system_roles_are_read_only(make_client):
    client = _super_admin_client(make_client)
    super_role = role_id(client, "super_admin")
    rename = client.patch(f"/api/admin/roles/{super_role}", json={"name": "Renamed"})
    assert rename.status_code == 409
    assert client.delete(f"/api/admin/roles/{super_role}").status_code == 409


def test_roles_list_shows_permissions_and_assignment_counts(make_client):
    client = _super_admin_client(make_client)
    roles = {r["key"]: r for r in client.get("/api/admin/roles").json()}
    assert roles["super_admin"]["admin_count"] == 1
    all_permissions = client.get("/api/admin/permissions").json()
    assert len(roles["super_admin"]["permissions"]) == len(all_permissions)
    assert roles["analyst"]["admin_count"] == 0
