"""Provider contract and output validation shared by guidance providers."""
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field, StrictStr, ValidationError, field_validator


class ProviderConfigurationError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


class ProviderOutputError(Exception):
    pass


SUPPORTED_STARTER_LANGUAGES = frozenset({"python", "java", "javascript", "cpp"})
STARTER_LEVEL_NAMES = {1: "Minimal", 2: "Guided", 3: "Strong Scaffold"}


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
    is_ai_generated: bool

    def generate_hints(self, context: dict) -> list[str]: ...

    def generate_starter_code(self, context: dict, language: str, level: int) -> str: ...


def validate_starter_code(raw: Any, template: str, language: str, level: int) -> str:
    """Reject malformed scaffolds and changed LeetCode entry-point signatures."""
    if not isinstance(raw, str):
        raise ProviderOutputError("Invalid starter code output")
    code = raw.strip()
    if not code or len(code) > 20000 or "```" in code or "todo" not in code.lower():
        raise ProviderOutputError("Invalid starter code output")
    signatures = [line.strip().rstrip(" {") for line in template.splitlines() if "(" in line]
    output_lines = [line.strip().rstrip(" {") for line in code.splitlines()]
    if any(output_lines.count(signature) != 1 for signature in signatures):
        raise ProviderOutputError("Starter code changed the submission signature")
    class_line = next((line.strip().rstrip(" {") for line in template.splitlines()
                       if line.strip().startswith("class ")), None)
    if class_line and class_line not in output_lines:
        raise ProviderOutputError("Starter code changed the submission class")
    placeholders = {
        "python": ("NotImplementedError",),
        "java": ("UnsupportedOperationException",),
        "javascript": ("throw new Error",),
        "cpp": ("throw ",),
    }
    if not any(marker in code for marker in placeholders[language]):
        raise ProviderOutputError("Starter code is missing unfinished logic")
    if level > 1 and code == template.strip():
        raise ProviderOutputError("Starter code lacks progressive guidance")
    return code
