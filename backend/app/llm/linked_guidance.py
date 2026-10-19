"""Policy 9: validate one progressively completed implementation as a unit."""
import ast
import re
import tempfile
from pathlib import Path
from typing import Any

from app.llm.base import StarterOutputDiagnostic
from app.llm.starter_batch import LEVEL_KEYS, validate_level, masked_source
from app.llm.starter_syntax import check_syntax


WARNING_MESSAGES = {
    "NO_USEFUL_SETUP": "This is a very minimal starting point; add setup as you work.",
    "UNSAFE_UNFINISHED_LOOP": "An unfinished loop may not stop or may return an incomplete result. Review it before running.",
    "SILENT_UNFINISHED_METHOD": "A TODO path may finish without doing the requested work. Review it before running.",
    "MISSING_UNFINISHED_PLACEHOLDER": "This starter may not clearly stop at unfinished logic. Review its TODOs before running.",
    "MISSING_MEANINGFUL_TODO": "This level may leave too little work for you to complete.",
    "APPARENT_COMPLETE_SOLUTION": "This starter may reveal more of the answer than intended.",
    "COMMENTED_OUT_ALGORITHM": "Comments may give away executable answer steps.",
    "ALGORITHM_RECIPE_IN_COMMENTS": "Comments may give away too much of the algorithm.",
    "APPROACH_CONTRADICTION": "This level may not follow the selected approach.",
    "UNREACHABLE_PLACEHOLDER": "An unfinished TODO may never be reached when this code runs.",
    "UNREACHABLE_TODO": "A TODO appears after a stopping statement and may never be reached.",
    "INVALID_SYNTAX": "A structural check found possible syntax trouble. Review this code before running it.",
    "INCOMPATIBLE_LEVEL_DESIGN": "This stage may change or omit setup from the previous stage.",
    "INVALID_LEVEL_PROGRESSION": "This stage may not add useful structure over the previous one.",
}


def _warning(scope: str, code: str, message: str | None = None) -> dict[str, str]:
    return {"scope": scope, "code": code,
            "message": message or WARNING_MESSAGES.get(code, "Review this generated code before running it.")}


def _submission_code(value: Any, template: str, language: str, scope: str,
                     warnings: list[dict[str, str]], *, max_length: int) -> str:
    """Only malformed, wrong-entry-point, or demonstrably invalid code blocks the response."""
    if not isinstance(value, str) or not value.strip() or len(value) > max_length or "```" in value:
        raise StarterOutputDiagnostic("Invalid linked guidance source", "INVALID_STRUCTURE")
    code = value.strip()
    signatures = [line.strip().rstrip(" {") for line in template.splitlines() if "(" in line]
    lines = [line.strip().rstrip(" {") for line in code.splitlines()]
    if not signatures or any(lines.count(signature) != 1 for signature in signatures):
        raise StarterOutputDiagnostic("Linked guidance changed a submission signature", "CHANGED_SIGNATURE")
    class_line = next((line.strip().rstrip(" {") for line in template.splitlines()
                       if line.strip().startswith("class ")), None)
    if class_line and lines.count(class_line) != 1:
        raise StarterOutputDiagnostic("Linked guidance changed the submission class", "CHANGED_CLASS")
    syntax = check_syntax(code, language)
    if syntax["status"] == "FAIL":
        if syntax["summary"] not in {"Bounded syntax check could not complete",
                                      "Syntax validation busy; retry generation"}:
            raise StarterOutputDiagnostic("Invalid linked guidance syntax", "INVALID_SYNTAX")
        warnings.append(_warning(scope, "SYNTAX_NOT_CHECKED",
                                 "The syntax checker was unavailable. Review this code before running it."))
    elif syntax["status"] == "NOT_RUN":
        warnings.append(_warning(scope, "SYNTAX_NOT_CHECKED",
                                 "A compiler was unavailable, so this code was not syntax-checked."))
    return code


def _working_lines(code: str, language: str) -> set[str]:
    """Concrete setup and state updates worth retaining; ignore scaffolding placeholders."""
    source = code if language == "python" else masked_source(code)
    lines = set()
    for raw in source.splitlines():
        line = raw.strip().rstrip(";{").strip()
        if not line or re.search(r"\b(TODO|throw|raise|pass|class|import|include)\b", line, re.I):
            continue
        if re.fullmatch(r"return\s*(?:\[\s*\]|\{\s*\}|None|null)?", line):
            continue
        if line in ("}", ")") or line.startswith(("//", "#", "*")):
            continue
        if not ("=" in line or re.search(r"\b(?:for|while|return)\b|\.\w+\s*\(|\+\+|--", line)):
            continue
        lines.add(re.sub(r"\s+", "", line))
    return lines


def _design_names(code: str, language: str) -> set[str]:
    if language == "python":
        tree = ast.parse(code)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    names.update(item.id for item in ast.walk(target) if isinstance(item, ast.Name) and
                                 not item.id.startswith("_") and len(item.id) > 2)
                    names.update(item.attr for item in ast.walk(target) if isinstance(item, ast.Attribute))
        return names
    source = masked_source(code)
    return set(re.findall(r"\b(?:this\.)?([A-Za-z_]\w{2,})\s*(?==|(?:\[.*?\])?\s*=)", source))


def validate_linked_bundle(raw: Any, context: dict, language: str) -> dict:
    if not isinstance(raw, dict) or not {*LEVEL_KEYS, "solution"} <= set(raw):
        raise StarterOutputDiagnostic("Invalid linked guidance fields", "INVALID_BATCH_FIELDS", "parsing")
    template = context["problem"]["submissionTemplate"]["code"]
    warnings: list[dict[str, str]] = []
    starters = {}
    for index, key in enumerate(LEVEL_KEYS, 1):
        code = _submission_code(raw[key], template, language, key, warnings, max_length=20000)
        starters[key] = code
        try:
            # The legacy quality validator remains a useful diagnostic. Its
            # heuristic teaching judgments no longer suppress valid code.
            validate_level(code, context, language, index)
        except StarterOutputDiagnostic as exc:
            warnings.append(_warning(key, exc.reason))

    source = raw["solution"]
    if not isinstance(source, dict) or any(
        not isinstance(source.get(field), str) or not source[field].strip() or len(source[field]) > limit
        for field, limit in (("code", 30000), ("explanation", 5000),
                             ("timeComplexity", 500), ("spaceComplexity", 500))
    ):
        raise StarterOutputDiagnostic("Invalid linked answer fields", "INVALID_FULL_SOLUTION")
    solution = {field: source[field].strip() for field in
                ("code", "explanation", "timeComplexity", "spaceComplexity")}
    solution["code"] = _submission_code(solution["code"], template, language, "solution",
                                        warnings, max_length=30000)
    if (re.search(r"\b(?:TODO|FIXME|NotImplementedError|UnsupportedOperationException|NotImplemented|placeholder)\b",
                  solution["code"], re.I)
        or re.search(r"(?m)^\s*(?:pass|\.\.\.)\s*(?:#.*)?$", solution["code"])
        or re.search(r"\b(?:throw|raise)\b[^\n]*(?:not\s+implemented|implement|complete|pending|todo|stub)",
                     solution["code"], re.I)):
        warnings.append(_warning("solution", "INCOMPLETE_FULL_SOLUTION",
                                 "The full answer appears to contain unfinished logic. Review or regenerate it."))
    if context["problem"]["slug"] == "two-sum" and re.search(
        r"\breturn\s*(?:\[\s*\]|\{\s*\}|new\s+int\s*\[\s*\]\s*\{\s*\})\s*;?", solution["code"]
    ):
        warnings.append(_warning("solution", "POSSIBLE_EMPTY_ANSWER",
                                 "This answer may return an empty result despite the guaranteed solution."))
    versions = [starters[key] for key in LEVEL_KEYS] + [solution["code"]]
    designs = [_design_names(code, language) for code in versions]
    for index, (earlier, later, old_names, new_names) in enumerate(zip(
        versions, versions[1:], designs, designs[1:]
    )):
        scope = (*LEVEL_KEYS, "solution")[index + 1]
        important = old_names - {"self", "nums", "target", "head"}
        if not important <= new_names:
            warnings.append(_warning(scope, "INCOMPATIBLE_LEVEL_DESIGN"))
        working = _working_lines(earlier, language)
        later_working = _working_lines(later, language)
        if working and len(working & later_working) < max(1, (3 * len(working) + 4) // 5):
            warnings.append(_warning(scope, "INCOMPATIBLE_LEVEL_DESIGN"))
        if index < 2 and not later_working - working:
            warnings.append(_warning(scope, "INVALID_LEVEL_PROGRESSION"))
    if len(set(starters.values())) != 3:
        warnings.append(_warning("bundle", "INVALID_LEVEL_PROGRESSION",
                                 "Two starter levels are identical. Try regenerating for more progression."))
    if context["problem"]["slug"] == "min-stack" and not re.search(
        r"\b(?:this\.|self\.)?(?:pairs|values|stack|minimums|min_stack)\s*=",
        masked_source(starters["level1"]) if language != "python" else starters["level1"]
    ):
        warnings.append(_warning("level1", "INCOMPATIBLE_LEVEL_DESIGN",
                                 "This level does not set up the stack used by later levels."))
    unique = list({(warning["scope"], warning["code"]): warning for warning in warnings}.values())
    return {**starters, "solution": solution, "warnings": unique}


def check_linked_correctness(slug: str, language: str, code: str) -> dict:
    """Execute only in the existing WSL bubblewrap runner, never on the API host."""
    from evaluation.correctness import FIXTURES, execute_solution, probe_sandbox
    if slug not in FIXTURES:
        return {"status": "NOT_RUN", "summary": "No representative fixture for this problem"}
    if language not in {"python", "cpp"} or language == "cpp" and slug not in {"two-sum", "3sum"}:
        return {"status": "NOT_RUN", "summary": "No isolated fixture harness for this language and problem"}
    available, reason = probe_sandbox()
    if not available:
        return {"status": "NOT_RUN", "summary": f"Isolated runner unavailable: {reason}"}
    with tempfile.TemporaryDirectory(prefix="leetcoach-guidance-") as temp:
        result = execute_solution(slug, language, code, Path(temp), sandbox_available=True)
    return {"status": result["status"], "summary": result["summary"]}
