"""Provider contract and output validation shared by guidance providers."""
import ast
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
STARTER_LEVEL_NAMES = {1: "Kickstart", 2: "Guided", 3: "Strong Scaffold"}
STARTER_CODE_POLICY_VERSION = 3


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

    def generate_solution(self, context: dict, language: str) -> dict[str, str]: ...


def validate_starter_code(raw: Any, template: str, language: str, level: int) -> str:
    """Reject malformed scaffolds and changed LeetCode entry-point signatures."""
    if not isinstance(raw, str):
        raise ProviderOutputError("Invalid starter code output")
    code = raw.strip()
    if not code or len(code) > 20000 or "```" in code or not re.search(r"\btodo\b", code, re.IGNORECASE):
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
    _validate_scaffold_quality(code, template, language, level)
    return code


_COMMENTED_CODE = re.compile(
    r"^\s*(?://|#)\s*(?:\b(?:if|for|while)\s*\(|"
    r"\b(?:if|for|while)\s+[^\n]*(?:==|!=|<=|>=|\bin\b|\brange\s*\()[^\n]*:"
    r"|return\s+(?:new\b|[\[{(]|\w+[.(])|[\w.\[\]]+\s*(?:=|\+\+|--|\.put\s*\(|\.add\s*\())",
    re.IGNORECASE,
)


def _validate_scaffold_quality(code: str, template: str, language: str, level: int) -> None:
    """Catch clear leakage and broken shells; this is not a semantic proof."""
    lines = code.splitlines()
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise ProviderOutputError("Invalid Python starter syntax") from exc
    else:
        # Ignore comments and literals when checking common brace mistakes.
        without_comments = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        without_comments = re.sub(r"//[^\n]*", "", without_comments)
        without_literals = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                                  '""', without_comments)
        depth = 0
        for char in without_literals:
            if char == "{": depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    raise ProviderOutputError("Broken starter class structure")
        if depth:
            raise ProviderOutputError("Broken starter class structure")

    # Two executable-looking commented lines often mean a copyable solution.
    if sum(bool(_COMMENTED_CODE.match(line)) for line in lines) >= 2:
        raise ProviderOutputError("Commented-out algorithm in starter code")

    todo_lines = [line.lower() for line in lines if re.search(r"\btodo\b", line, re.IGNORECASE)]
    if level >= 2 and all(re.search(r"\btodo\s*:\s*(?:review|explain|optimi[sz]e|test|done)\b", line)
                          for line in todo_lines):
        raise ProviderOutputError("Starter TODO does not leave meaningful work")

    # A return at the same or shallower indentation than the final placeholder
    # makes that placeholder unreachable on the main path.
    executable = [(len(line) - len(line.lstrip()), line.strip()) for line in lines
                  if line.strip() and not line.lstrip().startswith(("#", "//"))]
    placeholder = next(((index, indent) for index, (indent, line) in enumerate(executable)
                        if any(marker in line for marker in ("NotImplementedError", "UnsupportedOperationException",
                                                              "throw new Error", "throw logic_error"))), None)
    if placeholder:
        index, indent = placeholder
        if any(re.match(r"return\b", line) and line_indent <= indent
               for line_indent, line in executable[:index]):
            raise ProviderOutputError("Unreachable unfinished placeholder")

    # A complete hash-map pair search is not a scaffold even if a TODO/throw
    # has been appended afterward. Keep this targeted to an obvious leak.
    active = "\n".join(line for line in lines if not line.lstrip().startswith(("#", "//")))
    has_control_flow = bool(re.search(r"(?m)^\s*(?:for|while|if)\b", active))
    if level == 1 and has_control_flow:
        raise ProviderOutputError("Kickstart contains algorithm control flow")
    if level == 1:
        # A bare submission shell plus a generic TODO is not a useful first step.
        template_lines = {line.strip() for line in template.splitlines() if line.strip()}
        code_without_block_comments = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        setup_lines = [line.strip() for line in code_without_block_comments.splitlines()
                       if line.strip() and not line.lstrip().startswith(("#", "//", "import ", "from ", "using ", "#include"))
                       and line.strip() not in template_lines
                       and not any(marker in line for marker in ("NotImplementedError", "UnsupportedOperationException",
                                                                 "throw new Error", "throw logic_error"))]
        if not setup_lines:
            raise ProviderOutputError("Kickstart lacks executable setup")
        if re.search(r"(?i)TODO:\s*(?:implement (?:the )?(?:selected )?approach|complete (?:the )?algorithm)", code):
            raise ProviderOutputError("Kickstart has only a generic teaching prompt")
    if level == 3 and not re.search(r"\bMinStack\b", code) and not has_control_flow:
        raise ProviderOutputError("Strong scaffold lacks control-flow structure")
    if re.search(r"\bif\s*\(\s*/\*.*?TODO.*?\*/\s*\)", active, re.IGNORECASE | re.DOTALL):
        raise ProviderOutputError("Invalid placeholder condition")
    if (re.search(r"\.containsKey\s*\(|\.has\s*\(|\bin\s+seen\b", active)
            and re.search(r"\.put\s*\(|\.set\s*\(|seen\s*\[", active)
            and re.search(r"\breturn\b", active)):
        raise ProviderOutputError("Complete lookup/update/return sequence in starter code")
