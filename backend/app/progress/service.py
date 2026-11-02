"""Recording what students do, grading quizzes, and turning both into progress and mastery.

Completion and mastery are kept apart, as the spec asks: completion says which sections a student
went through, mastery says how well they did in the quiz and the interview practice. Neither is a
single score for "how good" a student is.

A section counts as done when the student:
- lesson: has seen every card;
- playground: has tried every task (opened its insight);
- video: watched to the end;
- python: ran the lab and got the expected output;
- quiz: submitted an attempt (graded here, never by the browser);
- interview: recorded answers to at least half the questions;
- revision: opened the cheat sheet.
"""

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content.schemas import COMPONENT_ORDER
from app.content.service import published_by_topic, visible_topics
from app.core.config import get_settings
from app.core.security import utcnow
from app.models import (
    AttemptStatus,
    Component,
    ContentVersion,
    LearningEvent,
    LearningEventKind,
    PracticeAttempt,
    QuizAttempt,
    QuizResponse,
    Topic,
    TopicProgress,
)

STRONG_AT = 75.0
DEVELOPING_AT = 50.0
# Mastery looks at recent evidence, so a student who improves sees it.
RECENT_QUIZZES = 3
RECENT_PRACTICE = 5
QUIZ_WEIGHT = 0.6  # quiz vs interview practice when a topic has both
# Time reports: the browser sends active seconds about once a minute. The server never credits
# more than the time that has passed since the student's previous report (plus a little slack for
# network delay), so parallel tabs or a tampered client can't inflate it.
MAX_TIME_REPORT = 120
TIME_SLACK = 10


class ProgressError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().usage_timezone)


# --- Topics a student can see --------------------------------------------------------------------


@dataclass(frozen=True)
class LiveTopic:
    topic: Topic
    parts: dict[Component, ContentVersion]

    @property
    def sections(self) -> list[Component]:
        return [c for c in COMPONENT_ORDER if c in self.parts]


def live_topics(db: Session) -> list[LiveTopic]:
    """Topics students can open (lesson published), in curriculum order."""
    topics = visible_topics(db)
    published = published_by_topic(db, [t.id for t in topics])
    return [
        LiveTopic(t, published[t.id]) for t in topics if Component.LESSON in published.get(t.id, {})
    ]


def live_topic(db: Session, slug: str) -> LiveTopic:
    found = next((t for t in live_topics(db) if t.topic.slug == slug), None)
    if found is None:
        raise ProgressError(404, "Topic not found.")
    return found


# --- Events --------------------------------------------------------------------------------------


def _int(value: Any, upper: int = 500) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= upper:
        raise ProgressError(422, "Invalid progress details.")
    return value


def _clean(kind: LearningEventKind, data: dict[str, Any], live: LiveTopic) -> dict[str, Any]:
    """Only the fields each kind of event may carry, checked against the published content."""
    if kind is LearningEventKind.LESSON_PROGRESS:
        return {"seen": _int(data.get("seen")), "of": _int(data.get("of"))}
    if kind is LearningEventKind.PLAYGROUND_TASK:
        return {"task": _int(data.get("task")), "of": _int(data.get("of"))}
    if kind is LearningEventKind.VIDEO_PROGRESS:
        return {"scene": _int(data.get("scene")), "of": _int(data.get("of"))}
    if kind is LearningEventKind.CODE_RUN:
        return {"ok": data.get("ok") is True, "matched": data.get("matched") is True}
    if kind is LearningEventKind.INTERVIEW_TAKE:
        question = data.get("question")
        interview = live.parts.get(Component.INTERVIEW)
        asked = {q["question"] for q in interview.body["questions"]} if interview else set()
        if not isinstance(question, str) or question not in asked:
            raise ProgressError(422, "That question isn't in this topic.")
        return {"question": question}
    return {}


def _section_after(
    section: dict[str, Any],
    component: Component,
    kind: LearningEventKind,
    data: dict[str, Any],
    live: LiveTopic,
) -> dict[str, Any]:
    section = dict(section)
    done = section.get("status") == "done"
    if kind is LearningEventKind.SECTION_DONE:
        done = True
    elif kind is LearningEventKind.LESSON_PROGRESS:
        section["seen"] = max(section.get("seen", 0), data["seen"])
        cards = len(live.parts[Component.LESSON].body["cards"])
        done = done or section["seen"] >= cards
    elif kind is LearningEventKind.PLAYGROUND_TASK:
        tried = sorted(set(section.get("tasks", [])) | {data["task"]})
        section["tasks"] = tried
        done = done or len(tried) >= len(live.parts[Component.PLAYGROUND].body["tasks"])
    elif kind is LearningEventKind.VIDEO_PROGRESS:
        section["scene"] = max(section.get("scene", 0), data["scene"])
    elif kind is LearningEventKind.CODE_RUN:
        section["runs"] = section.get("runs", 0) + 1
        done = done or (data["ok"] and data["matched"])
    elif kind is LearningEventKind.INTERVIEW_TAKE:
        takes = sorted(set(section.get("takes", [])) | {data["question"]})
        section["takes"] = takes
        questions = len(live.parts[Component.INTERVIEW].body["questions"])
        done = done or len(takes) >= math.ceil(questions / 2)
    elif kind is LearningEventKind.SECTION_OPENED and component is Component.REVISION:
        done = True
    section["status"] = "done" if done else "started"
    section["updated_at"] = utcnow().isoformat()
    return section


def _progress_row(db: Session, student_id: uuid.UUID, topic_id: uuid.UUID) -> TopicProgress:
    """The row for this student and topic, created if needed and locked for the update."""
    db.execute(
        insert(TopicProgress)
        .values(student_id=student_id, topic_id=topic_id, sections={})
        .on_conflict_do_nothing()
    )
    row = db.scalars(
        select(TopicProgress)
        .where(TopicProgress.student_id == student_id, TopicProgress.topic_id == topic_id)
        .with_for_update()
    ).one()
    return row


def _advance(
    db: Session,
    student_id: uuid.UUID,
    live: LiveTopic,
    component: Component,
    kind: LearningEventKind,
    data: dict[str, Any],
) -> TopicProgress:
    row = _progress_row(db, student_id, live.topic.id)
    sections = dict(row.sections or {})
    sections[component.value] = _section_after(
        sections.get(component.value, {}), component, kind, data, live
    )
    row.sections = sections  # a new object, so the JSONB change is saved
    row.last_component = component.value
    row.last_visited_at = utcnow()
    if row.completed_at is None and all(
        sections.get(c.value, {}).get("status") == "done" for c in live.sections
    ):
        row.completed_at = utcnow()
    return row


def record_event(
    db: Session,
    student_id: uuid.UUID,
    *,
    slug: str,
    component: Component,
    kind: LearningEventKind,
    data: dict[str, Any],
) -> TopicProgress:
    if kind is LearningEventKind.ACTIVE_TIME:
        raise ProgressError(422, "Report learning time with record_time.")
    live = live_topic(db, slug)
    version = live.parts.get(component)
    if version is None:
        raise ProgressError(404, "That section isn't published.")
    clean = _clean(kind, data, live)
    db.add(
        LearningEvent(
            student_id=student_id,
            topic_id=live.topic.id,
            component=component,
            kind=kind,
            version_id=version.id,
            data=clean,
        )
    )
    row = _advance(db, student_id, live, component, kind, clean)
    db.commit()
    return row


def record_time(
    db: Session, student_id: uuid.UUID, *, slug: str, component: Component, seconds: int
) -> int:
    """Credit active time on a topic page; returns the seconds credited (possibly fewer)."""
    if not 1 <= seconds <= MAX_TIME_REPORT:
        raise ProgressError(422, "Invalid learning time.")
    live = live_topic(db, slug)
    version = live.parts.get(component)
    if version is None:
        raise ProgressError(404, "That section isn't published.")
    # One report at a time per student, so two tabs can't both claim the same minute.
    db.execute(select(func.pg_advisory_xact_lock(student_id.int & 0x7FFF_FFFF_FFFF_FFFF)))
    elapsed = db.scalar(
        select(func.extract("epoch", func.now() - func.max(LearningEvent.occurred_at))).where(
            LearningEvent.student_id == student_id,
            LearningEvent.kind == LearningEventKind.ACTIVE_TIME,
        )
    )
    credited = seconds if elapsed is None else min(seconds, max(0, int(elapsed) + TIME_SLACK))
    if credited == 0:
        db.rollback()
        return 0
    db.add(
        LearningEvent(
            student_id=student_id,
            topic_id=live.topic.id,
            component=component,
            kind=LearningEventKind.ACTIVE_TIME,
            version_id=version.id,
            data={"seconds": credited},
        )
    )
    row = _progress_row(db, student_id, live.topic.id)
    row.active_seconds += credited
    row.last_visited_at = utcnow()
    db.commit()
    return credited


# --- Quizzes --------------------------------------------------------------------------------------


def submit_quiz(
    db: Session,
    student_id: uuid.UUID,
    *,
    slug: str,
    version_id: uuid.UUID,
    answers: list[int | None],
    duration_seconds: int | None,
) -> QuizAttempt:
    """Grade a finished quiz against the published version and keep it as a new attempt."""
    live = live_topic(db, slug)
    quiz = live.parts.get(Component.QUIZ)
    if quiz is None:
        raise ProgressError(404, "This topic has no quiz.")
    if quiz.id != version_id:
        raise ProgressError(409, "This quiz was just updated. Reload the page and try again.")
    questions = quiz.body["questions"]
    if len(answers) != len(questions):
        raise ProgressError(422, "Answer every question before submitting.")
    responses = []
    for index, (question, chosen) in enumerate(zip(questions, answers, strict=True)):
        if chosen is not None and not 0 <= chosen < len(question["options"]):
            raise ProgressError(422, "Invalid answer.")
        responses.append(
            QuizResponse(
                question_index=index,
                chosen=chosen,
                correct=chosen == question["answer"],
                difficulty=question["difficulty"],
                kind=question["kind"],
            )
        )
    correct = sum(r.correct for r in responses)
    previous = db.scalar(
        select(func.count()).where(
            QuizAttempt.student_id == student_id, QuizAttempt.topic_id == live.topic.id
        )
    )
    attempt = QuizAttempt(
        student_id=student_id,
        topic_id=live.topic.id,
        version_id=quiz.id,
        attempt_number=(previous or 0) + 1,
        total=len(questions),
        correct=correct,
        score_pct=(Decimal(correct * 100) / len(questions)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        duration_seconds=duration_seconds,
    )
    db.add(attempt)
    db.flush()
    for response in responses:
        response.attempt_id = attempt.id
        db.add(response)
    _advance(db, student_id, live, Component.QUIZ, LearningEventKind.SECTION_DONE, {})
    db.commit()
    return attempt


# --- Mastery -------------------------------------------------------------------------------------


def band(score: float | None) -> str:
    if score is None:
        return "not_enough_evidence"
    return (
        "strong" if score >= STRONG_AT else "developing" if score >= DEVELOPING_AT else "needs_work"
    )


def mastery(quiz_scores: list[float], practice_scores: list[float]) -> dict[str, Any]:
    """Recent quiz percentages and interview-practice scores (out of 10), newest last."""
    quiz = quiz_scores[-RECENT_QUIZZES:]
    practice = [s * 10 for s in practice_scores[-RECENT_PRACTICE:]]
    quiz_avg = sum(quiz) / len(quiz) if quiz else None
    practice_avg = sum(practice) / len(practice) if practice else None
    if quiz_avg is not None and practice_avg is not None:
        score = QUIZ_WEIGHT * quiz_avg + (1 - QUIZ_WEIGHT) * practice_avg
    else:
        score = quiz_avg if quiz_avg is not None else practice_avg
    return {
        "score": round(score, 1) if score is not None else None,
        "band": band(score),
        "quiz_average": round(quiz_avg, 1) if quiz_avg is not None else None,
        "practice_average": round(practice_avg / 10, 1) if practice_avg is not None else None,
    }


# --- Summaries -----------------------------------------------------------------------------------


def _local_day(moment: datetime) -> date:
    return moment.astimezone(local_tz()).date()


def _streak(days: set[date], today: date) -> int:
    """Consecutive active days ending today (or yesterday, so a streak survives until tonight)."""
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def topic_sections(row: TopicProgress | None, live: LiveTopic) -> dict[str, str]:
    """Each published section: 'done', 'started' or 'not_started'."""
    sections = row.sections if row else {}
    return {c.value: sections.get(c.value, {}).get("status", "not_started") for c in live.sections}


def student_summary(db: Session, student_id: uuid.UUID) -> dict[str, Any]:
    """Everything a dashboard needs about one student, from their stored activity."""
    lives = live_topics(db)
    by_id = {live.topic.id: live for live in lives}
    rows = {
        r.topic_id: r
        for r in db.scalars(select(TopicProgress).where(TopicProgress.student_id == student_id))
    }
    attempts = db.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.submitted_at)
    ).all()
    quiz_by_topic: dict[uuid.UUID, list[QuizAttempt]] = defaultdict(list)
    for attempt in attempts:
        quiz_by_topic[attempt.topic_id].append(attempt)
    practice = db.execute(
        select(PracticeAttempt.topic_id, PracticeAttempt.score, PracticeAttempt.created_at)
        .where(
            PracticeAttempt.student_id == student_id,
            PracticeAttempt.status == AttemptStatus.COMPLETED,
            PracticeAttempt.deleted_at.is_(None),
        )
        .order_by(PracticeAttempt.created_at)
    ).all()
    practice_by_topic: dict[uuid.UUID, list[float]] = defaultdict(list)
    for topic_id, score, _ in practice:
        practice_by_topic[topic_id].append(float(score))

    topics = []
    for live in lives:
        row = rows.get(live.topic.id)
        sections = topic_sections(row, live)
        done = sum(status == "done" for status in sections.values())
        quizzes = quiz_by_topic.get(live.topic.id, [])
        takes = len((row.sections or {}).get("interview", {}).get("takes", [])) if row else 0
        topics.append(
            {
                "slug": live.topic.slug,
                "name": live.topic.name,
                "domain": live.topic.domain.name,
                "sections": sections,
                "done": done,
                "total": len(sections),
                "completion": round(done * 100 / len(sections)) if sections else 0,
                "completed": bool(row and row.completed_at),
                "started": row is not None,
                "last_visited_at": row.last_visited_at if row else None,
                "last_section": row.last_component if row else None,
                "quiz_attempts": len(quizzes),
                "quiz_best": float(max(q.score_pct for q in quizzes)) if quizzes else None,
                "quiz_last": float(quizzes[-1].score_pct) if quizzes else None,
                "interview_takes": takes,
                "active_seconds": row.active_seconds if row else 0,
                "mastery": mastery(
                    [float(q.score_pct) for q in quizzes], practice_by_topic.get(live.topic.id, [])
                ),
            }
        )

    domains: dict[str, dict[str, Any]] = {}
    for item in topics:
        domain = domains.setdefault(item["domain"], {"name": item["domain"], "done": 0, "total": 0})
        domain["done"] += item["done"]
        domain["total"] += item["total"]
    for domain in domains.values():
        domain["completion"] = (
            round(domain["done"] * 100 / domain["total"]) if domain["total"] else 0
        )

    done_all = sum(t["done"] for t in topics)
    total_all = sum(t["total"] for t in topics)
    in_progress = [t for t in topics if t["started"] and not t["completed"]]
    continue_with = max(in_progress, key=lambda t: t["last_visited_at"], default=None)
    if continue_with:
        pending = [s for s, status in continue_with["sections"].items() if status != "done"]
        continue_with = {**continue_with, "next_section": pending[0] if pending else None}

    recommended = []
    fresh = next((t for t in topics if not t["started"]), None)
    if fresh:
        recommended.append({**fresh, "reason": "Next in your path"})
    weakest = sorted(
        (t for t in topics if t["mastery"]["band"] in ("needs_work", "developing")),
        key=lambda t: t["mastery"]["score"],
    )
    if weakest:
        recommended.append({**weakest[0], "reason": "Boost a weak spot"})

    recent_events = db.execute(
        select(LearningEvent.occurred_at, LearningEvent.kind, LearningEvent.data).where(
            LearningEvent.student_id == student_id,
            LearningEvent.occurred_at >= utcnow() - timedelta(days=60),
        )
    ).all()
    active_days = {_local_day(moment) for moment, _, _ in recent_events}
    week_ago = utcnow() - timedelta(days=7)
    seconds_last_7 = sum(
        data.get("seconds", 0)
        for moment, kind, data in recent_events
        if kind is LearningEventKind.ACTIVE_TIME and moment >= week_ago
    )
    active_days |= {_local_day(a.submitted_at) for a in attempts}
    active_days |= {_local_day(moment) for _, _, moment in practice}
    today = _local_day(utcnow())
    week_start = today - timedelta(days=today.weekday())
    last_active = max(
        [
            *(r.last_visited_at for r in rows.values()),
            *(a.submitted_at for a in attempts),
            *(moment for _, _, moment in practice),
        ],
        default=None,
    )

    return {
        "overall_completion": round(done_all * 100 / total_all) if total_all else 0,
        "sections_done": done_all,
        "sections_total": total_all,
        "topics_completed": sum(t["completed"] for t in topics),
        "topics_started": sum(t["started"] for t in topics),
        "topics": topics,
        "domains": list(domains.values()),
        "continue": continue_with,
        "recommended": recommended,
        "recent_quizzes": [
            {
                "topic": by_id[a.topic_id].topic.name if a.topic_id in by_id else "Retired topic",
                "slug": by_id[a.topic_id].topic.slug if a.topic_id in by_id else None,
                "score_pct": float(a.score_pct),
                "correct": a.correct,
                "total": a.total,
                "attempt_number": a.attempt_number,
                "submitted_at": a.submitted_at,
            }
            for a in reversed(attempts[-5:])
        ],
        "quiz_average": round(sum(float(a.score_pct) for a in attempts) / len(attempts), 1)
        if attempts
        else None,
        "strengths": [t["name"] for t in topics if t["mastery"]["band"] == "strong"],
        "weaknesses": [t["name"] for t in topics if t["mastery"]["band"] == "needs_work"],
        "interview": {
            "answers_recorded": sum(t["interview_takes"] for t in topics),
            "feedback_count": len(practice),
            "average_score": round(sum(float(s) for _, s, _ in practice) / len(practice), 1)
            if practice
            else None,
            "recent_scores": [
                {"score": float(s), "at": moment} for _, s, moment in list(practice)[-8:]
            ],
        },
        "activity": {
            "streak_days": _streak(active_days, today),
            "active_days_this_week": sum(day >= week_start for day in active_days),
            "active_days_last_30": sum(day > today - timedelta(days=30) for day in active_days),
            "last_active_at": last_active,
            "learning_seconds": sum(r.active_seconds for r in rows.values()),
            "learning_seconds_last_7": seconds_last_7,
        },
    }


def topic_progress(db: Session, student_id: uuid.UUID, slug: str) -> dict[str, Any]:
    """One topic's sections, quiz attempts and recorded interview answers, for its page."""
    live = live_topic(db, slug)
    row = db.get(TopicProgress, (student_id, live.topic.id))
    attempts = db.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student_id, QuizAttempt.topic_id == live.topic.id)
        .order_by(QuizAttempt.submitted_at)
    ).all()
    practised = set(
        db.scalars(
            select(PracticeAttempt.question).where(
                PracticeAttempt.student_id == student_id,
                PracticeAttempt.topic_id == live.topic.id,
                PracticeAttempt.status != AttemptStatus.FAILED,
            )
        )
    )
    takes = set((row.sections or {}).get("interview", {}).get("takes", [])) if row else set()
    return {
        "sections": topic_sections(row, live),
        "last_section": row.last_component if row else None,
        "completed": bool(row and row.completed_at),
        "quiz": {
            "attempts": len(attempts),
            "best_pct": float(max(a.score_pct for a in attempts)) if attempts else None,
            "last_pct": float(attempts[-1].score_pct) if attempts else None,
        },
        "answered_questions": sorted(takes | practised),
    }
