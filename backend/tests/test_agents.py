"""Phase 3: the Exploration and Market Research agents, review, and run history.

All records and model replies here are synthetic test fixtures in the throwaway test database."""

from decimal import Decimal
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.agents.common import strict_schema
from app.agents.exploration import ExtractionOutput
from app.agents.research import ResearchOutput
from app.ai import openrouter
from app.intelligence.taxonomy import seed_default_taxonomy
from app.jobs.runner import run_pending_jobs
from app.models import AiUsageEvent, AuditLog, InterviewQuestion, Topic
from app.sources import service
from tests.fake_ai import FakeOpenRouter, experience, extraction, question
from tests.fakeweb import FakeWeb
from tests.helpers import create_admin, login_admin

# Synthetic interview write-ups (test fixtures, not real interviews).
RECORD_A = (
    "Interview experience (test fixture): Machine Learning Engineer at Acme Analytics.\n"
    'Round 1, phone screen: they asked "What is the bias-variance tradeoff?" and how I would '
    "deal with a fraud dataset where only 1% of rows are fraud.\n"
    "Round 2: Explain how gradient boosting differs from random forests."
)
RECORD_B = (
    "Data Scientist loop on 14 March 2026 (test fixture). The hiring manager asked: what is "
    "the bias variance trade-off? Then a SQL window functions exercise."
)
RECORD_C = "Ten pandas tips for beginners (test fixture). Use vectorised operations."

REPLY_A = extraction(
    experience(
        question(
            "What is the bias-variance tradeoff?",
            round="Round 1, phone screen",
            topic="machine-learning/model-evaluation",
        ),
        # Paraphrased by the model: not word-for-word in the record.
        question(
            "How do you handle class imbalance in fraud detection?",
            topic="machine-learning/classification",
        ),
        question(
            "Explain how gradient boosting differs from random forests.",
            round="Round 2",
            topic="machine-learning/ensemble-learning",
        ),
        company="Acme Analytics",
        role="Machine Learning Engineer",
    )
)
REPLY_B = extraction(
    experience(
        question("what is the bias variance trade-off?", topic="machine-learning/model-evaluation"),
        company="Globex",  # not in the record: must be dropped
        role="Data Scientist",
        interview_date="2026-03-14",
    )
)


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch) -> FakeOpenRouter:
    fake = FakeOpenRouter()
    fake.extractions = {"Acme Analytics": REPLY_A, "hiring manager asked": REPLY_B}
    monkeypatch.setattr(openrouter, "make_ai_client", fake.client)
    return fake


@pytest.fixture
def taxonomy(db: Session) -> None:
    seed_default_taxonomy(db)


@pytest.fixture
def admin(make_client, taxonomy) -> TestClient:
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def notes_source(admin: TestClient, *records: tuple[str, str]) -> str:
    source = admin.post(
        "/api/admin/sources",
        json={"name": "Alumni notes (test)", "connector_type": "file_upload"},
    ).json()
    for name, content in records:
        response = admin.post(
            f"/api/admin/sources/{source['id']}/upload",
            files={"file": (name, content.encode())},
        )
        assert response.status_code == 201, response.text
    return source["id"]


def explore(admin: TestClient, source_id: str, **options: Any) -> dict[str, Any]:
    started = admin.post(
        "/api/admin/agents/exploration",
        json={"source_ids": [source_id], "fetch_first": False, **options},
    )
    assert started.status_code == 202, started.text
    job_id = started.json()["started"][0]["id"]
    run_pending_jobs()
    return admin.get(f"/api/admin/agents/jobs/{job_id}").json()


def questions(admin: TestClient, **params: Any) -> list[dict[str, Any]]:
    page = admin.get("/api/admin/intelligence/questions", params={"page_size": 100, **params})
    assert page.status_code == 200, page.text
    return page.json()["items"]


def by_text(items: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    return next(q for q in items if q["original_text"].lower().startswith(prefix.lower()))


def standard_run(admin: TestClient) -> tuple[str, dict[str, Any]]:
    source_id = notes_source(admin, ("a.txt", RECORD_A), ("b.txt", RECORD_B), ("c.txt", RECORD_C))
    return source_id, explore(admin, source_id)


# --- Exploration ------------------------------------------------------------------------------


def test_exploration_extracts_only_what_the_records_say(admin, ai, db: Session):
    source_id, job = standard_run(admin)

    assert job["status"] == "succeeded", job
    assert job["result"] == {
        "fetched_new": 0,
        "fetched_updated": 0,
        "records_read": 3,
        "interview_records": 2,
        "not_interview": 1,
        "failed": 0,
        "questions": 4,
        "not_word_for_word": 1,
        "possible_duplicates": 1,
        "records_left": 0,
    }
    items = questions(admin)
    assert {q["status"] for q in items} == {"pending_review"}  # nothing counts until reviewed

    verbatim = by_text(items, "What is the bias-variance")
    assert verbatim["grounded"] is True
    assert verbatim["experience"]["company"] == "Acme Analytics"
    assert verbatim["topic"]["slug"] == "machine-learning/model-evaluation"
    assert verbatim["round"] == "Round 1, phone screen"
    assert by_text(items, "How do you handle class imbalance")["grounded"] is False

    from_b = by_text(items, "what is the bias variance trade-off")
    assert from_b["experience"]["company"] is None  # "Globex" isn't in the record
    assert from_b["experience"]["interview_date"] == "2026-03-14"  # written in the record
    assert from_b["duplicate_of_id"] == verbatim["id"]  # near-identical wording

    # Every call is billed to this run, and records go to the model inside <record> tags.
    costs = db.scalars(select(AiUsageEvent.job_id)).all()
    assert len(costs) == 3 and {str(c) for c in costs} == {job["id"]}
    assert job["cost_usd"] == "0.03000000"
    first = ai.calls("extraction")[0]
    assert first["model"] == "anthropic/claude-haiku-5.5"
    assert first["response_format"]["json_schema"]["strict"] is True
    assert first["provider"] == {"require_parameters": True}
    assert "<record>" in first["messages"][1]["content"]


def test_records_are_never_sent_to_the_model_twice(admin, ai):
    source_id, _ = standard_run(admin)
    again = explore(admin, source_id)
    assert again["status"] == "succeeded"
    assert again["result"]["records_read"] == 0
    assert any("already been read" in e["message"] for e in again["events"])
    assert len(ai.calls("extraction")) == 3


def test_a_date_that_is_not_written_down_is_not_kept(admin, ai):
    ai.extractions["vague date"] = extraction(
        experience(question("Explain dropout in neural networks."), interview_date="2026-03-02")
    )
    source_id = notes_source(
        admin,
        ("v.txt", "Interview in March 2026 (vague date). Explain dropout in neural networks."),
    )
    explore(admin, source_id)
    assert questions(admin)[0]["experience"]["interview_date"] is None


def test_an_invalid_reply_is_repaired_once_then_recorded_as_failed(admin, ai):
    replies = iter(["not json at all", REPLY_A])
    ai.extractions = {"Acme Analytics": lambda _: next(replies)}
    source_id = notes_source(admin, ("a.txt", RECORD_A))
    job = explore(admin, source_id)
    assert job["status"] == "succeeded"
    assert len(ai.calls("extraction")) == 2  # one repair request
    assert len(questions(admin)) == 3

    ai.extractions = {"hiring manager asked": "still not json"}
    source_b = admin.post(
        "/api/admin/sources", json={"name": "More notes (test)", "connector_type": "file_upload"}
    ).json()["id"]
    admin.post(
        f"/api/admin/sources/{source_b}/upload", files={"file": ("b.txt", RECORD_B.encode())}
    )
    failed = explore(admin, source_b)
    assert failed["status"] == "completed_with_errors"
    assert failed["result"]["failed"] == 1 and failed["result"]["records_left"] == 1
    assert any("retried next run" in e["message"] for e in failed["events"])

    ai.extractions = {"hiring manager asked": REPLY_B}
    retried = explore(admin, source_b)
    assert retried["result"]["records_read"] == 1  # the failed record is read again


def test_a_rejected_key_stops_the_run(admin, ai):
    ai.fail_status = 401
    source_id = notes_source(admin, ("a.txt", RECORD_A), ("b.txt", RECORD_B))
    job = explore(admin, source_id)
    assert job["status"] == "failed"
    assert "refused the request" in job["error"]
    assert len(ai.requests) == 1  # it didn't try every remaining record


def test_runs_stop_at_their_spending_limit(admin, ai):
    ai.cost = 0.6
    source_id = notes_source(admin, ("a.txt", RECORD_A), ("b.txt", RECORD_B), ("c.txt", RECORD_C))
    job = explore(admin, source_id, max_cost_usd="1.00")
    assert job["status"] == "completed_with_errors"
    assert job["result"]["records_read"] == 2 and job["result"]["records_left"] == 1
    assert any("spending limit" in e["message"] for e in job["events"])


def test_exploration_can_fetch_new_records_first(admin, ai, monkeypatch):
    web = FakeWeb()
    web.json("https://careers.example.com/api/posts", {"items": [{"id": 1, "text": RECORD_A}]})
    monkeypatch.setattr(service, "make_http", lambda *, min_interval: web.http())
    source = admin.post(
        "/api/admin/sources",
        json={
            "name": "Experiences API (test)",
            "connector_type": "json_api",
            "base_url": "https://careers.example.com",
            "config": {"endpoint": "/api/posts", "items_path": "items"},
        },
    ).json()
    job = explore(admin, source["id"], fetch_first=True)
    assert job["status"] == "succeeded", job
    assert job["result"]["fetched_new"] == 1 and job["result"]["questions"] == 3


def test_agents_need_the_ai_provider(admin):
    source_id = notes_source(admin, ("a.txt", RECORD_A))
    response = admin.post("/api/admin/agents/exploration", json={"source_ids": [source_id]})
    assert response.status_code == 409
    assert "IPP_OPENROUTER_API_KEY" in response.json()["detail"]
    assert admin.get("/api/admin/agents/status").json()["ai_configured"] is False


def test_agent_permissions(make_client, taxonomy, ai):
    create_admin(email="analyst@example.com", roles=("analyst",))
    create_admin(email="publisher@example.com", roles=("content_publisher",))
    analyst, publisher = make_client(), make_client()
    login_admin(analyst, email="analyst@example.com")
    login_admin(publisher, email="publisher@example.com")
    assert analyst.get("/api/admin/agents/jobs").status_code == 200
    assert analyst.get("/api/admin/intelligence/questions").status_code == 200
    assert analyst.post("/api/admin/agents/research", json={"roles": ["X"]}).status_code == 403
    assert analyst.post("/api/admin/intelligence/questions/review", json={}).status_code in (
        403,
        422,
    )
    assert publisher.get("/api/admin/agents/jobs").status_code == 403


# --- Review ---------------------------------------------------------------------------------------


def test_review_decides_what_counts(admin, ai, db: Session):
    standard_run(admin)
    items = questions(admin)
    canonical = by_text(items, "What is the bias-variance")
    duplicate = by_text(items, "what is the bias variance trade-off")
    boosting = by_text(items, "Explain how gradient boosting")
    paraphrase = by_text(items, "How do you handle class imbalance")

    assert admin.get("/api/admin/intelligence/topics").json()[0]["signal"] == "no_evidence"
    result = admin.post(
        "/api/admin/intelligence/questions/review",
        json={
            "question_ids": [canonical["id"], duplicate["id"], boosting["id"]],
            "status": "approved",
        },
    )
    assert result.json() == {"updated": 3}
    rejected = admin.patch(
        f"/api/admin/intelligence/questions/{paraphrase['id']}",
        json={"status": "rejected", "review_note": "Not the candidate's wording"},
    ).json()
    assert rejected["status"] == "rejected" and rejected["reviewed_by"] == "Platform Admin"

    detail = admin.get(f"/api/admin/intelligence/questions/{canonical['id']}").json()
    assert detail["seen_in_records"] == 2  # approved in two different records
    assert [d["id"] for d in detail["duplicates"]] == [duplicate["id"]]
    assert "What is the bias-variance tradeoff?" in detail["context"]

    topics = {t["topic"]["slug"]: t for t in admin.get("/api/admin/intelligence/topics").json()}
    evaluation = topics["machine-learning/model-evaluation"]
    assert (evaluation["approved_questions"], evaluation["interview_records"]) == (2, 2)
    assert set(evaluation["roles"]) == {"Machine Learning Engineer", "Data Scientist"}
    assert evaluation["signal"] == "asked"
    assert topics["machine-learning/classification"]["approved_questions"] == 0

    summary = admin.get("/api/admin/intelligence/summary").json()
    assert summary["approved_questions"] == 3 and summary["rejected_questions"] == 1
    assert summary["interview_records"] == 2 and summary["pending_questions"] == 0
    assert db.scalar(
        select(AuditLog.details).where(AuditLog.action == "intelligence.questions_reviewed")
    ) == {
        "status": "approved",
        "count": 3,
    }


def test_reviewers_fix_topics_duplicates_and_interview_details(admin, ai, db: Session):
    standard_run(admin)
    items = questions(admin)
    canonical = by_text(items, "What is the bias-variance")
    duplicate = by_text(items, "what is the bias variance trade-off")
    boosting = by_text(items, "Explain how gradient boosting")
    topic = db.scalar(select(Topic).where(Topic.slug == "machine-learning/supervised-learning"))

    moved = admin.patch(
        f"/api/admin/intelligence/questions/{boosting['id']}",
        json={"topic_id": str(topic.id), "difficulty": "medium"},
    ).json()
    assert moved["topic"]["slug"] == "machine-learning/supervised-learning"

    # Marking a question as a duplicate of a duplicate points it at the original.
    merged = admin.patch(
        f"/api/admin/intelligence/questions/{boosting['id']}",
        json={"duplicate_of_id": duplicate["id"]},
    ).json()
    assert merged["duplicate_of_id"] == canonical["id"]
    selfdup = admin.patch(
        f"/api/admin/intelligence/questions/{canonical['id']}",
        json={"duplicate_of_id": canonical["id"]},
    )
    assert selfdup.status_code == 422

    corrected = admin.patch(
        f"/api/admin/intelligence/experiences/{duplicate['experience']['id']}",
        json={"company": "Initech", "role": "Senior Data Scientist"},
    )
    assert corrected.json()["company"] == "Initech"
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "intelligence.interview_corrected"))
    assert audit.details["company"] == {"from": None, "to": "Initech"}
    assert audit.details["role"] == {"from": "Data Scientist", "to": "Senior Data Scientist"}


# --- Market research ------------------------------------------------------------------------------

SOURCES = [
    {
        "url": "https://jobs.example.org/ml-engineer-report",
        "title": "ML engineer hiring report (fixture)",
        "content": "Postings for ML engineers increasingly ask for experience with LLM agents "
        "and retrieval-augmented generation. Demand for RAG skills rose sharply this year.",
    },
    {
        "url": "https://survey.example.net/data-science-2026",
        "title": "Data science survey (fixture)",
        "content": "SQL and experiment design remain the most requested data science skills.",
    },
]


def research_reply(_: dict[str, Any]) -> dict[str, Any]:
    finding = {
        "roles": ["Machine Learning Engineer"],
        "skills": ["RAG"],
        "evidence": [],
    }
    return {
        "title": "AI/ML hiring, fixture report",
        "summary": "Agent and RAG skills are rising for ML engineers (fixture).",
        "findings": [
            {
                **finding,
                "topic": "generative-ai-and-llms/rag",
                "topic_label": "RAG",
                "observation": "Demand for RAG skills rose sharply.",
                "trend": "rising",
                "evidence": [
                    {"source": 1, "quote": "Demand for RAG skills rose sharply this year."}
                ],
            },
            {
                **finding,
                "topic": None,
                "topic_label": "Quantum ML",
                "observation": "Quantum ML is booming.",
                "trend": "emerging",
                "evidence": [{"source": 99, "quote": "made up"}],  # no such source: dropped
            },
            {
                **finding,
                "topic": "machine-learning/model-evaluation",
                "topic_label": "Experiment design",
                "observation": "Experiment design remains in demand.",
                "trend": "stable",
                "evidence": [{"source": 2, "quote": "Experiment design is the top skill."}],
            },
        ],
        "recommendations": [
            {
                "kind": "add_topic",
                "topic": None,
                "domain": "agentic-ai",
                "proposed_name": "Agent Memory",
                "rationale": "Agent work is rising.",
                "findings": [1],
            },
            {
                "kind": "prioritize",
                "topic": "generative-ai-and-llms/rag",
                "domain": None,
                "proposed_name": None,
                "rationale": "RAG demand rose.",
                "findings": [1],
            },
            {
                "kind": "add_topic",
                "topic": None,
                "domain": "astrology",
                "proposed_name": "Horoscopes",
                "rationale": "No.",
                "findings": [1],
            },
            {
                "kind": "deprioritize",
                "topic": "machine-learning/clustering",
                "domain": None,
                "proposed_name": None,
                "rationale": "Based on a dropped finding.",
                "findings": [2],
            },
            {
                "kind": "add_topic",
                "topic": None,
                "domain": "agentic-ai",
                "proposed_name": "LangGraph",
                "rationale": "Already exists.",
                "findings": [1],
            },
        ],
        "questions": [
            {
                "text": "How would you evaluate a retrieval-augmented generation pipeline?",
                "topic": "generative-ai-and-llms/rag",
                "topic_label": "RAG",
                "role": "Machine Learning Engineer",
                "rationale": "RAG demand is rising.",
                "findings": [1],
            },
            {
                "text": "Unbacked question?",
                "topic": None,
                "topic_label": "General",
                "role": None,
                "rationale": "None.",
                "findings": [],
            },
        ],
    }


def research(admin: TestClient, **fields: Any) -> dict[str, Any]:
    started = admin.post(
        "/api/admin/agents/research",
        json={
            "roles": ["Machine Learning Engineer", "Data Scientist"],
            "region": "India",
            **fields,
        },
    )
    assert started.status_code == 202, started.text
    run_pending_jobs()
    return admin.get(f"/api/admin/agents/jobs/{started.json()['id']}").json()


def test_research_keeps_only_findings_backed_by_sources(admin, ai):
    ai.searches = {
        "Machine Learning Engineer": ("ML notes [jobs.example.org]", [SOURCES[0]]),
        "Data Scientist": ("DS notes", [SOURCES[1], SOURCES[0]]),
    }
    ai.structure = research_reply
    job = research(admin)

    assert job["status"] == "succeeded", job
    searches = ai.calls("search")
    assert len(searches) == 2
    assert searches[0]["plugins"] == [{"id": "web", "engine": "exa", "max_results": 5}]
    assert "in India" in searches[0]["messages"][0]["content"]
    assert job["result"] == {
        "sources": 2,
        "findings": 2,
        "findings_dropped": 1,
        "unverified_quotes": 1,
        "recommendations": 2,
        "questions": 1,
        "suggestions_dropped": 4,
        "report_id": job["report_id"],
    }

    report = admin.get(f"/api/admin/research/reports/{job['report_id']}").json()
    assert [s["site"] for s in report["source_list"]] == ["jobs.example.org", "survey.example.net"]
    rag, design = report["finding_list"]
    assert rag["evidence"][0]["quote_verified"] is True
    assert design["evidence"][0]["quote_verified"] is False  # not in the excerpt
    assert [r["kind"] for r in report["recommendations"]] == ["add_topic", "prioritize"]
    assert {r["status"] for r in report["recommendations"]} == {"pending"}
    assert report["question_list"][0]["text"].startswith("How would you evaluate")

    topics = {t["topic"]["slug"]: t for t in admin.get("/api/admin/intelligence/topics").json()}
    assert topics["generative-ai-and-llms/rag"]["research"]["latest_trend"] == "rising"
    assert topics["generative-ai-and-llms/rag"]["signal"] == "rising_in_market"


def test_research_without_sources_fails_honestly(admin, ai):
    ai.searches = {}
    job = research(admin)
    assert job["status"] == "failed"
    assert "no sources" in job["error"]
    assert not ai.calls("structure")


def test_recommendations_need_a_human_decision(make_client, taxonomy, ai, db: Session):
    ai.searches = {"Machine Learning Engineer": ("notes", [SOURCES[0]])}
    ai.structure = research_reply
    create_admin(email="curator@example.com", roles=("content_manager",))
    create_admin(email="analyst@example.com", roles=("analyst",))
    create_admin(email="ops@example.com", roles=("intelligence_operator",))
    curator, analyst, ops = make_client(), make_client(), make_client()
    login_admin(curator, email="curator@example.com")
    login_admin(analyst, email="analyst@example.com")
    login_admin(ops, email="ops@example.com")
    research(ops, roles=["Machine Learning Engineer"])

    pending = curator.get("/api/admin/research/recommendations").json()
    add_topic = next(r for r in pending if r["kind"] == "add_topic")
    prioritize = next(r for r in pending if r["kind"] == "prioritize")
    path = "/api/admin/research/recommendations/{}/decision"
    assert (
        analyst.post(path.format(add_topic["id"]), json={"decision": "approved"}).status_code == 403
    )

    approved = curator.post(
        path.format(add_topic["id"]), json={"decision": "approved", "note": "Worth adding"}
    ).json()
    created = db.get(Topic, approved["created_topic_id"])
    assert (created.slug, created.is_pilot) == ("agentic-ai/agent-memory", False)
    assert (
        curator.post(path.format(add_topic["id"]), json={"decision": "rejected"}).status_code == 409
    )

    deferred = curator.post(path.format(prioritize["id"]), json={"decision": "deferred"}).json()
    assert deferred["status"] == "deferred"
    assert (
        curator.post(path.format(prioritize["id"]), json={"decision": "rejected"}).json()["status"]
        == "rejected"
    )
    assert curator.get("/api/admin/research/recommendations").json() == []

    question_id = curator.get(f"/api/admin/research/reports/{approved['report_id']}").json()[
        "question_list"
    ][0]["id"]
    assert (
        curator.patch(
            f"/api/admin/research/questions/{question_id}", json={"status": "approved"}
        ).status_code
        == 403
    )
    reviewed = ops.patch(
        f"/api/admin/research/questions/{question_id}", json={"status": "approved"}
    )
    assert reviewed.json()["status"] == "approved"


# --- Run history ----------------------------------------------------------------------------------


def test_run_history_shows_cost_and_supports_retry_and_stop(admin, ai):
    source_id, job = standard_run(admin)
    history = admin.get("/api/admin/agents/jobs", params={"kind": "exploration"}).json()
    assert history["total"] == 1
    assert history["items"][0]["source_name"] == "Alumni notes (test)"
    assert history["items"][0]["cost_usd"] == "0.03000000"

    retry = admin.post(f"/api/admin/agents/jobs/{job['id']}/retry")
    assert retry.status_code == 202
    assert (
        admin.post(f"/api/admin/agents/jobs/{job['id']}/retry").status_code == 409
    )  # one at a time
    stopped = admin.post(f"/api/admin/agents/jobs/{retry.json()['id']}/cancel").json()
    assert stopped["status"] == "cancelled"
    assert admin.get("/api/admin/agents/jobs").json()["total"] == 2 + 3  # plus the 3 imports


# --- Permanence and schemas -------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE record_extractions SET error = 'x'",
        "DELETE FROM interview_questions",
        "DELETE FROM interview_experiences",
        "DELETE FROM topics",
    ],
)
def test_intelligence_records_are_permanent(admin, ai, db: Session, statement):
    standard_run(admin)
    with pytest.raises(DBAPIError, match="append-only|kept permanently"):
        db.execute(text(statement))
    db.rollback()


def test_reviewed_questions_can_change_status_but_not_their_wording(admin, ai, db: Session):
    standard_run(admin)
    first = db.scalar(select(InterviewQuestion).order_by(InterviewQuestion.created_at))
    response = admin.patch(
        f"/api/admin/intelligence/questions/{first.id}",
        json={"original_text": "rewritten", "status": "approved"},
    )
    assert response.status_code == 200
    assert response.json()["original_text"] == first.original_text  # wording is not editable
    assert response.json()["status"] == "approved"


@pytest.mark.parametrize("model", [ExtractionOutput, ResearchOutput])
def test_structured_output_schemas_are_strict(model):
    def objects(node: Any) -> list[dict[str, Any]]:
        if isinstance(node, dict):
            found = [node] if node.get("type") == "object" else []
            return found + [o for v in node.values() for o in objects(v)]
        if isinstance(node, list):
            return [o for v in node for o in objects(v)]
        return []

    schema = strict_schema(model)
    for node in objects(schema):
        assert node["additionalProperties"] is False
        assert set(node["required"]) == set(node["properties"])
    # Field names survive, even ones that look like schema keywords ("title").
    assert set(schema["properties"]) == set(model.model_fields)
    assert "maxLength" not in str(schema) and "minItems" not in str(schema)


def test_provider_busy_responses_are_retried_without_double_billing(db: Session):
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429, headers={"retry-after": "1"})
        return httpx.Response(
            200,
            json={
                "id": "gen-retry",
                "choices": [
                    {
                        "message": {
                            "content": "ok",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url_citation": {
                                        "url": "https://a.example/x",
                                        "title": "A",
                                        "content": "c",
                                    },
                                },
                                {
                                    "type": "url_citation",
                                    "url_citation": {
                                        "url": "https://a.example/x",
                                        "title": "A",
                                        "content": "c",
                                    },
                                },
                                {
                                    "type": "url_citation",
                                    "url_citation": {"url": "javascript:alert(1)"},
                                },
                            ],
                        }
                    }
                ],
                "usage": {"cost": 0.002},
            },
        )

    pauses: list[float] = []
    client = openrouter.OpenRouterClient(
        "k",
        "https://openrouter.test/api/v1",
        transport=httpx.MockTransport(handler),
        sleep=pauses.append,
    )
    result = client.chat(feature="test", model="m", messages=[])
    assert pauses == [1.0, 1.0] and len(attempts) == 3
    assert result.citations == [{"url": "https://a.example/x", "title": "A", "content": "c"}]
    assert db.scalar(select(AiUsageEvent.cost_usd)) == Decimal("0.00200000")
