"""Small generic offline shells for catalog entries without curated mock code.

These are deliberately labeled starter-only by the API. They let developers
exercise every new problem and language without fabricating full answers.
"""

import re


INPUT_NAME = {
    "valid-sudoku": "board", "container-with-most-water": "height",
    "evaluate-reverse-polish-notation": "tokens", "car-fleet": "position",
    "search-a-2d-matrix": "matrix", "koko-eating-bananas": "piles",
    "permutation-in-string": "s2", "rotting-oranges": "grid",
    "coin-change": "coins", "generate-parentheses": "n",
}
TREE_SLUGS = {
    "invert-binary-tree", "same-tree", "diameter-of-binary-tree", "balanced-binary-tree",
}
FAIL = {
    "python": 'raise NotImplementedError("Complete the TODOs")',
    "java": 'throw new UnsupportedOperationException("Complete the TODOs");',
    "javascript": 'throw new Error("Complete the TODOs");',
    "cpp": 'throw logic_error("Complete the TODOs");',
}


def generate_catalog_mock(context: dict, language: str, level: int) -> str:
    slug = context["problem"]["slug"]
    template = context["problem"]["submissionTemplate"]["code"]
    steps = context["approach"]["thinkingSteps"]
    if slug == "time-based-key-value-store":
        return _time_map(template, language, level, steps)

    comment = "#" if language == "python" else "//"
    source = INPUT_NAME.get(slug, "nums")
    if slug in TREE_SLUGS:
        source = "p" if slug == "same-tree" else "root"
        setup = {"python": f"node = {source}", "java": f"TreeNode node = {source};",
                 "javascript": f"let node = {source};", "cpp": f"TreeNode* node = {source};"}[language]
        second = {"python": "processed = 0", "java": "int processed = 0;",
                  "javascript": "let processed = 0;", "cpp": "int processed = 0;"}[language]
        third = {"python": "left_child = node.left if node else None",
                 "java": "TreeNode leftChild = node == null ? null : node.left;",
                 "javascript": "const leftChild = node ? node.left : null;",
                 "cpp": "TreeNode* leftChild = node ? node->left : nullptr;"}[language]
    else:
        size = source if source == "n" else {
            "python": f"len({source})", "java": f"{source}.length()" if source == "s2" else f"{source}.length",
            "javascript": f"{source}.length", "cpp": f"{source}.size()",
        }[language]
        setup = {"python": f"input_size = {size}", "java": f"int inputSize = {size};",
                 "javascript": f"const inputSize = {size};", "cpp": f"int inputSize = {size};"}[language]
        second = {"python": "processed = 0", "java": "int processed = 0;",
                  "javascript": "let processed = 0;", "cpp": "int processed = 0;"}[language]
        third = {"python": "remaining = input_size - processed",
                 "java": "int remaining = inputSize - processed;",
                 "javascript": "const remaining = inputSize - processed;",
                 "cpp": "int remaining = inputSize - processed;"}[language]
    lines = [setup]
    if level >= 2:
        lines.append(second)
    if level >= 3:
        lines.append(third)
        if slug in TREE_SLUGS:
            condition = {"python": "if node is None:", "java": "if (node == null) {",
                         "javascript": "if (node === null) {", "cpp": "if (node == nullptr) {"}[language]
        else:
            condition = {"python": "if processed < input_size:", "java": "if (processed < inputSize) {",
                         "javascript": "if (processed < inputSize) {", "cpp": "if (processed < inputSize) {"}[language]
        lines.extend((condition, f"    {comment} TODO: {steps[min(2, len(steps) - 1)]}",
                      "    " + FAIL[language]))
        if language != "python":
            lines.append("}")
    lines.extend((f"{comment} TODO: {steps[min(level - 1, len(steps) - 1)]}", FAIL[language]))
    return _fill_one(template, language, lines)


def _fill_one(template: str, language: str, lines: list[str]) -> str:
    indent = "        " if language in {"python", "java", "cpp"} else "    "
    body = "\n".join(indent + line for line in lines)
    if language == "python":
        return template.replace("        pass", body, 1)
    return template.replace("{\n\n", "{\n" + body + "\n", 1)


def _time_map(template: str, language: str, level: int, steps: list[str]) -> str:
    comment = "#" if language == "python" else "//"
    if language == "python":
        get_body = (["history = self.entries.get(key, [])"] if level >= 3 else [])
        if level >= 3:
            get_body.extend(["if not history:", "    # TODO: Decide what to return when no earlier value exists.",
                             "    " + FAIL[language]])
        fragments = [
            ["self.entries = {}", f"{comment} TODO: {steps[0]}", FAIL[language]],
            (["history = self.entries.setdefault(key, [])"] if level >= 2 else [])
            + [f"{comment} TODO: {steps[1]}", FAIL[language]],
            get_body + [f"{comment} TODO: {steps[2]}", FAIL[language]],
        ]
        for fragment in fragments:
            body = "\n".join("        " + line for line in fragment)
            template = template.replace("        pass", body, 1)
        return template

    entries = {
        "java": ("private java.util.Map<String, java.util.List<java.util.Map.Entry<Integer, String>>> entries;",
                 "this.entries = new java.util.HashMap<>();",
                 "java.util.List<java.util.Map.Entry<Integer, String>> history = entries.get(key);"),
        "javascript": ("", "this.entries = new Map();", "const history = this.entries.get(key);"),
        "cpp": ("unordered_map<string, vector<pair<int, string>>> entries;",
                "entries.clear();", "auto history = entries.find(key);"),
    }[language]
    field, first, lookup = entries
    if field:
        template = template.replace("class TimeMap {\n", "class TimeMap {\n    " + field + "\n", 1)
    get_body = [lookup] if level >= 3 else []
    if level >= 3:
        condition = {"java": "history == null", "javascript": "history === undefined",
                     "cpp": "history == entries.end()"}[language]
        get_body.extend([f"if ({condition}) {{", "    " + comment + " TODO: Handle a missing earlier value.",
                         "    " + FAIL[language], "}"])
    bodies = [
        [first, f"{comment} TODO: {steps[0]}", FAIL[language]],
        ([lookup] if level >= 2 else []) + [f"{comment} TODO: {steps[1]}", FAIL[language]],
        get_body + [f"{comment} TODO: {steps[2]}", FAIL[language]],
    ]
    indent = "    " if language == "javascript" else "        "
    iterator = iter(bodies)
    def fill(match):
        body = "\n".join(indent + line for line in next(iterator))
        return match.group(1) + body + "\n" + match.group(2)
    result, count = re.subn(r"(?m)(^[^\n]*\([^\n]*\)\s*\{\n)\s*\n(\s*\})", fill, template)
    if count != 3:
        raise ValueError("TimeMap mock shell must preserve all three methods")
    return result
