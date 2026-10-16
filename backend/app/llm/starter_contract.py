"""Trusted Starter Code assembly with one bounded, additive AI contribution.

The offline scaffold owns signatures, methods, control flow and fail-loud paths.
The model can add one executable intermediate or conceptual TODO at a named
slot; it cannot replace or remove any trusted source line.
"""
import re

from app.llm.base import StarterOutputDiagnostic, validate_starter_code
from app.llm.mock_provider import MockLLMProvider
from app.llm.starter_diagnostics import observe


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


def _inside_guard(rows: list[str], slot_line: int, pattern: str) -> bool:
    """Only trust a preceding guard if its indented block still contains the slot."""
    slot_indent = len(rows[slot_line]) - len(rows[slot_line].lstrip())
    for index, row in enumerate(rows[:slot_line]):
        indent = len(row) - len(row.lstrip())
        if indent >= slot_indent or not re.search(pattern, row):
            continue
        if all(not later.strip() or later.lstrip().startswith(("#", "//"))
               or len(later) - len(later.lstrip()) > indent
               for later in rows[index + 1:slot_line]):
            return True
    return False


def _validate_code(line: str, baseline: str, slot: dict, language: str) -> str:
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
            or re.search(r"\[\s*\d+\s*\]", expr)
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
    rows = baseline.splitlines()
    prior = "\n".join(rows[:slot["line"]])
    for receiver in re.findall(r"\b(root|head|current|first|second|list1|list2)\s*\.\s*(?:next|left|right|val)\b", expr):
        if not _inside_guard(rows, slot["line"],
                             rf"\bwhile\b.*\b{re.escape(receiver)}\b\s*(?:is\s+not|!=)\s*(?:None|nullptr|null)"):
            raise StarterOutputDiagnostic("Unguarded node access in starter edit",
                                          "UNSAFE_STRUCTURE_MODIFICATION")
    known = set(_IDENTIFIER.findall("\n".join(row for row in prior.splitlines()
                                              if not row.lstrip().startswith(("#", "//")))))
    expression_without_strings = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '', expr)
    loop_guard = _inside_guard(rows, slot["line"], r"^\s*(?:for|while)\b")
    for receiver, _index in re.findall(r"\b([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*\]", expression_without_strings):
        if receiver not in {"nums", "numbers", "s", "prices", "grid", "temperatures", "strs"} or not loop_guard:
            raise StarterOutputDiagnostic("Unguarded container access in starter edit",
                                          "UNSAFE_STRUCTURE_MODIFICATION")
    expression_identifiers = set(_IDENTIFIER.findall(expression_without_strings))
    referenced = {word for word in expression_identifiers if not re.search(
        rf"\.\s*{re.escape(word)}\b", expression_without_strings)}
    referenced -= {"len", "size", "true", "false", "null", "None", "True", "False", "static_cast", "int"}
    if not (known & referenced) or referenced - known:
        raise StarterOutputDiagnostic("Starter edit is not grounded in this scaffold",
                                      "EMPTY_AI_CONTRIBUTION")
    return line


def _validate_guidance(value: object, existing_todo: str) -> str | None:
    """Treat optional low-value prose independently from an otherwise safe edit."""
    if not isinstance(value, str) or not value.strip() or len(value) > 150 or "```" in value:
        return None
    guidance = re.sub(r"^\s*(?:(?:#|//)\s*)?(?:TODO\s*:\s*)?", "", value).strip()
    if (not guidance or len(guidance) > 120 or any(char in guidance for char in "\r\n{};")
            or _GENERIC_GUIDANCE.search(guidance) or _DIRECT_GUIDANCE.search(guidance)
            or re.search(r"\b(?:if|then|otherwise|else)\b", guidance, re.I)
            or re.search(r"\b(?:if|else|for|while|def|class|throw|raise)\b\s*[(]", guidance, re.I)):
        return None
    existing = set(re.findall(r"[a-z]{4,}", existing_todo.lower())) - {
        "todo", "which", "what", "could", "would", "this", "that"}
    proposed = set(re.findall(r"[a-z]{4,}", guidance.lower())) - {
        "which", "what", "could", "would", "this", "that"}
    if existing and proposed and len(existing & proposed) / min(len(existing), len(proposed)) >= 0.6:
        return None
    return guidance


def _single_edit(plan: object) -> dict:
    """Accept the new flat response and the prior one-edit envelope for replay."""
    if not isinstance(plan, dict):
        raise StarterOutputDiagnostic("Invalid starter edit plan", "INVALID_GENERATION_PLAN")
    if "edits" in plan:
        if (set(plan) != {"edits"} or not isinstance(plan["edits"], list)
                or len(plan["edits"]) != 1):
            raise StarterOutputDiagnostic("Starter edit is empty or too broad", "EMPTY_AI_CONTRIBUTION")
        edit = plan["edits"][0]
        if not isinstance(edit, dict) or set(edit) - {"slot", "lines", "guidance"}:
            raise StarterOutputDiagnostic("Invalid starter edit plan", "INVALID_GENERATION_PLAN")
        lines = edit.get("lines")
        if lines is not None and (not isinstance(lines, list) or len(lines) != 1
                                  or not isinstance(lines[0], str)):
            raise StarterOutputDiagnostic("Starter edit needs one line", "EMPTY_AI_CONTRIBUTION")
        return {"slot": edit.get("slot"), "code": lines[0] if lines else None,
                "guidance": edit.get("guidance")}
    if set(plan) - {"slot", "code", "guidance"}:
        raise StarterOutputDiagnostic("Invalid starter edit plan", "INVALID_GENERATION_PLAN")
    return plan


def assemble_starter_plan(plan: object, baseline: str, template: str,
                          language: str, level: int) -> str:
    """Apply a single safe insertion before a known TODO, preserving all old lines."""
    edit = _single_edit(plan)
    if not isinstance(edit.get("slot"), str):
        raise StarterOutputDiagnostic("Invalid starter edit target", "INVALID_GENERATION_PLAN")
    slot = next((slot for slot in starter_slots(baseline) if slot["id"] == edit["slot"]), None)
    if slot is None:
        raise StarterOutputDiagnostic("Unknown starter edit target", "UNKNOWN_EDIT_TARGET")
    raw_code = edit.get("code")
    if raw_code is not None and not isinstance(raw_code, str):
        raise StarterOutputDiagnostic("Invalid starter code contribution", "INVALID_GENERATION_PLAN")
    line = _validate_code(raw_code.strip(), baseline, slot, language) if raw_code and raw_code.strip() else None
    raw_guidance = edit.get("guidance")
    guidance = _validate_guidance(raw_guidance, slot["existingTodo"])
    if not line and not guidance:
        raise StarterOutputDiagnostic("Starter edit adds nothing useful", "EMPTY_AI_CONTRIBUTION")
    rows = baseline.splitlines()
    indent = re.match(r"\s*", rows[slot["line"]]).group()
    comment = "#" if language == "python" else "//"
    additions = [indent + line] if line else []
    if guidance:
        additions.append(indent + f"{comment} TODO: {guidance}")
    rows[slot["line"]:slot["line"]] = additions
    assembled = "\n".join(rows)
    try:
        code = validate_starter_code(assembled, template, language, level)
    except StarterOutputDiagnostic:
        if not line or not guidance:
            raise
        # Optional prose must never turn a valid executable edit into fallback.
        rows = baseline.splitlines()
        rows[slot["line"]:slot["line"]] = [indent + line]
        code = validate_starter_code("\n".join(rows), template, language, level)
        guidance = None
    if raw_guidance is not None and not guidance:
        observe({"kind": "partial_acceptance", "stage": "validation",
                 "reason": "OPTIONAL_GUIDANCE_OMITTED"})
    return code
