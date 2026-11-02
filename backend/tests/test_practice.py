"""Interview practice: a student's spoken answer is transcribed and scored like an interviewer
would, within an admin switch and a daily limit, without keeping the audio, and only ever visible
to that student. All answers and AI replies here are synthetic test fixtures."""

import io
import struct
import uuid
import wave
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.ai.openrouter import TranscriptSegment
from app.content.schemas import COMPONENT_ORDER
from app.content.seed import seed_starter_content
from app.content.starter import TOPICS
from app.core.config import get_settings
from app.core.rate_limit import reset_all_rate_limits
from app.core.security import utcnow
from app.intelligence.taxonomy import seed_default_taxonomy
from app.models import (
    AiUsageEvent,
    AttemptStatus,
    AuditLog,
    Component,
    PracticeAttempt,
    Topic,
)
from app.practice.audio import AudioProblem, wav_duration_ms
from app.practice.delivery import measure
from app.practice.feedback import AnswerFeedback, overall_score, verdict
from app.practice.service import recover_stale_attempts, run_pending_attempts
from tests.fake_ai import FakeOpenRouter
from tests.helpers import create_admin, login_admin, register_student

SUPERVISED = "machine-learning/supervised-learning"
INTERVIEW = {module.TOPIC: module.CONTENT["interview"] for module in TOPICS}[SUPERVISED]
FIRST = INTERVIEW["questions"][0]

# What the synthetic student "says". Long enough to be judged, with two filler words.
ANSWER = (
    "Um so supervised learning means we learn from labelled examples, basically every input "
    "comes with the right answer and the model learns a mapping from inputs to outputs so it "
    "can predict labels for new data, like spam detection or house prices."
)


def wav(seconds: float = 20, rate: int = 16_000, channels: int = 1) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(struct.pack("<h", 0) * int(seconds * rate) * channels)
    return buffer.getvalue()


def feedback_reply(**overrides: Any) -> dict[str, Any]:
    reply = {
        "answered_question": True,
        "summary": "You nailed the core idea. Add how the model is evaluated to sound senior.",
        "technical_accuracy": {"score": 4, "comment": "Correct definition and examples."},
        "depth": {"score": 4, "comment": "Covers labels and prediction; misses evaluation."},
        "structure": {"score": 3, "comment": "Direct opening, but no clear close."},
        "communication": {"score": 4, "comment": "Clear and well paced."},
        "strengths": [
            {"point": "Clear definition", "quote": "we learn from labelled examples"},
            # Not in the transcript: code must drop it.
            {"point": "Mentions overfitting", "quote": "we must guard against overfitting"},
        ],
        "improvements": [
            {"point": "Mention evaluation", "how": "Say how you'd test on held-out data."}
        ],
        "key_points_covered": ["labelled data", "input to output mapping"],
        "key_points_missed": ["train/test split"],
        "mistakes": [
            {
                "quote": "like spam detection or house prices",
                "correction": "Both are fine examples.",
            },
            {"quote": "labels are optional", "correction": "Never said, so it is dropped."},
        ],
        "tips": ["Open with a one-line definition, then one example."],
        "better_answer": "Supervised learning is learning from labelled examples...",
        "follow_up_index": 0,
    }
    reply.update(overrides)
    return reply


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch) -> FakeOpenRouter:
    fake = FakeOpenRouter()
    fake.transcript = ANSWER
    fake.segments = [
        {"id": 0, "start": 1.5, "end": 8.0, "text": ANSWER[:90]},
        {"id": 1, "start": 12.0, "end": 18.0, "text": ANSWER[90:]},
    ]
    fake.content["AnswerFeedback"] = feedback_reply()
    monkeypatch.setattr(openrouter, "make_ai_client", fake.client)
    return fake


@pytest.fixture
def admin(make_client, db: Session) -> TestClient:
    seed_default_taxonomy(db)
    seed_starter_content(db)
    create_admin()
    client = make_client()
    login_admin(client)
    return client


def step_to_published(admin: TestClient, version_id: str) -> str:
    for action in ("submit", "approve", "publish"):
        response = admin.post(
            f"/api/admin/content/versions/{version_id}/transition", json={"action": action}
        )
        assert response.status_code == 200, response.text
    return version_id


def publish(admin: TestClient, db: Session, topic: str, component: str) -> str:
    topic_id = db.scalar(select(Topic.id).where(Topic.slug == topic))
    detail = admin.get(f"/api/admin/content/topics/{topic_id}").json()
    version = next(c for c in detail["components"] if c["component"] == component)["latest"]
    return step_to_published(admin, version["id"])


@pytest.fixture
def interview(admin: TestClient, db: Session) -> str:
    publish(admin, db, SUPERVISED, "lesson")
    return publish(admin, db, SUPERVISED, "interview")


@pytest.fixture
def student(make_client, interview: str) -> TestClient:
    client = make_client()
    register_student(client)
    return client


def submit(
    student: TestClient,
    version_id: str,
    *,
    index: int = 0,
    audio: bytes | None = None,
    topic: str = SUPERVISED,
    expect: int = 202,
) -> dict[str, Any]:
    response = student.post(
        "/api/student/practice/attempts",
        data={"topic": topic, "version_id": version_id, "question_index": str(index)},
        files={"audio": ("answer.wav", audio if audio is not None else wav(), "audio/wav")},
    )
    assert response.status_code == expect, response.text
    return response.json()


# --- The happy path -----------------------------------------------------------------------------


def test_a_spoken_answer_gets_interviewer_feedback(
    ai: FakeOpenRouter, student: TestClient, interview: str, db: Session
):
    page = student.get(f"/api/student/learn/topics/{SUPERVISED}").json()
    assert page["interview"]["version_id"] == interview

    status = student.get("/api/student/practice/status").json()
    assert status == {
        "feedback_available": True,
        "reason": None,
        "daily_limit": 10,
        "used_today": 0,
        "max_seconds": 180,
    }

    queued = submit(student, interview)
    assert queued["status"] == "queued" and queued["question"] == FIRST["question"]
    assert queued["duration_ms"] == 20_000
    assert run_pending_attempts() == 1

    done = student.get(f"/api/student/practice/attempts/{queued['id']}").json()
    assert done["status"] == "completed" and done["transcript"] == ANSWER
    feedback = done["feedback"]
    # 4·0.35 + 4·0.30 + 3·0.15 + 4·0.20 = 3.85 on 1-5, i.e. 7.1 out of 10.
    assert feedback["score"] == 7.1 and done["score"] == 7.1
    assert feedback["verdict"] == {"key": "almost", "label": "Almost there"}
    assert [c["key"] for c in feedback["criteria"]] == [
        "technical_accuracy",
        "depth",
        "structure",
        "communication",
    ]
    # Quotes the student never said are dropped; the follow-up is the question's own.
    assert [s["point"] for s in feedback["strengths"]] == ["Clear definition"]
    assert [m["quote"] for m in feedback["mistakes"]] == ["like spam detection or house prices"]
    assert feedback["follow_up"] == {
        "question": FIRST["follow_ups"][0]["question"],
        "answer": FIRST["follow_ups"][0]["answer"],
    }
    assert "dropped_quotes" not in feedback

    delivery = done["delivery"]
    assert delivery["fillers"] == {"um": 1, "basically": 1} and delivery["filler_count"] == 2
    assert delivery["longest_pause_s"] == 4.0 and delivery["long_pauses"] == 1
    assert delivery["opening_pause_s"] == 1.5 and delivery["pace"] in {"good", "slow", "fast"}

    # Students never see which models ran.
    settings = get_settings()
    assert settings.model_feedback not in str(done)
    assert settings.model_transcription not in str(done)

    # The voice is gone; the spend is attributed to the student and the attempt.
    attempt = db.get(PracticeAttempt, uuid.UUID(queued["id"]))
    assert attempt is not None and attempt.audio is None
    assert attempt.transcription_model and attempt.feedback_model
    events = db.scalars(select(AiUsageEvent).order_by(AiUsageEvent.id)).all()
    assert [e.feature for e in events] == ["practice_transcription", "practice_feedback"]
    assert {e.practice_attempt_id for e in events} == {attempt.id}
    assert {e.triggered_by_student_id for e in events} == {attempt.student_id}
    assert events[0].cost_usd == Decimal("0.002")

    call = ai.transcription_calls()[0]
    assert call["input_audio"]["format"] == "wav" and call["language"] == "en"
    assert call["response_format"] == "verbose_json"
    prompt = ai.schema_calls("AnswerFeedback")[0]["messages"][1]["content"]
    assert FIRST["answer"] in prompt and FIRST["interviewer_wants"] in prompt
    assert f"<transcript>\n{ANSWER}\n</transcript>" in prompt
    assert "Filler words: 2 (um ×1, basically ×1)" in prompt

    listed = student.get("/api/student/practice/attempts", params={"topic": SUPERVISED}).json()
    assert [(a["id"], a["score"], a["verdict"]) for a in listed] == [
        (queued["id"], 7.1, "Almost there")
    ]
    assert student.get("/api/student/practice/status").json()["used_today"] == 1


def test_providers_without_timed_segments_still_work(
    ai: FakeOpenRouter, student: TestClient, interview: str
):
    ai.plain_transcripts_only = True
    attempt = submit(student, interview)
    run_pending_attempts()
    done = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()
    assert done["status"] == "completed"
    assert done["delivery"]["longest_pause_s"] is None
    assert [c.get("response_format") for c in ai.transcription_calls()] == ["verbose_json", None]


def test_too_little_speech_is_not_sent_for_feedback(
    ai: FakeOpenRouter, student: TestClient, interview: str
):
    ai.transcript = "Um, I am not sure."
    attempt = submit(student, interview)
    run_pending_attempts()
    done = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()
    assert done["status"] == "no_answer" and done["feedback"] is None
    assert ai.schema_calls("AnswerFeedback") == []


def test_off_topic_and_wrong_answers_are_never_interview_ready(
    ai: FakeOpenRouter, student: TestClient, interview: str
):
    ai.content["AnswerFeedback"] = feedback_reply(
        answered_question=False,
        technical_accuracy={"score": 5, "comment": "-"},
        depth={"score": 5, "comment": "-"},
    )
    attempt = submit(student, interview)
    run_pending_attempts()
    feedback = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()["feedback"]
    assert feedback["score"] == 2.0 and feedback["verdict"]["key"] == "off_topic"


def test_failures_erase_the_audio_and_do_not_use_up_the_daily_limit(
    ai: FakeOpenRouter, student: TestClient, interview: str, db: Session
):
    ai.fail_status = 503
    attempt = submit(student, interview)
    run_pending_attempts()
    done = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()
    assert done["status"] == "failed"
    assert done["error"] == "The AI is busy right now. Try again in a minute."
    assert done["transcript"] is None
    row = db.get(PracticeAttempt, uuid.UUID(attempt["id"]))
    assert row is not None and row.audio is None
    assert student.get("/api/student/practice/status").json()["used_today"] == 0


def test_garbled_feedback_is_retried_once_then_fails(
    ai: FakeOpenRouter, student: TestClient, interview: str
):
    ai.content["AnswerFeedback"] = {"summary": "not the schema"}
    attempt = submit(student, interview)
    run_pending_attempts()
    done = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()
    assert done["status"] == "failed" and "wrong shape" in done["error"]
    assert len(ai.schema_calls("AnswerFeedback")) == 2


# --- Limits ------------------------------------------------------------------------------------


def test_feedback_needs_the_ai_provider(student: TestClient, interview: str):
    status = student.get("/api/student/practice/status").json()
    assert status["feedback_available"] is False
    assert status["reason"] == "AI feedback isn't set up yet."
    response = student.post(
        "/api/student/practice/attempts",
        data={"topic": SUPERVISED, "version_id": interview, "question_index": "0"},
        files={"audio": ("a.wav", wav(), "audio/wav")},
    )
    assert response.status_code == 503


def test_admins_set_the_daily_limit_and_can_switch_feedback_off(
    ai: FakeOpenRouter, admin: TestClient, student: TestClient, interview: str, db: Session
):
    view = admin.put("/api/admin/practice/settings", json={"enabled": True, "daily_limit": 1})
    assert view.status_code == 200 and view.json()["daily_limit"] == 1

    submit(student, interview)
    run_pending_attempts()
    limited = submit(student, interview, expect=429)
    assert limited["detail"] == "You've used today's 1 feedback requests. More tomorrow!"

    admin.put("/api/admin/practice/settings", json={"enabled": False, "daily_limit": 5})
    status = student.get("/api/student/practice/status").json()
    assert status["feedback_available"] is False
    assert status["reason"] == "AI feedback is switched off right now."
    submit(student, interview, expect=503)

    stats = admin.get("/api/admin/practice/settings").json()
    assert stats["enabled"] is False and stats["ai_configured"] is True
    assert stats["last_7_days"]["attempts"] == 1 and stats["last_7_days"]["students"] == 1
    assert stats["last_7_days"]["average_score"] == 7.1
    assert Decimal(stats["last_7_days"]["cost_usd"]) == Decimal("0.012")  # 0.002 + 0.01

    audits = db.scalars(
        select(AuditLog).where(AuditLog.action == "practice.settings_changed").order_by(AuditLog.id)
    ).all()
    assert [a.details for a in audits] == [
        {"daily_limit": {"from": 10, "to": 1}},
        {"enabled": {"from": True, "to": False}, "daily_limit": {"from": 1, "to": 5}},
    ]


def test_practice_settings_need_admin_permissions(make_client, student: TestClient):
    assert student.get("/api/admin/practice/settings").status_code == 401

    create_admin(email="cm@example.com", roles=("content_manager",))
    content = make_client()
    login_admin(content, email="cm@example.com")
    assert content.get("/api/admin/practice/settings").status_code == 403

    create_admin(email="analyst@example.com", roles=("analyst",))
    analyst = make_client()
    login_admin(analyst, email="analyst@example.com")
    assert analyst.get("/api/admin/practice/settings").status_code == 403
    assert (
        analyst.put(
            "/api/admin/practice/settings", json={"enabled": False, "daily_limit": 3}
        ).status_code
        == 403
    )
    bad = make_client()
    login_admin(bad)
    assert (
        bad.put(
            "/api/admin/practice/settings", json={"enabled": True, "daily_limit": 0}
        ).status_code
        == 422
    )


# --- Uploads ------------------------------------------------------------------------------------


def test_uploads_are_checked(
    ai: FakeOpenRouter, admin: TestClient, student: TestClient, interview: str
):
    assert "WAV" in submit(student, interview, audio=b"not audio", expect=422)["detail"]
    assert "mono" in submit(student, interview, audio=wav(channels=2), expect=422)["detail"]
    assert "short" in submit(student, interview, audio=wav(seconds=1), expect=422)["detail"]
    assert "3 minutes" in submit(student, interview, audio=wav(seconds=190), expect=422)["detail"]
    too_big = wav(seconds=10) + b"\0" * 10_000_000
    assert submit(student, interview, audio=too_big, expect=413)["detail"]
    reset_all_rate_limits()  # six uploads a minute per student
    for _ in range(6):
        submit(student, interview, audio=b"x", expect=422)
    assert submit(student, interview, expect=429)["detail"].startswith("Too many answers")
    reset_all_rate_limits()
    assert submit(student, str(uuid.uuid4()), expect=409)["detail"].startswith("These questions")
    submit(student, interview, index=99, expect=404)
    submit(student, interview, topic="machine-learning/regression", expect=404)  # unpublished
    assert ai.requests == []


def test_a_republished_question_set_needs_a_reload(
    ai: FakeOpenRouter, admin: TestClient, student: TestClient, interview: str
):
    restored = admin.post(f"/api/admin/content/versions/{interview}/restore")
    assert restored.status_code == 201, restored.text
    newer = step_to_published(admin, restored.json()["id"])
    submit(student, interview, expect=409)
    assert submit(student, newer)["status"] == "queued"


# --- Privacy -------------------------------------------------------------------------------------


def test_students_only_ever_see_their_own_attempts(
    ai: FakeOpenRouter, make_client, student: TestClient, interview: str, db: Session
):
    mine = submit(student, interview)

    other = make_client()
    register_student(other, email="ravi@example.com", name="Ravi K")
    assert other.get(f"/api/student/practice/attempts/{mine['id']}").status_code == 404
    assert other.delete(f"/api/student/practice/attempts/{mine['id']}").status_code == 404
    assert other.get("/api/student/practice/attempts").json() == []

    # Still processing: it can't be deleted yet.
    assert student.delete(f"/api/student/practice/attempts/{mine['id']}").status_code == 409
    run_pending_attempts()
    assert student.delete(f"/api/student/practice/attempts/{mine['id']}").status_code == 204
    assert student.get(f"/api/student/practice/attempts/{mine['id']}").status_code == 404
    assert student.get("/api/student/practice/attempts").json() == []

    row = db.get(PracticeAttempt, uuid.UUID(mine["id"]))
    assert row is not None and row.deleted_at is not None
    assert row.transcript is None and row.feedback is None and row.delivery is None
    # Deleting doesn't hand back the day's feedback request.
    assert student.get("/api/student/practice/status").json()["used_today"] == 1


def test_practice_rows_are_never_deleted(
    ai: FakeOpenRouter, student: TestClient, interview: str, db: Session
):
    submit(student, interview)
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM practice_attempts"))
        db.commit()
    db.rollback()


def test_interrupted_attempts_fail_and_free_the_quota(
    ai: FakeOpenRouter, student: TestClient, interview: str, db: Session
):
    attempt = submit(student, interview)
    db.execute(
        update(PracticeAttempt)
        .where(PracticeAttempt.id == uuid.UUID(attempt["id"]))
        .values(status=AttemptStatus.PROCESSING, heartbeat_at=utcnow() - timedelta(minutes=30))
    )
    db.commit()
    assert recover_stale_attempts() == 1
    done = student.get(f"/api/student/practice/attempts/{attempt['id']}").json()
    assert done["status"] == "failed" and "took too long" in done["error"]
    assert student.get("/api/student/practice/status").json()["used_today"] == 0


# --- Units --------------------------------------------------------------------------------------


def test_quiz_comes_before_interview_practice():
    order = list(COMPONENT_ORDER)
    assert order.index(Component.QUIZ) < order.index(Component.INTERVIEW)


def test_the_overall_score_follows_the_rubric():
    def fb(accuracy: int, depth: int, structure: int, communication: int) -> AnswerFeedback:
        return AnswerFeedback.model_validate(
            feedback_reply(
                technical_accuracy={"score": accuracy, "comment": "-"},
                depth={"score": depth, "comment": "-"},
                structure={"score": structure, "comment": "-"},
                communication={"score": communication, "comment": "-"},
            )
        )

    assert overall_score(fb(5, 5, 5, 5)) == Decimal("10.0")
    assert overall_score(fb(1, 1, 1, 1)) == Decimal("0.0")
    perfect_delivery_wrong_facts = fb(2, 5, 5, 5)
    score = overall_score(perfect_delivery_wrong_facts)
    assert score == Decimal("7.4")
    assert verdict(perfect_delivery_wrong_facts, score) == "getting_there"
    assert verdict(fb(5, 5, 4, 5), overall_score(fb(5, 5, 4, 5))) == "ready"


def test_delivery_is_measured_from_the_transcript():
    segments = [TranscriptSegment(0.8, 30.0, "a"), TranscriptSegment(33.5, 60.8, "b")]
    words = " ".join(["word"] * 120) + " um uh basically you know"
    measured = measure(words, 62_000, segments)
    assert measured["words"] == 125
    assert measured["wpm"] == 125  # 125 words over the 60 s actually spoken
    assert measured["fillers"] == {"um": 1, "uh": 1, "basically": 1, "you know": 1}
    assert measured["longest_pause_s"] == 3.5 and measured["long_pauses"] == 1
    assert measured["opening_pause_s"] == 0.8
    no_segments = measure("one two three", 3_000, [])
    assert no_segments["wpm"] == 60 and no_segments["longest_pause_s"] is None


def test_wav_checks():
    assert wav_duration_ms(wav(seconds=12.5), 180) == 12_500
    for bad in (b"", b"RIFF....WAVE", wav(rate=44_100)):
        with pytest.raises(AudioProblem):
            wav_duration_ms(bad, 180)
