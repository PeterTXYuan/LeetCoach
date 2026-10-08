"""Offline, deterministic guidance derived from canonical DB context."""
import re

from app.llm.base import validate_hints, validate_starter_code


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
        if context["problem"]["slug"] == "min-stack":
            return _min_stack_scaffold(template, approach["id"], language, level)
        comment = "#" if language == "python" else "//"
        steps = approach["thinkingSteps"]
        lines = [f"{comment} TODO: implement the selected approach."]
        if level >= 2:
            pattern = approach["pattern"].lower()
            if "map" in pattern or "frequency" in pattern:
                declarations = {"python": "seen = {}", "java": "java.util.Map<Object, Object> seen = new java.util.HashMap<>();",
                                "javascript": "const seen = new Map();", "cpp": "unordered_map<int, int> seen;"}
            elif "set" in pattern:
                declarations = {"python": "seen = set()", "java": "java.util.Set<Object> seen = new java.util.HashSet<>();",
                                "javascript": "const seen = new Set();", "cpp": "unordered_set<int> seen;"}
            elif "stack" in pattern:
                declarations = {"python": "stack = []", "java": "java.util.Deque<Object> stack = new java.util.ArrayDeque<>();",
                                "javascript": "const stack = [];", "cpp": "stack<int> pending;"}
            else:
                declarations = {"python": "position = 0", "java": "int position = 0;",
                                "javascript": "let position = 0;", "cpp": "int position = 0;"}
            lines = [declarations[language], f"{comment} TODO: {steps[0]}"]
        if level == 3:
            signature = next(line for line in template.splitlines() if "(" in line)
            args = signature.split("(", 1)[1].split(")", 1)[0].split(",")
            first = re.search(r"[A-Za-z][A-Za-z0-9_]*$", args[0].strip())
            parameter = first.group() if first else "n"
            if parameter == "self" and len(args) > 1:
                parameter = args[1].split(":", 1)[0].strip()
            loop = _mock_control_flow(language, parameter, template, comment, steps, approach["pattern"], approach["id"])
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
        return validate_starter_code(code, template, language, level)


def _min_stack_scaffold(template: str, approach_id: str, language: str, level: int) -> str:
    comment = "#" if language == "python" else "//"
    is_auxiliary = approach_id == "paired-minimums"
    constructor = [f"{comment} TODO: implement the selected stack approach."]
    if level >= 2:
        constructor = {
            "python": ["self.values = []"],
            "java": ["java.util.Deque<Integer> values = new java.util.ArrayDeque<>();"],
            "javascript": ["this.values = [];"],
            "cpp": ["vector<int> values;"],
        }[language]
        constructor.append(f"{comment} TODO: keep values available to all operations.")
    if level == 3:
        if is_auxiliary:
            constructor.insert(1, {
                "python": "self.minimums = []", "java": "java.util.Deque<Integer> minimums = new java.util.ArrayDeque<>();",
                "javascript": "this.minimums = [];", "cpp": "vector<int> minimums;",
            }[language])
            constructor.append(f"{comment} TODO: keep the minimum tracker in sync on push and pop.")
        else:
            constructor.append(f"{comment} TODO: make getMin scan stored values for the smallest one.")
    failure = {"python": 'raise NotImplementedError("Complete the TODOs")',
               "java": 'throw new UnsupportedOperationException("Complete the TODOs");',
               "javascript": 'throw new Error("Complete the TODOs");',
               "cpp": 'throw logic_error("Complete the TODOs");'}[language]
    constructor.append(failure)
    if language == "python":
        first = "\n".join("        " + line for line in constructor)
        code = template.replace("        pass", first, 1)
        code = code.replace("        pass", "        # TODO: complete this stack operation.\n        " + failure)
    else:
        indentation = "    " if language == "javascript" else "        "
        first = "\n".join(indentation + line for line in constructor)
        code = template.replace("{\n\n", "{\n" + first + "\n", 1)
        code = code.replace("{\n\n", "{\n" + indentation + f"{comment} TODO: complete this stack operation.\n" + indentation + failure + "\n")
    return validate_starter_code(code, template, language, level)


def _mock_control_flow(language: str, parameter: str, template: str, comment: str,
                       steps: list[str], pattern: str, approach_id: str) -> list[str]:
    """A deliberately unfinished control-flow outline; the student supplies decisions."""
    next_step = steps[1] if len(steps) > 1 else steps[0]
    if "recursion" in pattern.lower() or "tree dfs" in pattern.lower():
        if language == "python":
            return [f"if {parameter} is None:", f"    {comment} TODO: choose the base-case result.", "    pass",
                    f"{comment} TODO: {next_step}"]
        null = "nullptr" if language == "cpp" else "null"
        return [f"if ({parameter} == {null}) {{", f"    {comment} TODO: choose the base-case result.", "}",
                f"{comment} TODO: {next_step}"]
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
            return ["left = 0", f"right = {end}", "while left <= right:",
                    "    mid = (left + right) // 2", f"    {comment} TODO: {next_step}", "    break"]
        int_type = "let" if language == "javascript" else "int"
        return [f"{int_type} left = 0;", f"{int_type} right = {end};", "while (left <= right) {",
                f"    {int_type} mid = left + (right - left) / 2;" if language != "javascript" else
                "    const mid = Math.floor((left + right) / 2);",
                f"    {comment} TODO: {next_step}", "    break;", "}"]
    if "two pointers" in pattern.lower() and parameter not in {"head", "list1"}:
        if language == "python":
            return ["left = 0", f"right = {limit} - 1", "while left < right:",
                    f"    {comment} TODO: {next_step}", "    break"]
        int_type = "let" if language == "javascript" else "int"
        return [f"{int_type} left = 0;", f"{int_type} right = {limit} - 1;", "while (left < right) {",
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
        return [f"for index in range({limit}):", f"    {comment} TODO: {next_step}", "    pass"]
    index_type = "let" if language == "javascript" else "int"
    return [f"for ({index_type} index = 0; index < {limit}; index++) {{", f"    {comment} TODO: {next_step}", "}"]
