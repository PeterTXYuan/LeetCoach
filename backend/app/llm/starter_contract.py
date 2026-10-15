"""Trusted Starter Code assembly with one bounded, additive AI edit.

The offline scaffold owns signatures, methods, control flow and fail-loud paths.
The model can add one executable intermediate at a named TODO slot; it cannot
replace or remove any trusted source line.
"""
import re

from app.llm.base import StarterOutputDiagnostic, validate_starter_code
from app.llm.mock_provider import MockLLMProvider


_TODO = re.compile(r"^\s*(?:#|//)\s*TODO\b", re.IGNORECASE)
_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
_DECLARATION = {
    "python": re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)$"),
    "java": re.compile(r"^(?:(?:final\s+)?(?:int|long|boolean|double|float|char|String|var)\s+)(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+);$"),
    "javascript": re.compile(r"^(?:const|let)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+);$"),
    "cpp": re.compile(r"^(?:(?:const\s+)?(?:auto|int|long|bool|double|size_t|string|vector<[^;]+>|pair<[^;]+>)\s+)(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+);$"),
}
_UNSAFE_EXPRESSION = re.compile(
    r"\b(?:return|throw|raise|yield|await|class|def|function|import|new|exec|eval)\b"
    r"|\+\+|--|\b(?:append|push|pop|put|set|add|remove|insert|update|containsKey|has)\s*\("
    r"|(?:==|!=|<=|>=|&&|\|\||\?|\bif\b|\belse\b)", re.IGNORECASE,
)
_GENERIC_GUIDANCE = re.compile(r"^(?:implement|finish|complete|review|test|optimi[sz]e)\b", re.I)
_DIRECT_GUIDANCE = re.compile(r"\b(?:return|store|insert|update|lookup|look up|put|set)\b", re.I)


def trusted_starter(context: dict, language: str, level: int) -> str:
    """Use the existing validated offline progression as the immutable baseline."""
    return MockLLMProvider().generate_starter_code(context, language, level)


def starter_slots(code: str) -> list[dict]:
    """Number each existing TODO line; slot IDs are scoped to this one request."""
    slots = []
    for index, line in enumerate(code.splitlines()):
        if _TODO.match(line):
            slots.append({"id": f"todo-{len(slots) + 1}", "line": index,
                          "existingTodo": line.strip()})
    return slots


def _balanced_expression(expr: str) -> bool:
    pairs = {')': '(', ']': '['}
    opened = []
    quote = None
    escaped = False
    for char in expr:
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char in '([':
            opened.append(char)
        elif char in ')]':
            if not opened or opened.pop() != pairs[char]:
                return False
    return not opened and quote is None


def _validate_contribution(edit: dict, baseline: str, slot: dict,
                           language: str) -> tuple[str, str | None]:
    if not isinstance(edit, dict) or set(edit) - {"slot", "lines", "guidance"}:
        raise StarterOutputDiagnostic("Invalid starter edit plan", "INVALID_GENERATION_PLAN")
    lines = edit.get("lines")
    if not isinstance(lines, list) or len(lines) != 1 or not isinstance(lines[0], str):
        raise StarterOutputDiagnostic("Starter edit needs one executable line", "EMPTY_AI_CONTRIBUTION")
    line = lines[0].strip()
    if (not line or len(line) > 180 or any(char in line for char in "\r\n{}#")
            or "//" in line or "```" in line):
        raise StarterOutputDiagnostic("Unsafe starter edit line", "UNSAFE_STRUCTURE_MODIFICATION")
    match = _DECLARATION[language].fullmatch(line)
    if not match:
        raise StarterOutputDiagnostic("Starter edit must be a local intermediate declaration",
                                      "UNSAFE_STRUCTURE_MODIFICATION")
    name, expr = match.group("name"), match.group("expr").strip()
    if (not expr or len(expr) > 120 or _UNSAFE_EXPRESSION.search(expr) or ";" in expr
            or re.search(r"(?<![=!<>])=(?!=)", expr) or not _balanced_expression(expr)
            or not re.fullmatch(r"[A-Za-z0-9_\s.\[\]()<>+\-*/%:!,\"'\\]*", expr)):
        raise StarterOutputDiagnostic("Unsafe starter edit expression", "UNSAFE_STRUCTURE_MODIFICATION")
    if any(call not in {"len", "size"} for call in
           re.findall(r"\b([A-Za-z_]\w*)\s*\(", expr)):
        raise StarterOutputDiagnostic("Starter edit calls an unapproved operation",
                                      "UNSAFE_STRUCTURE_MODIFICATION")
    active = "\n".join(row for row in baseline.splitlines()
                       if row.strip() and not row.lstrip().startswith(("#", "//")))
    if re.search(rf"\b{re.escape(name)}\b", active) or line in baseline:
        raise StarterOutputDiagnostic("Starter edit duplicates trusted setup", "EMPTY_AI_CONTRIBUTION")
    # A new intermediate must derive from a parameter or earlier trusted state,
    # rather than being a generic constant or unrelated statement.
    prior = "\n".join(baseline.splitlines()[:slot["line"]])
    known = set(_IDENTIFIER.findall("\n".join(row for row in prior.splitlines()
                                              if not row.lstrip().startswith(("#", "//")))))
    expression_without_strings = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '', expr)
    expression_identifiers = set(_IDENTIFIER.findall(expression_without_strings))
    referenced = {word for word in expression_identifiers if not re.search(
        rf"\.\s*{re.escape(word)}\b", expression_without_strings)}
    referenced -= {"len", "size", "true", "false", "null", "None", "True", "False", "static_cast", "int"}
    if not (known & referenced) or referenced - known:
        raise StarterOutputDiagnostic("Starter edit is not grounded in this scaffold",
                                      "EMPTY_AI_CONTRIBUTION")
    guidance = edit.get("guidance")
    if guidance is not None:
        if (not isinstance(guidance, str) or not guidance.strip() or len(guidance) > 120
                or any(char in guidance for char in "\r\n") or "TODO" in guidance.upper()
                or _GENERIC_GUIDANCE.search(guidance.strip()) or _DIRECT_GUIDANCE.search(guidance)):
            raise StarterOutputDiagnostic("Invalid educational guidance", "INVALID_GENERATION_PLAN")
        guidance = guidance.strip()
        existing = set(re.findall(r"[a-z]{4,}", slot["existingTodo"].lower())) - {"todo", "which", "what", "could", "would", "this", "that"}
        proposed = set(re.findall(r"[a-z]{4,}", guidance.lower())) - {"which", "what", "could", "would", "this", "that"}
        if existing and proposed and len(existing & proposed) / min(len(existing), len(proposed)) >= 0.6:
            raise StarterOutputDiagnostic("Starter guidance repeats trusted TODO",
                                          "EMPTY_AI_CONTRIBUTION")
    return line, guidance


def assemble_starter_plan(plan: object, baseline: str, template: str,
                          language: str, level: int) -> str:
    """Apply a single safe insertion before a known TODO, preserving all old lines."""
    if not isinstance(plan, dict) or set(plan) != {"edits"} or not isinstance(plan["edits"], list):
        raise StarterOutputDiagnostic("Invalid starter edit plan", "INVALID_GENERATION_PLAN")
    if len(plan["edits"]) != 1:
        raise StarterOutputDiagnostic("Starter edit is empty or too broad", "EMPTY_AI_CONTRIBUTION")
    edit = plan["edits"][0]
    if not isinstance(edit, dict) or not isinstance(edit.get("slot"), str):
        raise StarterOutputDiagnostic("Invalid starter edit target", "INVALID_GENERATION_PLAN")
    slot = next((slot for slot in starter_slots(baseline) if slot["id"] == edit["slot"]), None)
    if slot is None:
        raise StarterOutputDiagnostic("Unknown starter edit target", "UNKNOWN_EDIT_TARGET")
    line, guidance = _validate_contribution(edit, baseline, slot, language)
    rows = baseline.splitlines()
    indent = re.match(r"\s*", rows[slot["line"]]).group()
    comment = "#" if language == "python" else "//"
    additions = [indent + line]
    if guidance:
        additions.append(indent + f"{comment} TODO: {guidance}")
    rows[slot["line"]:slot["line"]] = additions
    assembled = "\n".join(rows)
    return validate_starter_code(assembled, template, language, level)
