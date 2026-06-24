from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LeetCoach API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|http://localhost(:[0-9]+)?|http://127\.0\.0\.1(:[0-9]+)?)$",
    allow_methods=["GET"],
    allow_headers=["*"],
)

PROBLEM_ANALYSES = {
    "two-sum": {
        "slug": "two-sum",
        "approaches": [
            {
                "id": "brute-force",
                "name": "Brute Force",
                "pattern": "Nested Loops",
                "summary": "Compare every possible pair until the target sum is found.",
                "thinkingSteps": [
                    "Consider all possible pairs of numbers.",
                    "Check whether each pair adds up to the target.",
                    "This approach takes O(n^2) time.",
                ],
            },
            {
                "id": "hash-map",
                "name": "One-pass Hash Map",
                "pattern": "Hash Map",
                "summary": "Store previously visited values so complements can be found quickly.",
                "thinkingSteps": [
                    "For each number, calculate the complement needed to reach the target.",
                    "Check whether the complement was previously stored.",
                    "Store the current number for future lookups.",
                    "This reduces the time complexity to O(n).",
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
                "thinkingSteps": [
                    "A valid innermost pair can be removed without changing the validity of the rest.",
                    "Keep removing adjacent valid pairs like (), [], and {}.",
                    "If the string becomes empty, every bracket found a valid match.",
                    "This is simple to reason about but can repeat a lot of work.",
                ],
            },
            {
                "id": "stack",
                "name": "Stack of Opening Brackets",
                "pattern": "Stack",
                "summary": "Track opening brackets so each closing bracket can match the most recent unresolved opener.",
                "thinkingSteps": [
                    "The order of closing brackets matters, not just their counts.",
                    "The most recent unmatched opening bracket must be closed first.",
                    "Use a stack to remember open brackets and validate each closing bracket.",
                    "At the end, the stack should be empty.",
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
                "thinkingSteps": [
                    "Start by considering every possible start and end position.",
                    "For each substring, check whether any character repeats.",
                    "Track the longest valid substring length found so far.",
                    "This is direct but does repeated validation work.",
                ],
            },
            {
                "id": "sliding-window-set",
                "name": "Sliding Window with Set",
                "pattern": "Sliding Window",
                "summary": "Maintain a moving window of unique characters and shrink it when a duplicate appears.",
                "thinkingSteps": [
                    "Keep a window that represents the current substring without duplicates.",
                    "Expand the right side while characters are unique.",
                    "When a duplicate appears, move the left boundary until the duplicate is removed.",
                    "Update the best length whenever the window is valid.",
                ],
            },
            {
                "id": "sliding-window-index-map",
                "name": "Sliding Window with Last Seen Index",
                "pattern": "Sliding Window + Hash Map",
                "summary": "Jump the left boundary past repeated characters using their most recent positions.",
                "thinkingSteps": [
                    "Store the most recent index where each character appeared.",
                    "When a repeated character is inside the current window, move the left boundary after its previous index.",
                    "Update the character's latest index as you scan.",
                    "This avoids removing characters one by one.",
                ],
            },
        ],
    },
}

UNAVAILABLE_DETAIL = "This problem is not available in the local LeetCoach dataset yet."


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/problems/{slug}")
def get_problem_analysis(slug: str):
    analysis = PROBLEM_ANALYSES.get(slug)

    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)

    return analysis
