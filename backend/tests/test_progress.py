"""Phase 6 (part A): learning progress stored per student, quiz attempts graded on the server and
never overwritten, completion kept apart from mastery, and the admin views and analytics.
Students and their activity here are synthetic test fixtures."""

import csv
import io
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.content.seed import seed_starter_content
from app.content.starter import TOPICS
from app.core.security import utcnow
from app.intelligence.taxonomy import seed_default_taxonomy
from app.models import (
    AttemptStatus,
    AuditLog,
    Cohort,
    PracticeAttempt,
    QuizAttempt,
    QuizResponse,
    Student,
    Topic,
    TopicProgress,
)
from app.progress.service import TIME_SLACK, band, mastery
from tests.helpers import create_admin, login_admin, login_student, register_student

SUPERVISED = "machine-learning/supervised-learning"
REGRESSION = "machine-learning/regression"
STARTER = {module.TOPIC: module.CONTENT for module in TOPICS}
LIVE = ["lesson", "playground", "video", "quiz", "interview", "revision"]  # python stays a draft


@pytest.fixture
def admin(make_client, db: Session) -> TestClient:
    seed_default_taxonomy(db)
    seed_starter_content(db)
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def publish(admin: TestClient, db: Session, slug: str, components: list[str]) -> None:
    topic_id = db.scalar(select(Topic.id).where(Topic.slug == slug))
    state = admin.get(f"/api/admin/content/topics/{topic_id}").json()
    for component in components:
        version = next(c for c in state["components"] if c["component"] == component)["latest"]
        for action in ("submit", "approve", "publish"):
            response = admin.post(
                f"/api/admin/content/versions/{version['id']}/transition", json={"action": action}
            )
            assert response.status_code == 200, response.text


@pytest.fixture
def live(admin: TestClient, db: Session) -> None:
    publish(admin, db, SUPERVISED, LIVE)
    publish(admin, db, REGRESSION, ["lesson", "quiz"])


@pytest.fixture
def student(make_client, live: None) -> TestClient:
    client = make_client()
    register_student(client)
    return client


def event(client: TestClient, component: str, kind: str, expect: int = 200, **data: Any) -> Any:
    response = client.post(
        "/api/student/progress/events",
        json={"topic": SUPERVISED, "component": component, "kind": kind, "data": data},
    )
    assert response.status_code == expect, response.text
    return response.json()


def spend(
    client: TestClient,
    seconds: int,
    component: str = "lesson",
    slug: str = SUPERVISED,
    expect: int = 204,
) -> None:
    response = client.post(
        "/api/student/progress/time",
        json={"topic": slug, "component": component, "seconds": seconds},
    )
    assert response.status_code == expect, response.text


def quiz_version(client: TestClient, slug: str = SUPERVISED) -> str:
    return client.get(f"/api/student/learn/topics/{slug}").json()["quiz_version_id"]


def submit(
    client: TestClient, answers: list[int | None], slug: str = SUPERVISED, expect: int = 201
) -> Any:
    response = client.post(
        "/api/student/progress/quiz-attempts",
        json={
            "topic": slug,
            "version_id": quiz_version(client, slug),
            "answers": answers,
            "duration_seconds": 95,
        },
    )
    assert response.status_code == expect, response.text
    return response.json()


def key(slug: str = SUPERVISED) -> list[int]:
    return [q["answer"] for q in STARTER[slug]["quiz"]["questions"]]


def wrong(answers: list[int], how_many: int) -> list[int | None]:
    return [(a + 1) % 4 if i < how_many else a for i, a in enumerate(answers)]


# --- Progress ------------------------------------------------------------------------------------


def test_progress_is_stored_and_follows_the_student_across_devices(
    student: TestClient, make_client
):
    cards = len(STARTER[SUPERVISED]["lesson"]["cards"])
    tasks = len(STARTER[SUPERVISED]["playground"]["tasks"])

    state = event(student, "lesson", "section_opened")
    assert state["sections"]["lesson"] == "started" and state["sections"]["quiz"] == "not_started"
    assert "python" not in state["sections"]  # unpublished sections don't count

    event(student, "lesson", "lesson_progress", seen=cards - 1, of=cards)
    assert (
        event(student, "lesson", "lesson_progress", seen=cards, of=cards)["sections"]["lesson"]
        == "done"
    )
    for task in range(tasks):
        state = event(student, "playground", "playground_task", task=task, of=tasks)
    assert state["sections"]["playground"] == "done"
    event(student, "video", "video_progress", scene=2, of=6)
    assert event(student, "video", "section_done")["sections"]["video"] == "done"
    assert event(student, "revision", "section_opened")["sections"]["revision"] == "done"

    phone = make_client()
    login_student(phone)
    seen = phone.get(f"/api/student/progress/topics/{SUPERVISED}").json()
    assert seen["sections"] == {
        "lesson": "done",
        "playground": "done",
        "video": "done",
        "quiz": "not_started",
        "interview": "not_started",
        "revision": "done",
    }
    assert seen["last_section"] == "revision" and seen["completed"] is False


def test_events_are_checked_against_published_content(student: TestClient):
    event(student, "python", "section_opened", expect=404)  # still a draft
    event(student, "lesson", "lesson_progress", expect=422, seen=-1, of=5)
    event(student, "lesson", "lesson_progress", expect=422, seen="all", of=5)
    event(student, "interview", "interview_take", expect=422, question="Not a real question")
    bad_topic = student.post(
        "/api/student/progress/events",
        json={"topic": "nope/nothing", "component": "lesson", "kind": "section_opened"},
    )
    assert bad_topic.status_code == 404


def test_progress_needs_a_signed_in_student(make_client, live):
    anonymous = make_client()
    assert anonymous.get("/api/student/progress").status_code == 401
    assert anonymous.get(f"/api/student/progress/topics/{SUPERVISED}").status_code == 401


def test_a_topic_completes_when_every_published_section_is_done(student: TestClient, db: Session):
    questions = [q["question"] for q in STARTER[SUPERVISED]["interview"]["questions"]]
    for component in ("lesson", "playground", "video", "revision"):
        event(student, component, "section_done")
    submit(student, key())
    for question in questions[: (len(questions) - 1) // 2]:  # just under half
        state = event(student, "interview", "interview_take", question=question)
    assert state["sections"]["interview"] == "started" and state["completed"] is False
    state = event(student, "interview", "interview_take", question=questions[len(questions) // 2])
    assert state["sections"]["interview"] == "done" and state["completed"] is True
    assert set(state["answered_questions"]) <= set(questions)

    summary = student.get("/api/student/progress").json()
    assert summary["topics_completed"] == 1
    supervised = next(t for t in summary["topics"] if t["slug"] == SUPERVISED)
    assert supervised["completion"] == 100 and supervised["completed"] is True


# --- Learning time ------------------------------------------------------------------------------


def test_learning_time_is_never_credited_faster_than_the_clock(
    student: TestClient, admin: TestClient, db: Session
):
    event(student, "lesson", "section_opened")
    spend(student, 60)  # the first report is credited in full
    spend(student, 60, component="quiz")  # moments later: only the network slack
    row = db.scalar(select(TopicProgress))
    assert 60 + TIME_SLACK <= row.active_seconds <= 60 + TIME_SLACK + 2
    # Time doesn't move sections along.
    progress = student.get(f"/api/student/progress/topics/{SUPERVISED}").json()
    assert progress["sections"]["lesson"] == "started"
    assert progress["sections"]["quiz"] == "not_started"

    summary = student.get("/api/student/progress").json()
    supervised = next(t for t in summary["topics"] if t["slug"] == SUPERVISED)
    assert supervised["active_seconds"] == row.active_seconds
    assert summary["activity"]["learning_seconds"] == row.active_seconds
    assert summary["activity"]["learning_seconds_last_7"] == row.active_seconds

    me = db.scalar(select(Student))
    learning = admin.get(f"/api/admin/students/{me.id}/learning").json()
    assert [entry["action"] for entry in learning["timeline"]] == ["Opened"]  # no time entries
    rows = admin.get("/api/admin/students").json()["items"]
    assert rows[0]["learning"]["learning_seconds"] == row.active_seconds


def test_learning_time_reports_are_checked(student: TestClient, make_client):
    spend(student, 0, expect=422)
    spend(student, 121, expect=422)
    spend(student, 30, component="python", expect=404)  # the lab is still a draft
    spend(student, 30, slug="machine-learning/not-a-topic", expect=404)
    event(student, "lesson", "active_time", expect=422, seconds=30)
    stranger = make_client()
    assert (
        stranger.post(
            "/api/student/progress/time",
            json={"topic": SUPERVISED, "component": "lesson", "seconds": 30},
        ).status_code
        == 401
    )


# --- Quizzes -------------------------------------------------------------------------------------


def test_quizzes_are_graded_on_the_server_and_never_overwritten(student: TestClient, db: Session):
    answers = key()
    first = submit(student, answers)
    assert first == {
        "attempt_number": 1,
        "correct": len(answers),
        "total": len(answers),
        "score_pct": 100.0,
        "best_pct": 100.0,
    }
    second = submit(student, wrong(answers, 4))
    assert second["attempt_number"] == 2 and second["correct"] == len(answers) - 4
    assert second["best_pct"] == 100.0

    attempts = db.scalars(select(QuizAttempt).order_by(QuizAttempt.attempt_number)).all()
    assert [a.attempt_number for a in attempts] == [1, 2]
    assert db.query(QuizResponse).count() == 2 * len(answers)
    with pytest.raises(DBAPIError):
        db.execute(update(QuizAttempt).values(correct=0))
        db.commit()
    db.rollback()

    assert submit(student, answers[:-1], expect=422)["detail"].startswith("Answer every")
    assert submit(student, [9] * len(answers), expect=422)["detail"] == "Invalid answer."
    stale = student.post(
        "/api/student/progress/quiz-attempts",
        json={"topic": SUPERVISED, "version_id": str(uuid.uuid4()), "answers": answers},
    )
    assert stale.status_code == 409

    page = student.get(f"/api/student/progress/topics/{SUPERVISED}").json()
    assert page["sections"]["quiz"] == "done"
    assert page["quiz"] == {"attempts": 2, "best_pct": 100.0, "last_pct": second["score_pct"]}


def test_mastery_is_separate_from_completion(student: TestClient, db: Session):
    # A struggling quiz on Regression, a strong one on Supervised; no sections finished.
    submit(student, wrong(key(REGRESSION), 5), slug=REGRESSION)
    submit(student, key())
    summary = student.get("/api/student/progress").json()
    topics = {t["slug"]: t for t in summary["topics"]}
    assert topics[SUPERVISED]["mastery"]["band"] == "strong"
    assert topics[REGRESSION]["mastery"]["band"] == "needs_work"
    assert topics[SUPERVISED]["completion"] < 100  # a great quiz isn't a finished topic
    assert summary["strengths"] == ["Supervised Learning"]
    assert summary["weaknesses"] == ["Regression"]
    assert [r["reason"] for r in summary["recommended"]] == ["Boost a weak spot"]
    assert summary["recent_quizzes"][0]["topic"] == "Supervised Learning"
    assert summary["activity"]["streak_days"] == 1
    assert summary["continue"]["slug"] in {SUPERVISED, REGRESSION}


def test_interview_practice_counts_toward_mastery_and_answered_questions(
    student: TestClient, db: Session
):
    me = db.scalar(select(Student))
    topic = db.scalar(select(Topic).where(Topic.slug == SUPERVISED))
    question = STARTER[SUPERVISED]["interview"]["questions"][0]["question"]
    db.add(
        PracticeAttempt(
            student_id=me.id,
            topic_id=topic.id,
            version_id=_interview_version(db, topic.id),
            question_index=0,
            question=question,
            status=AttemptStatus.COMPLETED,
            duration_ms=60_000,
            score=Decimal("8.0"),
            feedback={"verdict": {"key": "ready", "label": "Interview-ready"}},
        )
    )
    db.commit()
    page = student.get(f"/api/student/progress/topics/{SUPERVISED}").json()
    assert page["answered_questions"] == [question]
    summary = student.get("/api/student/progress").json()
    supervised = next(t for t in summary["topics"] if t["slug"] == SUPERVISED)
    assert supervised["mastery"] == {
        "score": 80.0,
        "band": "strong",
        "quiz_average": None,
        "practice_average": 8.0,
    }
    assert summary["interview"]["feedback_count"] == 1
    assert summary["interview"]["average_score"] == 8.0


def _interview_version(db: Session, topic_id: uuid.UUID) -> uuid.UUID:
    from app.models import Component, ContentItem

    return db.scalar(
        select(ContentItem.published_version_id).where(
            ContentItem.topic_id == topic_id, ContentItem.component == Component.INTERVIEW
        )
    )


def test_mastery_bands():
    assert band(None) == "not_enough_evidence" and band(75) == "strong"
    assert band(74.9) == "developing" and band(49.9) == "needs_work"
    # Recent quizzes count (the last three), with practice weighted 40 %.
    assert mastery([20, 90, 90, 90], [])["score"] == 90.0
    assert mastery([80], [6.0])["score"] == 72.0


# --- Admin views ---------------------------------------------------------------------------------


def test_admins_see_each_students_learning_without_transcripts(
    admin: TestClient, student: TestClient, db: Session
):
    event(student, "lesson", "section_opened")
    submit(student, wrong(key(), 2))
    me = db.scalar(select(Student))

    learning = admin.get(f"/api/admin/students/{me.id}/learning").json()
    attempt = learning["quiz_attempts"][0]
    assert attempt["attempt_number"] == 1 and attempt["topic"] == "Supervised Learning"
    assert (
        attempt["responses"][0]["prompt"] == STARTER[SUPERVISED]["quiz"]["questions"][0]["prompt"]
    )
    assert [r["correct"] for r in attempt["responses"][:3]] == [False, False, True]
    assert learning["timeline"][0]["action"] == "Opened"
    assert learning["summary"]["topics_started"] == 1
    assert "transcript" not in str(learning)

    rows = admin.get("/api/admin/students").json()["items"]
    assert rows[0]["learning"]["quiz_attempts"] == 1
    assert rows[0]["learning"]["topics_started"] == 1 and rows[0]["learning"]["flags"] == []

    assert student.get(f"/api/admin/students/{me.id}/learning").status_code == 401


def test_students_needing_attention_are_flagged(
    admin: TestClient, student: TestClient, make_client, db: Session
):
    submit(student, wrong(key(), 6))
    submit(student, wrong(key(), 5))  # two attempts under 50 %: struggling
    idle = make_client()
    register_student(idle, email="idle@example.com", name="Idle Student")
    db.execute(
        update(Student)
        .where(Student.email == "idle@example.com")
        .values(created_at=utcnow() - timedelta(days=20))
    )
    db.commit()

    def flagged(kind: str) -> dict[str, list[str]]:
        items = admin.get("/api/admin/students", params={"attention": kind}).json()["items"]
        return {i["full_name"]: i["learning"]["flags"] for i in items}

    assert flagged("struggling") == {"Asha Rao": ["struggling"]}
    assert flagged("inactive") == {"Idle Student": ["inactive"]}
    assert set(flagged("any")) == {"Asha Rao", "Idle Student"}


def test_analytics_report_filters_and_permissions(
    admin: TestClient, student: TestClient, make_client, db: Session
):
    cohort = Cohort(name="Batch A")
    db.add(cohort)
    db.commit()
    db.execute(update(Student).values(cohort_id=cohort.id))
    db.commit()
    event(student, "lesson", "section_opened")
    for misses in (0, 2, 4):
        submit(student, wrong(key(), misses))

    report = admin.get("/api/admin/analytics").json()
    kpis = report["kpis"]
    assert kpis["students"] == 1 and kpis["active_students"] == 1 and kpis["new_students"] == 1
    assert kpis["quiz_attempts"] == 3 and kpis["published_topics"] == 2
    assert sum(b["count"] for b in report["score_distribution"]) == 3
    supervised = next(t for t in report["topics"] if t["slug"] == SUPERVISED)
    assert supervised["started"] == 1 and supervised["quiz_attempts"] == 3
    assert [t["slug"] for t in report["weak_topics"]] == [SUPERVISED]  # 3 attempts is enough
    assert report["cohorts"] == [
        {"name": "Batch A", "students": 1, "active": 1, "quiz_average": kpis["quiz_average"]}
    ]
    assert sum(r["count"] for r in report["registrations"]) == 1
    assert len(report["registrations"]) == 30  # every day, zeros included
    assert len(report["weekly_active"]) in (5, 6)

    assert kpis["learning_seconds"] == 0 and kpis["learning_seconds_per_learner"] is None
    assert kpis["average_completion"] == round(100 / 8)  # the quiz: 1 of 8 live sections

    narrowed = admin.get("/api/admin/analytics", params={"topic": REGRESSION}).json()
    assert narrowed["kpis"]["quiz_attempts"] == 0 and len(narrowed["topics"]) == 1
    assert (
        admin.get(
            "/api/admin/analytics", params={"start": "2026-01-02", "end": "2026-01-01"}
        ).status_code
        == 422
    )

    create_admin(email="cm@example.com", roles=("content_manager",))
    content = make_client()
    login_admin(content, email="cm@example.com")
    assert content.get("/api/admin/analytics").status_code == 403
    assert content.get("/api/admin/analytics/students.csv").status_code == 403


def test_analytics_counts_learning_time_and_path_completion(
    admin: TestClient, student: TestClient, make_client, db: Session
):
    cards = len(STARTER[SUPERVISED]["lesson"]["cards"])
    event(student, "lesson", "lesson_progress", seen=cards, of=cards)
    event(student, "revision", "section_opened")  # opening the cheat sheet finishes it
    spend(student, 90)
    other = make_client()
    register_student(other, email="other@example.com", name="Other Student")

    kpis = admin.get("/api/admin/analytics").json()["kpis"]
    # 2 of 8 live sections (6 in supervised, 2 in regression) for one student, 0 for the other.
    assert kpis["average_completion"] == round(2 * 100 / 16)
    assert kpis["learning_seconds"] == 90 and kpis["learning_seconds_per_learner"] == 90
    topics = admin.get("/api/admin/analytics").json()["topics"]
    assert {t["slug"]: t["learning_seconds"] for t in topics} == {SUPERVISED: 90, REGRESSION: 0}


def test_analytics_can_be_filtered_to_one_student(
    admin: TestClient, student: TestClient, make_client, db: Session
):
    cohort = Cohort(name="Batch A")
    db.add(cohort)
    db.commit()
    db.execute(update(Student).values(cohort_id=cohort.id))
    db.commit()
    submit(student, key())
    other = make_client()
    register_student(other, email="other@example.com", name="Other Student")
    submit(other, wrong(key(), 4))
    asha = db.scalar(select(Student).where(Student.full_name == "Asha Rao"))

    everyone = admin.get("/api/admin/analytics").json()
    assert everyone["kpis"]["students"] == 2 and everyone["kpis"]["quiz_attempts"] == 2
    assert everyone["student"] is None

    report = admin.get("/api/admin/analytics", params={"student_id": str(asha.id)}).json()
    assert report["kpis"]["students"] == 1 and report["kpis"]["quiz_attempts"] == 1
    assert report["kpis"]["quiz_average"] == 100
    assert report["student"] == {
        "id": str(asha.id),
        "full_name": "Asha Rao",
        "student_code": asha.student_code,
    }
    assert report["cohorts"] == []  # one student isn't compared with whole cohorts
    unknown = admin.get("/api/admin/analytics", params={"student_id": str(uuid.uuid4())})
    assert unknown.status_code == 404

    # Seeing one student's numbers needs access to student profiles too.
    owner = admin.post(
        "/api/admin/roles",
        json={"name": "Numbers Only", "permissions": ["analytics.view"]},
    )
    assert owner.status_code == 201, owner.text
    create_admin(email="numbers@example.com", roles=(owner.json()["key"],))
    numbers = make_client()
    login_admin(numbers, email="numbers@example.com")
    assert numbers.get("/api/admin/analytics").status_code == 200
    filtered = numbers.get("/api/admin/analytics", params={"student_id": str(asha.id)})
    assert filtered.status_code == 403


def test_csv_export_is_audited_and_formula_safe(admin: TestClient, make_client, live, db: Session):
    risky = make_client()
    register_student(risky, email="formula@example.com", name="=HYPERLINK(1)")
    response = admin.get("/api/admin/analytics/students.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][0] == "Student ID" and len(rows) == 2
    assert rows[1][1] == "'=HYPERLINK(1)"
    assert rows[1][rows[0].index("Learning time (min)")] == "0"
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "analytics.students_exported"))
    assert audit is not None and audit.details["rows"] == 1


def test_learning_records_are_permanent(student: TestClient, db: Session):
    event(student, "lesson", "section_opened")
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM learning_events"))
        db.commit()
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM topic_progress"))
        db.commit()
    db.rollback()
