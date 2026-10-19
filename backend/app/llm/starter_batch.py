"""Policy 7: full-source batches with immutable interfaces and bounded checks.

These are conservative checks for obvious defects, not a proof of algorithmic
correctness, termination, or teaching quality. Generated programs are never run.
"""
import ast
import re
from typing import Any

from app.llm.base import StarterOutputDiagnostic, SUPPORTED_STARTER_LANGUAGES


LEVEL_KEYS = ("level1", "level2", "level3")


def reject(reason: str, stage="validation"):
    raise StarterOutputDiagnostic("Starter batch could not be validated", reason, stage)


def model_context(context: dict, language: str) -> dict:
    """Send facts once, separately from the selected algorithm guidance."""
    problem = context.get("problem", {})
    approach = context.get("approach", {})
    template = problem.get("submissionTemplate", {})
    if (language not in SUPPORTED_STARTER_LANGUAGES or template.get("language") != language
            or not isinstance(template.get("code"), str) or not template["code"].strip()
            or not approach.get("id") or not approach.get("name")):
        reject("INVALID_CONTEXT", "context")
    if (not isinstance(problem.get("description"), str) or not problem["description"].strip()
            or not problem.get("descriptionVerifiedAt") or not problem.get("descriptionSourceType")):
        reject("MISSING_VERIFIED_DESCRIPTION", "context")
    return {
        "problem": {key: problem[key] for key in (
            "title", "description", "constraints", "examples",
            "timeComplexityInstruction", "spaceComplexityInstruction",
        ) if problem.get(key) is not None},
        "approach": {key: approach[key] for key in ("id", "name", "summary", "thinkingSteps")
                     if key in approach},
        "language": language,
        "submissionTemplate": template["code"],
    }


_COMMENTS_LITERALS = re.compile(
    r"(?P<comment>/\*.*?\*/|//[^\n]*)|(?P<literal>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)",
    re.DOTALL,
)


def masked_source(code: str) -> str:
    # Keep offsets/newlines stable for matching function and loop bodies.
    def mask(match):
        value = "".join("\n" if c == "\n" else " " for c in match.group())
        return ("L" + value[1:]) if match.lastgroup == "literal" else value
    return _COMMENTS_LITERALS.sub(mask, code)


def _close_brace(code: str, start: int) -> int:
    depth = 0
    for index in range(start, len(code)):
        if code[index] == "{": depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0: return index
    reject("INVALID_SYNTAX")


def _python_interface(tree: ast.Module, template: str):
    expected = ast.parse(template)
    classes = [node for node in expected.body if isinstance(node, ast.ClassDef)]
    actual = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if [node.name for node in actual] != [node.name for node in classes]:
        reject("CHANGED_CLASS")
    methods = []
    for want, got in zip(classes, actual):
        if got.decorator_list or got.keywords: reject("CHANGED_CLASS")
        if ast.dump(ast.Module(body=want.bases, type_ignores=[])) != ast.dump(ast.Module(body=got.bases, type_ignores=[])):
            reject("CHANGED_CLASS")
        required = {node.name: node for node in want.body if isinstance(node, ast.FunctionDef)}
        found = [node for node in got.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for name, original in required.items():
            matches = [node for node in found if node.name == name]
            if len(matches) != 1: reject("CHANGED_SIGNATURE")
            node = matches[0]
            if isinstance(node, ast.AsyncFunctionDef) or ast.dump(node.args) != ast.dump(original.args):
                reject("CHANGED_SIGNATURE")
            if (ast.dump(node.returns) if node.returns else None) != (ast.dump(original.returns) if original.returns else None):
                reject("CHANGED_SIGNATURE")
            if node.decorator_list: reject("CHANGED_SIGNATURE")
            methods.append(node)
        if any(node.name not in required and (not node.name.startswith("_") or node.name.startswith("__"))
               for node in found):
            reject("ADDITIONAL_PUBLIC_ENTRY_POINT")
        if any(isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
                isinstance(child, ast.Name) and child.id in required for child in ast.walk(node))
               for node in got.body):
            reject("CHANGED_SIGNATURE")
    if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
           for node in tree.body):
        reject("ADDITIONAL_PUBLIC_ENTRY_POINT")
    return methods


def _is_raise(node):
    return (isinstance(node, ast.Raise) and node.exc is not None
            and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name)
            and node.exc.func.id in {"NotImplementedError", "RuntimeError"})


def _guaranteed_stop(body):
    for node in body:
        if isinstance(node, (ast.Raise, ast.Return, ast.Break)): return True
        if isinstance(node, ast.If) and node.orelse and _guaranteed_stop(node.body) and _guaranteed_stop(node.orelse):
            return True
    return False


def _python_paths(body):
    """Discard constant-dead branches and catch elementary unreachable markers."""
    reachable = []
    stopped = False
    for node in body:
        if stopped:
            if any(_is_raise(child) for child in ast.walk(node)):
                reject("UNREACHABLE_PLACEHOLDER")
            # Any dead implementation is suspect, even when Python permits it.
            if not isinstance(node, ast.Pass): reject("UNREACHABLE_CODE")
        reachable.append(node)
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Constant):
                reachable.extend(_python_paths(node.body if node.test.value else node.orelse))
                other = node.orelse if node.test.value else node.body
                if any(_is_raise(child) for child in ast.walk(ast.Module(body=other, type_ignores=[]))):
                    reject("UNREACHABLE_PLACEHOLDER")
            else:
                reachable.extend(_python_paths(node.body))
                reachable.extend(_python_paths(node.orelse))
        elif isinstance(node, (ast.For, ast.While)):
            children = _python_paths(node.body)
            reachable.extend(children)
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is False:
                    reject("UNREACHABLE_PLACEHOLDER")
                # A while with unfinished work needs a fail-loud path in its
                # body; an empty/pass loop followed by a raise cannot reach it.
                condition_names = {child.id for child in ast.walk(node.test) if isinstance(child, ast.Name)}
                has_progress = any(
                    isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name)
                    and child.target.id in condition_names and not (isinstance(child.value, ast.Constant) and child.value.value == 0)
                    or isinstance(child, ast.Assign) and any(isinstance(target, ast.Name) and target.id in condition_names
                        and not (isinstance(child.value, ast.Name) and child.value.id == target.id) for target in child.targets)
                    or isinstance(child, ast.Expr) and isinstance(child.value, ast.Call)
                    and isinstance(child.value.func, ast.Attribute) and isinstance(child.value.func.value, ast.Name)
                    and child.value.func.value.id in condition_names and child.value.func.attr in {"pop", "popleft", "remove"}
                    for child in children)
                if not _guaranteed_stop(node.body) and not has_progress: reject("UNSAFE_UNFINISHED_LOOP")
                if isinstance(node.test, ast.Constant) and node.test.value is True and not _guaranteed_stop(node.body):
                    reject("UNSAFE_UNFINISHED_LOOP")
        elif isinstance(node, (ast.Try, ast.With)):
            # A swallowed placeholder can turn an unfinished result into success.
            if isinstance(node, ast.Try): reject("UNSUPPORTED_EXCEPTION_FLOW")
            reachable.extend(_python_paths(node.body))
        stopped = isinstance(node, (ast.Return, ast.Raise, ast.Break, ast.Continue)) or (
            isinstance(node, ast.If) and bool(node.orelse)
            and _guaranteed_stop(node.body) and _guaranteed_stop(node.orelse))
    return reachable


def _normalize(value):
    return re.sub(r"\s+", "", value)


def _function_name(signature):
    assigned = re.search(r"(?:var|let|const)\s+(\w+)\s*=|\.prototype\.(\w+)\s*=", signature)
    if assigned: return assigned.group(1) or assigned.group(2)
    return re.findall(r"\b(\w+)\s*\(", signature)[-1]


def _cf_interface(code: str, template: str, language: str):
    active = masked_source(code)
    required = [line.strip().rstrip(" {") for line in template.splitlines() if "(" in line]
    # Match declarations, not call sites or text in comments/strings. Formatting
    # whitespace may vary; names, argument order/types and modifiers may not.
    spans = []
    for signature in required:
        pattern = r"\s*".join(re.escape(token) for token in re.findall(r"\w+|[^\w\s]", signature))
        matches = list(re.finditer(r"(?<![\w.])" + pattern + r"\s*\{", active))
        if len(matches) != 1: reject("CHANGED_SIGNATURE")
        start = active.index("{", matches[0].start())
        if language == "cpp":
            access = list(re.finditer(r"\b(public|private|protected)\s*:", active[:start]))
            if not access or access[-1].group(1) != "public": reject("CHANGED_SIGNATURE")
        spans.append((signature, start, _close_brace(active, start)))
    want_classes = re.findall(r"\bclass\s+(\w+)", masked_source(template))
    if re.findall(r"\bclass\s+(\w+)", active) != want_classes:
        reject("CHANGED_CLASS")
    if language in {"java", "cpp"}:
        # Additional private helpers are allowed, additional public methods or
        # overloads are not. The curated C++ shells start in a public section.
        declarations = re.finditer(
            r"(?m)(?:^|(?<=[{};]))\s*((?:(?:public|private|protected|static|final|virtual|inline)\s+)*"
            r"[\w:<>,?\[\]*& ]+?\s+\w+\s*\([^;{}]*\))\s*\{", active)
        for match in declarations:
            decl = match.group(1).strip()
            if re.match(r"(?:if|for|while|switch|catch)\b", decl): continue
            if any(_normalize(decl) == _normalize(want) for want in required): continue
            if any(start < match.start() < end for _, start, end in spans): continue
            private = bool(re.search(r"\bprivate\b", decl))
            if language == "cpp":
                sections = list(re.finditer(r"\b(public|private|protected)\s*:", active[:match.start()]))
                private = bool(sections and sections[-1].group(1) == "private")
            if not private: reject("ADDITIONAL_PUBLIC_ENTRY_POINT")
            opening = active.index("{", match.start())
            spans.append((decl, opening, _close_brace(active, opening)))
    else:
        if re.search(r"\b\w+\.prototype\s*=", active): reject("CHANGED_SIGNATURE")
        declarations = re.finditer(
            r"(?m)(?:^|(?<=[{};]))\s*((?:(?:var|let|const)\s+\w+|\w+\.prototype\.\w+)\s*=\s*function\s*\([^)]*\)|function\s+\w+\s*\([^)]*\))\s*\{", active)
        for match in declarations:
            if any(_normalize(match.group(1)) == _normalize(want) for want in required): continue
            if any(start < match.start() < end for _, start, end in spans): continue
            if not re.search(r"(?:function\s+_|prototype\._|(?:var|let|const)\s+_)", match.group(1)):
                reject("ADDITIONAL_PUBLIC_ENTRY_POINT")
            opening = active.index("{", match.start())
            spans.append((match.group(1), opening, _close_brace(active, opening)))
    return active, spans


_FAIL = re.compile(r"\bthrow\s+(?:new\s+(?:UnsupportedOperationException|Error)|(?:std::)?(?:logic_error|runtime_error))\s*\(")


def _cf_stops(body):
    """Recognize a direct stop or a complete if/else whose arms all stop."""
    index = 0
    while index < len(body):
        if re.match(r"\b(?:throw|return|break)\b", body[index:]): return True
        branch = re.match(r"\bif\s*\([^{}]*\)\s*\{", body[index:])
        if branch:
            opening = body.index("{", index)
            ending = _close_brace(body, opening)
            first_stops = _cf_stops(body[opening + 1:ending])
            remaining = body[ending + 1:].lstrip()
            if remaining.startswith("else"):
                other = remaining[4:].lstrip()
                if other.startswith("if"):
                    if first_stops and _cf_stops(other): return True
                elif other.startswith("{"):
                    closing = _close_brace(other, 0)
                    if first_stops and _cf_stops(other[1:closing]): return True
            index = ending + 1
            continue
        if body[index] == "{": index = _close_brace(body, index) + 1
        else: index += 1
    return False


def _cf_paths(active: str, spans, code: str):
    fails = []
    for signature, start, end in spans:
        body = active[start + 1:end]
        local_fails = list(_FAIL.finditer(body))
        for match in local_fails:
            before = body[:match.start()]
            # A terminal in the same lexical block makes a later throw dead.
            tail = re.split(r"[{}]", before)[-1]
            if re.search(r"(?:^|;)\s*(?:return|throw)\b[^;]*;", tail):
                reject("UNREACHABLE_PLACEHOLDER")
        if re.search(r"\b(?:if|while)\s*\(\s*(?:false|0)\s*\)\s*\{[^}]*\bthrow\b", body):
            reject("UNREACHABLE_PLACEHOLDER")
        if re.search(r"\bcatch\s*\(", body): reject("UNSUPPORTED_EXCEPTION_FLOW")
        for loop in re.finditer(r"\bwhile\s*\([^\n{}]*\)\s*\{", body):
            opening = body.index("{", loop.start())
            loop_body = body[opening + 1:_close_brace(body, opening)]
            original_body = code[start + 1 + opening:start + 1 + _close_brace(body, opening)]
            if re.search(r"\bTODO\b", original_body, re.I) and not _FAIL.search(loop_body):
                reject("UNSAFE_UNFINISHED_LOOP")
            condition = loop.group().split("(", 1)[1].rsplit(")", 1)[0]
            names = set(re.findall(r"\b[a-zA-Z_]\w*\b", condition)) - {"true", "false"}
            has_progress = any(re.search(rf"\b{re.escape(name)}\s*(?:\+\+|--|\+=|-=|=\s*(?!{re.escape(name)}\s*;))", loop_body)
                               or re.search(rf"\b{re.escape(name)}\.(?:pop|poll|remove|shift)\s*\(", loop_body)
                               for name in names)
            if not _cf_stops(loop_body) and not has_progress: reject("UNSAFE_UNFINISHED_LOOP")
            if re.search(r"while\s*\(\s*(?:true|1)\s*\)", loop.group()) and not _cf_stops(loop_body):
                reject("UNSAFE_UNFINISHED_LOOP")
        fails.extend(local_fails)
    return fails


def _obvious_leaks(code: str, active: str, context: dict, language: str):
    slug, key = context["problem"]["slug"], context["approach"]["id"]
    # Target clear counterexamples, not every allowed standard-library call.
    if slug == "two-sum" and key == "hash-map":
        lookup = re.search(r"containsKey\s*\(|\.has\s*\(|\bin\s+\w+\b|\.find\s*\(", active)
        store = re.search(r"\.put\s*\(|\.set\s*\(|\w+\s*\[[^]]+\]\s*=", active)
        result = re.search(r"\breturn\s+(?:new\s+int\s*\[\]\s*\{|[\[{])", active)
        if lookup and store and result: reject("APPARENT_COMPLETE_SOLUTION")
    if key == "brute-force" and re.search(r"HashMap|unordered_map|new\s+Map\s*\(|\bseen\s*=\s*\{", code):
        reject("APPROACH_CONTRADICTION")
    if slug == "min-stack" and key == "paired-minimums" and re.search(r"\b(?:minimums|min_stack|minStack)\b", active):
        reject("APPROACH_CONTRADICTION")
    if slug == "maximum-depth-of-binary-tree" and re.search(r"return\s+(?:1\s*\+\s*(?:max|Math.max|std::max)|(?:max|Math.max|std::max)\([^;\n]+\)\s*\+\s*1)", active):
        reject("APPARENT_COMPLETE_SOLUTION")
    if slug == "binary-search" and key == "binary-search":
        if re.search(r"return\s+(?:mid|middle)\b", active) and re.search(r"left\s*=\s*(?:mid|middle)\s*\+\s*1", active) and re.search(r"right\s*=\s*(?:mid|middle)\s*-\s*1", active):
            reject("APPARENT_COMPLETE_SOLUTION")
    # A TODO offering a complete executable recipe defeats an unfinished file.
    comments = [line for line in code.splitlines() if line.lstrip().startswith(("#", "//"))]
    if sum(bool(re.match(r"\s*(?:#|//)\s*(?:if\s*\(|return\s+[\[{]|seen\[[^]]+\]\s*=|seen\.put\s*\()", line))
           for line in comments) >= 2:
        reject("COMMENTED_OUT_ALGORITHM")
    # Three consecutive commented statements are a code recipe, not an
    # explanation. Plain-language comments and isolated examples remain valid.
    target = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*|\[[^]\n]+\])*"
    assignment = re.compile(rf"^(?:(?:const|let|var|auto|int|long|bool|String)\s+)?{target}\s*(?:=(?!=)|\+=|-=)\s*\S+")
    statement = re.compile(rf"^(?:return\s+\S+|{target}\s*\([^{{}}]*\)\s*;?)$")
    consecutive = 0
    for line in code.splitlines():
        match = re.match(r"^\s*(?:#(?!include\b)|//)\s*(.*)$", line)
        part = match.group(1).strip() if match else ""
        if part and (assignment.match(part) or statement.match(part)):
            consecutive += 1
            if consecutive >= 3: reject("COMMENTED_OUT_ALGORITHM")
        else:
            consecutive = 0


def validate_level(code: Any, context: dict, language: str, level: int):
    if not isinstance(code, str): reject("INVALID_OUTPUT_TYPE")
    code = code.strip()
    if not code or len(code) > 20000 or "```" in code: reject("INVALID_STRUCTURE")
    todos = re.findall(r"(?im)^\s*(?:#|//)\s*TODO\s*:?\s*(.+)$", code)
    tree = None
    if language == "python":
        try: tree = ast.parse(code)
        except (SyntaxError, ValueError, RecursionError): reject("INVALID_SYNTAX")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                todos.extend(re.findall(r"(?im)^\s*TODO\s*:?\s*(.+)$", ast.get_docstring(node) or ""))
    if not todos or all(len(todo.strip()) < 6 or re.match(r"(?:review|explain|test|optimi[sz]e|done)\b", todo, re.I) for todo in todos):
        reject("MISSING_MEANINGFUL_TODO")
    template = context["problem"]["submissionTemplate"]["code"]
    if language == "python":
        methods = _python_interface(tree, template)
        for loop in (node for node in ast.walk(tree) if isinstance(node, ast.While)):
            loop_text = "\n".join(code.splitlines()[loop.lineno - 1:loop.end_lineno])
            if re.search(r"\bTODO\b", loop_text, re.I) and not any(_is_raise(node) for node in ast.walk(loop)):
                reject("UNSAFE_UNFINISHED_LOOP")
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        if len(functions) > 32: reject("INVALID_STRUCTURE")
        unfinished = set()
        function_paths = {}
        for method in functions:
            paths = _python_paths(method.body)
            function_paths[method.name] = paths
            if any(_is_raise(node) for node in paths): unfinished.add(method.name)
            if any(isinstance(node, (ast.Pass, ast.Expr)) and (isinstance(node, ast.Pass) or
                   isinstance(node.value, ast.Constant) and node.value.value is Ellipsis) for node in paths):
                reject("SILENT_UNFINISHED_METHOD")
        # A main entry point may delegate to an unfinished recursive helper.
        # Uncalled helpers do not make a completed entry point unfinished.
        for _ in functions:
            for name, paths in function_paths.items():
                for node in paths:
                    if isinstance(node, ast.FunctionDef): continue
                    if any(isinstance(child, ast.Call) and (
                            isinstance(child.func, ast.Name) and child.func.id in unfinished or
                            isinstance(child.func, ast.Attribute) and child.func.attr in unfinished)
                           for child in ast.walk(node)):
                        unfinished.add(name)
        for method in functions:
            method_text = "\n".join(code.splitlines()[method.lineno - 1:method.end_lineno])
            if re.search(r"\bTODO\b", method_text) and method.name not in unfinished:
                reject("SILENT_UNFINISHED_METHOD")
        if not any(method.name in unfinished for method in methods): reject("MISSING_UNFINISHED_PLACEHOLDER")
        active = ast.unparse(tree)
        score = sum(isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.If, ast.For, ast.While, ast.Return))
                    for node in ast.walk(tree))
        design = set(re.findall(r"self\.(\w+)\s*=", active))
    else:
        active, spans = _cf_interface(code, template, language)
        if len(spans) > 32: reject("INVALID_STRUCTURE")
        if re.search(r"(?<![=!<>])=\s*;|\b(?:if|while|for)\s*\(\s*\)", active):
            reject("INVALID_SYNTAX")
        for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
            depth = 0
            for char in active:
                depth += (char == opening) - (char == closing)
                if depth < 0: reject("INVALID_SYNTAX")
                if depth > 64: reject("INVALID_STRUCTURE")
            if depth: reject("INVALID_SYNTAX")
        fails = _cf_paths(active, spans, code)
        if not fails: reject("MISSING_UNFINISHED_PLACEHOLDER")
        unfinished = {_function_name(signature) for signature, start, end in spans
                      if _FAIL.search(active[start:end])}
        for _ in spans:
            for signature, start, end in spans:
                if any(re.search(rf"\b{re.escape(name)}\s*\(", active[start + 1:end]) for name in unfinished):
                    unfinished.add(_function_name(signature))
        required_count = sum("(" in line for line in template.splitlines())
        if not any(_function_name(signature) in unfinished for signature, _, _ in spans[:required_count]):
            reject("MISSING_UNFINISHED_PLACEHOLDER")
        for signature, start, end in spans:
            if re.search(r"\bTODO\b", code[start:end], re.I) and _function_name(signature) not in unfinished:
                reject("SILENT_UNFINISHED_METHOD")
        score_code = re.sub(r"\bthrow\b[^;]*;", "", active)
        parens = 0
        statements = 0
        for char in score_code:
            if char == "(": parens += 1
            elif char == ")": parens -= 1
            elif char == ";" and parens == 0: statements += 1
        score = statements + 2 * len(re.findall(r"\b(?:if|for|while|switch)\s*\(", score_code))
        design = set(re.findall(r"(?:this\.|self\.)?(pairs|values|stack|minimums|min_stack|minStack)\s*[=;]", active))
    _obvious_leaks(code, active, context, language)
    if score < 1: reject("NO_USEFUL_SETUP")
    return code, score, design


def validate_starter_batch(raw: Any, context: dict, language: str, *, check_compilers=True,
                           require_score_progression=True) -> dict[str, str]:
    model_context(context, language)
    if not isinstance(raw, dict) or set(raw) != set(LEVEL_KEYS): reject("INVALID_BATCH_FIELDS", "parsing")
    validated = [validate_level(raw[key], context, language, index) for index, key in enumerate(LEVEL_KEYS, 1)]
    codes, scores, designs = zip(*validated)
    if len(set(codes)) != 3 or (require_score_progression and not scores[0] < scores[1] < scores[2]):
        reject("INVALID_LEVEL_PROGRESSION")
    if context["problem"]["slug"] == "min-stack" and (not designs[0] or not all(designs[0] <= design for design in designs[1:])):
        reject("INCOMPATIBLE_LEVEL_DESIGN")
    if check_compilers:
        from app.llm.starter_syntax import check_syntax
        for code in codes:
            if check_syntax(code, language)["status"] == "FAIL": reject("INVALID_SYNTAX")
    return dict(zip(LEVEL_KEYS, codes))
