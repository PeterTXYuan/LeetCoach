from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.services.related_problem_service import get_related_problems

from app.services.hint_service import (
    get_approach_hints,
    get_primary_approach_hints,
)
from app.services.solution_service import (
    UnsupportedLanguageError,
    generate_approach_solution,
)
from app.services.starter_code_service import (
    UnsupportedStarterLanguageError,
    generate_starter_code,
)

app = FastAPI(title="LeetCoach API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|http://localhost(:[0-9]+)?|http://127\.0\.0\.1(:[0-9]+)?)$",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SolutionRequest(BaseModel):
    language: str


class StarterCodeRequest(BaseModel):
    language: str
    level: int = Field(strict=True, ge=1, le=3)

PROBLEM_ANALYSES = {
    "two-sum": {
        "slug": "two-sum",
        "approaches": [
            {
                "id": "brute-force",
                "name": "Brute Force",
                "pattern": "Nested Loops",
                "summary": "Compare every possible pair until the target sum is found.",
                "isPrimary": False,
                "displayOrder": 1,
                "thinkingSteps": [
                    "Consider every possible pair of indices.",
                    "Check whether each pair reaches the target.",
                    "Recognize that this requires quadratic time.",
                ],
                "hints": [
                    "Start with the most direct way to examine possible pairs.",
                    "How many pairs exist if every number can be matched with every later number?",
                    "Try using two nested loops, while avoiding using the same index twice.",
                ],
            },
            {
                "id": "hash-map",
                "name": "One-pass Hash Map",
                "pattern": "Hash Map",
                "summary": "Remember previously visited values so complements can be found quickly.",
                "isPrimary": True,
                "displayOrder": 2,
                "thinkingSteps": [
                    "For each value, determine the complement needed to reach the target.",
                    "Check whether that complement has already been seen.",
                    "Store the current value for later lookups.",
                ],
                "hints": [
                    "For the current number, what other value would complete the target sum?",
                    "Could remembering previously visited values avoid checking every pair?",
                    "Which data structure supports average constant-time lookup for a previously seen complement?",
                ],
            },
        ],
    },
    "valid-parentheses": {
        "slug": "valid-parentheses",
        "approaches": [
            {
                "id": "replace-pairs",
                "name": "Repeated Pair Removal",
                "pattern": "String Reduction",
                "summary": "Repeatedly remove valid adjacent bracket pairs until no more can be removed.",
                "isPrimary": False,
                "displayOrder": 1,
                "thinkingSteps": [
                    "A valid innermost pair can be removed without changing the validity of the rest.",
                    "Keep removing adjacent valid pairs like (), [], and {}.",
                    "If the string becomes empty, every bracket found a valid match.",
                    "Recognize that repeated string scans can do unnecessary work.",
                ],
                "hints": [
                    "Look for the smallest valid bracket groups that can be resolved first.",
                    "If an adjacent pair is valid, what happens if you remove it and inspect the remaining string?",
                    "Try repeatedly removing (), [], and {} until no more changes are possible.",
                ],
            },
            {
                "id": "stack",
                "name": "Stack of Opening Brackets",
                "pattern": "Stack",
                "summary": "Track opening brackets so each closing bracket can match the most recent unresolved opener.",
                "isPrimary": True,
                "displayOrder": 2,
                "thinkingSteps": [
                    "The order of closing brackets matters, not just their counts.",
                    "The most recent unmatched opening bracket must be closed first.",
                    "Use a stack to remember open brackets and validate each closing bracket.",
                    "At the end, the stack should be empty.",
                ],
                "hints": [
                    "A closing bracket must match the most recent unresolved opening bracket.",
                    "What structure naturally remembers the most recent item that has not been resolved?",
                    "Push opening brackets, and when a closing bracket appears, compare it with the latest stored opener.",
                ],
            },
        ],
    },
    "longest-substring-without-repeating-characters": {
        "slug": "longest-substring-without-repeating-characters",
        "approaches": [
            {
                "id": "brute-force-substrings",
                "name": "Check Every Substring",
                "pattern": "Brute Force",
                "summary": "Generate candidate substrings and test whether each one contains only unique characters.",
                "isPrimary": False,
                "displayOrder": 1,
                "thinkingSteps": [
                    "Start by considering every possible start and end position.",
                    "For each substring, check whether any character repeats.",
                    "Track the longest valid substring length found so far.",
                    "This is direct but does repeated validation work.",
                ],
                "hints": [
                    "Begin with the definition: a candidate answer is any substring with no repeated characters.",
                    "How could you test every possible substring and reject the ones with duplicates?",
                    "Use two boundaries to generate substrings, then use a set to check each candidate.",
                ],
            },
            {
                "id": "sliding-window-set",
                "name": "Sliding Window with Set",
                "pattern": "Sliding Window",
                "summary": "Maintain a moving window of unique characters and shrink it when a duplicate appears.",
                "isPrimary": True,
                "displayOrder": 2,
                "thinkingSteps": [
                    "Keep a window that represents the current substring without duplicates.",
                    "Expand the right side while characters are unique.",
                    "When a duplicate appears, move the left boundary until the duplicate is removed.",
                    "Update the best length whenever the window is valid.",
                ],
                "hints": [
                    "A valid substring can grow until the next character would create a duplicate.",
                    "Can you keep a moving range of characters that is always duplicate-free?",
                    "Use a set for the current window, expand right, and move left while removing duplicates.",
                ],
            },
            {
                "id": "sliding-window-index-map",
                "name": "Sliding Window with Last Seen Index",
                "pattern": "Sliding Window + Hash Map",
                "summary": "Jump the left boundary past repeated characters using their most recent positions.",
                "isPrimary": False,
                "displayOrder": 3,
                "thinkingSteps": [
                    "Store the most recent index where each character appeared.",
                    "When a repeated character is inside the current window, move the left boundary after its previous index.",
                    "Update the character's latest index as you scan.",
                    "This avoids removing characters one by one.",
                ],
                "hints": [
                    "When a duplicate appears, only its most recent position inside the current window matters.",
                    "Could remembering the last index of each character let you skip several left moves at once?",
                    "Store last-seen indices and jump the left boundary to one position after the repeated character.",
                ],
            },
        ],
    },
}

UNAVAILABLE_DETAIL = "This problem is not available in the local LeetCoach dataset yet."
APPROACH_UNAVAILABLE_DETAIL = (
    "This approach is not available for the requested LeetCoach problem."
)


def validate_problem_dataset(problem_data):
    for slug, problem in problem_data.items():
        approaches = problem.get("approaches", [])

        if not approaches:
            raise ValueError(f"Problem '{slug}' must have at least one approach.")

        approach_ids = [approach.get("id") for approach in approaches]
        if len(approach_ids) != len(set(approach_ids)):
            raise ValueError(f"Problem '{slug}' has duplicate approach IDs.")

        primary_count = sum(1 for approach in approaches if approach.get("isPrimary"))
        if primary_count != 1:
            raise ValueError(
                f"Problem '{slug}' must have exactly one primary approach."
            )


validate_problem_dataset(PROBLEM_ANALYSES)


def get_problem_or_404(slug: str):
    problem = PROBLEM_ANALYSES.get(slug)

    if problem is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)

    return problem


def get_approach_or_404(problem, approach_id: str):
    for approach in problem["approaches"]:
        if approach["id"] == approach_id:
            return approach

    raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)


def public_problem_analysis(problem):
    return {
        "slug": problem["slug"],
        "approaches": [
            public_approach(approach)
            for approach in sorted(
                problem["approaches"],
                key=lambda approach: approach["displayOrder"],
            )
        ],
    }


def public_approach(approach):
    return {
        "id": approach["id"],
        "name": approach["name"],
        "pattern": approach["pattern"],
        "summary": approach["summary"],
        "isPrimary": approach["isPrimary"],
        "displayOrder": approach["displayOrder"],
        "thinkingSteps": approach["thinkingSteps"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/problems/{slug}")
def get_problem_analysis(slug: str):
    return public_problem_analysis(get_problem_or_404(slug))


@app.get("/api/problems/{slug}/hints")
def get_problem_hints(slug: str):
    problem = get_problem_or_404(slug)
    approach_id, hints = get_primary_approach_hints(problem)

    return {
        "slug": problem["slug"],
        "approachId": approach_id,
        "hints": hints,
    }


@app.get("/api/problems/{slug}/related")
def get_problem_related(slug: str):
    get_problem_or_404(slug)
    return get_related_problems(slug)


@app.get("/api/problems/{slug}/approaches/{approach_id}/hints")
def get_problem_approach_hints(slug: str, approach_id: str):
    problem = get_problem_or_404(slug)

    try:
        hints = get_approach_hints(problem, approach_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)

    return {
        "slug": problem["slug"],
        "approachId": approach_id,
        "hints": hints,
    }


@app.post("/api/problems/{slug}/approaches/{approach_id}/solution")
def generate_problem_approach_solution(
    slug: str, approach_id: str, request: SolutionRequest
):
    problem = get_problem_or_404(slug)
    approach = get_approach_or_404(problem, approach_id)

    try:
        return generate_approach_solution(problem, approach, request.language)
    except UnsupportedLanguageError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, java, javascript, cpp.",
        )


@app.post("/api/problems/{slug}/approaches/{approach_id}/starter-code")
def get_problem_starter_code(slug: str, approach_id: str, request: StarterCodeRequest):
    problem = get_problem_or_404(slug)
    approach = get_approach_or_404(problem, approach_id)
    try:
        return generate_starter_code(problem, approach, request.language, request.level)
    except UnsupportedStarterLanguageError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, java, javascript, cpp.",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Starter code is not available for this approach yet.")
