"""Phase 5: content quality. Automated checks and the publish gate, AI reviews (advice only),
reviewer ratings, revising with AI, retrying what failed, interview coverage and the pilot
evaluation. Every interview record and AI reply here is a synthetic test fixture."""

import copy
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.content.seed import seed_starter_content
from app.content.starter import TOPICS
from app.intelligence.taxonomy import seed_default_taxonomy
from app.jobs.runner import run_pending_jobs
from app.models import (
    AiUsageEvent,
    AuditLog,
    ContentRating,
    ContentVersion,
    InterviewQuestion,
    Job,
    QualityReview,
    ReviewStatus,
    Topic,
    VersionOrigin,
)
from tests.fake_ai import FakeOpenRouter
from tests.helpers import create_admin, login_admin
from tests.test_content import approved_question

SUPERVISED = "machine-learning/supervised-learning"
STARTER = {module.TOPIC: module.CONTENT for module in TOPICS}


@pytest.fixture
def admin(make_client, db: Session) -> TestClient:
    seed_default_taxonomy(db)
    seed_starter_content(db)
    create_admin()
    client = make_client()
    login_admin(client)
    return client


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch) -> FakeOpenRouter:
    fake = FakeOpenRouter()
    monkeypatch.setattr(openrouter, "make_ai_client", fake.client)
    return fake


def as_role(make_client, role: str) -> TestClient:
    create_admin(email=f"{role}@example.com", roles=(role,))
    client = make_client()
    login_admin(client, email=f"{role}@example.com")
    return client


def topic_id(db: Session, slug: str = SUPERVISED) -> str:
    return str(db.scalar(select(Topic.id).where(Topic.slug == slug)))


def latest(
    admin: TestClient, db: Session, component: str, slug: str = SUPERVISED
) -> dict[str, Any]:
    state = admin.get(f"/api/admin/content/topics/{topic_id(db, slug)}").json()
    return next(c for c in state["components"] if c["component"] == component)["latest"]


def edit(admin: TestClient, db: Session, component: str, body: dict[str, Any]) -> str:
    response = admin.post(
        f"/api/admin/content/topics/{topic_id(db)}/components/{component}/versions",
        json={"body": body, "note": "test edit"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def step(admin: TestClient, version_id: str, action: str, expect: int = 200) -> dict[str, Any]:
    response = admin.post(
        f"/api/admin/content/versions/{version_id}/transition", json={"action": action}
    )
    assert response.status_code == expect, response.text
    return response.json()


def quality(admin: TestClient, version_id: str) -> dict[str, Any]:
    response = admin.get(f"/api/admin/content/versions/{version_id}/quality")
    assert response.status_code == 200, response.text
    return response.json()


def check(report: dict[str, Any], key: str) -> dict[str, Any]:
    return next(c for c in report["automated"]["checks"] if c["key"] == key)


# --- Automated checks ----------------------------------------------------------------------------


def test_starter_content_passes_every_automated_check(admin, db: Session):
    for version in db.scalars(select(ContentVersion)).unique():
        report = quality(admin, str(version.id))["automated"]
        problems = [
            (c["key"], f["message"])
            for c in report["checks"]
            for f in c["findings"]
            if c["key"] != "code_check"  # labs still need their browser run
        ]
        assert report["errors"] == 0 and problems == [], (version.item.component, problems)


def test_company_names_block_publishing(admin, db: Session):
    approved_question(db, SUPERVISED)  # interview records mention "Acme Analytics"
    lesson = copy.deepcopy(STARTER[SUPERVISED]["lesson"])
    lesson["cards"][0]["body"] = "At Acme Analytics, spam filters learn from labelled mail."
    version = edit(admin, db, "lesson", lesson)
    found = check(quality(admin, version), "companies")
    assert found["status"] == "error"
    assert found["findings"][0]["message"] == "Mentions the company “Acme Analytics”."
    assert found["findings"][0]["where"] == "cards 1 · body"

    step(admin, version, "submit")
    step(admin, version, "approve")
    refused = step(admin, version, "publish", expect=409)
    assert refused["detail"].startswith("Fix the quality check errors first: cards 1 · body")


def test_actual_questions_must_still_match_an_approved_record(admin, db: Session):
    record = approved_question(db, SUPERVISED)
    interview = copy.deepcopy(STARTER[SUPERVISED]["interview"])
    interview["questions"][0].update(
        origin="actual_interview", source_ref=str(record.id), question=record.original_text
    )
    version = edit(admin, db, "interview", interview)
    assert check(quality(admin, version), "references")["status"] == "passed"

    record.status = ReviewStatus.REJECTED
    db.commit()
    references = check(quality(admin, version), "references")
    assert references["status"] == "error"
    assert references["findings"][0]["where"] == "Question 1"


def test_lab_code_is_checked_for_unsafe_or_unlisted_imports(admin, db: Session):
    lab = copy.deepcopy(STARTER[SUPERVISED]["python"])
    lab["steps"][0]["code"] = "import os\nimport pandas as pd\nprint(open('x').read())"
    lab["packages"] = ["numpy"]
    safety = check(quality(admin, edit(admin, db, "python", lab)), "code_safety")
    messages = [f["message"] for f in safety["findings"]]
    assert safety["status"] == "error"
    assert "Imports os, which isn't allowed in labs." in messages
    assert "Imports pandas but packages doesn't list pandas." in messages
    assert "Calls open(), which labs must not use." in messages

    lab["steps"][0]["code"] = "def broken(:\n    pass"
    safety = check(quality(admin, edit(admin, db, "python", lab)), "code_safety")
    assert safety["findings"][0]["message"].startswith("The code doesn't parse")


def test_quiz_and_video_warnings(admin, db: Session):
    quiz = copy.deepcopy(STARTER[SUPERVISED]["quiz"])
    for question in quiz["questions"]:  # every answer is now the first option
        correct = question["options"][question["answer"]]
        question["options"].remove(correct)
        question["options"].insert(0, correct)
        question["answer"] = 0
    quiz["questions"][1]["prompt"] = quiz["questions"][0]["prompt"]
    quiz["questions"][2]["explanation"] = "See https://example.com/notes for more."
    report = quality(admin, edit(admin, db, "quiz", quiz))
    assert check(report, "answer_key")["status"] == "warning"
    assert check(report, "duplicates")["findings"][0]["message"] == (
        "Questions 1 and 2 are near-duplicates."
    )
    assert check(report, "links")["findings"][0]["where"] == "questions 3 · explanation"
    assert report["automated"]["errors"] == 0  # warnings never block publishing

    video = copy.deepcopy(STARTER[SUPERVISED]["video"])
    video["scenes"][0]["seconds"] = 8
    timing = check(quality(admin, edit(admin, db, "video", video)), "timing")
    assert timing["status"] == "warning" and timing["findings"][0]["where"] == "Scene 1"


def test_duplicates_across_topics_are_flagged(admin, db: Session):
    other = latest(admin, db, "interview", "machine-learning/regression")
    for action in ("submit", "approve", "publish"):
        step(admin, other["id"], action)
    regression = STARTER["machine-learning/regression"]["interview"]["questions"][0]["question"]
    interview = copy.deepcopy(STARTER[SUPERVISED]["interview"])
    interview["questions"][0]["question"] = regression
    duplicates = check(quality(admin, edit(admin, db, "interview", interview)), "duplicates")
    assert duplicates["findings"][0]["message"] == (
        "Question 1 repeats a published question in Regression."
    )


# --- AI review -----------------------------------------------------------------------------------


def review_reply(**overrides: Any) -> dict[str, Any]:
    reply = {
        "summary": "Accurate and well paced; one ambiguous question.",
        "scores": {
            "factual_correctness": 5,
            "clarity": 4,
            "math_consistency": None,
            "topic_relevance": 5,
            "interview_relevance": 4,
            "difficulty_fit": 4,
            "component": 3,
        },
        "issues": [
            {
                "severity": "warning",
                "location": "Question 1",
                "quote": STARTER[SUPERVISED]["quiz"]["questions"][0]["prompt"][:60],
                "problem": "Two options could be read as correct.",
                "fix": "Make the distractor clearly wrong.",
            },
            {
                "severity": "error",
                "location": "Question 9",
                "quote": "this sentence is not in the quiz at all",
                "problem": "Invented.",
                "fix": "-",
            },
            {
                "severity": "suggestion",
                "location": "Overall",
                "quote": None,
                "problem": "Add one code-reading question.",
                "fix": "Swap a recall question for a code snippet.",
            },
        ],
    }
    reply.update(overrides)
    return reply


def test_ai_review_rescores_and_resolves_the_quiz(admin, ai: FakeOpenRouter, db: Session):
    quiz = STARTER[SUPERVISED]["quiz"]["questions"]
    picks = [
        {"question": n, "choice": q["answer"], "confident": True}
        for n, q in enumerate(quiz, start=1)
    ]
    picks[2]["choice"] = (quiz[2]["answer"] + 1) % len(quiz[2]["options"])  # disagrees once
    ai.content["QuizAnswers"] = {"answers": picks}
    ai.content["ContentReview"] = review_reply()

    version = latest(admin, db, "quiz")["id"]
    job = admin.post(f"/api/admin/content/versions/{version}/ai-review", json={})
    assert job.status_code == 202, job.text
    assert job.json()["kind"] == "content_review"
    run_pending_jobs()

    solve = ai.schema_calls("QuizAnswers")[0]["messages"][1]["content"]
    assert quiz[0]["prompt"] in solve
    assert '"answer"' not in solve and quiz[0]["explanation"] not in solve  # no key, no hints

    report = quality(admin, version)["ai_reviews"][0]
    assert report["scores"]["assessment_quality"] == 3 and "component" not in report["scores"]
    assert report["average"] == 4.17
    assert [i["location"] for i in report["issues"]] == ["Question 1", "Overall"]
    assert report["dropped_issues"] == 1
    disagreement = [row for row in report["quiz_check"] if not row["agrees"]]
    assert [row["question"] for row in disagreement] == [3]
    assert report["requested_by"] == "Platform Admin"

    features = {e.feature for e in db.scalars(select(AiUsageEvent))}
    assert features == {"content_review"}
    assert db.scalar(select(AuditLog.action).where(AuditLog.action == "content.ai_review_started"))
    # Reviews are advice: the version is untouched and still a draft.
    assert db.get(ContentVersion, version).status.value == "draft"


def test_ai_review_needs_the_provider_and_a_reviewer(admin, make_client, db: Session):
    version = latest(admin, db, "lesson")["id"]
    assert (
        admin.post(f"/api/admin/content/versions/{version}/ai-review", json={}).status_code == 409
    )
    operator = as_role(make_client, "intelligence_operator")
    assert (
        operator.post(f"/api/admin/content/versions/{version}/ai-review", json={}).status_code
        == 403
    )


def test_ai_reviews_are_append_only(admin, ai: FakeOpenRouter, db: Session):
    ai.content["ContentReview"] = review_reply(issues=[])
    version = latest(admin, db, "lesson")["id"]
    admin.post(f"/api/admin/content/versions/{version}/ai-review", json={})
    run_pending_jobs()
    assert db.scalar(select(QualityReview.id))
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE content_quality_reviews SET summary = 'changed'"))
        db.commit()
    db.rollback()


# --- Ratings -------------------------------------------------------------------------------------


def test_reviewers_rate_versions_on_the_rubric(admin, make_client, db: Session):
    version = latest(admin, db, "playground")["id"]
    criteria = [c["key"] for c in quality(admin, version)["ratings"]["criteria"]]
    assert criteria == [
        "technical_correctness",
        "clarity",
        "interview_relevance",
        "student_experience",
        "visualization_quality",
    ]
    bad = admin.post(
        f"/api/admin/content/versions/{version}/ratings", json={"scores": {"clarity": 5}}
    )
    assert bad.status_code == 422

    first = admin.post(
        f"/api/admin/content/versions/{version}/ratings",
        json={"scores": dict.fromkeys(criteria, 4), "note": "Solid."},
    )
    assert first.status_code == 201 and first.json()["average"] == 4.0
    again = admin.post(
        f"/api/admin/content/versions/{version}/ratings",
        json={"scores": dict.fromkeys(criteria, 5)},
    ).json()
    assert len(again["ratings"]) == 1 and again["average"] == 5.0  # my latest counts

    publisher = as_role(make_client, "content_publisher")
    other = publisher.post(
        f"/api/admin/content/versions/{version}/ratings",
        json={"scores": dict.fromkeys(criteria, 3)},
    ).json()
    assert other["average"] == 4.0 and len(other["ratings"]) == 2
    assert [r["mine"] for r in other["ratings"]] == [True, False]
    assert db.query(ContentRating).count() == 3  # every rating is kept

    operator = as_role(make_client, "intelligence_operator")
    assert (
        operator.post(
            f"/api/admin/content/versions/{version}/ratings",
            json={"scores": dict.fromkeys(criteria, 1)},
        ).status_code
        == 403
    )


# --- Revise with AI ----------------------------------------------------------------------------


def test_revising_writes_a_new_draft_from_the_version(admin, ai: FakeOpenRouter, db: Session):
    ai.content["ContentReview"] = review_reply()
    ai.content["QuizAnswers"] = {
        "answers": [
            {"question": n, "choice": q["answer"], "confident": True}
            for n, q in enumerate(STARTER[SUPERVISED]["quiz"]["questions"], start=1)
        ]
    }
    revised = copy.deepcopy(STARTER[SUPERVISED]["quiz"])
    revised["questions"][0]["explanation"] = "Revised explanation."
    ai.content["Quiz"] = revised

    base = latest(admin, db, "quiz")
    refused = admin.post(
        f"/api/admin/content/versions/{base['id']}/revise", json={"use_review": True}
    )
    assert refused.status_code == 409  # no AI review yet
    assert (
        admin.post(f"/api/admin/content/versions/{base['id']}/revise", json={}).status_code == 422
    )

    admin.post(f"/api/admin/content/versions/{base['id']}/ai-review", json={})
    run_pending_jobs()
    job = admin.post(
        f"/api/admin/content/versions/{base['id']}/revise",
        json={"instructions": "Make question 1 less ambiguous.", "use_review": True},
    )
    assert job.status_code == 202, job.text
    run_pending_jobs()

    prompt = ai.schema_calls("Quiz")[0]["messages"][1]["content"]
    assert "Make question 1 less ambiguous." in prompt
    assert "Two options could be read as correct." in prompt  # the review's finding
    assert "<current>" in prompt and STARTER[SUPERVISED]["quiz"]["questions"][1]["prompt"] in prompt

    new = latest(admin, db, "quiz")
    assert new["number"] == base["number"] + 1 and new["based_on_id"] == base["id"]
    assert new["origin"] == VersionOrigin.AI_GENERATED.value and new["status"] == "draft"
    assert new["note"] == f"Revised by AI from version {base['number']}; review before publishing."


def test_revising_respects_the_pilot_gate(admin, ai: FakeOpenRouter, db: Session):
    topic = db.scalar(select(Topic).where(Topic.slug == SUPERVISED))
    topic.is_pilot = False
    db.commit()
    version = latest(admin, db, "lesson")["id"]
    refused = admin.post(
        f"/api/admin/content/versions/{version}/revise", json={"instructions": "Shorter cards."}
    )
    assert refused.status_code == 409


# --- Retries and batches -----------------------------------------------------------------------


def test_retry_runs_only_what_failed_in_the_same_batch(admin, ai: FakeOpenRouter, db: Session):
    ai.content["Lesson"] = copy.deepcopy(STARTER[SUPERVISED]["lesson"])
    ai.content["Quiz"] = {"questions": []}  # invalid twice: the quiz fails
    started = admin.post(
        "/api/admin/content/generate",
        json={"topic_ids": [topic_id(db)], "components": ["lesson", "quiz"]},
    ).json()
    run_pending_jobs()
    first = admin.get(f"/api/admin/content/jobs/{started['started'][0]['id']}").json()
    assert first["result"]["failed_components"] == ["quiz"]

    ai.content["Quiz"] = copy.deepcopy(STARTER[SUPERVISED]["quiz"])
    retry = admin.post(f"/api/admin/content/jobs/{first['id']}/retry")
    assert retry.status_code == 202, retry.text
    assert retry.json()["batch_id"] == started["batch_id"]
    run_pending_jobs()
    second = admin.get(f"/api/admin/content/jobs/{retry.json()['id']}").json()
    assert second["payload"]["components"] == ["quiz"]
    assert second["result"]["generated_components"] == ["quiz"]
    assert any(e["message"] == f"Retry of run {first['id']}." for e in second["events"])

    batch = admin.get("/api/admin/content/jobs", params={"batch_id": started["batch_id"]}).json()
    assert {j["id"] for j in batch["items"]} == {first["id"], second["id"]}
    assert admin.post(f"/api/admin/content/jobs/{second['id']}/retry").status_code == 409


# --- Coverage and the pilot evaluation ---------------------------------------------------------


def test_topic_insights_show_spend_and_interview_coverage(admin, ai: FakeOpenRouter, db: Session):
    used = approved_question(db, SUPERVISED)
    db.add(
        InterviewQuestion(
            experience_id=used.experience_id,
            source_id=used.source_id,
            record_id=used.record_id,
            job_id=used.job_id,
            original_text="How do you choose k in k-NN?",
            normalized_hash="h2",
            question_type=used.question_type,
            grounded=True,
            status=ReviewStatus.APPROVED,
            topic_id=used.topic_id,
            technologies=[],
        )
    )
    db.commit()
    interview = copy.deepcopy(STARTER[SUPERVISED]["interview"])
    interview["questions"][0].update(
        origin="actual_interview", source_ref=str(used.id), question=used.original_text
    )
    edit(admin, db, "interview", interview)
    ai.content["ContentReview"] = review_reply(issues=[])
    admin.post(
        f"/api/admin/content/versions/{latest(admin, db, 'lesson')['id']}/ai-review", json={}
    )
    run_pending_jobs()

    insights = admin.get(f"/api/admin/content/topics/{topic_id(db)}/insights").json()
    assert Decimal(insights["spend_usd"]) == Decimal("0.01") and insights["runs"] == 1
    assert insights["interview_version"] == 2 and insights["interview_published"] is False
    coverage = {q["question"]: q["used"] for q in insights["actual_questions"]}
    assert coverage == {used.original_text: True, "How do you choose k in k-NN?": False}
    assert "Acme" not in str(insights)  # never a company, even for admins here


def test_pilot_evaluation_summarises_every_pilot_component(admin, ai: FakeOpenRouter, db: Session):
    lesson = latest(admin, db, "lesson")["id"]
    for action in ("submit", "approve", "publish"):
        step(admin, lesson, action)
    criteria = [c["key"] for c in quality(admin, lesson)["ratings"]["criteria"]]
    admin.post(
        f"/api/admin/content/versions/{lesson}/ratings",
        json={"scores": dict.fromkeys(criteria, 4)},
    )
    ai.content["ContentReview"] = review_reply(issues=[])
    admin.post(f"/api/admin/content/versions/{lesson}/ai-review", json={})
    run_pending_jobs()

    evaluation = admin.get("/api/admin/content/pilot-evaluation").json()
    assert len(evaluation["topics"]) == 6 and evaluation["expansion_approved"] is False
    assert evaluation["totals"]["components"] == 42
    assert evaluation["totals"]["published"] == 1
    assert evaluation["totals"]["rated"] == 1 and evaluation["totals"]["average_rating"] == 4.0
    assert evaluation["totals"]["ai_reviewed"] == 1
    supervised = next(t for t in evaluation["topics"] if t["topic"]["slug"] == SUPERVISED)
    row = next(c for c in supervised["components"] if c["component"] == "lesson")
    assert row["published_number"] == 1 and row["errors"] == 0 and row["ai_score"] == 4.17


def test_content_quality_endpoints_need_content_permissions(make_client, admin, db: Session):
    version = latest(admin, db, "lesson")["id"]
    operator = as_role(make_client, "intelligence_operator")
    for path in (
        f"/api/admin/content/versions/{version}/quality",
        f"/api/admin/content/topics/{topic_id(db)}/insights",
        "/api/admin/content/pilot-evaluation",
    ):
        assert operator.get(path).status_code == 403
    assert db.scalar(select(InterviewQuestion.id)) is None
    assert db.scalar(select(Job.id)) is None
