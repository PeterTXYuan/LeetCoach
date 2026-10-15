"""Offline, deterministic guidance derived from canonical DB context."""
import re

from app.llm.base import ProviderUnavailableError, validate_hints, validate_starter_code
from app.llm.solution_validation import validate_solution
from app.services.solution_service import MOCK_SOLUTIONS


class MockLLMProvider:
    is_ai_generated = False

    def generate_hints(self, context: dict) -> list[str]:
        approach = context["approach"]
        steps = approach.get("thinkingSteps", [])
        quote = approach.get("recognitionSignals", {}).get("quote")
        hints = [
            "What detail tells you whether an answer is valid?",
            f"Why might “{quote}” matter here?" if quote else
            "Which part of the input could narrow your choices?",
            steps[0] if steps else "What is one small check you could try next?",
        ]
        return validate_hints(hints)

    def generate_starter_code(self, context: dict, language: str, level: int) -> str:
        template = context["problem"]["submissionTemplate"]["code"]
        approach = context["approach"]
        slug = context["problem"]["slug"]
        if slug == "min-stack":
            return _min_stack_scaffold(template, approach["id"], language, level)
        comment = "#" if language == "python" else "//"
        steps = approach["thinkingSteps"]
        lines = _mock_setup(slug, approach["pattern"].lower(), approach["id"], language)
        if level == 1:
            next_step = steps[1] if approach["id"] in {"sort-and-two-pointers", "running-minimum",
                                                      "rolling-dynamic-programming", "iterative-pointers"} else steps[0]
            lines.append(f"{comment} TODO: {next_step}")
        if level >= 2:
            signature = next(line for line in template.splitlines() if "(" in line)
            args = signature.split("(", 1)[1].split(")", 1)[0].split(",")
            first = re.search(r"[A-Za-z][A-Za-z0-9_]*$", args[0].strip())
            parameter = first.group() if first else "n"
            if parameter == "self" and len(args) > 1:
                parameter = args[1].split(":", 1)[0].strip()
            flow = _mock_guided_flow if level == 2 else _mock_control_flow
            loop = flow(language, parameter, template, comment, steps, approach["pattern"], approach["id"])
            lines.extend(loop)
        failure = {"python": 'raise NotImplementedError("Complete the TODOs")',
                   "java": 'throw new UnsupportedOperationException("Complete the TODOs");',
                   "javascript": 'throw new Error("Complete the TODOs");',
                   "cpp": 'throw logic_error("Complete the TODOs");'}[language]
        lines.append(failure)
        indentation = "        " if language == "python" else "        " if language in ("java", "cpp") else "    "
        body = "\n".join(indentation + line if line else "" for line in lines)
        if language == "python":
            code = template.replace("        pass", body)
        else:
            code = template.replace("{\n\n", "{\n" + body + "\n", 1)
        code = _with_imports(code, language)
        return validate_starter_code(code, template, language, level)

    def generate_solution(self, context: dict, language: str) -> dict[str, str]:
        key = (context["problem"]["slug"], context["approach"]["id"])
        curated = MOCK_SOLUTIONS.get(key)
        if curated is None or language not in curated["code"]:
            raise ProviderUnavailableError("No curated offline full solution for this approach")
        template = context["problem"]["submissionTemplate"]["code"]
        code = _canonical_mock_solution(curated["code"][language], template, language)
        return validate_solution({
            "code": code, "explanation": curated["explanation"],
            "timeComplexity": curated["timeComplexity"],
            "spaceComplexity": curated["spaceComplexity"],
        }, template, language)


def _canonical_mock_solution(code: str, template: str, language: str) -> str:
    """Keep legacy curated algorithms while restoring the DB's exact submission entry point."""
    if language == "python":
        signature = next(line for line in template.splitlines() if line.strip().startswith("def "))
        code = re.sub(r"(?m)^\s*def\s+[^\n]+", signature, code, count=1)
        needed = [name for name in ("List", "Optional") if f"{name}[" in signature]
        if needed:
            code = "from typing import " + ", ".join(needed) + "\n\n" + code
    elif language == "java" and re.search(r"(?<![.\w])(?:Map|HashMap|Deque|ArrayDeque|Set)<", code):
        code = "import java.util.*;\n\n" + code
    elif language == "cpp":
        headers = ["vector", "string", "unordered_map", "stack", "algorithm"]
        needed = [header for header in headers if re.search(rf"\b{header}\b", code)]
        code = "\n".join(f"#include <{header}>" for header in needed) + "\nusing namespace std;\n\n" + code
    return code


def _with_imports(code: str, language: str) -> str:
    if language == "python":
        needed = [name for name in ("List", "Optional") if f"{name}[" in code]
        if needed:
            return "from typing import " + ", ".join(needed) + "\n\n" + code
    if language == "java" and re.search(r"(?<![.\w])(?:List|Map|Set|Deque)<", code):
        return "import java.util.*;\n\n" + code
    if language == "cpp":
        headers = ["stdexcept"]
        for name, header in (("vector<", "vector"), ("string", "string"),
                             ("unordered_map<", "unordered_map"), ("unordered_set<", "unordered_set"),
                             ("stack<", "stack"), ("queue<", "queue"), ("sort(", "algorithm"),
                             ("isalnum(", "cctype"), ("pair<", "utility")):
            if name in code:
                headers.append(header)
        return "\n".join(f"#include <{header}>" for header in headers) + "\nusing namespace std;\n\n" + code
    return code


def _mock_setup(slug: str, pattern: str, approach_id: str, language: str) -> list[str]:
    """A few typed, approach-appropriate starting variables; no solution logic."""
    if slug == "3sum" and approach_id == "sort-and-two-pointers":
        return [{"python": "nums.sort()", "java": "java.util.Arrays.sort(nums);",
                 "javascript": "nums.sort((a, b) => a - b);",
                 "cpp": "sort(nums.begin(), nums.end());"}[language],
                {"python": "results = []",
                 "java": "java.util.List<java.util.List<Integer>> results = new java.util.ArrayList<>();",
                 "javascript": "const results = [];", "cpp": "vector<vector<int>> results;"}[language]]
    if slug == "3sum" and approach_id == "brute-force":
        return [{"python": "results = []", "java": "java.util.List<java.util.List<Integer>> results = new java.util.ArrayList<>();",
                 "javascript": "const results = [];", "cpp": "vector<vector<int>> results;"}[language]]
    if approach_id == "binary-search-complement":
        return [{"python": "search_start = 0", "java": "int searchStart = 0;",
                 "javascript": "let searchStart = 0;", "cpp": "int searchStart = 0;"}[language]]
    if approach_id == "memoized-recursion":
        return [{"python": "memo = {}", "java": "java.util.Map<Integer, Integer> memo = new java.util.HashMap<>();",
                 "javascript": "const memo = new Map();", "cpp": "unordered_map<int, int> memo;"}[language]]
    if approach_id == "rolling-dynamic-programming":
        return [{"python": "previous, current = 1, 1", "java": "int previous = 1, current = 1;",
                 "javascript": "let previous = 1, current = 1;", "cpp": "int previous = 1, current = 1;"}[language]]
    if slug == "merge-two-sorted-lists":
        return [{"python": "first, second = list1, list2",
                 "java": "ListNode first = list1, second = list2;",
                 "javascript": "let first = list1, second = list2;",
                 "cpp": "auto first = list1, second = list2;"}[language]]
    if "map" in pattern or "frequency" in pattern:
        if slug == "group-anagrams":
            return [{"python": "groups = {}",
                     "java": "java.util.Map<String, java.util.List<String>> groups = new java.util.HashMap<>();",
                     "javascript": "const groups = new Map();",
                     "cpp": "unordered_map<string, vector<string>> groups;"}[language]]
        key_type = "Integer" if slug == "two-sum" else "Character"
        cpp_key = "int" if slug == "two-sum" else "char"
        return [{"python": "seen = {}",
                 "java": f"java.util.Map<{key_type}, Integer> seen = new java.util.HashMap<>();",
                 "javascript": "const seen = new Map();",
                 "cpp": f"unordered_map<{cpp_key}, int> seen;"}[language]]
    if "set" in pattern:
        key_type = "Integer" if slug == "contains-duplicate" else "Character"
        cpp_key = "int" if slug == "contains-duplicate" else "char"
        return [{"python": "seen = set()", "java": f"java.util.Set<{key_type}> seen = new java.util.HashSet<>();",
                 "javascript": "const seen = new Set();", "cpp": f"unordered_set<{cpp_key}> seen;"}[language]]
    if "stack" in pattern:
        key_type = "Character" if slug == "valid-parentheses" else "Integer"
        cpp_key = "char" if slug == "valid-parentheses" else "int"
        return [{"python": "pending = []",
                 "java": f"java.util.Deque<{key_type}> pending = new java.util.ArrayDeque<>();",
                 "javascript": "const pending = [];", "cpp": f"stack<{cpp_key}> pending;"}[language]]
    if "sliding window" in pattern:
        return [{"python": "best = 0", "java": "int best = 0;",
                 "javascript": "let best = 0;", "cpp": "int best = 0;"}[language]]
    if "two pointers" in pattern or "binary search" in pattern:
        return [{"python": "left = 0", "java": "int left = 0;",
                 "javascript": "let left = 0;", "cpp": "int left = 0;"}[language]]
    if "tree bfs" in pattern:
        return {"python": ["queue = []"],
                "java": ["java.util.Deque<TreeNode> queue = new java.util.ArrayDeque<>();"],
                "javascript": ["const queue = [];"],
                "cpp": ["queue<TreeNode*> pending;"]}[language]
    if slug == "reverse-linked-list" and approach_id == "iterative-pointers":
        return [{"python": "previous, current = None, head",
                 "java": "ListNode previous = null, current = head;",
                 "javascript": "let previous = null, current = head;",
                 "cpp": "ListNode *previous = nullptr, *current = head;"}[language]]
    if slug == "number-of-islands":
        count = {"python": "islands = 0", "java": "int islands = 0;",
                 "javascript": "let islands = 0;", "cpp": "int islands = 0;"}[language]
        if approach_id == "breadth-first-flood-fill":
            structure = {"python": "queue = []", "java": "java.util.Deque<int[]> queue = new java.util.ArrayDeque<>();",
                         "javascript": "const queue = [];", "cpp": "queue<pair<int, int>> pending;"}[language]
        else:
            structure = {"python": "visited = set()",
                         "java": "boolean[][] visited = new boolean[grid.length][grid[0].length];",
                         "javascript": "const visited = grid.map(row => Array(row.length).fill(false));",
                         "cpp": "vector<vector<bool>> visited(grid.size(), vector<bool>(grid[0].size(), false));"}[language]
        return [count, structure]
    if slug == "valid-anagram" and approach_id == "sorting":
        prepared = {"python": ["sorted_s = sorted(s)"],
                    "java": ["char[] sortedS = s.toCharArray();", "java.util.Arrays.sort(sortedS);"],
                    "javascript": ["const sortedS = [...s].sort();"],
                    "cpp": ["string sortedS = s;", "sort(sortedS.begin(), sortedS.end());"]}[language]
        return prepared
    if approach_id == "clean-and-reverse":
        return [{"python": "cleaned = []", "java": "StringBuilder cleaned = new StringBuilder();",
                 "javascript": "const cleaned = [];", "cpp": "string cleaned;"}[language]]
    if approach_id == "replace-pairs":
        return [{"python": "working = s", "java": "String working = s;",
                 "javascript": "let working = s;", "cpp": "string working = s;"}[language]]
    if approach_id == "running-minimum":
        return [{"python": "lowest = prices[0]", "java": "int lowest = prices[0];",
                 "javascript": "let lowest = prices[0];", "cpp": "int lowest = prices[0];"}[language]]
    if approach_id in {"brute-force", "brute-force-substrings", "brute-force-windows"}:
        if slug == "best-time-to-buy-and-sell-stock" or "substring" in slug or "replacement" in slug:
            return [{"python": "best = 0", "java": "int best = 0;",
                     "javascript": "let best = 0;", "cpp": "int best = 0;"}[language]]
        source = "nums" if slug in {"two-sum", "contains-duplicate"} else "s"
        size = {"python": f"len({source})", "java": f"{source}.length" if source == "nums" else "s.length()",
                "javascript": f"{source}.length", "cpp": f"{source}.size()"}[language]
        return [{"python": f"count = {size}", "java": f"int count = {size};",
                 "javascript": f"const count = {size};", "cpp": f"int count = {size};"}[language]]
    if approach_id in {"linear-scan", "forward-scan"}:
        if slug == "daily-temperatures":
            return [{"python": "answer = [0] * len(temperatures)",
                     "java": "int[] answer = new int[temperatures.length];",
                     "javascript": "const answer = Array(temperatures.length).fill(0);",
                     "cpp": "vector<int> answer(temperatures.size(), 0);"}[language]]
        return [{"python": "answer = -1", "java": "int answer = -1;",
                 "javascript": "let answer = -1;", "cpp": "int answer = -1;"}[language]]
    if approach_id == "recursive-unwind":
        return [{"python": "next_node = head.next if head else None",
                 "java": "ListNode nextNode = head == null ? null : head.next;",
                 "javascript": "const nextNode = head ? head.next : null;",
                 "cpp": "ListNode* nextNode = head ? head->next : nullptr;"}[language]]
    if "tree dfs" in pattern:
        return [{"python": "left_child = root.left if root else None",
                 "java": "TreeNode leftChild = root == null ? null : root.left;",
                 "javascript": "const leftChild = root ? root.left : null;",
                 "cpp": "TreeNode* leftChild = root ? root->left : nullptr;"}[language]]
    # All curated approaches have a specific starting state above. Fail loudly if
    # a new approach is added without a useful first step.
    raise ValueError(f"No Kickstart setup for {slug}/{approach_id}")


def _min_stack_scaffold(template: str, approach_id: str, language: str, level: int) -> str:
    comment = "#" if language == "python" else "//"
    is_paired = approach_id == "paired-minimums"
    if is_paired:
        constructor = {
            "python": ["self.pairs = []"],
            "java": [f"{comment} The shared stack stores value/minimum pairs."],
            "javascript": ["this.pairs = [];"],
            "cpp": [f"{comment} The shared stack stores value/minimum pairs."],
        }[language]
    else:
        constructor = {
            "python": ["self.values = []"],
            "java": [f"{comment} The shared stack stores values."],
            "javascript": ["this.values = [];"],
            "cpp": [f"{comment} The shared stack stores values."],
        }[language]
    constructor.append(f"{comment} TODO: decide how operations use this shared state.")
    failure = {"python": 'raise NotImplementedError("Complete the TODOs")',
               "java": 'throw new UnsupportedOperationException("Complete the TODOs");',
               "javascript": 'throw new Error("Complete the TODOs");',
               "cpp": 'throw logic_error("Complete the TODOs");'}[language]
    if language == "python":
        first = "\n".join("        " + line for line in constructor)
        code = template.replace("        pass", first, 1)
        code = code.replace("        pass", "        # TODO: complete this stack operation.\n        " + failure)
    else:
        indentation = "    " if language == "javascript" else "        "
        first = "\n".join(indentation + line for line in constructor)
        code = template.replace("{\n\n", "{\n" + first + "\n", 1)
        code = code.replace("{\n\n", "{\n" + indentation + f"{comment} TODO: complete this stack operation.\n" + indentation + failure + "\n")
    if language == "java":
        fields = ("    private java.util.Deque<int[]> pairs = new java.util.ArrayDeque<>();\n"
                  if is_paired else
                  "    private java.util.Deque<Integer> values = new java.util.ArrayDeque<>();\n")
        code = code.replace("class MinStack {\n", "class MinStack {\n" + fields, 1)
    if language == "cpp":
        fields = "    vector<pair<int, int>> pairs;\n" if is_paired else "    vector<int> values;\n"
        code = code.replace("public:\n", "public:\n" + fields, 1)
    if level >= 2:
        tasks = ({
            "push": "decide which minimum belongs beside the new value",
            "pop": "remove the latest value/minimum pair",
            "top": "read the value from the latest pair",
            "getMin": "read the minimum from the latest pair",
        } if is_paired else {
            "push": "store the incoming value",
            "pop": "remove the latest value",
            "top": "read the latest stored value",
            "getMin": "scan stored values and update the smallest one",
        })
        current_method = None
        revised = []
        for line in code.splitlines():
            method = re.search(r"\b(push|pop|top|getMin)\s*(?:=\s*function\s*)?\(", line)
            if method:
                current_method = method.group(1)
            if current_method and "TODO: complete this stack operation." in line:
                line = line.replace("complete this stack operation", tasks[current_method])
                indent = line[:len(line) - len(line.lstrip())]
                if current_method == "getMin" and not is_paired:
                    if language == "python":
                        line = indent + "smallest = None\n" + line
                        if level == 3:
                            line += "\n" + indent + "for value in self.values:\n" + indent + "    # TODO: update smallest when this value is lower.\n" + indent + "    pass"
                    else:
                        state = {"java": "Integer smallest = null;", "javascript": "let smallest = null;",
                                 "cpp": "int smallest = 0;"}[language]
                        line = indent + state + "\n" + line
                        if level == 3:
                            collection = {"java": "values", "javascript": "this.values", "cpp": "values"}[language]
                            header = {"java": f"for (int value : {collection}) {{",
                                      "javascript": f"for (const value of {collection}) {{",
                                      "cpp": f"for (int value : {collection}) {{"}[language]
                            line += "\n" + indent + header + "\n" + indent + "    // TODO: update smallest when this value is lower.\n" + indent + "}"
                elif current_method == "push" and is_paired:
                    previous = {
                        "python": "previous_pair = self.pairs[-1] if self.pairs else None",
                        "java": "int[] previousPair = pairs.peek();",
                        "javascript": "const previousPair = this.pairs.length ? this.pairs[this.pairs.length - 1] : null;",
                        "cpp": "const pair<int, int>* previousPair = pairs.empty() ? nullptr : &pairs.back();",
                    }[language]
                    line = indent + previous + "\n" + line
                    if level == 3:
                        if language == "python":
                            line += "\n" + indent + "if previous_pair is not None:\n" + indent + "    # TODO: compare val with the earlier minimum.\n" + indent + "    pass"
                        else:
                            condition = "previousPair" if language == "javascript" else "previousPair != null" if language == "java" else "previousPair != nullptr"
                            line += "\n" + indent + f"if ({condition}) {{\n" + indent + "    // TODO: compare val with the earlier minimum.\n" + indent + "}"
            revised.append(line)
        code = "\n".join(revised)
    return validate_starter_code(_with_imports(code, language), template, language, level)


def _mock_guided_flow(language: str, parameter: str, template: str, comment: str,
                      steps: list[str], pattern: str, approach_id: str) -> list[str]:
    """One useful control-flow decision beyond Kickstart, without the core operations."""
    todo = f"{comment} TODO: {steps[1] if len(steps) > 1 else steps[0]}"
    def shell(header: str, inside: list[str] | None = None) -> list[str]:
        body = inside or []
        if language == "python":
            return [header, *["    " + line for line in body], "    " + todo,
                    *([] if body else ["    pass"])]
        return [header, *["    " + line for line in body], "    " + todo, "}"]

    if approach_id == "hash-map" and parameter == "nums":
        todo = f"{comment} TODO: Determine which earlier value could complete the target pair."
        current = {"python": "current = nums[index]", "java": "int current = nums[index];",
                   "javascript": "const current = nums[index];", "cpp": "int current = nums[index];"}[language]
        header = {"python": "for index in range(len(nums)):",
                  "java": "for (int index = 0; index < nums.length; index++) {",
                  "javascript": "for (let index = 0; index < nums.length; index++) {",
                  "cpp": "for (int index = 0; index < nums.size(); index++) {"}[language]
        return shell(header, [current])
    if approach_id == "sort-and-two-pointers" and parameter == "nums":
        header = {"python": "for first in range(len(nums) - 2):",
                  "java": "for (int first = 0; first < nums.length - 2; first++) {",
                  "javascript": "for (let first = 0; first < nums.length - 2; first++) {",
                  "cpp": "for (int first = 0; first < nums.size() - 2; first++) {"}[language]
        pointers = {"python": "left, right = first + 1, len(nums) - 1",
                    "java": "int left = first + 1, right = nums.length - 1;",
                    "javascript": "let left = first + 1, right = nums.length - 1;",
                    "cpp": "int left = first + 1, right = nums.size() - 1;"}[language]
        return shell(header, [pointers])
    if approach_id == "binary-search-complement" and parameter == "numbers":
        header = {"python": "for first in range(len(numbers) - 1):",
                  "java": "for (int first = 0; first < numbers.length - 1; first++) {",
                  "javascript": "for (let first = 0; first < numbers.length - 1; first++) {",
                  "cpp": "for (int first = 0; first < numbers.size() - 1; first++) {"}[language]
        return shell(header)
    if approach_id == "memoized-recursion" and parameter == "n":
        return shell("if n <= 2:" if language == "python" else "if (n <= 2) {")
    if approach_id == "sorting" and parameter == "s":
        other = {"python": "sorted_t = sorted(t)", "java": "char[] sortedT = t.toCharArray();",
                 "javascript": "const sortedT = [...t].sort();", "cpp": "string sortedT = t;"}[language]
        prepare = {"python": [], "java": ["java.util.Arrays.sort(sortedT);"],
                   "javascript": [], "cpp": ["sort(sortedT.begin(), sortedT.end());"]}[language]
        return [other, *prepare, todo]
    if approach_id == "replace-pairs":
        return shell("while working:" if language == "python" else "while (!working.empty()) {" if language == "cpp" else "while (working.length() > 0) {" if language == "java" else "while (working.length > 0) {")
    if "tree bfs" in pattern.lower():
        enqueue = {"python": ["if root is not None:", "    queue.append(root)"],
                   "java": ["if (root != null) queue.add(root);"],
                   "javascript": ["if (root) queue.push(root);"],
                   "cpp": ["if (root) pending.push(root);"]}[language]
        header = {"python": "while queue:", "java": "while (!queue.isEmpty()) {",
                  "javascript": "while (queue.length > 0) {", "cpp": "while (!pending.empty()) {"}[language]
        return [*enqueue, *shell(header)]
    if "recursion" in pattern.lower() or "tree dfs" in pattern.lower():
        header = f"if {parameter} is None:" if language == "python" else (
            f"if ({parameter} == {'nullptr' if language == 'cpp' else 'null'}) {{")
        return shell(header)
    if approach_id == "iterative-merge":
        header = "while first is not None and second is not None:" if language == "python" else (
            f"while (first != {'nullptr' if language == 'cpp' else 'null'} && second != {'nullptr' if language == 'cpp' else 'null'}) {{")
        return shell(header)
    if approach_id == "iterative-pointers":
        header = "while current is not None:" if language == "python" else (
            f"while (current != {'nullptr' if language == 'cpp' else 'null'}) {{")
        return shell(header)
    limit = "n" if parameter == "n" else {"python": f"len({parameter})",
        "java": f"{parameter}.length" if "[]" in template else f"{parameter}.length()",
        "javascript": f"{parameter}.length", "cpp": f"{parameter}.size()"}[language]
    if "binary search" in pattern.lower():
        right = {"python": f"right = {limit} - 1", "java": f"int right = {limit} - 1;",
                 "javascript": f"let right = {limit} - 1;", "cpp": f"int right = {limit} - 1;"}[language]
        return [right, *shell("while left <= right:" if language == "python" else "while (left <= right) {")]
    if "two pointers" in pattern.lower():
        right = {"python": f"right = {limit} - 1", "java": f"int right = {limit} - 1;",
                 "javascript": f"let right = {limit} - 1;", "cpp": f"int right = {limit} - 1;"}[language]
        return [right, *shell("while left < right:" if language == "python" else "while (left < right) {")]
    if parameter == "grid":
        return shell(f"for row in range({limit}):" if language == "python" else
                     f"for ({'let' if language == 'javascript' else 'int'} row = 0; row < {limit}; row++) {{")
    if parameter in {"root", "head", "list1"}:
        header = f"while {parameter} is not None:" if language == "python" else (
            f"while ({parameter} != {'nullptr' if language == 'cpp' else 'null'}) {{")
        return shell(header)
    if parameter == "n":
        return shell("for step in range(3, n + 1):" if language == "python" else
                     f"for ({'let' if language == 'javascript' else 'int'} step = 3; step <= n; step++) {{")
    header = f"for index in range({limit}):" if language == "python" else (
        f"for ({'let' if language == 'javascript' else 'int'} index = 0; index < {limit}; index++) {{")
    return shell(header)


def _mock_control_flow(language: str, parameter: str, template: str, comment: str,
                       steps: list[str], pattern: str, approach_id: str) -> list[str]:
    """A deliberately unfinished control-flow outline; the student supplies decisions."""
    next_step = steps[1] if len(steps) > 1 else steps[0]
    if approach_id == "hash-map" and parameter == "nums":
        if language == "python":
            return ["for index, current in enumerate(nums):", "    complement = target - current",
                    f"    {comment} TODO: decide whether the complement was seen earlier.",
                    f"    {comment} TODO: construct indices or remember this value and position.", "    pass"]
        if language == "java":
            return ["for (int index = 0; index < nums.length; index++) {", "    int current = nums[index];",
                    "    int complement = target - current;",
                    f"    {comment} TODO: check for an earlier matching value and form the indices.",
                    f"    {comment} TODO: otherwise remember this value and its position.", "}"]
        if language == "javascript":
            return ["for (let index = 0; index < nums.length; index++) {", "    const current = nums[index];",
                    "    const complement = target - current;",
                    f"    {comment} TODO: check for an earlier matching value and form the indices.",
                    f"    {comment} TODO: otherwise remember this value and its position.", "}"]
        return ["for (int index = 0; index < nums.size(); index++) {", "    int current = nums[index];",
                "    int complement = target - current;",
                f"    {comment} TODO: check for an earlier matching value and form the indices.",
                f"    {comment} TODO: otherwise remember this value and its position.", "}"]
    if approach_id == "sort-and-two-pointers" and parameter == "nums":
        if language == "python":
            return ["for first in range(len(nums) - 2):",
                    "    if first > 0 and nums[first] == nums[first - 1]:",
                    "        # TODO: decide how to skip a repeated first value.",
                    "        raise NotImplementedError('Handle repeated starting values')",
                    "    left, right = first + 1, len(nums) - 1", "    while left < right:",
                    "        total = nums[first] + nums[left] + nums[right]",
                    "        if total == 0:",
                    "            # TODO: record a triplet and handle duplicates before moving pointers.",
                    "            raise NotImplementedError('Complete a matching triplet')",
                    "        elif total < 0:",
                    "            # TODO: move the pointer that could increase the sum.",
                    "            raise NotImplementedError('Move a pointer for a small sum')",
                    "        else:",
                    "            # TODO: move the pointer that could decrease the sum.",
                    "            raise NotImplementedError('Move a pointer for a large sum')"]
        if language == "java":
            return ["for (int first = 0; first < nums.length - 2; first++) {",
                    "    int left = first + 1, right = nums.length - 1;", "    while (left < right) {",
                    "        int total = nums[first] + nums[left] + nums[right];",
                    "        if (total == 0) {",
                    f"            {comment} TODO: record a triplet and handle duplicate values.",
                    "            throw new UnsupportedOperationException(\"Complete a matching triplet\");",
                    "        } else if (total < 0) {",
                    f"            {comment} TODO: move the pointer that could increase the sum.",
                    "            throw new UnsupportedOperationException(\"Move a pointer\");",
                    "        } else {",
                    f"            {comment} TODO: move the pointer that could decrease the sum.",
                    "            throw new UnsupportedOperationException(\"Move a pointer\");",
                    "        }", "    }", "}"]
        if language == "javascript":
            return ["for (let first = 0; first < nums.length - 2; first++) {",
                    "    let left = first + 1, right = nums.length - 1;", "    while (left < right) {",
                    "        const total = nums[first] + nums[left] + nums[right];",
                    "        if (total === 0) {",
                    f"            {comment} TODO: record a triplet and handle duplicate values.",
                    "            throw new Error(\"Complete a matching triplet\");",
                    "        } else if (total < 0) {",
                    f"            {comment} TODO: move the pointer that could increase the sum.",
                    "            throw new Error(\"Move a pointer\");",
                    "        } else {",
                    f"            {comment} TODO: move the pointer that could decrease the sum.",
                    "            throw new Error(\"Move a pointer\");",
                    "        }", "    }", "}"]
        return ["for (int first = 0; first < nums.size() - 2; first++) {",
                "    int left = first + 1, right = nums.size() - 1;", "    while (left < right) {",
                "        int total = nums[first] + nums[left] + nums[right];",
                "        if (total == 0) {",
                f"            {comment} TODO: record a triplet and handle duplicate values.",
                "            throw logic_error(\"Complete a matching triplet\");",
                "        } else if (total < 0) {",
                f"            {comment} TODO: move the pointer that could increase the sum.",
                "            throw logic_error(\"Move a pointer\");",
                "        } else {",
                f"            {comment} TODO: move the pointer that could decrease the sum.",
                "            throw logic_error(\"Move a pointer\");",
                "        }", "    }", "}"]
    if approach_id == "binary-search-complement" and parameter == "numbers":
        if language == "python":
            return ["for first in range(len(numbers) - 1):", "    search_start = first + 1",
                    "    right = len(numbers) - 1", "    while search_start <= right:",
                    "        mid = (search_start + right) // 2",
                    f"        {comment} TODO: compare with the complement and choose a search half or answer.",
                    "        raise NotImplementedError('Complete the search decision')"]
        if language == "java":
            return ["for (int first = 0; first < numbers.length - 1; first++) {",
                    "    searchStart = first + 1;", "    int right = numbers.length - 1;",
                    "    while (searchStart <= right) {", "        int mid = searchStart + (right - searchStart) / 2;",
                    f"        {comment} TODO: compare with the complement and choose a search half or answer.",
                    "        throw new UnsupportedOperationException(\"Complete the search decision\");", "    }", "}"]
        if language == "javascript":
            return ["for (let first = 0; first < numbers.length - 1; first++) {",
                    "    searchStart = first + 1;", "    let right = numbers.length - 1;",
                    "    while (searchStart <= right) {", "        const mid = Math.floor((searchStart + right) / 2);",
                    f"        {comment} TODO: compare with the complement and choose a search half or answer.",
                    "        throw new Error(\"Complete the search decision\");", "    }", "}"]
        return ["for (int first = 0; first < numbers.size() - 1; first++) {",
                "    searchStart = first + 1;", "    int right = numbers.size() - 1;",
                "    while (searchStart <= right) {", "        int mid = searchStart + (right - searchStart) / 2;",
                f"        {comment} TODO: compare with the complement and choose a search half or answer.",
                "        throw logic_error(\"Complete the search decision\");", "    }", "}"]
    if approach_id == "brute-force" and parameter == "nums" and "threeSum" in template:
        limit = {"python": "len(nums)", "java": "nums.length", "javascript": "nums.length",
                 "cpp": "nums.size()"}[language]
        if language == "python":
            return [f"for first in range({limit}):", f"    for second in range(first + 1, {limit}):",
                    f"        for third in range(second + 1, {limit}):",
                    "            # TODO: decide whether this triplet qualifies and is new.", "            pass"]
        kind = "let" if language == "javascript" else "int"
        return [f"for ({kind} first = 0; first < {limit}; first++) {{",
                f"    for ({kind} second = first + 1; second < {limit}; second++) {{",
                f"        for ({kind} third = second + 1; third < {limit}; third++) {{",
                f"            {comment} TODO: decide whether this triplet qualifies and is new.",
                "        }", "    }", "}"]
    if approach_id in {"brute-force-substrings", "brute-force-windows"} and parameter == "s":
        limit = {"python": "len(s)", "java": "s.length()", "javascript": "s.length",
                 "cpp": "s.size()"}[language]
        if language == "python":
            return [f"for start in range({limit}):", f"    for end in range(start, {limit}):",
                    "        # TODO: decide whether this window qualifies and update best.", "        pass"]
        kind = "let" if language == "javascript" else "int"
        return [f"for ({kind} start = 0; start < {limit}; start++) {{",
                f"    for ({kind} end = start; end < {limit}; end++) {{",
                f"        {comment} TODO: decide whether this window qualifies and update best.",
                "    }", "}"]
    if approach_id == "running-minimum" and parameter == "prices":
        limit = {"python": "len(prices)", "java": "prices.length", "javascript": "prices.length",
                 "cpp": "prices.size()"}[language]
        if language == "python":
            return ["best = 0", f"for index in range({limit}):", "    current = prices[index]",
                    "    # TODO: compare a sale today with the lowest earlier price.",
                    "    # TODO: update the lowest price for later days.", "    pass"]
        kind = "let" if language == "javascript" else "int"
        current = "const" if language == "javascript" else "int"
        return [f"{kind} best = 0;", f"for ({kind} index = 0; index < {limit}; index++) {{",
                f"    {current} today = prices[index];",
                f"    {comment} TODO: compare a sale today with the lowest earlier price.",
                f"    {comment} TODO: update the lowest price for later days.", "}"]
    if approach_id in {"depth-first-flood-fill", "breadth-first-flood-fill"} and parameter == "grid":
        row_limit = {"python": "len(grid)", "java": "grid.length", "javascript": "grid.length",
                     "cpp": "grid.size()"}[language]
        col_limit = {"python": "len(grid[row])", "java": "grid[row].length",
                     "javascript": "grid[row].length", "cpp": "grid[row].size()"}[language]
        search = "queue" if language != "cpp" else "pending"
        if language == "python":
            result = [f"for row in range({row_limit}):", f"    for col in range({col_limit}):",
                      "        if grid[row][col] == '1':",
                      "            # TODO: decide whether this land starts a new island.",
                      "            raise NotImplementedError('Complete island discovery')"]
            if approach_id == "breadth-first-flood-fill":
                result += [f"        while {search}:",
                           "            # TODO: visit neighboring land and add it to the queue.",
                           "            raise NotImplementedError('Complete breadth-first exploration')"]
            else:
                result += ["        # TODO: explore the island's neighbors recursively."]
            return result
        kind = "let" if language == "javascript" else "int"
        cell = "grid[row][col] == '1'" if language in {"java", "cpp"} else "grid[row][col] === '1'"
        result = [f"for ({kind} row = 0; row < {row_limit}; row++) {{",
                  f"    for ({kind} col = 0; col < {col_limit}; col++) {{",
                  f"        if ({cell}) {{",
                  f"            {comment} TODO: decide whether this land starts a new island.",
                  "            " + {"java": 'throw new UnsupportedOperationException("Complete island discovery");',
                           "javascript": 'throw new Error("Complete island discovery");',
                           "cpp": 'throw logic_error("Complete island discovery");'}[language],
                  "        }"]
        if approach_id == "breadth-first-flood-fill":
            condition = {"java": "!queue.isEmpty()", "javascript": "queue.length > 0",
                         "cpp": "!pending.empty()"}[language]
            result += [f"        while ({condition}) {{",
                       f"            {comment} TODO: visit neighboring land and add it to the queue.",
                       "            " + {"java": 'throw new UnsupportedOperationException("Complete breadth-first exploration");',
                                "javascript": 'throw new Error("Complete breadth-first exploration");',
                                "cpp": 'throw logic_error("Complete breadth-first exploration");'}[language],
                       "        }"]
        else:
            result += [f"        {comment} TODO: explore the island's neighbors recursively."]
        return result + ["    }", "}"]
    if approach_id == "memoized-recursion" and parameter == "n":
        if language == "python":
            return ["if n <= 2:", f"    {comment} TODO: decide the base-case count.",
                    "    raise NotImplementedError('Complete the base case')",
                    "if n in memo:", "    # TODO: use the saved count for this staircase.",
                    "    raise NotImplementedError('Complete memo reuse')",
                    f"{comment} TODO: reuse or combine smaller answers, then store the result."]
        failure = {"java": 'throw new UnsupportedOperationException("Complete the base case");',
                   "javascript": 'throw new Error("Complete the base case");',
                   "cpp": 'throw logic_error("Complete the base case");'}[language]
        lookup = {"java": "memo.containsKey(n)", "javascript": "memo.has(n)",
                  "cpp": "memo.count(n) > 0"}[language]
        return ["if (n <= 2) {", f"    {comment} TODO: decide the base-case count.",
                f"    {failure}", "}",
                f"if ({lookup}) {{", f"    {comment} TODO: use the saved count for this staircase.",
                f"    {failure}", "}",
                f"{comment} TODO: reuse or combine smaller answers, then store the result."]
    if approach_id == "rolling-dynamic-programming" and parameter == "n":
        if language == "python":
            return ["for step in range(3, n + 1):", "    next_count = previous + current",
                    "    # TODO: advance the two rolling counts without losing either one.",
                    "    raise NotImplementedError('Complete the count update')"]
        kind = "let" if language == "javascript" else "int"
        failure = {"java": 'throw new UnsupportedOperationException("Complete the count update");',
                   "javascript": 'throw new Error("Complete the count update");',
                   "cpp": 'throw logic_error("Complete the count update");'}[language]
        return [f"for ({kind} step = 3; step <= n; step++) {{",
                f"    {kind} nextCount = previous + current;",
                f"    {comment} TODO: advance the two rolling counts without losing either one.",
                "    " + failure, "}"]
    if approach_id == "sorting" and parameter == "s":
        if language == "python":
            return ["if len(s) != len(t):", "    # TODO: decide the length-mismatch result.",
                    "    raise NotImplementedError('Handle differing lengths')",
                    "# TODO: compare the prepared character orders."]
        header = {"java": "if (s.length() != t.length()) {", "javascript": "if (s.length !== t.length) {",
                  "cpp": "if (s.size() != t.size()) {"}[language]
        return [header, f"    {comment} TODO: decide the length-mismatch result.",
                "    " + {"java": 'throw new UnsupportedOperationException("Handle differing lengths");',
                         "javascript": 'throw new Error("Handle differing lengths");',
                         "cpp": 'throw logic_error("Handle differing lengths");'}[language], "}",
                f"{comment} TODO: compare the prepared character orders."]
    if approach_id == "clean-and-reverse":
        condition = {"python": "if char.isalnum():", "java": "if (Character.isLetterOrDigit(ch)) {",
                     "javascript": "if (/[a-z0-9]/i.test(ch)) {", "cpp": "if (isalnum(ch)) {"}[language]
        header = {"python": "for char in s:", "java": "for (char ch : s.toCharArray()) {",
                  "javascript": "for (const ch of s) {", "cpp": "for (char ch : s) {"}[language]
        if language == "python":
            return [header, "    " + condition, "        # TODO: normalize and collect this character.", "        pass",
                    "# TODO: compare the normalized text with its reverse."]
        return [header, "    " + condition, f"        {comment} TODO: normalize and collect this character.",
                "    }", "}", f"{comment} TODO: compare the normalized text with its reverse."]
    if approach_id == "replace-pairs":
        previous = {"python": "previous_length = len(working)", "java": "int previousLength = working.length();",
                    "javascript": "const previousLength = working.length;", "cpp": "int previousLength = working.size();"}[language]
        header = "while working:" if language == "python" else (
            "while (!working.empty()) {" if language == "cpp" else
            "while (working.length() > 0) {" if language == "java" else "while (working.length > 0) {")
        if language == "python":
            return [header, "    " + previous, "    # TODO: remove a valid adjacent pair, if any.",
                    "    raise NotImplementedError('Complete pair removal')"]
        return [header, "    " + previous, f"    {comment} TODO: remove a valid adjacent pair, if any.",
                "    " + {"java": 'throw new UnsupportedOperationException("Complete pair removal");',
                         "javascript": 'throw new Error("Complete pair removal");',
                         "cpp": 'throw logic_error("Complete pair removal");'}[language], "}"]
    if "sliding window" in pattern.lower() and parameter == "s":
        if language == "python":
            return ["left = 0", "for right, current in enumerate(s):",
                    f"    {comment} TODO: decide when and how to shrink the window.",
                    f"    {comment} TODO: update the state and best length.", "    raise NotImplementedError('Complete the window decisions')"]
        if language == "java":
            return ["int left = 0;", "for (int right = 0; right < s.length(); right++) {",
                    "    char current = s.charAt(right);",
                    f"    {comment} TODO: decide when to shrink and how to update state and best length.",
                    "    throw new UnsupportedOperationException(\"Complete the window decisions\");", "}"]
        if language == "javascript":
            return ["let left = 0;", "for (let right = 0; right < s.length; right++) {",
                    "    const current = s[right];",
                    f"    {comment} TODO: decide when to shrink and how to update state and best length.",
                    "    throw new Error(\"Complete the window decisions\");", "}"]
        return ["int left = 0;", "for (int right = 0; right < s.size(); right++) {",
                "    char current = s[right];",
                f"    {comment} TODO: decide when to shrink and how to update state and best length.",
                "    throw logic_error(\"Complete the window decisions\");", "}"]
    if "tree bfs" in pattern.lower() and parameter == "root":
        if language == "python":
            return ["if root is not None:", "    queue.append(root)", "depth = 0", "while queue:",
                    "    level_size = len(queue)", f"    {comment} TODO: process one full level and enqueue its children.",
                    "    raise NotImplementedError('Complete level traversal')"]
        if language == "java":
            return ["if (root != null) queue.add(root);", "int depth = 0;", "while (!queue.isEmpty()) {",
                    "    int levelSize = queue.size();",
                    f"    {comment} TODO: process one full level and enqueue its children.",
                    "    throw new UnsupportedOperationException(\"Complete level traversal\");", "}"]
        if language == "javascript":
            return ["if (root) queue.push(root);", "let depth = 0;", "while (queue.length > 0) {",
                    "    const levelSize = queue.length;",
                    f"    {comment} TODO: process one full level and enqueue its children.",
                    "    throw new Error(\"Complete level traversal\");", "}"]
        return ["if (root) pending.push(root);", "int depth = 0;", "while (!pending.empty()) {",
                "    int levelSize = pending.size();",
                f"    {comment} TODO: process one full level and enqueue its children.",
                "    throw logic_error(\"Complete level traversal\");", "}"]
    if approach_id == "iterative-merge" and parameter == "list1":
        if language == "python":
            return ["while first is not None and second is not None:",
                    "    if first.val <= second.val:",
                    f"        {comment} TODO: connect and advance the first list.",
                    "        raise NotImplementedError('Complete the first merge branch')",
                    "    else:",
                    f"        {comment} TODO: connect and advance the second list.",
                    "        raise NotImplementedError('Complete the second merge branch')"]
        null = "nullptr" if language == "cpp" else "null"
        failure = {"java": 'throw new UnsupportedOperationException("Complete the merge decision");',
                   "javascript": 'throw new Error("Complete the merge decision");',
                   "cpp": 'throw logic_error("Complete the merge decision");'}[language]
        first_value = "first->val" if language == "cpp" else "first.val"
        second_value = "second->val" if language == "cpp" else "second.val"
        return [f"while (first != {null} && second != {null}) {{",
                f"    if ({first_value} <= {second_value}) {{",
                f"        {comment} TODO: connect and advance the first list.",
                f"        {failure}", "    } else {",
                f"        {comment} TODO: connect and advance the second list.",
                f"        {failure}", "    }", "}"]
    if approach_id == "iterative-pointers" and parameter == "head":
        if language == "python":
            return ["while current is not None:",
                    "    next_node = current.next",
                    f"    {comment} TODO: redirect the link, then advance current and previous.",
                    "    raise NotImplementedError('Complete pointer updates')"]
        null = "nullptr" if language == "cpp" else "null"
        failure = {"java": 'throw new UnsupportedOperationException("Complete pointer updates");',
                   "javascript": 'throw new Error("Complete pointer updates");',
                   "cpp": 'throw logic_error("Complete pointer updates");'}[language]
        saved_next = {"java": "ListNode nextNode = current.next;",
                      "javascript": "const nextNode = current.next;",
                      "cpp": "ListNode* nextNode = current->next;"}[language]
        return [f"while (current != {null}) {{", f"    {saved_next}",
                f"    {comment} TODO: redirect the link, then advance current and previous.",
                f"    {failure}", "}"]
    if approach_id == "recursive-unwind" and parameter == "head":
        if language == "python":
            return ["if head is None or head.next is None:",
                    "    # TODO: choose the unchanged-list result.",
                    "    raise NotImplementedError('Complete the base case')",
                    "rest = self.reverseList(head.next)",
                    "# TODO: reverse this link and return the new head."]
        null = "nullptr" if language == "cpp" else "null"
        call = {"java": "reverseList(head.next)", "javascript": "reverseList(head.next)",
                "cpp": "reverseList(head->next)"}[language]
        kind = "ListNode*" if language == "cpp" else "ListNode" if language == "java" else "const"
        assignment = f"{kind} rest = {call};"
        failure = {"java": 'throw new UnsupportedOperationException("Complete the base case");',
                   "javascript": 'throw new Error("Complete the base case");',
                   "cpp": 'throw logic_error("Complete the base case");'}[language]
        return [f"if (head == {null} || head.next == {null}) {{" if language != "cpp" else
                "if (head == nullptr || head->next == nullptr) {",
                f"    {comment} TODO: choose the unchanged-list result.", "    " + failure, "}",
                assignment, f"{comment} TODO: reverse this link and return the new head."]
    if approach_id == "recursive-merge" and parameter == "list1":
        if language == "python":
            return ["if list1 is None:", "    # TODO: return the remaining second list.",
                    "    raise NotImplementedError('Complete the first base case')",
                    "if list2 is None:", "    # TODO: return the remaining first list.",
                    "    raise NotImplementedError('Complete the second base case')",
                    "if list1.val <= list2.val:",
                    "    # TODO: connect the first node to a recursive merge of the rest.",
                    "    raise NotImplementedError('Complete the merge choice')",
                    "# TODO: handle the second node symmetrically."]
        null = "nullptr" if language == "cpp" else "null"
        first_value = "list1->val" if language == "cpp" else "list1.val"
        second_value = "list2->val" if language == "cpp" else "list2.val"
        failure = {"java": 'throw new UnsupportedOperationException("Complete the merge choice");',
                   "javascript": 'throw new Error("Complete the merge choice");',
                   "cpp": 'throw logic_error("Complete the merge choice");'}[language]
        return [f"if (list1 == {null}) {{", f"    {comment} TODO: use the remaining second list.",
                "    " + failure, "}", f"if (list2 == {null}) {{",
                f"    {comment} TODO: use the remaining first list.", "    " + failure, "}",
                f"if ({first_value} <= {second_value}) {{",
                f"    {comment} TODO: connect the first node to a recursive merge of the rest.",
                "    " + failure, "}", f"{comment} TODO: handle the second node symmetrically."]
    if "tree dfs" in pattern.lower() and parameter == "root":
        if language == "python":
            return ["if root is None:", "    # TODO: return the empty-tree depth.",
                    "    raise NotImplementedError('Complete the base case')",
                    "left_depth = self.maxDepth(root.left)", "right_depth = self.maxDepth(root.right)",
                    "# TODO: combine child depths into this tree's depth."]
        null = "nullptr" if language == "cpp" else "null"
        call = "maxDepth(root->left)" if language == "cpp" else "maxDepth(root.left)"
        other = "maxDepth(root->right)" if language == "cpp" else "maxDepth(root.right)"
        failure = {"java": 'throw new UnsupportedOperationException("Complete the base case");',
                   "javascript": 'throw new Error("Complete the base case");',
                   "cpp": 'throw logic_error("Complete the base case");'}[language]
        kind = "const" if language == "javascript" else "int"
        return [f"if (root == {null}) {{", f"    {comment} TODO: choose the empty-tree depth.",
                "    " + failure, "}", f"{kind} leftDepth = {call};",
                f"{kind} rightDepth = {other};", f"{comment} TODO: combine child depths into this tree's depth."]
    if "recursion" in pattern.lower() or "tree dfs" in pattern.lower():
        if language == "python":
            return [f"if {parameter} is None:", f"    {comment} TODO: choose the base-case result.", "    pass",
                    f"{comment} TODO: decide what the recursive call should return, then {next_step.lower()}"]
        null = "nullptr" if language == "cpp" else "null"
        return [f"if ({parameter} == {null}) {{", f"    {comment} TODO: choose the base-case result.", "}",
                f"{comment} TODO: decide what the recursive call should return, then {next_step.lower()}"]
    if parameter in {"head", "list1", "root"}:
        if language == "python":
            return [f"current = {parameter}", "while current is not None:", f"    {comment} TODO: {next_step}", "    break"]
        if language == "java":
            node_type = "TreeNode" if parameter == "root" else "ListNode"
            return [f"{node_type} current = {parameter};", "while (current != null) {", f"    {comment} TODO: {next_step}", "    break;", "}"]
        return [f"auto current = {parameter};" if language == "cpp" else f"let current = {parameter};",
                "while (current != null) {" if language == "javascript" else "while (current != nullptr) {",
                f"    {comment} TODO: {next_step}", "    break;", "}"]
    if parameter == "n":
        limit = "n"
    else:
        limit = {"python": f"len({parameter})", "java": f"{parameter}.length" if "[]" in template else f"{parameter}.length()",
                 "javascript": f"{parameter}.length", "cpp": f"{parameter}.size()"}[language]
    if "binary search" in pattern.lower():
        end = f"{limit} - 1"
        if language == "python":
            return [f"right = {end}", "while left <= right:",
                    "    mid = (left + right) // 2", f"    {comment} TODO: {next_step}", "    break"]
        int_type = "let" if language == "javascript" else "int"
        return [f"{int_type} right = {end};", "while (left <= right) {",
                f"    {int_type} mid = left + (right - left) / 2;" if language != "javascript" else
                "    const mid = Math.floor((left + right) / 2);",
                f"    {comment} TODO: {next_step}", "    break;", "}"]
    if "two pointers" in pattern.lower() and parameter not in {"head", "list1"}:
        if parameter in {"numbers", "s"}:
            if language == "python":
                values = [f"    left_value, right_value = {parameter}[left], {parameter}[right]"]
            elif language == "java":
                java_value = "numbers[left]" if parameter == "numbers" else "s.charAt(left)"
                java_right = "numbers[right]" if parameter == "numbers" else "s.charAt(right)"
                kind = "int" if parameter == "numbers" else "char"
                values = [f"    {kind} leftValue = {java_value}, rightValue = {java_right};"]
            elif language == "javascript":
                values = [f"    const leftValue = {parameter}[left], rightValue = {parameter}[right];"]
            else:
                kind = "int" if parameter == "numbers" else "char"
                values = [f"    {kind} leftValue = {parameter}[left], rightValue = {parameter}[right];"]
            if language == "python":
                return [f"right = {limit} - 1", "while left < right:", *values,
                        f"    {comment} TODO: {next_step}", "    break"]
            int_type = "let" if language == "javascript" else "int"
            return [f"{int_type} right = {limit} - 1;", "while (left < right) {", *values,
                    f"    {comment} TODO: {next_step}", "    break;", "}"]
        if language == "python":
            return [f"right = {limit} - 1", "while left < right:",
                    f"    {comment} TODO: {next_step}", "    break"]
        int_type = "let" if language == "javascript" else "int"
        return [f"{int_type} right = {limit} - 1;", "while (left < right) {",
                f"    {comment} TODO: {next_step}", "    break;", "}"]
    if "nested loops" in pattern.lower():
        if language == "python":
            return [f"for first in range({limit}):", f"    for second in range(first + 1, {limit}):",
                    f"        {comment} TODO: {next_step}", "        pass"]
        int_type = "let" if language == "javascript" else "int"
        return [f"for ({int_type} first = 0; first < {limit}; first++) {{",
                f"    for ({int_type} second = first + 1; second < {limit}; second++) {{",
                f"        {comment} TODO: {next_step}", "    }", "}"]
    if parameter == "grid":
        inner = {"python": "len(grid[row])", "java": "grid[row].length",
                 "javascript": "grid[row].length", "cpp": "grid[row].size()"}[language]
        if language == "python":
            return [f"for row in range({limit}):", f"    for col in range({inner}):",
                    f"        {comment} TODO: {next_step}", "        pass"]
        int_type = "let" if language == "javascript" else "int"
        return [f"for ({int_type} row = 0; row < {limit}; row++) {{",
                f"    for ({int_type} col = 0; col < {inner}; col++) {{",
                f"        {comment} TODO: {next_step}", "    }", "}"]
    if language == "python":
        return [f"for index in range({limit}):", f"    current = {parameter}[index]",
                f"    {comment} TODO: {next_step}", "    pass"]
    index_type = "let" if language == "javascript" else "int"
    if language == "java":
        kind = "String" if parameter == "strs" else "char" if parameter == "s" else "int"
        value = f"{parameter}.charAt(index)" if parameter == "s" else f"{parameter}[index]"
        current = f"{kind} current = {value};"
    elif language == "cpp":
        kind = "string" if parameter == "strs" else "char" if parameter == "s" else "int"
        current = f"{kind} current = {parameter}[index];"
    else:
        current = f"const current = {parameter}[index];"
    return [f"for ({index_type} index = 0; index < {limit}; index++) {{", "    " + current,
            f"    {comment} TODO: {next_step}", "}"]
