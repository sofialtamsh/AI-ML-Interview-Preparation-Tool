"""Delivery numbers measured in code from the transcript, never estimated by the model."""

import re
from typing import Any

from app.ai.openrouter import TranscriptSegment

# Crutch words interview coaches flag. Speech-to-text often drops "um" and "uh", so the count is
# a floor, and the app says so.
FILLERS: dict[str, re.Pattern[str]] = {
    "um": re.compile(r"\b(?:u+m+|u+h+m+)\b"),
    "uh": re.compile(r"\b(?:u+h+|e+r+m+)\b"),
    "hmm": re.compile(r"\bhm+\b"),
    "basically": re.compile(r"\bbasically\b"),
    "actually": re.compile(r"\bactually\b"),
    "you know": re.compile(r"\byou know\b"),
    "I mean": re.compile(r"\bi mean\b"),
}
_WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
# Comfortable interview pace in words per minute.
SLOW_BELOW = 110
FAST_ABOVE = 170
LONG_PAUSE_SECONDS = 3.0


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def measure(transcript: str, duration_ms: int, segments: list[TranscriptSegment]) -> dict[str, Any]:
    words = word_count(transcript)
    lowered = transcript.lower()
    fillers = {name: n for name, pattern in FILLERS.items() if (n := len(pattern.findall(lowered)))}

    duration = duration_ms / 1000
    spoken = [s for s in segments if s.text]
    speaking = duration
    longest_pause = long_pauses = opening_pause = None
    if spoken:
        speaking = max(spoken[-1].end - spoken[0].start, 1.0)
        gaps = [max(b.start - a.end, 0.0) for a, b in zip(spoken, spoken[1:], strict=False)]
        longest_pause = round(max(gaps, default=0.0), 1)
        long_pauses = sum(gap >= LONG_PAUSE_SECONDS for gap in gaps)
        opening_pause = round(spoken[0].start, 1)

    wpm = round(words / (speaking / 60)) if words and speaking > 0 else 0
    pace = "slow" if wpm < SLOW_BELOW else "fast" if wpm > FAST_ABOVE else "good"
    return {
        "duration_s": round(duration, 1),
        "words": words,
        "wpm": wpm,
        "pace": pace,
        "fillers": fillers,
        "filler_count": sum(fillers.values()),
        "longest_pause_s": longest_pause,
        "long_pauses": long_pauses,
        "opening_pause_s": opening_pause,
    }
