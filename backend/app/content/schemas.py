"""The shape of every content component.

One contract serves four jobs: the JSON Schema the AI must fill (strict structured output), the
validation of drafts and edits, the admin preview, and what the student app renders. Length
limits are deliberate: lessons are short cards, not lectures.

Text fields allow a tiny markdown subset rendered safely by the app: **bold** and `code`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import Component


def text(max_length: int, min_length: int = 1) -> type[str]:
    return Annotated[  # type: ignore[return-value]
        str, StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)
    ]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Small animated illustrations the app can draw inside a lesson card or a video scene.
Figure = Literal[
    "labels_vs_no_labels",
    "train_test_split",
    "decision_boundary",
    "overfit_underfit",
    "clusters",
    "scatter_line",
    "residuals",
    "neuron",
    "network",
    "activation_curves",
    "loss_bowl",
    "learning_rate",
]
FIGURES: tuple[str, ...] = Figure.__args__  # type: ignore[attr-defined]

# Hands-on playgrounds, each a purpose-built interactive component in the app.
Widget = Literal[
    "knn_classifier",
    "kmeans",
    "linear_regression",
    "neural_network",
    "activation_functions",
    "gradient_descent",
]
WIDGETS: tuple[str, ...] = Widget.__args__  # type: ignore[attr-defined]


# --- Lesson -----------------------------------------------------------------------------------


class Symbol(Strict):
    symbol: text(20)
    meaning: text(120)


class LessonCard(Strict):
    kind: Literal[
        "hook",
        "tldr",
        "intuition",
        "analogy",
        "steps",
        "math",
        "example",
        "myth",
        "interview",
        "recap",
    ]
    title: text(70)
    body: text(320) = Field(description="Two or three short sentences at most")
    emoji: text(4) | None = None
    bullets: list[text(140)] = Field(default_factory=list, max_length=5)
    figure: Figure | None = None
    formula: text(120) | None = Field(default=None, description="For math cards, e.g. ŷ = w·x + b")
    symbols: list[Symbol] = Field(default_factory=list, max_length=6)
    myth: text(160) | None = None
    fact: text(220) | None = None

    @model_validator(mode="after")
    def _fields_fit_kind(self) -> "LessonCard":
        if self.kind == "math" and not self.formula:
            raise ValueError("math cards need a formula")
        if self.kind == "myth" and not (self.myth and self.fact):
            raise ValueError("myth cards need both a myth and a fact")
        return self


class KeyTerm(Strict):
    term: text(40)
    meaning: text(160)


class Lesson(Strict):
    tagline: text(110) = Field(description="One catchy line that sells the topic")
    minutes: int = Field(ge=3, le=20)
    level: Literal["beginner", "intermediate", "advanced"]
    cards: list[LessonCard] = Field(min_length=5, max_length=14)
    key_terms: list[KeyTerm] = Field(min_length=2, max_length=10)


# --- Playground --------------------------------------------------------------------------------


class PlaygroundTask(Strict):
    prompt: text(200) = Field(description="Something to try in the playground")
    hint: text(200)
    insight: text(260) = Field(description="What the student should notice")


class Playground(Strict):
    widget: Widget
    title: text(70)
    intro: text(260)
    tasks: list[PlaygroundTask] = Field(min_length=2, max_length=6)


# --- Python lab ------------------------------------------------------------------------------


Package = Literal["numpy", "scikit-learn", "pandas"]


class CodeStep(Strict):
    title: text(70)
    explanation: text(320)
    code: text(3000)


class PythonLab(Strict):
    packages: list[Package] = Field(max_length=3)
    dataset: text(300) = Field(description="What data the code uses")
    steps: list[CodeStep] = Field(min_length=2, max_length=8)
    expected_output: text(2000) = Field(
        description="Exactly what the whole program prints (deterministic: fixed seeds, rounding)"
    )
    mistakes: list[text(200)] = Field(min_length=2, max_length=6)
    applications: list[text(160)] = Field(min_length=2, max_length=5)

    @property
    def program(self) -> str:
        """All steps in order: they run in one shared namespace."""
        return "\n\n".join(step.code for step in self.steps)


# --- Interview prep ------------------------------------------------------------------------------


class FollowUp(Strict):
    question: text(240)
    answer: text(700)


class InterviewItem(Strict):
    level: Literal["basic", "intermediate", "advanced"]
    kind: Literal["conceptual", "math", "coding", "scenario", "practical"]
    question: text(300)
    answer: text(1400)
    interviewer_wants: text(400) = Field(description="What a good answer must show")
    follow_ups: list[FollowUp] = Field(default_factory=list, max_length=3)
    # actual_interview items carry the id of an approved interview question; never a company.
    origin: Literal["ai_generated", "admin_created", "actual_interview", "research_derived"]
    source_ref: text(64) | None = None
    # For actual interview questions: role and round only (never the company).
    asked_for_role: text(120) | None = None

    @model_validator(mode="after")
    def _provenance(self) -> "InterviewItem":
        needs_ref = self.origin in ("actual_interview", "research_derived")
        if needs_ref != bool(self.source_ref):
            raise ValueError("actual and research-derived questions must reference their source")
        return self


class InterviewPrep(Strict):
    questions: list[InterviewItem] = Field(min_length=4, max_length=15)
    takeaways: list[text(200)] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def _all_levels(self) -> "InterviewPrep":
        if {q.level for q in self.questions} != {"basic", "intermediate", "advanced"}:
            raise ValueError("include basic, intermediate and advanced questions")
        return self


# --- Quiz --------------------------------------------------------------------------------------


class QuizQuestion(Strict):
    difficulty: Literal["easy", "medium", "hard"]
    kind: Literal["concept", "scenario", "code", "math"]
    prompt: text(300)
    code: text(800) | None = None
    options: list[text(200)] = Field(min_length=2, max_length=5)
    answer: int = Field(ge=0, description="Index of the correct option")
    explanation: text(500)

    @model_validator(mode="after")
    def _answer_exists(self) -> "QuizQuestion":
        if self.answer >= len(self.options):
            raise ValueError("answer must be the index of one of the options")
        if len({o.lower() for o in self.options}) != len(self.options):
            raise ValueError("options must be different")
        return self


class Quiz(Strict):
    questions: list[QuizQuestion] = Field(min_length=5, max_length=12)


# --- Revision ------------------------------------------------------------------------------------


class Definition(Strict):
    term: text(60)
    meaning: text(220)


class Formula(Strict):
    name: text(60)
    expression: text(140)
    meaning: text(220)


class Comparison(Strict):
    title: text(80)
    columns: list[text(40, min_length=0)] = Field(min_length=2, max_length=4)  # corner may be blank
    rows: list[list[text(120, min_length=0)]] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def _rectangular(self) -> "Comparison":
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("every comparison row needs one cell per column")
        return self


class Confusion(Strict):
    pair: text(80)
    difference: text(240)


class Revision(Strict):
    definitions: list[Definition] = Field(min_length=3, max_length=10)
    formulas: list[Formula] = Field(default_factory=list, max_length=6)
    comparison: Comparison | None = None
    mistakes: list[text(200)] = Field(min_length=2, max_length=6)
    confusions: list[Confusion] = Field(default_factory=list, max_length=4)
    takeaways: list[text(200)] = Field(min_length=3, max_length=6)


# --- Video ---------------------------------------------------------------------------------------


class Scene(Strict):
    title: text(70)
    narration: text(650) = Field(description="Spoken text, about 20-45 seconds")
    on_screen: text(120) = Field(description="Big caption shown on screen")
    figure: Figure | None = None
    seconds: int = Field(ge=8, le=60)


class VideoScript(Strict):
    title: text(90)
    scenes: list[Scene] = Field(min_length=4, max_length=10)

    @model_validator(mode="after")
    def _length(self) -> "VideoScript":
        total = sum(scene.seconds for scene in self.scenes)
        if not 120 <= total <= 300:
            raise ValueError(f"the video should run 2-5 minutes; these scenes total {total}s")
        return self


SCHEMAS: dict[Component, type[Strict]] = {
    Component.LESSON: Lesson,
    Component.PLAYGROUND: Playground,
    Component.PYTHON: PythonLab,
    Component.INTERVIEW: InterviewPrep,
    Component.QUIZ: Quiz,
    Component.REVISION: Revision,
    Component.VIDEO: VideoScript,
}

# The order students meet the components in.
COMPONENT_ORDER = [
    Component.LESSON,
    Component.PLAYGROUND,
    Component.VIDEO,
    Component.PYTHON,
    Component.INTERVIEW,
    Component.QUIZ,
    Component.REVISION,
]
