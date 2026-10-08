"""Curated learning scaffolds, authored independently of full solutions.

Bodies for levels 2 and 3 are stored per canonical problem/approach/language.
Only signatures and fail-loud placeholders are shared. No solution is imported,
truncated, or transformed to produce starter code.
"""
from textwrap import indent

from app.llm.base import STARTER_LEVEL_NAMES, SUPPORTED_STARTER_LANGUAGES


SUPPORTED_LANGUAGES = SUPPORTED_STARTER_LANGUAGES
LEVEL_NAMES = STARTER_LEVEL_NAMES


class UnsupportedStarterLanguageError(ValueError):
    pass


class UnsupportedGuidanceLevelError(ValueError):
    pass


# Each pair contains (level 2 body, level 3 body), without the shared signature.
STARTER_BODIES = {
    ("two-sum", "brute-force"): {
        "python": (
            "n = len(nums)\n# TODO: choose two different indices and compare their sum.",
            "n = len(nums)\nfor i in range(n):\n    for j in range(i + 1, n):\n        # TODO: check the pair and return its indices when it matches.\n        pass",
        ),
        "java": (
            "int n = nums.length;\n// TODO: choose two different indices and compare their sum.",
            "int n = nums.length;\nfor (int i = 0; i < n; i++) {\n    for (int j = i + 1; j < n; j++) {\n        // TODO: check the pair and return its indices when it matches.\n    }\n}",
        ),
        "javascript": (
            "const n = nums.length;\n// TODO: choose two different indices and compare their sum.",
            "const n = nums.length;\nfor (let i = 0; i < n; i++) {\n    for (let j = i + 1; j < n; j++) {\n        // TODO: check the pair and return its indices when it matches.\n    }\n}",
        ),
        "cpp": (
            "int n = nums.size();\n// TODO: choose two different indices and compare their sum.",
            "int n = nums.size();\nfor (int i = 0; i < n; i++) {\n    for (int j = i + 1; j < n; j++) {\n        // TODO: check the pair and return its indices when it matches.\n    }\n}",
        ),
    },
    ("two-sum", "hash-map"): {
        "python": (
            "seen = {}\n# TODO: iterate through nums and use the map.",
            "seen = {}\nfor i, value in enumerate(nums):\n    complement = target - value\n    # TODO: determine whether the complement has already been seen.\n    # TODO: return matching indices, or record the current value and index.",
        ),
        "java": (
            "Map<Integer, Integer> seen = new HashMap<>();\n// TODO: iterate through nums and use the map.",
            "Map<Integer, Integer> seen = new HashMap<>();\nfor (int i = 0; i < nums.length; i++) {\n    int complement = target - nums[i];\n    // TODO: determine whether the complement has already been seen.\n    // TODO: return matching indices, or record the current value and index.\n}",
        ),
        "javascript": (
            "const seen = new Map();\n// TODO: iterate through nums and use the map.",
            "const seen = new Map();\nfor (let i = 0; i < nums.length; i++) {\n    const complement = target - nums[i];\n    // TODO: determine whether the complement has already been seen.\n    // TODO: return matching indices, or record the current value and index.\n}",
        ),
        "cpp": (
            "unordered_map<int, int> seen;\n// TODO: iterate through nums and use the map.",
            "unordered_map<int, int> seen;\nfor (int i = 0; i < nums.size(); i++) {\n    int complement = target - nums[i];\n    // TODO: determine whether the complement has already been seen.\n    // TODO: return matching indices, or record the current value and index.\n}",
        ),
    },
    ("valid-parentheses", "replace-pairs"): {
        "python": (
            "previous = None\n# TODO: repeatedly remove adjacent matching bracket pairs.",
            "previous = None\nwhile previous != s:\n    previous = s\n    # TODO: remove (), [], and {} from s during this pass.\n# TODO: decide validity from the remaining string.",
        ),
        "java": (
            'String previous;\n// TODO: repeatedly remove adjacent matching bracket pairs.',
            'String previous;\ndo {\n    previous = s;\n    // TODO: remove (), [], and {} from s during this pass.\n} while (!s.equals(previous));\n// TODO: decide validity from the remaining string.',
        ),
        "javascript": (
            "let previous;\n// TODO: repeatedly remove adjacent matching bracket pairs.",
            "let previous;\ndo {\n    previous = s;\n    // TODO: remove (), [], and {} from s during this pass.\n} while (s !== previous);\n// TODO: decide validity from the remaining string.",
        ),
        "cpp": (
            "string previous;\n// TODO: repeatedly remove adjacent matching bracket pairs.",
            "string previous;\ndo {\n    previous = s;\n    // TODO: find and erase (), [], and {} from s during this pass.\n} while (s != previous);\n// TODO: decide validity from the remaining string.",
        ),
    },
    ("valid-parentheses", "stack"): {
        "python": (
            "stack = []\npairs = {')': '(', ']': '[', '}': '{'}\n# TODO: use the stack to track unmatched opening brackets.",
            "stack = []\npairs = {')': '(', ']': '[', '}': '{'}\nfor ch in s:\n    if ch in pairs.values():\n        # TODO: remember this opening bracket.\n        pass\n    else:\n        # TODO: reject missing/mismatched openers, then consume the match.\n        pass\n# TODO: decide whether any unmatched openers remain.",
        ),
        "java": (
            "Deque<Character> stack = new ArrayDeque<>();\nMap<Character, Character> pairs = Map.of(')', '(', ']', '[', '}', '{');\n// TODO: use the stack to track unmatched opening brackets.",
            "Deque<Character> stack = new ArrayDeque<>();\nMap<Character, Character> pairs = Map.of(')', '(', ']', '[', '}', '{');\nfor (char ch : s.toCharArray()) {\n    if (pairs.containsValue(ch)) {\n        // TODO: remember this opening bracket.\n    } else {\n        // TODO: reject missing/mismatched openers, then consume the match.\n    }\n}\n// TODO: decide whether any unmatched openers remain.",
        ),
        "javascript": (
            "const stack = [];\nconst pairs = {')': '(', ']': '[', '}': '{'};\n// TODO: use the stack to track unmatched opening brackets.",
            "const stack = [];\nconst pairs = {')': '(', ']': '[', '}': '{'};\nfor (const ch of s) {\n    if (ch === '(' || ch === '[' || ch === '{') {\n        // TODO: remember this opening bracket.\n    } else {\n        // TODO: reject missing/mismatched openers, then consume the match.\n    }\n}\n// TODO: decide whether any unmatched openers remain.",
        ),
        "cpp": (
            "stack<char> open;\nunordered_map<char, char> pairs = {{')', '('}, {']', '['}, {'}', '{'}};\n// TODO: use the stack to track unmatched opening brackets.",
            "stack<char> open;\nunordered_map<char, char> pairs = {{')', '('}, {']', '['}, {'}', '{'}};\nfor (char ch : s) {\n    if (ch == '(' || ch == '[' || ch == '{') {\n        // TODO: remember this opening bracket.\n    } else {\n        // TODO: reject missing/mismatched openers, then consume the match.\n    }\n}\n// TODO: decide whether any unmatched openers remain.",
        ),
    },
    ("longest-substring-without-repeating-characters", "brute-force-substrings"): {
        "python": (
            "best = 0\n# TODO: test candidate substrings with a fresh set for each candidate.",
            "best = 0\nfor left in range(len(s)):\n    for right in range(left, len(s)):\n        seen = set()\n        valid = True\n        for i in range(left, right + 1):\n            # TODO: detect duplicates, update seen, and reject invalid candidates.\n            pass\n        # TODO: update best only for a valid candidate.\n# TODO: return the best length.",
        ),
        "java": (
            "int best = 0;\n// TODO: test candidate substrings with a fresh set for each candidate.",
            "int best = 0;\nfor (int left = 0; left < s.length(); left++) {\n    for (int right = left; right < s.length(); right++) {\n        Set<Character> seen = new HashSet<>();\n        boolean valid = true;\n        for (int i = left; i <= right; i++) {\n            // TODO: detect duplicates, update seen, and reject invalid candidates.\n        }\n        // TODO: update best only for a valid candidate.\n    }\n}\n// TODO: return the best length.",
        ),
        "javascript": (
            "let best = 0;\n// TODO: test candidate substrings with a fresh set for each candidate.",
            "let best = 0;\nfor (let left = 0; left < s.length; left++) {\n    for (let right = left; right < s.length; right++) {\n        const seen = new Set();\n        let valid = true;\n        for (let i = left; i <= right; i++) {\n            // TODO: detect duplicates, update seen, and reject invalid candidates.\n        }\n        // TODO: update best only for a valid candidate.\n    }\n}\n// TODO: return the best length.",
        ),
        "cpp": (
            "int best = 0;\n// TODO: test candidate substrings with a fresh set for each candidate.",
            "int best = 0;\nfor (int left = 0; left < s.size(); left++) {\n    for (int right = left; right < s.size(); right++) {\n        unordered_set<char> seen;\n        bool valid = true;\n        for (int i = left; i <= right; i++) {\n            // TODO: detect duplicates, update seen, and reject invalid candidates.\n        }\n        // TODO: update best only for a valid candidate.\n    }\n}\n// TODO: return the best length.",
        ),
    },
    ("longest-substring-without-repeating-characters", "sliding-window-set"): {
        "python": (
            "seen = set()\nleft = 0\nbest = 0\n# TODO: maintain a duplicate-free window using seen.",
            "seen = set()\nleft = 0\nbest = 0\nfor right, ch in enumerate(s):\n    while ch in seen:\n        # TODO: remove the leftmost character and advance left.\n        raise NotImplementedError('Complete the window-shrinking step')\n    # TODO: add ch to the window and update best.\n# TODO: return the best length.",
        ),
        "java": (
            "Set<Character> seen = new HashSet<>();\nint left = 0;\nint best = 0;\n// TODO: maintain a duplicate-free window using seen.",
            "Set<Character> seen = new HashSet<>();\nint left = 0;\nint best = 0;\nfor (int right = 0; right < s.length(); right++) {\n    char ch = s.charAt(right);\n    while (seen.contains(ch)) {\n        // TODO: remove the leftmost character and advance left.\n        throw new UnsupportedOperationException(\"Complete the window-shrinking step\");\n    }\n    // TODO: add ch to the window and update best.\n}\n// TODO: return the best length.",
        ),
        "javascript": (
            "const seen = new Set();\nlet left = 0;\nlet best = 0;\n// TODO: maintain a duplicate-free window using seen.",
            "const seen = new Set();\nlet left = 0;\nlet best = 0;\nfor (let right = 0; right < s.length; right++) {\n    const ch = s[right];\n    while (seen.has(ch)) {\n        // TODO: remove the leftmost character and advance left.\n        throw new Error('Complete the window-shrinking step');\n    }\n    // TODO: add ch to the window and update best.\n}\n// TODO: return the best length.",
        ),
        "cpp": (
            "unordered_set<char> seen;\nint left = 0;\nint best = 0;\n// TODO: maintain a duplicate-free window using seen.",
            "unordered_set<char> seen;\nint left = 0;\nint best = 0;\nfor (int right = 0; right < s.size(); right++) {\n    char ch = s[right];\n    while (seen.count(ch)) {\n        // TODO: remove the leftmost character and advance left.\n        throw logic_error(\"Complete the window-shrinking step\");\n    }\n    // TODO: add ch to the window and update best.\n}\n// TODO: return the best length.",
        ),
    },
    ("longest-substring-without-repeating-characters", "sliding-window-index-map"): {
        "python": (
            "last_seen = {}\nleft = 0\nbest = 0\n# TODO: use last-seen indices to move the window boundary.",
            "last_seen = {}\nleft = 0\nbest = 0\nfor right, ch in enumerate(s):\n    if ch in last_seen and last_seen[ch] >= left:\n        # TODO: move left past the previous occurrence without moving backward.\n        pass\n    # TODO: record the current index and update best.\n# TODO: return the best length.",
        ),
        "java": (
            "Map<Character, Integer> lastSeen = new HashMap<>();\nint left = 0;\nint best = 0;\n// TODO: use last-seen indices to move the window boundary.",
            "Map<Character, Integer> lastSeen = new HashMap<>();\nint left = 0;\nint best = 0;\nfor (int right = 0; right < s.length(); right++) {\n    char ch = s.charAt(right);\n    if (lastSeen.containsKey(ch) && lastSeen.get(ch) >= left) {\n        // TODO: move left past the previous occurrence without moving backward.\n    }\n    // TODO: record the current index and update best.\n}\n// TODO: return the best length.",
        ),
        "javascript": (
            "const lastSeen = new Map();\nlet left = 0;\nlet best = 0;\n// TODO: use last-seen indices to move the window boundary.",
            "const lastSeen = new Map();\nlet left = 0;\nlet best = 0;\nfor (let right = 0; right < s.length; right++) {\n    const ch = s[right];\n    if (lastSeen.has(ch) && lastSeen.get(ch) >= left) {\n        // TODO: move left past the previous occurrence without moving backward.\n    }\n    // TODO: record the current index and update best.\n}\n// TODO: return the best length.",
        ),
        "cpp": (
            "unordered_map<char, int> lastSeen;\nint left = 0;\nint best = 0;\n// TODO: use last-seen indices to move the window boundary.",
            "unordered_map<char, int> lastSeen;\nint left = 0;\nint best = 0;\nfor (int right = 0; right < s.size(); right++) {\n    char ch = s[right];\n    if (lastSeen.count(ch) && lastSeen[ch] >= left) {\n        // TODO: move left past the previous occurrence without moving backward.\n    }\n    // TODO: record the current index and update best.\n}\n// TODO: return the best length.",
        ),
    },
}

SIGNATURES = {
    "two-sum": {
        "python": "def twoSum(self, nums, target):",
        "java": "public int[] twoSum(int[] nums, int target)",
        "javascript": "var twoSum = function(nums, target)",
        "cpp": "vector<int> twoSum(vector<int>& nums, int target)",
    },
    "valid-parentheses": {
        "python": "def isValid(self, s):",
        "java": "public boolean isValid(String s)",
        "javascript": "var isValid = function(s)",
        "cpp": "bool isValid(string s)",
    },
    "longest-substring-without-repeating-characters": {
        "python": "def lengthOfLongestSubstring(self, s):",
        "java": "public int lengthOfLongestSubstring(String s)",
        "javascript": "var lengthOfLongestSubstring = function(s)",
        "cpp": "int lengthOfLongestSubstring(string s)",
    },
}


def wrap_scaffold(slug, language, body, level):
    signature = SIGNATURES[slug][language]
    if language == "python":
        body += '\nraise NotImplementedError("Complete the TODOs")'
        return "class Solution:\n    " + signature + "\n" + indent(body, "        ")
    if language == "java":
        body += '\nthrow new UnsupportedOperationException("Complete the TODOs");'
        imports = "import java.util.*;\n\n" if level > 1 else ""
        return imports + "class Solution {\n    " + signature + " {\n" + indent(body, "        ") + "\n    }\n}"
    if language == "javascript":
        body += '\nthrow new Error("Complete the TODOs");'
        return signature + " {\n" + indent(body, "    ") + "\n};"
    body += '\nthrow logic_error("Complete the TODOs");'
    includes = "#include <vector>\n#include <string>\n#include <stdexcept>\n"
    if level > 1:
        includes += "#include <unordered_map>\n#include <unordered_set>\n#include <stack>\n"
    return includes + "using namespace std;\n\nclass Solution {\npublic:\n    " + signature + " {\n" + indent(body, "        ") + "\n    }\n};"


def generate_starter_code(problem, approach, language, level):
    language = language.lower()
    if language not in SUPPORTED_LANGUAGES:
        raise UnsupportedStarterLanguageError(language)
    if type(level) is not int or level not in LEVEL_NAMES:
        raise UnsupportedGuidanceLevelError(level)
    templates = STARTER_BODIES[(problem["slug"], approach["id"])]
    if level == 1:
        comment = "#" if language == "python" else "//"
        body = f"{comment} TODO: implement the selected approach."
    else:
        body = templates[language][level - 2]
    return {
        "slug": problem["slug"],
        "approachId": approach["id"],
        "language": language,
        "level": level,
        "levelName": LEVEL_NAMES[level],
        "isAiGenerated": False,
        "code": wrap_scaffold(problem["slug"], language, body, level),
        "notice": "Curated starter code, not a full solution. Complete the TODOs and replace the placeholder exceptions before running.",
    }
