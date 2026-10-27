"""Interview Data Sources through the admin API: configuration, secrets, runs, imports, records."""

from datetime import timedelta
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import utcnow
from app.core.vault import get_vault
from app.jobs.runner import recover_stale_jobs, run_pending_jobs
from app.models import AuditLog, Job, JobStatus, RawSourceRecord, SourceCredential
from app.sources import service
from tests.fakeweb import FakeWeb, docx, pdf
from tests.helpers import create_admin, login_admin

SITE = "https://interviews.example.com"
SECRET = "pa55-Very-Secret-Value"


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch) -> FakeWeb:
    fake = FakeWeb()
    monkeypatch.setattr(service, "make_http", lambda *, min_interval: fake.http())
    return fake


@pytest.fixture
def admin(make_client) -> TestClient:
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def api_source(admin: TestClient, **overrides: Any) -> dict[str, Any]:
    body = {
        "name": "Interview API",
        "connector_type": "json_api",
        "base_url": SITE,
        "config": {"endpoint": "/api/questions", "items_path": "items"},
        **overrides,
    }
    response = admin.post("/api/admin/sources", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def serve_questions(web: FakeWeb, items: list[dict[str, Any]], status: int = 200) -> None:
    web.json(f"{SITE}/api/questions", {"items": items}, status=status)


def fetch(admin: TestClient, source_id: str) -> dict[str, Any]:
    started = admin.post(f"/api/admin/sources/{source_id}/fetch")
    assert started.status_code == 202, started.text
    assert run_pending_jobs() == 1
    job = admin.get(f"/api/admin/sources/{source_id}/jobs/{started.json()['id']}")
    return job.json()


# --- Configuration ----------------------------------------------------------------------------


def test_catalog_describes_connectors_and_sign_in_methods(admin):
    catalog = admin.get("/api/admin/sources/catalog").json()
    assert [c["key"] for c in catalog["connectors"]] == [
        "web_pages",
        "json_api",
        "rss_feed",
        "file_upload",
    ]
    web_pages = catalog["connectors"][0]
    max_records = next(f for f in web_pages["settings_fields"] if f["key"] == "max_records")
    assert (max_records["default"], max_records["min"], max_records["max"]) == (50, 1, 1000)
    form = next(m for m in catalog["auth_methods"] if m["key"] == "form_login")
    assert [f["key"] for f in form["secret_fields"]] == ["username", "password"]
    assert catalog["credential_storage_ready"] is True
    assert ".pdf" in catalog["upload_extensions"]


def test_sources_are_created_listed_and_named_uniquely(admin):
    created = api_source(admin, description="Partner API")
    assert created["connection_status"] == "untested"
    assert created["config"]["page_size"] == 50  # defaults filled in
    assert created["credentials"] == {
        "required": [],
        "stored": [],
        "complete": True,
        "updated_at": None,
        "updated_by": None,
    }
    duplicate = admin.post(
        "/api/admin/sources",
        json={"name": "interview api", "connector_type": "rss_feed", "base_url": SITE},
    )
    assert duplicate.status_code == 409
    assert [s["name"] for s in admin.get("/api/admin/sources").json()] == ["Interview API"]


@pytest.mark.parametrize(
    ("body", "field", "message"),
    [
        ({"base_url": "ftp://files.example.com"}, "base_url", "http"),
        ({"base_url": "https://user:pw@example.com"}, "base_url", "username or password"),
        ({"base_url": None}, "base_url", "need a URL"),
        ({"config": {"items_path": "data..x"}}, "items_path", "pattern"),
        ({"config": {"endpoint": "https://other.com/api"}}, "endpoint", "same site"),
        ({"config": {"pagination": "cursor"}}, "next_path", "Required"),
        ({"config": {"surprise": 1}}, "surprise", "Extra inputs"),
        (
            {"connector_type": "web_pages", "config": {"link_selector": "a[["}},
            "link_selector",
            "not a valid CSS selector",
        ),
        (
            {"connector_type": "web_pages", "config": {"start_urls": [SITE, "https://x.com/"]}},
            "start_urls",
            "https://x.com/ is not on the same site",
        ),
        (
            {"auth_method": "api_key_header", "auth_config": {"header_name": "Host"}},
            "header_name",
            "can't be used",
        ),
    ],
)
def test_invalid_settings_are_rejected_per_field(admin, body, field, message):
    payload = {"name": "Bad", "connector_type": "json_api", "base_url": SITE, **body}
    response = admin.post("/api/admin/sources", json=payload)
    assert response.status_code == 422, response.text
    problem = next(d for d in response.json()["detail"] if d["loc"][-1] == field)
    assert message in problem["msg"]


def test_a_sign_in_method_must_suit_the_connector(admin):
    response = admin.post(
        "/api/admin/sources",
        json={
            "name": "Feed",
            "connector_type": "rss_feed",
            "base_url": SITE,
            "auth_method": "form_login",
            "auth_config": {"login_url": f"{SITE}/login"},
        },
    )
    assert response.status_code == 422
    assert "can't be used with RSS / Atom feed sources" in response.json()["detail"]


def test_file_import_sources_need_no_url(admin):
    created = admin.post(
        "/api/admin/sources",
        json={"name": "Alumni notes", "connector_type": "file_upload", "base_url": SITE},
    ).json()
    assert created["base_url"] is None
    assert created["connection_status"] == "manual_import_required"
    assert admin.post(f"/api/admin/sources/{created['id']}/test").status_code == 409
    assert admin.post(f"/api/admin/sources/{created['id']}/fetch").status_code == 409


# --- Credentials ------------------------------------------------------------------------------


def _with_basic_auth(admin: TestClient) -> dict[str, Any]:
    source = api_source(admin, auth_method="http_basic")
    assert source["credentials"]["complete"] is False
    response = admin.put(
        f"/api/admin/sources/{source['id']}/credentials",
        json={"values": {"username": "ops@example.com", "password": SECRET}},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_credentials_are_encrypted_and_never_returned(admin, db: Session):
    source = _with_basic_auth(admin)
    assert source["credentials"]["stored"] == ["password", "username"]
    assert source["credentials"]["complete"] is True
    assert source["credentials"]["updated_by"] == "Platform Admin"

    stored = db.scalar(select(SourceCredential))
    assert SECRET not in stored.ciphertext and "ops@example.com" not in stored.ciphertext
    assert get_vault().decrypt(stored.ciphertext)["password"] == SECRET

    responses = [
        admin.get("/api/admin/sources"),
        admin.get(f"/api/admin/sources/{source['id']}"),
        admin.get("/api/admin/audit-logs"),
    ]
    for response in responses:
        assert response.status_code == 200
        assert SECRET not in response.text and "ops@example.com" not in response.text
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "source.credentials_set"))
    assert audit.details == {"fields": ["password", "username"]}


def test_blank_values_keep_the_stored_secret(admin, db: Session):
    source = _with_basic_auth(admin)
    admin.put(
        f"/api/admin/sources/{source['id']}/credentials",
        json={"values": {"username": "new@example.com", "password": ""}},
    )
    values = get_vault().decrypt(db.scalar(select(SourceCredential)).ciphertext)
    assert values == {"username": "new@example.com", "password": SECRET}


def test_credential_input_is_checked(admin):
    source = api_source(admin, auth_method="http_basic")
    path = f"/api/admin/sources/{source['id']}/credentials"
    missing = admin.put(path, json={"values": {"username": "a"}})
    assert (missing.status_code, missing.json()["detail"]) == (422, "Enter: Password.")
    unknown = admin.put(path, json={"values": {"username": "a", "password": "b", "pin": "1"}})
    assert unknown.status_code == 422 and "pin" in unknown.json()["detail"]
    too_long = admin.put(path, json={"values": {"username": "a", "password": "x" * 5000}})
    assert too_long.status_code == 422 and "x" * 50 not in too_long.text


def test_credentials_need_storage_to_be_configured(admin, monkeypatch):
    monkeypatch.setattr(get_settings(), "credentials_keys", None)
    source = api_source(admin, auth_method="bearer_token")
    response = admin.put(
        f"/api/admin/sources/{source['id']}/credentials", json={"values": {"token": "t"}}
    )
    assert response.status_code == 422
    assert "IPP_CREDENTIALS_KEYS" in response.json()["detail"]
    assert admin.get("/api/admin/sources/catalog").json()["credential_storage_ready"] is False


def test_moving_a_source_to_another_site_clears_its_credentials(admin, db: Session):
    source = _with_basic_auth(admin)
    moved = admin.patch(
        f"/api/admin/sources/{source['id']}",
        json={"base_url": "https://attacker.example.net", "config": {}},
    ).json()
    assert moved["credentials"]["stored"] == []
    assert db.scalar(select(SourceCredential)) is None
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "source.updated"))
    assert audit.details["credentials_cleared"] == "the site they are sent to changed"


def test_switching_sign_in_method_keeps_only_the_secrets_it_uses(admin, db: Session):
    source = api_source(admin, connector_type="web_pages", config={}, auth_method="http_basic")
    admin.put(
        f"/api/admin/sources/{source['id']}/credentials",
        json={"values": {"username": "u", "password": SECRET}},
    )
    to_form = admin.patch(
        f"/api/admin/sources/{source['id']}",
        json={"auth_method": "form_login", "auth_config": {"login_url": f"{SITE}/login"}},
    ).json()
    assert to_form["credentials"]["complete"] is True  # username and password carry over
    to_token = admin.patch(
        f"/api/admin/sources/{source['id']}",
        json={"auth_method": "bearer_token", "auth_config": {}},
    ).json()
    assert to_token["credentials"] == {**to_token["credentials"], "stored": [], "complete": False}
    assert db.scalar(select(SourceCredential)) is None


def test_editing_sources_and_setting_credentials_are_separate_permissions(make_client):
    create_admin()
    owner = make_client()
    login_admin(owner)
    source = api_source(owner, auth_method="bearer_token")

    editor = make_client()
    owner.post(
        "/api/admin/roles",
        json={"name": "Source editor", "permissions": ["sources.view", "sources.manage"]},
    )
    role = next(r for r in owner.get("/api/admin/roles").json() if r["name"] == "Source editor")
    owner.post(
        "/api/admin/admin-users",
        json={
            "email": "editor@example.com",
            "full_name": "Ed Itor",
            "temporary_password": "temporary-pass-1",
            "role_ids": [role["id"]],
        },
    )
    login_admin(editor, email="editor@example.com", password="temporary-pass-1")
    editor.post(
        "/api/admin/auth/change-password",
        json={"current_password": "temporary-pass-1", "new_password": "editor-pass-123"},
    )
    path = f"/api/admin/sources/{source['id']}/credentials"
    assert editor.put(path, json={"values": {"token": "t"}}).status_code == 403
    assert editor.delete(path).status_code == 403
    assert (
        editor.patch(f"/api/admin/sources/{source['id']}", json={"enabled": False}).status_code
        == 200
    )


@pytest.mark.parametrize("role", ["analyst", "student_success", "content_publisher"])
def test_roles_without_source_access_are_refused(make_client, role):
    create_admin(email="owner@example.com")
    owner = make_client()
    login_admin(owner, email="owner@example.com")
    source = api_source(owner)
    create_admin(email="other@example.com", roles=(role,))
    other = make_client()
    login_admin(other, email="other@example.com")
    assert other.get("/api/admin/sources").status_code == 403
    assert other.get(f"/api/admin/sources/{source['id']}").status_code == 403
    assert other.post(f"/api/admin/sources/{source['id']}/fetch").status_code == 403


# --- Connection tests and fetches ---------------------------------------------------------------


def test_connection_test_reports_success_and_failure(admin, web, db: Session):
    source = _with_basic_auth(admin)
    serve_questions(web, [{"id": 1}, {"id": 2}])
    tested = admin.post(f"/api/admin/sources/{source['id']}/test").json()
    assert tested["connection_status"] == "ok"
    assert tested["connection_message"] == "Connected. The first page has 2 items."
    assert web.requests[0].headers["authorization"].startswith("Basic ")

    serve_questions(web, [], status=401)
    failed = admin.post(f"/api/admin/sources/{source['id']}/test").json()
    assert failed["connection_status"] == "failed"
    assert "Check the credentials" in failed["connection_message"]
    assert SECRET not in failed["connection_message"]
    results = db.scalars(
        select(AuditLog.details).where(AuditLog.action == "source.connection_tested")
    ).all()
    assert [d["result"] for d in results] == ["ok", "failed"]


def test_a_fetch_stores_records_and_later_runs_are_incremental(admin, web, db: Session):
    source = api_source(
        admin, config={"endpoint": "/api/questions", "items_path": "items", "title_field": "q"}
    )
    serve_questions(web, [{"id": 1, "q": "What is dropout?"}, {"id": 2, "q": "Define recall"}])

    first = fetch(admin, source["id"])
    assert first["status"] == "succeeded"
    assert first["result"] == {
        "seen": 2,
        "new": 2,
        "updated": 0,
        "unchanged": 0,
        "skipped_known": 0,
    }
    assert first["events"][-1]["message"] == "Finished."

    serve_questions(web, [{"id": 1, "q": "What is dropout?"}, {"id": 2, "q": "Define recall."}])
    second = fetch(admin, source["id"])
    assert second["result"]["unchanged"] == 1 and second["result"]["updated"] == 1

    revisions = db.execute(
        select(RawSourceRecord.external_id, RawSourceRecord.revision).order_by(RawSourceRecord.id)
    ).all()
    assert revisions == [("1", 1), ("2", 1), ("2", 2)]  # the first version is kept

    detail = admin.get(f"/api/admin/sources/{source['id']}").json()
    assert detail["record_count"] == 2
    assert detail["connection_status"] == "ok"
    assert detail["last_successful_sync_at"] is not None
    history = admin.get(f"/api/admin/sources/{source['id']}/jobs").json()
    assert history["total"] == 2


def test_a_failed_fetch_is_recorded_with_its_reason(admin, web):
    source = api_source(admin)
    serve_questions(web, [], status=500)
    job = fetch(admin, source["id"])
    assert job["status"] == "failed"
    assert "server error (HTTP 500)" in job["error"]
    detail = admin.get(f"/api/admin/sources/{source['id']}").json()
    assert detail["connection_status"] == "failed"
    assert detail["last_attempted_sync_at"] is not None
    assert detail["last_successful_sync_at"] is None


def test_a_blocked_site_is_marked_for_manual_import(admin, web):
    source = api_source(admin, connector_type="web_pages", config={})
    web.route(
        f"{SITE}/robots.txt", lambda _: httpx.Response(200, text="User-agent: *\nDisallow: /")
    )
    job = fetch(admin, source["id"])
    assert job["status"] == "failed"
    detail = admin.get(f"/api/admin/sources/{source['id']}").json()
    assert detail["connection_status"] == "manual_import_required"


def test_fetches_only_start_when_the_source_is_ready(admin, web):
    source = api_source(admin, auth_method="bearer_token")
    path = f"/api/admin/sources/{source['id']}/fetch"
    assert admin.post(path).json()["detail"] == "The source needs credentials first."
    admin.put(f"/api/admin/sources/{source['id']}/credentials", json={"values": {"token": "t"}})
    admin.patch(f"/api/admin/sources/{source['id']}", json={"enabled": False})
    assert admin.post(path).json()["detail"] == "The source is turned off."
    admin.patch(f"/api/admin/sources/{source['id']}", json={"enabled": True})
    assert admin.post(path).status_code == 202
    again = admin.post(path)
    assert (again.status_code, again.json()["detail"]) == (
        409,
        "A fetch is already running for this source.",
    )


def test_several_sources_can_be_fetched_at_once(admin, web):
    one = api_source(admin, name="One")
    two = api_source(admin, name="Two", auth_method="bearer_token")
    serve_questions(web, [{"id": 1}])
    result = admin.post("/api/admin/sources/fetch", json={"source_ids": [one["id"], two["id"]]})
    assert result.status_code == 202
    body = result.json()
    assert [j["source_id"] for j in body["started"]] == [one["id"]]
    assert body["skipped"] == [
        {"source_id": two["id"], "name": "Two", "reason": "The source needs credentials first."}
    ]
    assert run_pending_jobs() == 1


def test_a_queued_fetch_can_be_stopped(admin, web):
    source = api_source(admin)
    job = admin.post(f"/api/admin/sources/{source['id']}/fetch").json()
    stopped = admin.post(f"/api/admin/sources/{source['id']}/jobs/{job['id']}/cancel").json()
    assert stopped["status"] == "cancelled"
    assert run_pending_jobs() == 0
    again = admin.post(f"/api/admin/sources/{source['id']}/jobs/{job['id']}/cancel")
    assert again.status_code == 409


def test_a_running_fetch_stops_at_the_next_record(admin, web, db: Session):
    source = api_source(admin, config={"endpoint": "/api/questions", "items_path": "items"})

    def page_then_stop(request: httpx.Request) -> httpx.Response:
        # The admin presses Stop while the worker is mid-run.
        with db.begin():
            db.execute(update(Job).values(cancel_requested=True))
        return httpx.Response(200, json={"items": [{"id": 1}, {"id": 2}, {"id": 3}]})

    web.route(f"{SITE}/api/questions", page_then_stop)
    job = fetch(admin, source["id"])
    assert job["status"] == "cancelled"
    assert job["result"]["seen"] <= 1
    assert job["events"][-1]["message"] == "Stopped by an admin."


def test_interrupted_jobs_are_marked_failed(admin, db: Session):
    source = api_source(admin)
    job_id = admin.post(f"/api/admin/sources/{source['id']}/fetch").json()["id"]
    with db.begin():
        db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.RUNNING, heartbeat_at=utcnow() - timedelta(hours=1))
        )
    assert recover_stale_jobs() == 1
    job = admin.get(f"/api/admin/sources/{source['id']}/jobs/{job_id}").json()
    assert job["status"] == "failed" and job["error"].startswith("Interrupted")


# --- Removal ------------------------------------------------------------------------------------


def test_removing_a_source_keeps_its_records_but_deletes_its_secrets(admin, web, db: Session):
    source = _with_basic_auth(admin)
    serve_questions(web, [{"id": 1}])
    fetch(admin, source["id"])

    assert admin.delete(f"/api/admin/sources/{source['id']}").status_code == 204
    assert admin.get("/api/admin/sources").json() == []
    removed = admin.get("/api/admin/sources", params={"include_removed": True}).json()
    assert removed[0]["removed_at"] is not None and removed[0]["enabled"] is False
    assert db.scalar(select(SourceCredential)) is None
    assert db.scalar(select(RawSourceRecord.external_id)) == "1"
    assert (
        admin.patch(f"/api/admin/sources/{source['id']}", json={"name": "Renamed"}).status_code
        == 409
    )
    assert api_source(admin)["name"] == "Interview API"  # the name can be reused


# --- File imports -------------------------------------------------------------------------------


def _upload(admin: TestClient, source_id: str, name: str, data: bytes, **form: str):
    return admin.post(
        f"/api/admin/sources/{source_id}/upload", files={"file": (name, data)}, data=form
    )


def test_files_can_be_imported_into_any_source(admin, db: Session):
    source = api_source(admin)
    csv = b"id,question\n1,What is dropout?\n2,Explain ROC AUC\n"
    first = _upload(admin, source["id"], "export.csv", csv, id_field="id", title_field="question")
    assert first.status_code == 201, first.text
    assert first.json()["kind"] == "source_import"
    assert first.json()["result"]["new"] == 2
    assert first.json()["file_name"] == "export.csv"
    again = _upload(admin, source["id"], "export.csv", csv, id_field="id")
    assert again.json()["result"]["unchanged"] == 2

    assert (
        _upload(admin, source["id"], "notes.docx", docx("Round 1", "SQL joins")).status_code == 201
    )
    assert _upload(admin, source["id"], "paper.pdf", pdf("Explain attention")).status_code == 201
    assert db.scalar(select(text("count(*)")).select_from(RawSourceRecord)) == 4
    audit = db.scalars(
        select(AuditLog.details).where(AuditLog.action == "source.file_imported")
    ).all()
    assert audit[0]["file_name"] == "export.csv" and audit[0]["new"] == 2


def test_unreadable_uploads_are_refused_and_recorded(admin):
    source = api_source(admin)
    bad = _upload(admin, source["id"], "../../etc/old.doc", b"binary")
    assert bad.status_code == 422 and "Save it as .docx" in bad.json()["detail"]
    history = admin.get(f"/api/admin/sources/{source['id']}/jobs").json()["items"]
    assert history[0]["status"] == "failed" and history[0]["file_name"] == "old.doc"

    big = _upload(admin, source["id"], "big.txt", b"x" * (10 * 1024 * 1024 + 1))
    assert big.status_code == 413


# --- Raw records ------------------------------------------------------------------------------


def test_raw_records_need_intelligence_access(make_client):
    create_admin(email="ops@example.com", roles=("intelligence_operator",))
    ops = make_client()
    login_admin(ops, email="ops@example.com")
    source = api_source(ops)
    _upload(
        ops,
        source["id"],
        "q.json",
        b'[{"id": 1, "question": "What is a p-value?"}]',
        id_field="id",
        title_field="question",
    )

    listed = ops.get(f"/api/admin/sources/{source['id']}/records").json()
    assert listed["total"] == 1
    record = listed["items"][0]
    assert record["title"] == "What is a p-value?"
    detail = ops.get(f"/api/admin/sources/{source['id']}/records/{record['id']}").json()
    assert '"question": "What is a p-value?"' in detail["content"]
    assert detail["meta"]["file_name"] == "q.json"
    searched = ops.get(f"/api/admin/sources/{source['id']}/records", params={"q": "nothing"})
    assert searched.json()["total"] == 0

    create_admin(email="success@example.com", roles=("student_success",))
    success = make_client()
    login_admin(success, email="success@example.com")
    assert success.get(f"/api/admin/sources/{source['id']}/records").status_code == 403


# --- Permanence ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("table", "statement"),
    [
        ("raw_source_records", "UPDATE raw_source_records SET content = 'rewritten'"),
        ("raw_source_records", "DELETE FROM raw_source_records"),
        ("job_events", "UPDATE job_events SET message = 'rewritten'"),
        ("job_events", "DELETE FROM job_events"),
        ("jobs", "DELETE FROM jobs"),
        ("interview_sources", "DELETE FROM interview_sources"),
    ],
)
def test_source_records_and_history_are_permanent(admin, db: Session, table, statement):
    source = api_source(admin)
    _upload(admin, source["id"], "a.txt", b"Explain gradient descent")
    with pytest.raises(DBAPIError, match="append-only|kept permanently"):
        db.execute(text(statement))
    db.rollback()


def test_api_keys_in_urls_never_reach_the_logs(admin, web, caplog):
    from app.core.logging import configure_logging

    configure_logging("INFO")
    source = api_source(admin, auth_method="api_key_query", auth_config={"param_name": "api_key"})
    admin.put(
        f"/api/admin/sources/{source['id']}/credentials", json={"values": {"api_key": SECRET}}
    )
    serve_questions(web, [{"id": 1}])
    with caplog.at_level("DEBUG"):
        job = fetch(admin, source["id"])
    assert job["status"] == "succeeded"
    assert web.requests[0].url.params["api_key"] == SECRET  # it was sent to the source...
    assert SECRET not in caplog.text  # ...but never logged
    assert SECRET not in str(job)
