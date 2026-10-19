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


class StarterOutputDiagnostic(ProviderOutputError):
    """A rejected starter response with a stable, safe reason code."""

    def __init__(self, message: str, reason: str, stage: str = "validation"):
        super().__init__(message)
        self.reason = reason
        self.stage = stage


class StarterProviderDiagnostic(ProviderUnavailableError):
    """A failed starter provider request with its typed failure category."""

    def __init__(self, reason: str):
        super().__init__("Starter code provider unavailable")
        self.reason = reason
        self.stage = "provider"


SUPPORTED_STARTER_LANGUAGES = frozenset({"python", "java", "javascript", "cpp"})
STARTER_LEVEL_NAMES = {1: "Kickstart", 2: "Guided", 3: "Strong Scaffold"}
LEGACY_STARTER_CODE_POLICY_VERSION = 6
STARTER_CODE_POLICY_VERSION = 8
LINKED_GUIDANCE_POLICY_VERSION = 9


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

    def generate_starter_batch(self, context: dict, language: str) -> dict[str, str]: ...

    def generate_solution(self, context: dict, language: str) -> dict[str, str]: ...

    def generate_guidance_bundle(self, context: dict, language: str) -> dict: ...


def validate_starter_code(raw: Any, template: str, language: str, level: int) -> str:
    """Reject malformed scaffolds and changed LeetCode entry-point signatures."""
    if not isinstance(raw, str):
        raise StarterOutputDiagnostic("Invalid starter code output", "INVALID_OUTPUT_TYPE")
    code = raw.strip()
    if not code or len(code) > 20000 or "```" in code:
        raise StarterOutputDiagnostic("Invalid starter code output", "INVALID_STRUCTURE")
    if not re.search(r"\btodo\b", code, re.IGNORECASE):
        raise StarterOutputDiagnostic("Invalid starter code output", "MISSING_TODO")
    signatures = [line.strip().rstrip(" {") for line in template.splitlines() if "(" in line]
    output_lines = [line.strip().rstrip(" {") for line in code.splitlines()]
    if any(output_lines.count(signature) != 1 for signature in signatures):
        raise StarterOutputDiagnostic("Starter code changed the submission signature", "CHANGED_SIGNATURE")
    class_line = next((line.strip().rstrip(" {") for line in template.splitlines()
                       if line.strip().startswith("class ")), None)
    if class_line and class_line not in output_lines:
        raise StarterOutputDiagnostic("Starter code changed the submission class", "CHANGED_CLASS")
    placeholders = {
        "python": ("NotImplementedError",),
        "java": ("UnsupportedOperationException",),
        "javascript": ("throw new Error",),
        "cpp": ("throw ",),
    }
    if not any(marker in code for marker in placeholders[language]):
        raise StarterOutputDiagnostic("Starter code is missing unfinished logic", "MISSING_UNFINISHED_PLACEHOLDER")
    if level > 1 and code == template.strip():
        raise StarterOutputDiagnostic("Starter code lacks progressive guidance", "INVALID_STRUCTURE")
    _validate_scaffold_quality(code, template, language, level)
    return code


_COMMENTED_CODE = re.compile(
    r"^\s*(?://|#)\s*(?:\b(?:if|for|while)\s*\(|"
    r"\b(?:if|for|while)\s+[^\n]*(?:==|!=|<=|>=|\bin\b|\brange\s*\()[^\n]*:"
    r"|return\s+(?:new\b|[\[{(]|\w+[.(])|[\w.\[\]]+\s*(?:=|\+\+|--|\.put\s*\(|\.add\s*\())",
    re.IGNORECASE,
)
_COMMENTED_DECLARATION = re.compile(
    r"^\s*(?://|#)\s*(?:(?:const|let|var|auto|int|long|bool|boolean|double|float|char|String)"
    r"|(?:(?:std::)?(?:vector|pair|map|unordered_map|List|Map|Deque|Set)<[^\n]+>))"
    r"\s+(?:[*&]\s*)?[A-Za-z_]\w*\s*=",
    re.IGNORECASE,
)
_DIRECT_PAIR_RECIPE = re.compile(r"\breturn\s*\[\s*seen\s*\[", re.IGNORECASE)


def _check_unfinished_min_stack_methods(code: str, language: str) -> None:
    """A TODO in a design operation must not silently do nothing."""
    lines = code.splitlines()
    declarations = {
        "python": r"^\s*def\s+(?:push|pop|top|getMin)\s*\(",
        "java": r"^\s*public\s+(?:void|int)\s+(?:push|pop|top|getMin)\s*\(",
        "javascript": r"^\s*MinStack\.prototype\.(?:push|pop|top|getMin)\s*=\s*function\s*\(",
        "cpp": r"^\s*(?:void|int)\s+(?:push|pop|top|getMin)\s*\(",
    }
    starts = [index for index, line in enumerate(lines)
              if re.search(declarations[language], line)]
    marker = {"python": "NotImplementedError", "java": "UnsupportedOperationException",
              "javascript": "throw new Error", "cpp": "throw "}[language]
    for position, start in enumerate(starts):
        method_lines = lines[start:starts[position + 1] if position + 1 < len(starts) else len(lines)]
        if not any(re.search(r"\btodo\b", line, re.IGNORECASE) for line in method_lines):
            continue
        active = "\n".join(line for line in method_lines
                           if not line.lstrip().startswith(("#", "//")))
        if marker not in active:
            raise StarterOutputDiagnostic("Unfinished design method returns silently",
                                          "SILENT_UNFINISHED_METHOD")


def _validate_scaffold_quality(code: str, template: str, language: str, level: int) -> None:
    """Catch clear leakage and broken shells; this is not a semantic proof."""
    lines = code.splitlines()
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise StarterOutputDiagnostic("Invalid Python starter syntax", "INVALID_SYNTAX") from exc
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
                    raise StarterOutputDiagnostic("Broken starter class structure", "INVALID_STRUCTURE")
        if depth:
            raise StarterOutputDiagnostic("Broken starter class structure", "INVALID_STRUCTURE")

    # Two executable-looking commented lines often mean a copyable solution.
    if sum(bool(_COMMENTED_CODE.match(line) or _COMMENTED_DECLARATION.match(line))
           for line in lines) >= 2:
        raise StarterOutputDiagnostic("Commented-out algorithm in starter code", "COMMENTED_OUT_ALGORITHM")
    if any(re.search(r"\btodo\b", line, re.IGNORECASE) and _DIRECT_PAIR_RECIPE.search(line)
           for line in lines if line.lstrip().startswith(("#", "//"))):
        raise StarterOutputDiagnostic("Algorithm recipe in starter comments", "ALGORITHM_RECIPE_IN_COMMENTS")
    if "twoSum" in template and level >= 2:
        comments = " ".join(line.lower() for line in lines
                            if line.lstrip().startswith(("#", "//")) and "todo" in line.lower())
        lookup = bool(re.search(r"\bcomplement\b.*\b(?:in|seen|map|earlier)\b|"
                                r"\b(?:seen|map)\b.*\bcomplement\b", comments))
        returned_pair = bool(re.search(r"\breturn\b.*\b(?:pair|indice|index)\b", comments))
        store = bool(re.search(r"\b(?:store|record|insert|update|put|set)\b.*\b(?:seen|map)\b|"
                               r"\b(?:seen|map)\b.*\b(?:store|record|insert|update|put|set)\b", comments))
        if lookup and returned_pair and store:
            raise StarterOutputDiagnostic("Algorithm recipe in starter comments",
                                          "ALGORITHM_RECIPE_IN_COMMENTS")
    if "maxDepth" in template and level == 2:
        active_lines = "\n".join(line for line in lines
                                 if not line.lstrip().startswith(("#", "//")))
        comments = " ".join(line.lower() for line in lines if line.lstrip().startswith(("#", "//")))
        if ("root.left" in active_lines and "root.right" in active_lines
                and re.search(r"\b(?:return|combine)\b.*(?:1\s*(?:\+|plus)|one\s+plus).*(?:larger|max)", comments)):
            raise StarterOutputDiagnostic("Recursion answer recipe in Guided starter",
                                          "ALGORITHM_RECIPE_IN_COMMENTS")
        if re.search(r"(?m)^\s*#\s*TODO:\s*compute.*right.*depth\s*$\n\s*right_depth\s*=", code, re.I):
            raise StarterOutputDiagnostic("TODO repeats the next implemented line",
                                          "REDUNDANT_GUIDANCE")
    if re.search(r"\bMinStack\b", code):
        _check_unfinished_min_stack_methods(code, language)

    # A TODO after an unconditional placeholder in the same block cannot be
    # reached. Dedentation/closing braces end the earlier block.
    last_throw_indent = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if last_throw_indent is not None and indent < last_throw_indent:
            last_throw_indent = None
        if re.match(r"^\s*(?:#|//)\s*TODO\b", line, re.I) and last_throw_indent is not None and indent >= last_throw_indent:
            raise StarterOutputDiagnostic("TODO follows an unreachable placeholder",
                                          "UNREACHABLE_TODO")
        if not stripped.startswith(("#", "//")) and any(marker in stripped for marker in (
                "raise NotImplementedError", "throw new UnsupportedOperationException",
                "throw new Error", "throw logic_error", "throw std::logic_error")):
            last_throw_indent = indent

    todo_lines = [line.lower() for line in lines if re.search(r"\btodo\b", line, re.IGNORECASE)]
    if level >= 2 and all(re.search(r"\btodo\s*:\s*(?:review|explain|optimi[sz]e|test|done)\b", line)
                          for line in todo_lines):
        raise StarterOutputDiagnostic("Starter TODO does not leave meaningful work", "APPARENT_COMPLETE_SOLUTION")

    # A return at the same or shallower indentation than the final placeholder
    # makes that placeholder unreachable on the main path.
    executable = [(len(line) - len(line.lstrip()), line.strip()) for line in lines
                  if line.strip() and not line.lstrip().startswith(("#", "//"))]
    placeholder = next(((index, indent) for index, (indent, line) in enumerate(executable)
                        if any(marker in line for marker in ("NotImplementedError", "UnsupportedOperationException",
                                                              "throw new Error", "throw logic_error",
                                                              "throw std::logic_error"))), None)
    if placeholder:
        index, indent = placeholder
        if any(re.match(r"return\b", line) and line_indent <= indent
               for line_indent, line in executable[:index]):
            raise StarterOutputDiagnostic("Unreachable unfinished placeholder", "APPARENT_COMPLETE_SOLUTION")

    # A complete hash-map pair search is not a scaffold even if a TODO/throw
    # has been appended afterward. Keep this targeted to an obvious leak.
    active = "\n".join(line for line in lines if not line.lstrip().startswith(("#", "//")))
    has_control_flow = bool(re.search(r"(?m)^\s*(?:for|while|if)\b", active))
    if level == 1 and has_control_flow:
        raise StarterOutputDiagnostic("Kickstart contains algorithm control flow", "LEVEL_ONE_EXCESSIVE_CONTROL_FLOW")
    if level == 1:
        # A bare submission shell plus a generic TODO is not a useful first step.
        template_lines = {line.strip() for line in template.splitlines() if line.strip()}
        code_without_block_comments = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        setup_lines = [line.strip() for line in code_without_block_comments.splitlines()
                       if line.strip() and not line.lstrip().startswith(("#", "//", "import ", "from ", "using ", "#include"))
                       and line.strip() not in template_lines
                       and not any(marker in line for marker in ("NotImplementedError", "UnsupportedOperationException",
                                                                 "throw new Error", "throw logic_error",
                                                                 "throw std::logic_error"))]
        if not setup_lines:
            raise StarterOutputDiagnostic("Kickstart lacks executable setup", "LEVEL_ONE_NO_USEFUL_SETUP")
        if re.search(r"(?i)TODO:\s*(?:implement (?:the )?(?:selected )?approach|complete (?:the )?algorithm)", code):
            raise StarterOutputDiagnostic("Kickstart has only a generic teaching prompt", "LEVEL_ONE_NO_USEFUL_SETUP")
    if level == 3 and not re.search(r"\bMinStack\b", code) and not has_control_flow:
        raise StarterOutputDiagnostic("Strong scaffold lacks control-flow structure", "INVALID_STRUCTURE")
    if re.search(r"\bif\s*\(\s*/\*.*?TODO.*?\*/\s*\)", active, re.IGNORECASE | re.DOTALL):
        raise StarterOutputDiagnostic("Invalid placeholder condition", "INVALID_PLACEHOLDER_CONDITION")
    if (re.search(r"\.containsKey\s*\(|\.has\s*\(|\bin\s+seen\b", active)
            and re.search(r"\.put\s*\(|\.set\s*\(|seen\s*\[", active)
            and re.search(r"\breturn\b", active)):
        raise StarterOutputDiagnostic("Complete lookup/update/return sequence in starter code", "APPARENT_COMPLETE_SOLUTION")
