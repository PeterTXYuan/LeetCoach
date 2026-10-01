"""Retained seed fixtures; the related-problem endpoint now reads SQLite.

Small, manually curated lists per seeded problem; no ranking or graph logic.

Group placement is editorial (relative practice challenge), while difficulty is
LeetCode's published label. Two Easy problems can differ in challenge.
Titles and difficulty labels checked against leetcode.com/problems/{slug}/.
"""

RELATED_PROBLEMS = {
    "two-sum": {
        "easier": [
            {
                "slug": "running-sum-of-1d-array",
                "title": "Running Sum of 1d Array",
                "difficulty": "Easy",
                "reason": "Warm up with array traversal and a running total.",
            }
        ],
        "similar": [
            {
                "slug": "contains-duplicate",
                "title": "Contains Duplicate",
                "difficulty": "Easy",
                "reason": "Practice remembering values you have already seen.",
            }
        ],
        "harder": [
            {
                "slug": "3sum",
                "title": "3Sum",
                "difficulty": "Medium",
                "reason": "Extend pair finding to triplets while avoiding duplicates.",
            }
        ],
    },
    "valid-parentheses": {
        "easier": [
            {
                "slug": "maximum-nesting-depth-of-the-parentheses",
                "title": "Maximum Nesting Depth of the Parentheses",
                "difficulty": "Easy",
                "reason": "Track one bracket type in an already valid expression.",
            }
        ],
        "similar": [
            {
                "slug": "baseball-game",
                "title": "Baseball Game",
                "difficulty": "Easy",
                "reason": "Use a stack to remember and undo recent operations.",
            }
        ],
        "harder": [
            {
                "slug": "minimum-remove-to-make-valid-parentheses",
                "title": "Minimum Remove to Make Valid Parentheses",
                "difficulty": "Medium",
                "reason": "Go beyond validation by repairing an invalid string.",
            }
        ],
    },
    "longest-substring-without-repeating-characters": {
        "easier": [
            {
                "slug": "longest-continuous-increasing-subsequence",
                "title": "Longest Continuous Increasing Subsequence",
                "difficulty": "Easy",
                "reason": "Track the longest contiguous run with a simpler validity rule.",
            }
        ],
        "similar": [
            {
                "slug": "maximum-sum-of-distinct-subarrays-with-length-k",
                "title": "Maximum Sum of Distinct Subarrays With Length K",
                "difficulty": "Medium",
                "reason": "Maintain distinct values inside a fixed-size window.",
            }
        ],
        "harder": [
            {
                "slug": "minimum-window-substring",
                "title": "Minimum Window Substring",
                "difficulty": "Hard",
                "reason": "Manage character counts while shrinking a valid window.",
            }
        ],
    },
}


def get_related_problems(slug):
    return {"slug": slug, **RELATED_PROBLEMS[slug]}
