from tests.helpers import create_admin, login_admin, register_student


def _admin(make_client, roles=("student_success",)):
    create_admin(roles=roles)
    client = make_client()
    login_admin(client)
    return client


def _seed_students(make_client):
    return [
        register_student(make_client(), email="asha@example.com", name="Asha Rao"),
        register_student(make_client(), email="vikram@example.com", name="Vikram Iyer"),
        register_student(make_client(), email="meera@example.com", name="Meera Nair"),
    ]


def test_list_search_filter_and_paginate(make_client):
    admin = _admin(make_client)
    asha, vikram, _ = _seed_students(make_client)

    page = admin.get("/api/admin/students", params={"page_size": 2}).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2

    by_name = admin.get("/api/admin/students", params={"q": "vikram"}).json()
    assert [s["email"] for s in by_name["items"]] == ["vikram@example.com"]

    by_code = admin.get("/api/admin/students", params={"q": asha["student_code"]}).json()
    assert [s["id"] for s in by_code["items"]] == [asha["id"]]

    admin.patch(f"/api/admin/students/{vikram['id']}", json={"status": "suspended"})
    suspended = admin.get("/api/admin/students", params={"status": "suspended"}).json()
    assert [s["id"] for s in suspended["items"]] == [vikram["id"]]


def test_student_detail_includes_login_history(make_client):
    admin = _admin(make_client)
    asha = _seed_students(make_client)[0]

    detail = admin.get(f"/api/admin/students/{asha['id']}").json()
    assert detail["active_sessions"] == 1
    assert detail["recent_logins"][0]["success"] is True
    assert admin.get("/api/admin/students/00000000-0000-0000-0000-000000000000").status_code == 404


def test_status_and_cohort_changes_are_audited(make_client):
    create_admin(email="auditor@example.com", roles=("super_admin",))
    admin = _admin(make_client)
    auditor = make_client()
    login_admin(auditor, email="auditor@example.com")
    asha = _seed_students(make_client)[0]

    cohort = admin.post("/api/admin/cohorts", json={"name": "Batch 2026-A"}).json()
    assert admin.post("/api/admin/cohorts", json={"name": "Batch 2026-A"}).status_code == 409

    updated = admin.patch(
        f"/api/admin/students/{asha['id']}", json={"status": "suspended", "cohort_id": cohort["id"]}
    ).json()
    assert updated["status"] == "suspended"
    assert updated["cohort"]["name"] == "Batch 2026-A"
    cohorts = admin.get("/api/admin/cohorts").json()
    assert cohorts[0]["student_count"] == 1

    cleared = admin.patch(f"/api/admin/students/{asha['id']}", json={"cohort_id": None}).json()
    assert cleared["cohort"] is None
    unknown = admin.patch(
        f"/api/admin/students/{asha['id']}",
        json={"cohort_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert unknown.status_code == 422

    logs = auditor.get("/api/admin/audit-logs", params={"action": "student."}).json()["items"]
    assert len(logs) == 2
    latest, first = logs
    assert first["details"]["status"] == {"from": "active", "to": "suspended"}
    assert first["actor_email"] == "admin@example.com"
    assert latest["details"]["cohort_id"]["to"] is None


def test_viewer_without_manage_permission_cannot_change_students(make_client):
    admin = _admin(make_client, roles=("analyst",))
    asha = _seed_students(make_client)[0]
    assert admin.get(f"/api/admin/students/{asha['id']}").status_code == 200
    blocked = admin.patch(f"/api/admin/students/{asha['id']}", json={"status": "suspended"})
    assert blocked.status_code == 403
    assert admin.post("/api/admin/cohorts", json={"name": "Nope"}).status_code == 403


def test_overview_reports_real_counts(make_client):
    admin = _admin(make_client)
    students = _seed_students(make_client)
    admin.patch(f"/api/admin/students/{students[2]['id']}", json={"status": "suspended"})

    stats = admin.get("/api/admin/overview").json()["students"]
    assert stats["total"] == 3
    assert stats["by_status"] == {"active": 2, "suspended": 1}
    assert stats["new_last_7_days"] == 3
    assert stats["new_last_30_days"] == 3
    assert len(stats["registrations_last_30_days"]) == 30
    assert stats["registrations_last_30_days"][-1]["count"] == 3
    # Suspension revoked the third student's sessions, but they were seen this week.
    assert stats["active_last_7_days"] == 3
    assert [s["email"] for s in stats["recent"]][0] == "meera@example.com"
