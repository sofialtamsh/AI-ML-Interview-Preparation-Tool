"""Text checks that keep agent output honest: is a quote really in the source?"""

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher

_WORD = re.compile(r"[a-z0-9]+")
# Share of a quote's 3-word sequences that must appear in the source for it to count as taken
# from the source (allows small differences such as a dropped word or changed punctuation).
GROUNDED_SHARE = 0.8
NEAR_DUPLICATE_RATIO = 0.9


def normalize(text: str) -> str:
    """Lowercase words only: punctuation, accents and spacing don't matter for comparison."""
    return " ".join(_WORD.findall(unicodedata.normalize("NFKC", text).lower()))


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def _trigrams(words: list[str]) -> set[tuple[str, str, str]]:
    return set(zip(words, words[1:], words[2:], strict=False))


class SourceText:
    """A source document prepared once for many containment checks."""

    def __init__(self, text: str) -> None:
        self.normalized = normalize(text)
        self._padded = f" {self.normalized} "
        self._trigrams = _trigrams(self.normalized.split())

    def contains_name(self, name: str) -> bool:
        """Whole-word match, e.g. a company name."""
        wanted = normalize(name)
        return bool(wanted) and f" {wanted} " in self._padded

    def contains_quote(self, quote: str) -> bool:
        wanted = normalize(quote)
        if not wanted:
            return False
        if wanted in self.normalized:
            return True
        grams = _trigrams(wanted.split())
        return bool(grams) and len(grams & self._trigrams) / len(grams) >= GROUNDED_SHARE


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()
