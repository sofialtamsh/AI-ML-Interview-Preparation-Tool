"""Phase 4: learning content. Starter content quality, the review → publish lifecycle, what
students can see, AI generation inside the pilot gate, and narration."""

import contextlib
import copy
import io
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.content.schemas import SCHEMAS, PythonLab
from app.content.seed import PILOT_TOPICS, seed_starter_content, starter_fixture
from app.content.starter import TOPICS
from app.intelligence.taxonomy import seed_default_taxonomy
from app.jobs.runner import run_pending_jobs
from app.models import (
    AiUsageEvent,
    AuditLog,
    Component,
    ConnectorType,
    ContentItem,
    ContentVersion,
    InterviewExperience,
    InterviewQuestion,
    InterviewSource,
    Job,
    JobKind,
    JobStatus,
    MediaAsset,
    QuestionType,
    RawSourceRecord,
    ReviewStatus,
    Topic,
)
from tests.fake_ai import FakeOpenRouter
from tests.helpers import create_admin, login_admin, register_student

SUPERVISED = "machine-learning/supervised-learning"
STARTER = {module.TOPIC: module.CONTENT for module in TOPICS}
SCHEMA_NAMES = {
    "lesson": "Lesson",
    "playground": "Playground",
    "python": "PythonLab",
    "interview": "InterviewPrep",
    "quiz": "Quiz",
    "revision": "Revision",
    "video": "VideoScript",
}


@pytest.fixture
def taxonomy(db: Session) -> None:
    seed_default_taxonomy(db)


@pytest.fixture
def starter(db: Session, taxonomy: None) -> dict[str, int]:
    return seed_starter_content(db)


@pytest.fixture
def admin(make_client, starter) -> TestClient:
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def as_role(make_client, role: str) -> TestClient:
    create_admin(email=f"{role}@example.com", roles=(role,))
    client = make_client()
    login_admin(client, email=f"{role}@example.com")
    return client


def topic_id(db: Session, slug: str) -> str:
    return str(db.scalar(select(Topic.id).where(Topic.slug == slug)))


def latest(admin: TestClient, topic: str, component: str) -> dict[str, Any]:
    state = admin.get(f"/api/admin/content/topics/{topic}").json()
    return next(c for c in state["components"] if c["component"] == component)["latest"]


def step(admin: TestClient, version_id: str, action: str, expect: int = 200) -> dict[str, Any]:
    response = admin.post(
        f"/api/admin/content/versions/{version_id}/transition", json={"action": action}
    )
    assert response.status_code == expect, response.text
    return response.json()


def publish(admin: TestClient, version_id: str) -> dict[str, Any]:
    for action in ("submit", "approve", "publish"):
        result = step(admin, version_id, action)
    return result


def pass_code_check(admin: TestClient, version_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = admin.post(
        f"/api/admin/content/versions/{version_id}/code-checks",
        json={
            "output": body["expected_output"] + "\n",
            "error": None,
            "duration_ms": 900,
            "runtime": "Pyodide 314.0.7",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Starter content quality ----------------------------------------------------------------


@pytest.mark.parametrize("module", TOPICS, ids=lambda m: m.TOPIC)
def test_starter_content_matches_every_component_schema(module):
    assert set(module.CONTENT) == {c.value for c in Component}
    for key, body in module.CONTENT.items():
        SCHEMAS[Component(key)].model_validate(body)


@pytest.mark.parametrize("module", TOPICS, ids=lambda m: m.TOPIC)
def test_every_starter_lab_runs_and_prints_its_expected_output(module):
    lab = PythonLab.model_validate(module.CONTENT["python"])
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        exec(compile(lab.program, module.TOPIC, "exec"), {"__name__": "__lab__"})  # noqa: S102
    assert printed.getvalue().rstrip("\n") == lab.expected_output


def test_refresh_adds_a_draft_only_where_the_starter_changed(
    db: Session, starter, monkeypatch: pytest.MonkeyPatch
):
    assert seed_starter_content(db, refresh=True)["refreshed"] == 0
    module = next(m for m in TOPICS if m.TOPIC == SUPERVISED)
    changed = copy.deepcopy(module.CONTENT)
    changed["quiz"]["questions"][0]["explanation"] = "A clearer explanation."
    monkeypatch.setattr(module, "CONTENT", changed)
    assert seed_starter_content(db, refresh=True)["refreshed"] == 1
    item = db.scalar(
        select(ContentItem)
        .join(Topic)
        .where(Topic.slug == SUPERVISED, ContentItem.component == "quiz")
    )
    numbers = db.scalars(
        select(ContentVersion.number).where(ContentVersion.item_id == item.id)
    ).all()
    assert sorted(numbers) == [1, 2]
    assert seed_starter_content(db, refresh=True)["refreshed"] == 0  # idempotent


def test_frontend_fixture_matches_the_starter_content():
    """The frontend renders this fixture in its tests; regenerate it with
    `python -m app.cli export-starter-fixture` when the starter content or schemas change."""
    fixture = Path(__file__).parents[2] / "frontend/src/test/fixtures/starter-content.json"
    if not fixture.exists():
        pytest.skip("frontend checkout not present")
    assert json.loads(fixture.read_text(encoding="utf-8")) == starter_fixture()


def test_seeding_marks_the_pilot_and_creates_drafts_once(db: Session, taxonomy):
    first = seed_starter_content(db)
    assert first == {"pilot_topics": 6, "drafts_created": 42, "already_present": 0, "refreshed": 0}
    again = seed_starter_content(db)
    assert again == {"pilot_topics": 6, "drafts_created": 0, "already_present": 42, "refreshed": 0}
    pilots = db.scalars(select(Topic.slug).where(Topic.is_pilot.is_(True))).all()
    assert sorted(pilots) == sorted(PILOT_TOPICS)
    versions = db.scalars(select(ContentVersion)).unique().all()
    assert {v.status.value for v in versions} == {"draft"}
    assert {v.origin.value for v in versions} == {"starter"}
    assert all("development assistant" in (v.note or "") for v in versions)


# --- Lifecycle --------------------------------------------------------------------------------


def test_students_only_ever_see_published_content(admin, make_client, db: Session):
    student = make_client()
    register_student(student)
    assert student.get("/api/student/learn").json() == []
    assert student.get(f"/api/student/learn/topics/{SUPERVISED}").status_code == 404

    tid = topic_id(db, SUPERVISED)
    lesson = latest(admin, tid, "lesson")
    published = publish(admin, lesson["id"])
    assert published["published"] is True and published["status"] == "published"

    domains = student.get("/api/student/learn").json()
    assert [d["name"] for d in domains] == ["Machine Learning"]
    card = domains[0]["topics"][0]
    assert card["slug"] == SUPERVISED and card["sections"] == ["lesson"]
    assert card["tagline"] == STARTER[SUPERVISED]["lesson"]["tagline"]

    page = student.get(f"/api/student/learn/topics/{SUPERVISED}").json()
    assert page["lesson"]["cards"][0]["title"] == "Your inbox already does this"
    assert page["quiz"] is None and page["python"] is None  # still drafts

    step(admin, lesson["id"], "unpublish")
    assert student.get("/api/student/learn").json() == []


def test_python_labs_need_a_passing_code_check_to_publish(admin, db: Session):
    tid = topic_id(db, SUPERVISED)
    lab = latest(admin, tid, "python")
    step(admin, lab["id"], "submit")
    step(admin, lab["id"], "approve")
    blocked = step(admin, lab["id"], "publish", expect=409)
    assert "code check" in blocked["detail"]

    wrong = admin.post(
        f"/api/admin/content/versions/{lab['id']}/code-checks",
        json={"output": "something else", "error": None, "duration_ms": 10, "runtime": "Pyodide"},
    ).json()
    assert wrong["passed"] is False
    crashed = admin.post(
        f"/api/admin/content/versions/{lab['id']}/code-checks",
        json={
            "output": STARTER[SUPERVISED]["python"]["expected_output"],
            "error": "Traceback: boom",
            "duration_ms": 10,
            "runtime": "Pyodide",
        },
    ).json()
    assert crashed["passed"] is False  # the server decides, not the client
    assert pass_code_check(admin, lab["id"], STARTER[SUPERVISED]["python"])["passed"] is True
    assert step(admin, lab["id"], "publish")["published"] is True

    # An edit is new code, so it needs its own passing check.
    edited = copy.deepcopy(STARTER[SUPERVISED]["python"])
    edited["steps"][0]["code"] += "\n# a comment changes the program"
    new = admin.post(
        f"/api/admin/content/topics/{tid}/components/python/versions",
        json={"body": edited, "based_on_id": lab["id"]},
    ).json()
    step(admin, new["id"], "submit")
    step(admin, new["id"], "approve")
    assert step(admin, new["id"], "publish", expect=409)


def test_editing_creates_versions_and_history_is_immutable(admin, db: Session):
    tid = topic_id(db, SUPERVISED)
    v1 = latest(admin, tid, "lesson")
    body = copy.deepcopy(STARTER[SUPERVISED]["lesson"])
    body["tagline"] = "Learn from labelled examples, then predict ✨"
    v2 = admin.post(
        f"/api/admin/content/topics/{tid}/components/lesson/versions",
        json={"body": body, "based_on_id": v1["id"], "note": "Punchier tagline"},
    ).json()
    assert (v2["number"], v2["origin"], v2["based_on_id"]) == (2, "edited", v1["id"])
    assert v2["body"]["tagline"].endswith("✨")

    bad = admin.post(
        f"/api/admin/content/topics/{tid}/components/lesson/versions",
        json={"body": {**body, "cards": body["cards"][:2]}},
    )
    assert bad.status_code == 422 and "cards" in bad.json()["detail"]

    publish(admin, v2["id"])
    restored = admin.post(f"/api/admin/content/versions/{v1['id']}/restore").json()
    assert restored["number"] == 3 and restored["body"]["tagline"] == v1_tagline(db, v1["id"])
    publish(admin, restored["id"])
    assert admin.get(f"/api/admin/content/versions/{v2['id']}").json()["status"] == "archived"

    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(text("UPDATE content_versions SET body = '{}'::jsonb"))
    db.rollback()
    with pytest.raises(DBAPIError, match="kept permanently"):
        db.execute(text("DELETE FROM content_versions"))
    db.rollback()


def v1_tagline(db: Session, version_id: str) -> str:
    return db.get(ContentVersion, version_id).body["tagline"]


def test_wrong_steps_are_refused(admin, db: Session):
    tid = topic_id(db, SUPERVISED)
    quiz = latest(admin, tid, "quiz")
    assert "can't be approved" in step(admin, quiz["id"], "approve", expect=409)["detail"]
    step(admin, quiz["id"], "reject")
    assert step(admin, quiz["id"], "submit", expect=409)
    not_python = admin.post(
        f"/api/admin/content/versions/{quiz['id']}/code-checks",
        json={"output": "", "duration_ms": 1, "runtime": "x"},
    )
    assert not_python.status_code == 409


def test_editing_and_publishing_are_separate_permissions(make_client, starter, db: Session):
    tid = topic_id(db, SUPERVISED)
    manager = as_role(make_client, "content_manager")  # generate + review, no publish
    publisher = as_role(make_client, "content_publisher")  # review + publish
    lesson = latest(manager, tid, "lesson")
    step(manager, lesson["id"], "submit")
    assert step(manager, lesson["id"], "approve", expect=403)
    step(publisher, lesson["id"], "approve")
    step(publisher, lesson["id"], "publish")
    assert (
        as_role(make_client, "analyst").get(f"/api/admin/content/topics/{tid}").status_code == 403
    )


def test_bulk_steps_report_what_they_skip(admin, db: Session):
    tid = topic_id(db, SUPERVISED)
    path = f"/api/admin/content/topics/{tid}/bulk"
    assert len(admin.post(path, json={"action": "submit"}).json()["changed"]) == 7
    assert len(admin.post(path, json={"action": "approve"}).json()["changed"]) == 7
    published = admin.post(path, json={"action": "publish"}).json()
    assert "python" not in published["changed"] and len(published["changed"]) == 6
    assert "code check" in published["skipped"]["python"]
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "content.bulk_publish"))
    assert len(audit.details["components"]) == 6


def test_students_never_see_where_questions_came_from(admin, make_client, db: Session):
    tid = topic_id(db, SUPERVISED)
    interview = copy.deepcopy(STARTER[SUPERVISED]["interview"])
    interview["questions"][0].update(
        origin="actual_interview",
        source_ref="11111111-1111-1111-1111-111111111111",
        asked_for_role="ML Engineer",
    )
    version = admin.post(
        f"/api/admin/content/topics/{tid}/components/interview/versions",
        json={"body": interview},
    ).json()
    publish(admin, version["id"])
    publish(admin, latest(admin, tid, "lesson")["id"])

    student = make_client()
    register_student(student)
    response = student.get(f"/api/student/learn/topics/{SUPERVISED}")
    items = response.json()["interview"]["questions"]
    assert items[0]["label"] == "Asked in real interviews"
    assert items[0]["asked_for_role"] == "ML Engineer"
    assert items[1]["label"] == "Practice question" and items[1]["asked_for_role"] is None
    assert "source_ref" not in response.text and "11111111" not in response.text
    assert "origin" not in items[0]


# --- AI generation ---------------------------------------------------------------------------


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch) -> FakeOpenRouter:
    fake = FakeOpenRouter()
    for component, name in SCHEMA_NAMES.items():
        fake.content[name] = copy.deepcopy(STARTER[SUPERVISED][component])
    monkeypatch.setattr(openrouter, "make_ai_client", fake.client)
    return fake


def approved_question(db: Session, topic: str) -> InterviewQuestion:
    """A reviewed, approved interview question (synthetic test fixture)."""
    source = InterviewSource(name="Fixture notes", connector_type=ConnectorType.FILE_UPLOAD)
    db.add(source)
    db.flush()
    job = Job(kind=JobKind.SOURCE_IMPORT, source_id=source.id, status=JobStatus.SUCCEEDED)
    db.add(job)
    db.flush()
    record = RawSourceRecord(
        source_id=source.id,
        job_id=job.id,
        external_id="fixture",
        content="Asked: what is a label?",
        content_type="text/plain",
        content_hash="x",
    )
    db.add(record)
    db.flush()
    experience = InterviewExperience(
        source_id=source.id,
        record_id=record.id,
        job_id=job.id,
        company="Acme Analytics",
        role="ML Engineer",
        technologies=[],
    )
    db.add(experience)
    db.flush()
    question = InterviewQuestion(
        experience_id=experience.id,
        source_id=source.id,
        record_id=record.id,
        job_id=job.id,
        original_text="What is a label in supervised learning?",
        normalized_hash="h",
        question_type=QuestionType.CONCEPTUAL,
        grounded=True,
        status=ReviewStatus.APPROVED,
        topic_id=db.scalar(select(Topic.id).where(Topic.slug == topic)),
        technologies=[],
    )
    db.add(question)
    db.commit()
    return question


def test_generation_writes_drafts_for_pilot_topics_only(admin, ai, db: Session):
    real = approved_question(db, SUPERVISED)
    interview = ai.content["InterviewPrep"]
    interview["questions"][0].update(
        origin="actual_interview",
        source_ref=str(real.id),
        question="A paraphrase the model made up",
    )
    interview["questions"][1].update(origin="actual_interview", source_ref="not-a-real-id")

    pilot, other = topic_id(db, SUPERVISED), topic_id(db, "machine-learning/clustering")
    response = admin.post(
        "/api/admin/content/generate",
        json={"topic_ids": [pilot, other], "components": ["lesson", "interview", "playground"]},
    ).json()
    assert len(response["started"]) == 1
    assert response["skipped"][0]["reason"].startswith("Not a pilot topic")
    assert run_pending_jobs() == 1

    job = admin.get(f"/api/admin/agents/jobs/{response['started'][0]['id']}").json()
    assert job["status"] == "completed_with_errors"  # the unknown reference was dropped
    assert any("didn't match an approved record" in e["message"] for e in job["events"])
    drafts = (
        db.scalars(select(ContentVersion).where(ContentVersion.origin == "ai_generated"))
        .unique()
        .all()
    )
    assert {d.item.component.value for d in drafts} == {"lesson", "interview", "playground"}
    assert {d.status.value for d in drafts} == {"draft"}  # never published automatically
    generated = next(d for d in drafts if d.item.component is Component.INTERVIEW).body
    grounded = generated["questions"][0]
    assert grounded["question"] == "What is a label in supervised learning?"
    assert grounded["asked_for_role"] == "ML Engineer"
    assert "Acme" not in str(generated)
    assert len(generated["questions"]) == len(STARTER[SUPERVISED]["interview"]["questions"]) - 1
    prompt = ai.requests[0]["messages"][1]["content"]
    assert "Acme" not in prompt  # companies never reach the generator either


def test_expansion_unlocks_other_topics_and_skips_missing_playgrounds(admin, ai, db: Session):
    other = topic_id(db, "machine-learning/dimensionality-reduction")
    body = {"topic_ids": [other], "components": ["lesson", "playground"]}
    assert admin.post("/api/admin/content/generate", json=body).json()["started"] == []
    assert admin.put("/api/admin/content/expansion", json={"approved": True}).status_code == 200
    started = admin.post("/api/admin/content/generate", json=body).json()["started"]
    run_pending_jobs()
    job = admin.get(f"/api/admin/agents/jobs/{started[0]['id']}").json()
    assert job["result"] == {"generated": 1, "failed": 0}
    assert any("Skipped the playground" in e["message"] for e in job["events"])
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "content.expansion_decided"))
    assert audit.details == {"approved": {"from": False, "to": True}}


def test_only_settings_admins_flip_the_expansion_gate_or_the_pilot(
    make_client, starter, db: Session
):
    manager = as_role(make_client, "content_manager")
    assert manager.put("/api/admin/content/expansion", json={"approved": True}).status_code == 403
    tid = topic_id(db, "machine-learning/clustering")
    assert (
        manager.patch(f"/api/admin/taxonomy/topics/{tid}", json={"is_pilot": True}).status_code
        == 403
    )
    renamed = manager.patch(f"/api/admin/taxonomy/topics/{tid}", json={"name": "Clustering 101"})
    assert renamed.status_code == 200
    created = manager.post(
        "/api/admin/taxonomy/topics",
        json={
            "domain_id": str(db.scalar(select(Topic.domain_id).where(Topic.id == tid))),
            "name": "Decision Trees",
        },
    )
    assert created.status_code == 201
    names = [t["name"] for d in created.json() for t in d["topics"]]
    assert "Decision Trees" in names and "Clustering 101" in names


def test_narration_audio_reaches_students_only_once_published(admin, ai, make_client, db: Session):
    tid = topic_id(db, SUPERVISED)
    video = latest(admin, tid, "video")
    voice = admin.get("/api/admin/content").json()["narration_voices"][0]
    started = admin.post(
        f"/api/admin/content/versions/{video['id']}/narration", json={"voice": voice}
    )
    assert started.status_code == 202, started.text
    run_pending_jobs()
    assets = db.scalars(select(MediaAsset).where(MediaAsset.version_id == video["id"])).all()
    assert len(assets) == len(STARTER[SUPERVISED]["video"]["scenes"])
    assert len(ai.speech_calls()) == len(assets) and ai.speech_calls()[0]["voice"] == voice
    costs = db.scalars(
        select(AiUsageEvent.cost_usd).where(AiUsageEvent.feature == "content_narration")
    ).all()
    assert len(costs) == len(assets) and float(costs[0]) == pytest.approx(0.004)

    student = make_client()
    register_student(student)
    assert student.get(f"/api/student/learn/media/{assets[0].id}").status_code == 404
    publish(admin, video["id"])
    publish(admin, latest(admin, tid, "lesson")["id"])
    scenes = student.get(f"/api/student/learn/topics/{SUPERVISED}").json()["video"]["scenes"]
    assert scenes[0]["audio_id"] == str(assets[0].id)
    audio = student.get(f"/api/student/learn/media/{assets[0].id}")
    assert audio.status_code == 200 and audio.content.startswith(b"ID3")
    assert audio.headers["content-type"] == "audio/mpeg"


def test_generation_needs_the_ai_provider(admin, db: Session):
    response = admin.post(
        "/api/admin/content/generate",
        json={"topic_ids": [topic_id(db, SUPERVISED)], "components": ["lesson"]},
    )
    assert response.status_code == 409 and "IPP_OPENROUTER_API_KEY" in response.json()["detail"]


def test_content_overview_lists_the_pilot(admin):
    overview = admin.get("/api/admin/content").json()
    assert [t["topic"]["slug"] for t in overview["topics"]] == PILOT_TOPICS
    assert overview["topics"][0]["statuses"]["lesson"] == "draft"
    assert overview["topics"][0]["live"] == [] and overview["topics"][0]["may_generate"] is True
    first = overview["topics"][0]["topic"]["id"]
    publish(admin, latest(admin, first, "lesson")["id"])
    assert admin.get("/api/admin/content").json()["topics"][0]["live"] == ["lesson"]
    assert overview["expansion_approved"] is False
    items = admin.get("/api/admin/taxonomy").json()
    assert sum(t["is_pilot"] for d in items for t in d["topics"]) == 6


def test_content_items_cannot_be_deleted(admin, db: Session):
    with pytest.raises(DBAPIError, match="kept permanently"):
        db.execute(text("DELETE FROM content_items"))
    db.rollback()
    assert db.scalar(select(ContentItem.id)) is not None


def test_content_runs_are_visible_and_stoppable_by_content_staff(
    make_client, starter, ai, db: Session
):
    manager = as_role(make_client, "content_manager")
    tid = topic_id(db, SUPERVISED)
    started = manager.post(
        "/api/admin/content/generate", json={"topic_ids": [tid], "components": ["lesson"]}
    )
    assert started.status_code == 202, started.text
    run = started.json()["started"][0]
    assert run["topic"]["slug"] == SUPERVISED

    # Reviewers see generation runs without needing the agents permission.
    publisher = as_role(make_client, "content_publisher")
    assert publisher.get("/api/admin/agents/jobs").status_code == 403
    listed = publisher.get(f"/api/admin/content/jobs?topic_id={tid}").json()
    assert listed["total"] == 1 and listed["items"][0]["id"] == run["id"]
    stopped = manager.post(f"/api/admin/content/jobs/{run['id']}/cancel")
    assert stopped.status_code == 200 and stopped.json()["status"] == "cancelled"
    detail = manager.get(f"/api/admin/content/jobs/{run['id']}").json()
    assert detail["events"][-1]["message"] == "Stopped by an admin."
    assert manager.post(f"/api/admin/content/jobs/{run['id']}/cancel").status_code == 409
    assert db.scalar(select(AuditLog).where(AuditLog.action == "content.run_stopped"))

    # The shared runs controls apply content permissions too, and never re-run generation.
    assert manager.post(f"/api/admin/agents/jobs/{run['id']}/cancel").status_code == 409
    assert publisher.post(f"/api/admin/content/jobs/{run['id']}/cancel").status_code == 403
    create_admin(email="root@example.com")
    root = make_client()
    login_admin(root, email="root@example.com")
    retry = root.post(f"/api/admin/agents/jobs/{run['id']}/retry")
    assert retry.status_code == 409 and "Content studio" in retry.json()["detail"]


def test_content_runs_only_list_content_jobs(admin, db: Session):
    db.add(Job(kind=JobKind.EXPLORATION, status=JobStatus.SUCCEEDED))
    db.commit()
    assert admin.get("/api/admin/content/jobs").json()["total"] == 0
    other = db.scalar(select(Job.id).where(Job.kind == JobKind.EXPLORATION))
    assert admin.get(f"/api/admin/content/jobs/{other}").status_code == 404
