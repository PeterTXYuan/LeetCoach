"""Mock guidance fixtures for the original three fully covered problems.

Stable-data seeding lives separately in app.stable_data. Hint, Starter Code,
and Full Solution routes still use these canonical approach contexts.
"""

PROBLEM_ANALYSES = {
    "two-sum": {
        "slug": "two-sum",
        "approaches": [
            {
                "id": "brute-force",
                "name": "Brute Force",
                "pattern": "Nested Loops",
                "summary": "Compare every possible pair until the target sum is found.",
                "recognitionSignals": {
                    "quote": "two numbers",
                    "bullets": [
                        "The problem asks you to find a pair.",
                        "Trying every possible pair is a simple starting point when you do not yet see a shortcut.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "two numbers such that they add up to target",
                    "bullets": [
                        "For each number x, the other number you need is target - x.",
                        "Repeatedly asking whether a value appeared before is a clue to consider a Hash Map.",
                        "The answer needs indices, so remembering where each value appeared is useful.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "determine if the input string is valid",
                    "bullets": [
                        "The input contains only brackets, and you only need a yes-or-no answer.",
                        "Even a nested group has a small matching pair inside it. This suggests simplifying the string a pair at a time.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "Open brackets must be closed in the correct order.",
                    "bullets": [
                        "The order matters, so counting opening and closing brackets is not enough.",
                        "The last bracket opened must close first. Whenever the newest unfinished item matters first, think about a Stack.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "longest substring",
                    "bullets": [
                        "A substring is a continuous piece of the text, with a start and an end.",
                        "The task asks for the longest piece that passes a simple rule: no repeated characters. Checking all possible pieces is a straightforward baseline.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "without duplicate characters",
                    "bullets": [
                        "The answer is one continuous piece of the text, which is a clue to consider a sliding window.",
                        "A repeated character is what makes a piece stop being valid.",
                        "You need to know which characters are already in that piece. A Set fits this yes-or-no question.",
                    ],
                },
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
                "recognitionSignals": {
                    "quote": "without duplicate characters",
                    "bullets": [
                        "A repeated character limits how far back a valid piece can start.",
                        "Knowing where that character last appeared is more useful than only knowing it appeared. This suggests a Hash Map of characters and positions.",
                    ],
                },
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
