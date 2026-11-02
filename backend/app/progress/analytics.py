"""Admin views of learning: per-student stats for the directory, one student's learning detail,
platform analytics, and the CSV export. Computed with SQL aggregates, so the directory stays fast.

Attention flags:
- inactive: no learning activity for INACTIVE_DAYS (or none since registering, once a week old);
- struggling: a quiz average under 50 % over at least two attempts, or an interview-practice
  average under 4/10 over at least two answers.
"""

import csv
import io
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Select, and_, distinct, func, or_, select, union_all
from sqlalchemy.orm import Session

from app.content.schemas import COMPONENT_ORDER
from app.core.security import utcnow
from app.models import (
    AttemptStatus,
    Cohort,
    ContentVersion,
    Domain,
    LearningEvent,
    LearningEventKind,
    PracticeAttempt,
    QuizAttempt,
    QuizResponse,
    Student,
    StudentStatus,
    Topic,
    TopicProgress,
)
from app.progress.service import live_topics, local_tz, student_summary

INACTIVE_DAYS = 14
STRUGGLING_QUIZ = 50
STRUGGLING_PRACTICE = 4


# --- Per-student aggregates ----------------------------------------------------------------------


def _activity_union() -> Any:
    """(student_id, moment) for every kind of learning activity."""
    return union_all(
        select(TopicProgress.student_id, TopicProgress.last_visited_at.label("at")),
        select(QuizAttempt.student_id, QuizAttempt.submitted_at.label("at")),
        select(PracticeAttempt.student_id, PracticeAttempt.created_at.label("at")),
    ).subquery()


def _last_active() -> Any:
    activity = _activity_union()
    return (
        select(activity.c.student_id, func.max(activity.c.at).label("last_active"))
        .group_by(activity.c.student_id)
        .subquery()
    )


def _quiz_stats() -> Any:
    return (
        select(
            QuizAttempt.student_id,
            func.count().label("quiz_attempts"),
            func.avg(QuizAttempt.score_pct).label("quiz_average"),
        )
        .group_by(QuizAttempt.student_id)
        .subquery()
    )


def _practice_stats() -> Any:
    return (
        select(
            PracticeAttempt.student_id,
            func.count().label("practice_count"),
            func.avg(PracticeAttempt.score).label("practice_average"),
        )
        .where(
            PracticeAttempt.status == AttemptStatus.COMPLETED,
            PracticeAttempt.deleted_at.is_(None),
        )
        .group_by(PracticeAttempt.student_id)
        .subquery()
    )


def _completed_stats() -> Any:
    return (
        select(
            TopicProgress.student_id,
            func.count().label("topics_started"),
            func.count(TopicProgress.completed_at).label("topics_completed"),
            func.sum(TopicProgress.active_seconds).label("learning_seconds"),
        )
        .group_by(TopicProgress.student_id)
        .subquery()
    )


def with_learning(query: Select[Any]) -> tuple[Select[Any], dict[str, Any]]:
    """Join a Student query with learning aggregates; returns the query and its columns."""
    last, quiz, practice, done = (
        _last_active(),
        _quiz_stats(),
        _practice_stats(),
        _completed_stats(),
    )
    query = (
        query.outerjoin(last, last.c.student_id == Student.id)
        .outerjoin(quiz, quiz.c.student_id == Student.id)
        .outerjoin(practice, practice.c.student_id == Student.id)
        .outerjoin(done, done.c.student_id == Student.id)
    )
    return query, {"last": last, "quiz": quiz, "practice": practice, "done": done}


def attention_conditions(cols: dict[str, Any], kind: str) -> list[Any]:
    now = utcnow()
    inactive = or_(
        cols["last"].c.last_active < now - timedelta(days=INACTIVE_DAYS),
        and_(
            cols["last"].c.last_active.is_(None),
            Student.created_at < now - timedelta(days=7),
        ),
    )
    struggling = or_(
        and_(cols["quiz"].c.quiz_attempts >= 2, cols["quiz"].c.quiz_average < STRUGGLING_QUIZ),
        and_(
            cols["practice"].c.practice_count >= 2,
            cols["practice"].c.practice_average < STRUGGLING_PRACTICE,
        ),
    )
    return {"inactive": [inactive], "struggling": [struggling], "any": [or_(inactive, struggling)]}[
        kind
    ]


def flags(row: dict[str, Any], created_at: datetime) -> list[str]:
    now = utcnow()
    found = []
    last = row.get("last_active")
    if (last and last < now - timedelta(days=INACTIVE_DAYS)) or (
        last is None and created_at < now - timedelta(days=7)
    ):
        found.append("inactive")
    quiz_struggle = (row.get("quiz_attempts") or 0) >= 2 and float(
        row.get("quiz_average") or 0
    ) < STRUGGLING_QUIZ
    practice_struggle = (row.get("practice_count") or 0) >= 2 and float(
        row.get("practice_average") or 0
    ) < STRUGGLING_PRACTICE
    if quiz_struggle or practice_struggle:
        found.append("struggling")
    return found


def learning_columns(cols: dict[str, Any]) -> list[Any]:
    return [
        cols["last"].c.last_active,
        cols["quiz"].c.quiz_attempts,
        cols["quiz"].c.quiz_average,
        cols["practice"].c.practice_count,
        cols["practice"].c.practice_average,
        cols["done"].c.topics_started,
        cols["done"].c.topics_completed,
        cols["done"].c.learning_seconds,
    ]


def learning_snapshot(row: Any, created_at: datetime) -> dict[str, Any]:
    values = {
        "last_active": row.last_active,
        "quiz_attempts": row.quiz_attempts or 0,
        "quiz_average": round(float(row.quiz_average), 1) if row.quiz_average is not None else None,
        "practice_count": row.practice_count or 0,
        "practice_average": round(float(row.practice_average), 1)
        if row.practice_average is not None
        else None,
        "topics_started": row.topics_started or 0,
        "topics_completed": row.topics_completed or 0,
    }
    return {
        "last_active_at": values["last_active"],
        "topics_started": values["topics_started"],
        "topics_completed": values["topics_completed"],
        "learning_seconds": int(row.learning_seconds or 0),
        "quiz_attempts": values["quiz_attempts"],
        "quiz_average": values["quiz_average"],
        "practice_answers": values["practice_count"],
        "practice_average": values["practice_average"],
        "flags": flags(values, created_at),
    }


# --- One student ---------------------------------------------------------------------------------


EVENT_LABELS = {
    "section_opened": "Opened",
    "section_done": "Finished",
    "lesson_progress": "Went through cards in",
    "playground_task": "Tried a task in",
    "video_progress": "Watched",
    "code_run": "Ran the code in",
    "interview_take": "Recorded an answer in",
}


def student_learning(db: Session, student_id: uuid.UUID) -> dict[str, Any]:
    """Learning history for the admin's student profile. Never transcripts or recordings."""
    attempts = db.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.submitted_at.desc())
    ).all()
    responses: dict[uuid.UUID, list[QuizResponse]] = {}
    if attempts:
        for response in db.scalars(
            select(QuizResponse)
            .where(QuizResponse.attempt_id.in_([a.id for a in attempts]))
            .order_by(QuizResponse.question_index)
        ):
            responses.setdefault(response.attempt_id, []).append(response)
    versions = {
        v.id: v
        for v in db.scalars(
            select(ContentVersion).where(
                ContentVersion.id.in_({a.version_id for a in attempts} or {uuid.UUID(int=0)})
            )
        ).unique()
    }
    topics = {t.id: t for t in db.scalars(select(Topic)).unique()}
    events = db.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.student_id == student_id,
            LearningEvent.kind != LearningEventKind.ACTIVE_TIME,
        )
        .order_by(LearningEvent.occurred_at.desc())
        .limit(40)
    ).all()
    practice = db.scalars(
        select(PracticeAttempt)
        .where(
            PracticeAttempt.student_id == student_id,
            PracticeAttempt.status.in_([AttemptStatus.COMPLETED, AttemptStatus.NO_ANSWER]),
        )
        .order_by(PracticeAttempt.created_at.desc())
        .limit(50)
    ).all()

    def prompt(attempt: QuizAttempt, index: int) -> str:
        version = versions.get(attempt.version_id)
        questions = version.body["questions"] if version else []
        return questions[index]["prompt"] if index < len(questions) else ""

    return {
        "summary": student_summary(db, student_id),
        "quiz_attempts": [
            {
                "id": a.id,
                "topic": topics[a.topic_id].name if a.topic_id in topics else "Unknown topic",
                "topic_slug": topics[a.topic_id].slug if a.topic_id in topics else None,
                "attempt_number": a.attempt_number,
                "correct": a.correct,
                "total": a.total,
                "score_pct": float(a.score_pct),
                "duration_seconds": a.duration_seconds,
                "submitted_at": a.submitted_at,
                "responses": [
                    {
                        "question_index": r.question_index,
                        "prompt": prompt(a, r.question_index),
                        "chosen": r.chosen,
                        "correct": r.correct,
                        "difficulty": r.difficulty,
                    }
                    for r in responses.get(a.id, [])
                ],
            }
            for a in attempts
        ],
        "practice": [
            {
                "topic": topics[p.topic_id].name if p.topic_id in topics else "Unknown topic",
                "question": p.question,
                "score": float(p.score) if p.score is not None else None,
                "verdict": (p.feedback or {}).get("verdict", {}).get("label"),
                "deleted": p.deleted_at is not None,
                "created_at": p.created_at,
            }
            for p in practice
        ],
        "timeline": [
            {
                "at": e.occurred_at,
                "topic": topics[e.topic_id].name if e.topic_id in topics else "Unknown topic",
                "section": e.component.value,
                "action": EVENT_LABELS[e.kind.value],
            }
            for e in events
        ],
    }


# --- Platform analytics --------------------------------------------------------------------------


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = local_tz()
    return datetime.combine(start, time.min, tz), datetime.combine(
        end + timedelta(days=1), time.min, tz
    )


def _daily(start: date, end: date, counts: dict[date, int]) -> list[dict[str, Any]]:
    days = (end - start).days + 1
    return [
        {"day": start + timedelta(days=i), "count": counts.get(start + timedelta(days=i), 0)}
        for i in range(days)
    ]


def _weekly(start: date, end: date, counts: dict[date, int]) -> list[dict[str, Any]]:
    """Monday-start weeks covering the range (Postgres date_trunc('week') starts on Monday)."""
    week = start - timedelta(days=start.weekday())
    rows = []
    while week <= end:
        rows.append({"week": week, "count": counts.get(week, 0)})
        week += timedelta(days=7)
    return rows


def analytics_report(
    db: Session,
    *,
    start: date,
    end: date,
    cohort_id: uuid.UUID | None = None,
    domain: str | None = None,
    topic: str | None = None,
    student: Student | None = None,
) -> dict[str, Any]:
    """Everything is limited to the filters; with a student, to that one student (even if
    deactivated, since an admin picked them)."""
    lo, hi = _bounds(start, end)
    tz_name = str(local_tz())
    if student:
        students = select(Student.id).where(Student.id == student.id)
    else:
        students = select(Student.id).where(Student.status != StudentStatus.DEACTIVATED)
    if cohort_id:
        students = students.where(Student.cohort_id == cohort_id)
    student_ids = students.scalar_subquery()

    lives = live_topics(db)
    scoped = [
        live
        for live in lives
        if (not domain or live.topic.domain.slug == domain)
        and (not topic or live.topic.slug == topic)
    ]
    topic_ids = [live.topic.id for live in scoped] or [uuid.UUID(int=0)]

    in_scope = Student.id.in_(student_ids)
    total = db.scalar(select(func.count()).where(in_scope)) or 0
    new = (
        db.scalar(
            select(func.count()).where(in_scope, Student.created_at >= lo, Student.created_at < hi)
        )
        or 0
    )

    activity = _activity_union()
    active_ids = (
        select(activity.c.student_id)
        .where(activity.c.at >= lo, activity.c.at < hi, activity.c.student_id.in_(student_ids))
        .distinct()
    )
    active = db.scalar(select(func.count()).select_from(active_ids.subquery())) or 0

    registrations = db.execute(
        select(func.date(func.timezone(tz_name, Student.created_at)).label("day"), func.count())
        .where(in_scope, Student.created_at >= lo, Student.created_at < hi)
        .group_by("day")
        .order_by("day")
    ).all()

    week = func.date_trunc("week", func.timezone(tz_name, activity.c.at))
    weekly_active = db.execute(
        select(week.label("week"), func.count(distinct(activity.c.student_id)))
        .where(activity.c.at >= lo, activity.c.at < hi, activity.c.student_id.in_(student_ids))
        .group_by("week")
        .order_by("week")
    ).all()

    quiz_scope = [
        QuizAttempt.submitted_at >= lo,
        QuizAttempt.submitted_at < hi,
        QuizAttempt.student_id.in_(student_ids),
        QuizAttempt.topic_id.in_(topic_ids),
    ]
    quiz_count, quiz_avg = db.execute(
        select(func.count(), func.avg(QuizAttempt.score_pct)).where(*quiz_scope)
    ).one()
    bucket = func.least(func.floor(QuizAttempt.score_pct / 10), 9)
    distribution = dict(
        db.execute(select(bucket, func.count()).where(*quiz_scope).group_by(bucket)).all()
    )

    practice_scope = [
        PracticeAttempt.created_at >= lo,
        PracticeAttempt.created_at < hi,
        PracticeAttempt.student_id.in_(student_ids),
        PracticeAttempt.topic_id.in_(topic_ids),
        PracticeAttempt.status == AttemptStatus.COMPLETED,
    ]
    practice_count, practice_avg = db.execute(
        select(func.count(), func.avg(PracticeAttempt.score)).where(*practice_scope)
    ).one()

    seconds = LearningEvent.data["seconds"].as_integer()
    time_scope = [
        LearningEvent.kind == LearningEventKind.ACTIVE_TIME,
        LearningEvent.occurred_at >= lo,
        LearningEvent.occurred_at < hi,
        LearningEvent.student_id.in_(student_ids),
        LearningEvent.topic_id.in_(topic_ids),
    ]
    time_by_topic = dict(
        db.execute(
            select(LearningEvent.topic_id, func.sum(seconds))
            .where(*time_scope)
            .group_by(LearningEvent.topic_id)
        ).all()
    )
    learners = (
        db.scalar(select(func.count(distinct(LearningEvent.student_id))).where(*time_scope)) or 0
    )
    learning_seconds = int(sum(time_by_topic.values()))

    # Path completion: each student's done sections out of every live section in scope, averaged
    # over all students in scope (those who haven't started count as 0 %).
    live_sections = {live.topic.id: {c.value for c in live.sections} for live in scoped}
    done_sections = 0
    for topic_id, sections in db.execute(
        select(TopicProgress.topic_id, TopicProgress.sections).where(
            TopicProgress.student_id.in_(student_ids), TopicProgress.topic_id.in_(topic_ids)
        )
    ):
        done_sections += sum(
            (sections or {}).get(key, {}).get("status") == "done"
            for key in live_sections.get(topic_id, ())
        )
    all_sections = sum(len(keys) for keys in live_sections.values())

    started = dict(
        db.execute(
            select(TopicProgress.topic_id, func.count())
            .where(TopicProgress.student_id.in_(student_ids), TopicProgress.topic_id.in_(topic_ids))
            .group_by(TopicProgress.topic_id)
        ).all()
    )
    completed = dict(
        db.execute(
            select(TopicProgress.topic_id, func.count())
            .where(
                TopicProgress.student_id.in_(student_ids),
                TopicProgress.topic_id.in_(topic_ids),
                TopicProgress.completed_at.is_not(None),
            )
            .group_by(TopicProgress.topic_id)
        ).all()
    )
    quiz_by_topic = {
        topic_id: (count, avg)
        for topic_id, count, avg in db.execute(
            select(QuizAttempt.topic_id, func.count(), func.avg(QuizAttempt.score_pct))
            .where(*quiz_scope)
            .group_by(QuizAttempt.topic_id)
        )
    }
    practice_by_topic = {
        topic_id: (count, avg)
        for topic_id, count, avg in db.execute(
            select(PracticeAttempt.topic_id, func.count(), func.avg(PracticeAttempt.score))
            .where(*practice_scope)
            .group_by(PracticeAttempt.topic_id)
        )
    }
    topics = []
    for live in scoped:
        tid = live.topic.id
        quiz_n, quiz_mean = quiz_by_topic.get(tid, (0, None))
        practice_n, practice_mean = practice_by_topic.get(tid, (0, None))
        topics.append(
            {
                "slug": live.topic.slug,
                "name": live.topic.name,
                "domain": live.topic.domain.name,
                "started": started.get(tid, 0),
                "completed": completed.get(tid, 0),
                "completion_rate": round(completed.get(tid, 0) * 100 / started[tid])
                if started.get(tid)
                else None,
                "quiz_attempts": quiz_n,
                "quiz_average": round(float(quiz_mean), 1) if quiz_mean is not None else None,
                "practice_answers": practice_n,
                "practice_average": round(float(practice_mean), 1)
                if practice_mean is not None
                else None,
                "learning_seconds": int(time_by_topic.get(tid, 0)),
            }
        )

    domains: dict[str, dict[str, Any]] = {}
    for item in topics:
        entry = domains.setdefault(
            item["domain"],
            {"name": item["domain"], "started": 0, "completed": 0, "quiz_scores": []},
        )
        entry["started"] += item["started"]
        entry["completed"] += item["completed"]
        if item["quiz_average"] is not None:
            entry["quiz_scores"].append((item["quiz_average"], item["quiz_attempts"]))
    domain_rows = []
    for entry in domains.values():
        weight = sum(n for _, n in entry["quiz_scores"])
        domain_rows.append(
            {
                "name": entry["name"],
                "started": entry["started"],
                "completed": entry["completed"],
                "completion_rate": round(entry["completed"] * 100 / entry["started"])
                if entry["started"]
                else None,
                "quiz_average": round(sum(a * n for a, n in entry["quiz_scores"]) / weight, 1)
                if weight
                else None,
            }
        )

    weak = sorted(
        (t for t in topics if t["quiz_attempts"] >= 3 and t["quiz_average"] is not None),
        key=lambda t: t["quiz_average"],
    )[:5]

    cohort_rows = []
    cohort_query = select(Cohort).order_by(Cohort.name)
    if cohort_id:
        cohort_query = cohort_query.where(Cohort.id == cohort_id)
    # A single student isn't compared with whole cohorts here; their profile has the detail.
    for cohort in [] if student else db.scalars(cohort_query):
        members = select(Student.id).where(Student.cohort_id == cohort.id).scalar_subquery()
        size = db.scalar(select(func.count()).where(Student.cohort_id == cohort.id)) or 0
        cohort_active = (
            db.scalar(
                select(func.count()).select_from(
                    select(activity.c.student_id)
                    .where(
                        activity.c.at >= lo, activity.c.at < hi, activity.c.student_id.in_(members)
                    )
                    .distinct()
                    .subquery()
                )
            )
            or 0
        )
        cohort_quiz = db.scalar(
            select(func.avg(QuizAttempt.score_pct)).where(
                QuizAttempt.student_id.in_(members),
                QuizAttempt.submitted_at >= lo,
                QuizAttempt.submitted_at < hi,
            )
        )
        cohort_rows.append(
            {
                "name": cohort.name,
                "students": size,
                "active": cohort_active,
                "quiz_average": round(float(cohort_quiz), 1) if cohort_quiz is not None else None,
            }
        )

    base, cols = with_learning(select(Student.id).where(in_scope))
    attention = (
        db.scalar(
            select(func.count()).select_from(
                base.where(*attention_conditions(cols, "any")).subquery()
            )
        )
        or 0
    )

    sections_per_topic = {
        live.topic.id: len([c for c in COMPONENT_ORDER if c in live.parts]) for live in scoped
    }
    return {
        "range": {"start": start, "end": end},
        "kpis": {
            "students": total,
            "new_students": new,
            "active_students": active,
            "quiz_attempts": quiz_count,
            "quiz_average": round(float(quiz_avg), 1) if quiz_avg is not None else None,
            "practice_answers": practice_count,
            "practice_average": round(float(practice_avg), 1) if practice_avg is not None else None,
            "needing_attention": attention,
            "published_topics": len(scoped),
            "published_sections": sum(sections_per_topic.values()),
            "average_completion": round(done_sections * 100 / (all_sections * total))
            if all_sections and total
            else None,
            "learning_seconds": learning_seconds,
            "learning_seconds_per_learner": round(learning_seconds / learners)
            if learners
            else None,
        },
        # Every day and week in the range, zeros included, so the timeline isn't misleading.
        "registrations": _daily(start, end, dict(registrations)),
        "weekly_active": _weekly(start, end, {w.date(): count for w, count in weekly_active}),
        "score_distribution": [
            {
                "from": b * 10,
                "to": b * 10 + 9 if b < 9 else 100,
                "count": int(distribution.get(b, 0)),
            }
            for b in range(10)
        ],
        "topics": topics,
        "domains": domain_rows,
        "weak_topics": weak,
        "cohorts": cohort_rows,
        "student": {
            "id": str(student.id),
            "full_name": student.full_name,
            "student_code": student.student_code,
        }
        if student
        else None,
        "filters": {
            "domains": [
                {"slug": d.slug, "name": d.name}
                for d in db.scalars(
                    select(Domain)
                    .where(
                        Domain.id.in_(
                            {live.topic.domain_id for live in lives} or {uuid.UUID(int=0)}
                        )
                    )
                    .order_by(Domain.position)
                )
            ],
            "topics": [{"slug": live.topic.slug, "name": live.topic.name} for live in lives],
            "cohorts": [
                {"id": str(c.id), "name": c.name}
                for c in db.scalars(select(Cohort).order_by(Cohort.name))
            ],
        },
    }


# --- Export --------------------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """A CSV cell that spreadsheet apps won't run as a formula."""
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def students_csv(db: Session, cohort_id: uuid.UUID | None = None) -> str:
    base = select(Student)
    if cohort_id:
        base = base.where(Student.cohort_id == cohort_id)
    query, cols = with_learning(base)
    rows = db.execute(
        query.add_columns(*learning_columns(cols)).order_by(Student.student_number)
    ).unique()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "Student ID",
            "Name",
            "Email",
            "Cohort",
            "Status",
            "Registered",
            "Last login",
            "Last learning activity",
            "Topics started",
            "Topics completed",
            "Learning time (min)",
            "Quiz attempts",
            "Quiz average %",
            "Practice answers scored",
            "Practice average /10",
            "Flags",
        ]
    )
    for row in rows:
        student: Student = row[0]
        learning = learning_snapshot(row, student.created_at)
        writer.writerow(
            [
                _cell(v)
                for v in (
                    student.student_code,
                    student.full_name,
                    student.email,
                    student.cohort.name if student.cohort else "",
                    student.status.value,
                    student.created_at.date().isoformat(),
                    student.last_login_at.isoformat() if student.last_login_at else "",
                    learning["last_active_at"].isoformat() if learning["last_active_at"] else "",
                    learning["topics_started"],
                    learning["topics_completed"],
                    round(learning["learning_seconds"] / 60),
                    learning["quiz_attempts"],
                    learning["quiz_average"],
                    learning["practice_answers"],
                    learning["practice_average"],
                    " ".join(learning["flags"]),
                )
            ]
        )
    return out.getvalue()
