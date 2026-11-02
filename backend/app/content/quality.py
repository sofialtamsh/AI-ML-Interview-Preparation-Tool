"""Automated quality checks for a content version: free, deterministic, and run in code.

Each check reports `passed`, `warning` or `error` with findings that say where. Errors block
publishing (a company name in student-facing text, a broken reference to an interview record,
unsafe or unparsable lab code, the wrong playground). Warnings are for the reviewer to judge.
The AI review (`app/content/review.py`) is separate, costs money and is only advisory.
"""

import ast
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.text import normalize
from app.content.schemas import PythonLab
from app.models import (
    Component,
    ContentItem,
    ContentVersion,
    InterviewExperience,
    InterviewQuestion,
    MediaAsset,
    ResearchQuestion,
    ReviewStatus,
    Topic,
)

Status = Literal["passed", "warning", "error"]

# Fields that hold labels or ids, not prose students read.
_NON_TEXT_KEYS = {
    "kind",
    "level",
    "difficulty",
    "origin",
    "source_ref",
    "widget",
    "figure",
    "packages",
    "emoji",
}
_LINK = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
DUPLICATE_RATIO = 0.85
# Comfortable narration pace is about 2.5 words a second. Scenes advance when the narration ends,
# so a scene's seconds only matter in captions-only mode: too few seconds and captions flash by.
FAST_WORDS_PER_SECOND = 3.3

ALLOWED_IMPORTS = {
    "numpy",
    "sklearn",
    "pandas",
    "math",
    "random",
    "statistics",
    "collections",
    "itertools",
    "functools",
    "operator",
    "typing",
    "dataclasses",
    "string",
    "re",
    "json",
    "heapq",
    "bisect",
    "copy",
    "fractions",
    "decimal",
    "warnings",
    "textwrap",
}
PACKAGE_OF = {"numpy": "numpy", "sklearn": "scikit-learn", "pandas": "pandas"}
BANNED_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint", "globals"}
# Dunder attributes are a classic sandbox escape (e.g. __subclasses__); these few are harmless.
SAFE_DUNDERS = {"__name__", "__init__", "__class__", "__doc__"}


def _is_risky_dunder(attr: str) -> bool:
    return attr.startswith("__") and attr.endswith("__") and attr not in SAFE_DUNDERS


LABELS = {
    "companies": "No company names",
    "links": "No links",
    "references": "Interview records still valid",
    "duplicates": "No duplicate questions",
    "difficulty": "Difficulty mix",
    "answer_key": "Answer key looks balanced",
    "timing": "Narration fits each scene",
    "narration": "Narration audio",
    "code_safety": "Lab code is safe to run",
    "determinism": "Lab output is repeatable",
    "code_check": "Code check passed",
    "widget": "Playground matches the topic",
}


@dataclass
class Check:
    key: str
    status: Status = "passed"
    findings: list[dict[str, str | None]] = field(default_factory=list)
    note: str | None = None

    def add(self, severity: Literal["warning", "error"], message: str, where: str | None = None):
        self.findings.append({"severity": severity, "message": message, "where": where})
        if severity == "error" or self.status == "passed":
            self.status = severity

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": LABELS[self.key],
            "status": self.status,
            "findings": self.findings,
            "note": self.note,
        }


def texts(body: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """Every piece of prose in a body, with a readable path like 'cards 3 · body'."""
    if isinstance(body, dict):
        for key, value in body.items():
            if key not in _NON_TEXT_KEYS:
                yield from texts(value, f"{path} · {key}" if path else key)
    elif isinstance(body, list):
        for index, value in enumerate(body):
            yield from texts(value, f"{path} {index + 1}")
    elif isinstance(body, str) and body.strip():
        yield path, body


def flat_text(body: Any) -> str:
    return "\n".join(text for _, text in texts(body))


class CheckContext:
    """Data many checks need, loaded once per request (a page can check dozens of versions)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._companies: set[str] | None = None
        self._published: dict[Component, list[tuple[uuid.UUID, str, list[str]]]] = {}

    def companies(self) -> set[str]:
        if self._companies is None:
            self._companies = {
                name.strip()
                for name in self.db.scalars(select(InterviewExperience.company).distinct())
                if name and len(name.strip()) >= 2
            }
        return self._companies

    def published_questions(self, component: Component) -> list[tuple[uuid.UUID, str, list[str]]]:
        """(topic id, topic name, normalised questions) of every published version."""
        if component not in self._published:
            rows = self.db.execute(
                select(Topic.id, Topic.name, ContentVersion.body)
                .join(ContentItem, ContentItem.published_version_id == ContentVersion.id)
                .join(Topic, ContentItem.topic_id == Topic.id)
                .where(ContentItem.component == component)
            ).all()
            self._published[component] = [
                (topic_id, name, [normalize(q) for q in _question_texts(component, body)])
                for topic_id, name, body in rows
            ]
        return self._published[component]


def _near_duplicate(a: str, b: str) -> bool:
    """Normalised texts at least DUPLICATE_RATIO alike. The cheap upper bounds rule out most
    pairs before the full comparison."""
    matcher = SequenceMatcher(None, a, b)
    return (
        matcher.real_quick_ratio() >= DUPLICATE_RATIO
        and matcher.quick_ratio() >= DUPLICATE_RATIO
        and matcher.ratio() >= DUPLICATE_RATIO
    )


# --- Checks for every component ----------------------------------------------------------------


def _companies(ctx: CheckContext, body: dict[str, Any]) -> Check:
    """Students must never see company names, so any name from interview records is an error."""
    check = Check("companies")
    names = ctx.companies()
    check.note = f"Compared with {len(names)} company name(s) from interview records."
    for path, text in texts(body):
        for name in names:
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text):
                check.add("error", f"Mentions the company “{name}”.", path)
    return check


def _links(body: dict[str, Any]) -> Check:
    check = Check("links")
    for path, text in texts(body):
        for link in _LINK.findall(text):
            check.add(
                "warning", f"Contains a link ({link[:80]}). Students shouldn't need links.", path
            )
    return check


# --- Questions ----------------------------------------------------------------------------------


def _question_texts(component: Component, body: dict[str, Any]) -> list[str]:
    key = "question" if component is Component.INTERVIEW else "prompt"
    return [q[key] for q in body.get("questions", [])]


def _duplicates(ctx: CheckContext, version: ContentVersion, body: dict[str, Any]) -> Check:
    check = Check("duplicates")
    component = version.item.component
    questions = [normalize(q) for q in _question_texts(component, body)]
    for i, first in enumerate(questions):
        for j in range(i + 1, len(questions)):
            if _near_duplicate(first, questions[j]):
                check.add("warning", f"Questions {i + 1} and {j + 1} are near-duplicates.")
    for topic_id, topic_name, others in ctx.published_questions(component):
        if topic_id == version.item.topic_id:
            continue
        for other in others:
            for i, question in enumerate(questions):
                if _near_duplicate(question, other):
                    check.add(
                        "warning", f"Question {i + 1} repeats a published question in {topic_name}."
                    )
    return check


def _difficulty(component: Component, body: dict[str, Any]) -> Check:
    check = Check("difficulty")
    key = "level" if component is Component.INTERVIEW else "difficulty"
    counts: dict[str, int] = {}
    for question in body.get("questions", []):
        counts[question[key]] = counts.get(question[key], 0) + 1
    check.note = ", ".join(f"{n} {level}" for level, n in counts.items())
    if len(counts) < 2:
        check.add("warning", "Every question has the same difficulty.")
    return check


def _references(db: Session, body: dict[str, Any]) -> Check:
    """Actual and research-derived questions must still point at an approved record, word for
    word, so provenance stays true."""
    check = Check("references")
    for index, item in enumerate(body.get("questions", []), start=1):
        if item["origin"] == "actual_interview":
            record = db.get(InterviewQuestion, _uuid(item.get("source_ref")))
            if (
                record is None
                or record.status is not ReviewStatus.APPROVED
                or record.duplicate_of_id is not None
            ):
                check.add(
                    "error",
                    "Says it was asked in real interviews, but its record is missing or no "
                    "longer approved.",
                    f"Question {index}",
                )
            elif normalize(record.original_text[:300]) != normalize(item["question"]):
                check.add(
                    "error",
                    "Its wording no longer matches the interview record.",
                    f"Question {index}",
                )
        elif item["origin"] == "research_derived":
            research = db.get(ResearchQuestion, _uuid(item.get("source_ref")))
            if research is None or research.status is not ReviewStatus.APPROVED:
                check.add(
                    "error",
                    "Its research-derived question is missing or no longer approved.",
                    f"Question {index}",
                )
    return check


def _uuid(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return uuid.UUID(int=0)  # matches no record


def _answer_key(body: dict[str, Any]) -> Check:
    check = Check("answer_key")
    answers = [q["answer"] for q in body.get("questions", [])]
    if len(answers) >= 5:
        most = max(set(answers), key=answers.count)
        share = answers.count(most) / len(answers)
        if share >= 0.7:
            check.add(
                "warning",
                f"{answers.count(most)} of {len(answers)} answers are option {chr(65 + most)}: "
                "students can guess the pattern.",
            )
    return check


# --- Video, Python, playground ------------------------------------------------------------------


def _timing(body: dict[str, Any]) -> Check:
    check = Check("timing")
    for index, scene in enumerate(body.get("scenes", []), start=1):
        words = len(scene["narration"].split())
        rate = words / scene["seconds"]
        if rate > FAST_WORDS_PER_SECOND:
            check.add(
                "warning",
                f"{words} words in {scene['seconds']} s is too fast to narrate; give it about "
                f"{round(words / 2.5)} s.",
                f"Scene {index}",
            )
    return check


def _narration(db: Session, version: ContentVersion, body: dict[str, Any]) -> Check:
    check = Check("narration")
    narrated = set(
        db.scalars(
            select(MediaAsset.position).where(
                MediaAsset.version_id == version.id, MediaAsset.kind == "narration"
            )
        )
    )
    scenes = len(body.get("scenes", []))
    missing = [i + 1 for i in range(scenes) if i not in narrated]
    if not narrated:
        check.note = "Not narrated: students get captions and their device's voice."
    elif missing:
        check.add("warning", f"Scenes {', '.join(map(str, missing))} have no narration audio.")
    return check


def _code_safety(body: dict[str, Any]) -> tuple[Check, Check]:
    safety, determinism = Check("code_safety"), Check("determinism")
    lab = PythonLab.model_validate(body)
    try:
        tree = ast.parse(lab.program)
    except SyntaxError as exc:
        safety.add("error", f"The code doesn't parse: {exc.msg} (line {exc.lineno}).")
        return safety, determinism

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) in BANNED_CALLS:
            name = getattr(node.func, "id", "")
            safety.add("error", f"Calls {name}(), which labs must not use.", f"line {node.lineno}")
        elif isinstance(node, ast.Attribute) and _is_risky_dunder(node.attr):
            safety.add(
                "error", f"Uses {node.attr}, which labs must not use.", f"line {node.lineno}"
            )
    for name in sorted(imported - ALLOWED_IMPORTS):
        safety.add("error", f"Imports {name}, which isn't allowed in labs.")
    for module, package in PACKAGE_OF.items():
        if module in imported and package not in lab.packages:
            safety.add("error", f"Imports {module} but packages doesn't list {package}.")

    code = lab.program
    if "random" in code and not any(m in code for m in ("seed(", "default_rng(", "random_state=")):
        determinism.add(
            "warning",
            "Uses randomness without a fixed seed, so the output may not match expected_output.",
        )
    return safety, determinism


def _code_check(db: Session, version: ContentVersion) -> Check:
    from app.content.service import has_passing_check

    check = Check("code_check")
    if not has_passing_check(db, version):
        check.add("warning", "Not run yet. A passing code check is needed before publishing.")
    return check


def _widget(version: ContentVersion, body: dict[str, Any]) -> Check:
    from app.content.generation import TOPIC_WIDGETS

    check = Check("widget")
    expected = TOPIC_WIDGETS.get(version.item.topic.slug)
    if expected is None:
        check.add("error", "This topic has no interactive playground.")
    elif body.get("widget") != expected:
        check.add(
            "error", f"Uses the {body.get('widget')} playground; this topic needs {expected}."
        )
    return check


# --- Entry points ------------------------------------------------------------------------------


def automated_checks(
    db: Session, version: ContentVersion, ctx: CheckContext | None = None
) -> list[Check]:
    ctx = ctx or CheckContext(db)
    body = version.body
    component = version.item.component
    checks = [_companies(ctx, body), _links(body)]
    if component is Component.INTERVIEW:
        checks += [
            _references(db, body),
            _duplicates(ctx, version, body),
            _difficulty(component, body),
        ]
    elif component is Component.QUIZ:
        checks += [_duplicates(ctx, version, body), _difficulty(component, body), _answer_key(body)]
    elif component is Component.VIDEO:
        checks += [_timing(body), _narration(db, version, body)]
    elif component is Component.PYTHON:
        checks += [*_code_safety(body), _code_check(db, version)]
    elif component is Component.PLAYGROUND:
        checks.append(_widget(version, body))
    return checks


def check_report(
    db: Session, version: ContentVersion, ctx: CheckContext | None = None
) -> dict[str, Any]:
    checks = automated_checks(db, version, ctx)
    return {
        "checks": [c.as_dict() for c in checks],
        "errors": sum(f["severity"] == "error" for c in checks for f in c.findings),
        "warnings": sum(f["severity"] == "warning" for c in checks for f in c.findings),
    }


def blocking_problems(db: Session, version: ContentVersion) -> list[str]:
    """Errors that stop a version from being published."""
    return [
        f"{f['where']}: {f['message']}" if f["where"] else str(f["message"])
        for check in automated_checks(db, version)
        for f in check.findings
        if f["severity"] == "error"
    ]
