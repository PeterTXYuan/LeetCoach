"""Provider contract and concise output validation shared by hint providers."""
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field, StrictStr, ValidationError, field_validator


class ProviderConfigurationError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


class ProviderOutputError(Exception):
    pass


MAX_HINT_WORDS = 18
MAX_HINT_CHARACTERS = 120
LEVEL_WORD_LIMITS = (10, 14, MAX_HINT_WORDS)
LEVEL_CHARACTER_LIMITS = (75, 100, MAX_HINT_CHARACTERS)
SHORT_FALLBACK_HINTS = (
    "What detail tells you whether an answer is valid?",
    "Which part of the input could narrow your choices?",
    "What is one small check you could try next?",
)


class HintBatch(BaseModel):
    hints: list[StrictStr] = Field(min_length=3, max_length=3)

    @field_validator("hints")
    @classmethod
    def nonempty_hints(cls, hints: list[str]) -> list[str]:
        stripped = [hint.strip() for hint in hints]
        if any(not hint for hint in stripped):
            raise ValueError("Hints must be nonempty")
        return stripped


def validate_hints(raw: Any) -> list[str]:
    try:
        hints = HintBatch.model_validate({"hints": raw}).hints
    except ValidationError as exc:
        raise ProviderOutputError("Invalid hint provider output") from exc
    return [shorten_hint(hint, index) for index, hint in enumerate(hints)]


def shorten_hint(hint: str, index: int) -> str:
    """Keep a complete short sentence; use a safe nudge if none fits."""
    compact = " ".join(hint.split())
    compact = re.sub(r"^(?:hint\s*\d+\s*:\s*|\d+[.)]\s*|[-*]\s*)", "", compact,
                     flags=re.IGNORECASE)
    first_sentence = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)[0]
    if (first_sentence and len(first_sentence.split()) <= LEVEL_WORD_LIMITS[index]
            and len(first_sentence) <= LEVEL_CHARACTER_LIMITS[index]):
        return first_sentence
    return SHORT_FALLBACK_HINTS[index]


class LLMProvider(Protocol):
    def generate_hints(self, context: dict) -> list[str]: ...
