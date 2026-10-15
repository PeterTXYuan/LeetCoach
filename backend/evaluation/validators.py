"""Response validation plus deliberately labeled teaching-quality heuristics."""
import re

from app.llm.base import (
    LEVEL_CHARACTER_LIMITS, LEVEL_WORD_LIMITS, ProviderOutputError,
    SHORT_FALLBACK_HINTS, validate_hints, validate_starter_code,
)
from app.llm.solution_validation import validate_solution

from evaluation.correctness import check_syntax


def criterion(name: str, status: str, detail: str) -> dict:
    return {"criterion": name, "status": status, "detail": detail}


def _identity(payload: dict, case) -> bool:
    return (payload.get("slug") == case.slug and
            payload.get("approachId") == case.approach_id and
            (case.language is None or payload.get("language") == case.language) and
            (case.level is None or payload.get("level") == case.level))


def evaluate_hints(payload: dict, case) -> dict:
    checks: list[dict] = []
    hints = payload.get("hints")
    try:
        validated = validate_hints(hints)
        structure = (_identity(payload, case) and hints == validated and
                     all(len(hint.split()) <= LEVEL_WORD_LIMITS[index] and
                         len(hint) <= LEVEL_CHARACTER_LIMITS[index]
                         for index, hint in enumerate(hints)))
    except (ProviderOutputError, TypeError):
        structure = False
    checks.append(criterion("three bounded hints and canonical identity", "PASS" if structure else "FAIL",
                            "API-delivered hints satisfy the existing validator" if structure
                            else "Hint batch, length, or identity is invalid"))
    if not structure:
        return {"structure": "FAIL", "syntax": None, "quality": checks,
                "human_review": ["Inspect invalid hint response"]}
    if any("```" in hint or "`" in hint or re.search(r"\b(?:def|return|for\s*\(|while\s*\()\b", hint)
           for hint in hints):
        checks.append(criterion("no code or executable pseudocode", "FAIL", "Code-like text detected"))
    else:
        checks.append(criterion("no code or executable pseudocode", "PASS",
                                "No obvious code-like text; manual leakage review remains necessary"))
    question_status = "PASS" if all(hint.endswith("?") for hint in hints) else "NEEDS_HUMAN_REVIEW"
    checks.append(criterion("short questions", question_status,
                            "All three end as questions" if question_status == "PASS"
                            else "At least one hint is not phrased as a question"))
    if any(hint in SHORT_FALLBACK_HINTS for hint in hints):
        checks.append(criterion("specificity", "NEEDS_HUMAN_REVIEW",
                                "At least one generic safety fallback reached the user"))
    if case.slug == "two-sum" and case.approach_id == "brute-force" and any(
        re.search(r"(?:check|compare) (?:each|every) (?:possible )?pair", hint, re.IGNORECASE)
        for hint in hints[:2]
    ):
        checks.append(criterion("early solution leakage", "NEEDS_HUMAN_REVIEW",
                                "An early hint may state the brute-force pair-search procedure"))
    checks.append(criterion("progression, approach fidelity, beginner clarity, and leakage",
                            "NEEDS_HUMAN_REVIEW",
                            "Read all three hints in order; keywords cannot prove teaching quality"))
    return {"structure": "PASS", "syntax": None, "quality": checks,
            "human_review": ["Hint progression, specificity, canonical approach, and solution leakage"]}


def evaluate_starter(payload: dict, case, template: str, output_dir) -> dict:
    checks: list[dict] = []
    code = payload.get("code")
    try:
        structure = (_identity(payload, case) and
                     payload.get("policyVersion") == 3 and
                     isinstance(code, str) and
                     validate_starter_code(code, template, case.language, case.level) == code.strip())
    except (ProviderOutputError, KeyError, TypeError):
        structure = False
    checks.append(criterion("API identity, signature, and unfinished scaffold", "PASS" if structure else "FAIL",
                            "Existing starter validator passed" if structure else "Starter response invalid"))
    if not structure:
        return {"structure": "FAIL", "syntax": None, "quality": checks,
                "human_review": ["Inspect rejected starter response"]}
    syntax = check_syntax(code, case.language, output_dir)
    checks.append(criterion("syntax or compilation", syntax["status"], syntax["summary"]))
    if payload.get("usedFallback") or not payload.get("isAiGenerated"):
        checks.append(criterion("live AI scaffold", "FAIL",
                                "Endpoint used an offline fallback after the Groq attempt"))
    comment_lines = [line.strip() for line in code.splitlines()
                     if line.lstrip().startswith(("#", "//"))]
    if (case.slug == "two-sum" and case.approach_id == "hash-map" and case.level == 3 and
            sum(bool(re.search(r"TODO.*(?:if|return|store).*(?:seen|complement)", line, re.I))
                for line in comment_lines) >= 2):
        checks.append(criterion("algorithm recipe in comments", "FAIL",
                                "TODO comments state the central lookup, return, and storage decisions"))
    if sum(bool(re.search(r"^//\s*(?:const|let|var)\s+\w+\s*=", line))
           for line in comment_lines) >= 2:
        checks.append(criterion("commented-out implementation", "FAIL",
                                "Multiple executable assignments are provided as comments"))
    checks.append(criterion("useful setup, central TODOs, and approach fidelity",
                            "NEEDS_HUMAN_REVIEW",
                            "Validator checks obvious leaks; inspect whether this level teaches the selected approach"))
    return {"structure": "PASS", "syntax": syntax, "quality": checks,
            "human_review": ["Useful setup, approach fidelity, central unfinished work, and leakage"]}


EXPECTED_TIME = {
    ("two-sum", "brute-force"): r"n\s*(?:\^|\*\*)\s*2|n\s*²",
    ("two-sum", "hash-map"): r"O\s*\(\s*n\s*\)",
    ("3sum", "sort-and-two-pointers"): r"n\s*(?:\^|\*\*)\s*2|n\s*²",
    ("binary-search", "binary-search"): r"log\s*n",
    ("valid-parentheses", "stack"): r"O\s*\(\s*n\s*\)",
    ("longest-substring-without-repeating-characters", "sliding-window-set"): r"O\s*\(\s*n\s*\)",
    ("reverse-linked-list", "iterative-pointers"): r"O\s*\(\s*n\s*\)",
}


def evaluate_solution(payload: dict, case, template: str, output_dir) -> dict:
    checks: list[dict] = []
    try:
        structure = (_identity(payload, case) and payload.get("isAiGenerated") is True and
                     validate_solution(payload, template, case.language)["code"] == payload.get("code", "").strip())
    except (ProviderOutputError, TypeError, KeyError):
        structure = False
    checks.append(criterion("API identity, signatures, and completed fields", "PASS" if structure else "FAIL",
                            "Existing full-solution validator passed" if structure else "Full-solution response invalid"))
    if not structure:
        return {"structure": "FAIL", "syntax": None, "quality": checks,
                "human_review": ["Inspect invalid full solution"]}
    code = payload["code"]
    syntax = check_syntax(code, case.language, output_dir)
    checks.append(criterion("syntax or compilation", syntax["status"], syntax["summary"]))
    expected = EXPECTED_TIME.get((case.slug, case.approach_id))
    time_text = payload.get("timeComplexity", "")
    if expected and re.search(expected, time_text, re.IGNORECASE):
        checks.append(criterion("reported time complexity", "NEEDS_HUMAN_REVIEW",
                                "Matches the expected broad order; compare it with actual code"))
    else:
        checks.append(criterion("reported time complexity", "NEEDS_HUMAN_REVIEW",
                                "Expected order is absent or this approach needs manual assessment"))
    if case.slug == "two-sum" and case.approach_id == "brute-force":
        suspect = re.search(r"\b(?:unordered_map|HashMap|Map\s*<|new\s+Map|dict\s*\()", code)
        checks.append(criterion("brute-force approach fidelity", "NEEDS_HUMAN_REVIEW" if suspect else "PASS",
                                "Map-like implementation detected" if suspect else "No obvious map substitution"))
    else:
        checks.append(criterion("canonical approach fidelity", "NEEDS_HUMAN_REVIEW",
                                "Inspect algorithm and data structures against selected approach"))
    if case.slug == "3sum" and re.search(r"O\s*\(\s*1\s*\)", payload.get("spaceComplexity", ""), re.I):
        if (case.language == "python" and "nums.sort(" in code) or (
            case.language == "cpp" and re.search(r"\b(?:std::)?sort\s*\(", code)
        ):
            checks.append(criterion("sorting auxiliary space", "FAIL",
                                    "O(1) auxiliary-space claim omits the sorting implementation's worst-case space"))
    checks.append(criterion("explanation and auxiliary-space accuracy", "NEEDS_HUMAN_REVIEW",
                            "Nonempty fields are validated; semantic accuracy needs review"))
    return {"structure": "PASS", "syntax": syntax, "quality": checks,
            "human_review": ["Approach fidelity, complexity, explanation, and edge-case completeness"]}


def evaluate_progression(records: list[dict]) -> None:
    """Compare complete level trios; attach heuristics without pretending to prove pedagogy."""
    groups: dict[tuple[str, str, str], dict[int, dict]] = {}
    for record in records:
        case = record["case"]
        if case["feature"] == "starter" and record.get("response"):
            groups.setdefault((case["slug"], case["approach_id"], case["language"]), {})[
                case["level"]] = record
    for trio in groups.values():
        if len(trio) != 3:
            continue
        codes = [trio[level]["response"].get("code", "") for level in (1, 2, 3)]
        if not all(codes):
            continue
        distinct = len(set(codes)) == 3
        executable_lines = [sum(bool(line.strip()) and not line.lstrip().startswith(("#", "//", "*"))
                                for line in code.splitlines()) for code in codes]
        increasing = executable_lines[0] < executable_lines[1] < executable_lines[2]
        for level in (1, 2, 3):
            record = trio[level]
            result = record["validation"]
            result["quality"].append(criterion(
                "three-level progression", "FAIL" if not distinct else "NEEDS_HUMAN_REVIEW",
                "Identical code at two levels" if not distinct else
                f"Executable line counts {executable_lines}; " +
                ("increasing depth is plausible" if increasing else "depth is not monotonically increasing")
            ))
            if not distinct:
                record["failure_categories"].append("pedagogical_quality")
            else:
                result["human_review"].append("Compare all three levels for meaningful progression")
        if trio[1]["case"]["slug"] == "min-stack" and trio[1]["case"]["language"] == "javascript":
            initial_state = set(re.findall(r"this\.(\w+)\s*=\s*\[\]", codes[0]))
            if initial_state and any(not initial_state.issubset(
                set(re.findall(r"this\.(\w+)\s*=\s*\[\]", code))
            ) for code in codes[1:]):
                for record in trio.values():
                    record["validation"]["quality"].append(criterion(
                        "consistent state across levels", "FAIL",
                        "A later level replaces the earlier level's core storage instead of building on it"
                    ))
                    record["failure_categories"] = sorted(set(record["failure_categories"] +
                                                              ["pedagogical_quality"]))
