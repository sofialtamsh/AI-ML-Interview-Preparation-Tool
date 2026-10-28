"""What students receive. Built only from *published* versions, and shaped here explicitly so
internal fields (source references, review notes, models) can never leak to the student app."""

import uuid
from typing import Any, Literal

from app.schemas.common import ApiModel


class LearnTopicCard(ApiModel):
    slug: str
    name: str
    tagline: str
    minutes: int
    level: str
    sections: list[str]


class LearnDomain(ApiModel):
    slug: str
    name: str
    topics: list[LearnTopicCard]


class StudentInterviewItem(ApiModel):
    level: str
    kind: str
    question: str
    answer: str
    interviewer_wants: str
    follow_ups: list[dict[str, str]]
    # What the student sees about where a question comes from. Never a company or a source.
    label: Literal["Practice question", "Asked in real interviews", "In demand right now"]
    asked_for_role: str | None


class StudentInterview(ApiModel):
    questions: list[StudentInterviewItem]
    takeaways: list[str]


class StudentScene(ApiModel):
    title: str
    narration: str
    on_screen: str
    figure: str | None
    seconds: int
    audio_id: uuid.UUID | None


class StudentVideo(ApiModel):
    title: str
    scenes: list[StudentScene]


class LearnTopic(ApiModel):
    slug: str
    name: str
    domain: dict[str, str]
    tagline: str
    minutes: int
    level: str
    lesson: dict[str, Any]
    playground: dict[str, Any] | None
    video: StudentVideo | None
    python: dict[str, Any] | None
    interview: StudentInterview | None
    quiz: dict[str, Any] | None
    revision: dict[str, Any] | None


LABELS = {
    "ai_generated": "Practice question",
    "admin_created": "Practice question",
    "actual_interview": "Asked in real interviews",
    "research_derived": "In demand right now",
}


def student_interview(body: dict[str, Any]) -> StudentInterview:
    return StudentInterview(
        questions=[
            StudentInterviewItem(
                level=q["level"],
                kind=q["kind"],
                question=q["question"],
                answer=q["answer"],
                interviewer_wants=q["interviewer_wants"],
                follow_ups=[
                    {"question": f["question"], "answer": f["answer"]} for f in q["follow_ups"]
                ],
                label=LABELS[q["origin"]],  # type: ignore[arg-type]
                asked_for_role=q.get("asked_for_role")
                if q["origin"] == "actual_interview"
                else None,
            )
            for q in body["questions"]
        ],
        takeaways=body["takeaways"],
    )
