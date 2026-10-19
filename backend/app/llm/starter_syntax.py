"""Bounded parse/compile checks; never load or execute generated programs."""
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import BoundedSemaphore


_COMPILERS = BoundedSemaphore(2)
_JAVA_NODES = """
class ListNode { int val; ListNode next; ListNode() {} ListNode(int v) {val=v;}
ListNode(int v, ListNode n) {val=v; next=n;} }
class TreeNode { int val; TreeNode left, right; TreeNode() {} TreeNode(int v) {val=v;}
TreeNode(int v, TreeNode l, TreeNode r) {val=v; left=l; right=r;} }
"""
_CPP_NODES = """
struct ListNode { int val; ListNode* next; ListNode(int v=0, ListNode* n=nullptr):val(v),next(n){} };
struct TreeNode { int val; TreeNode *left,*right; TreeNode(int v=0, TreeNode* l=nullptr, TreeNode* r=nullptr):val(v),left(l),right(r){} };
"""


def check_syntax(code: str, language: str) -> dict:
    if language == "python":
        try: ast.parse(code)
        except (SyntaxError, ValueError, RecursionError): return {"status": "FAIL", "summary": "Python syntax error"}
        return {"status": "PASS", "summary": "Python AST parses"}
    tool = {"java": "javac", "javascript": "node", "cpp": "g++"}[language]
    # Compilers can read includes while parsing. Only ordinary standard headers
    # are allowed; no arbitrary local includes, macros or annotation processors.
    if language == "cpp" and any(not re.fullmatch(r"\s*#\s*include\s*<[a-z_]+(?:/[a-z_+.]+)?>\s*", line)
                                  for line in code.splitlines() if line.lstrip().startswith("#")):
        return {"status": "FAIL", "summary": "Unsupported preprocessor directive"}
    executable = shutil.which(tool)
    if not executable:
        return {"status": "NOT_RUN", "summary": f"{tool} is unavailable; structural checks only"}
    if not _COMPILERS.acquire(timeout=2):
        return {"status": "FAIL", "summary": "Syntax validation busy; retry generation"}
    try:
        with tempfile.TemporaryDirectory(prefix="leetcoach-syntax-") as temporary:
            root = Path(temporary)
            if language == "java":
                class_name = re.search(r"\bpublic\s+class\s+(\w+)", code)
                path = root / ((class_name.group(1) if class_name else "Solution") + ".java")
                node_types = _JAVA_NODES if re.search(r"\b(?:ListNode|TreeNode)\b", code) else ""
                source = "import java.util.*;\n" + code + "\n" + node_types
                command = [executable, "-J-Xmx128m", "-proc:none", "-encoding", "UTF-8", "-d", temporary, str(path)]
            elif language == "cpp":
                path = root / "solution.cpp"
                headers = "\n".join(f"#include <{header}>" for header in (
                    "vector", "string", "unordered_map", "unordered_set", "map", "set", "stack", "queue",
                    "deque", "algorithm", "utility", "stdexcept", "climits", "cctype", "functional"))
                source = headers + "\nusing namespace std;\n" + _CPP_NODES + "\n" + code
                command = [executable, "-std=c++17", "-fsyntax-only", "-fmax-errors=3", str(path)]
            else:
                path = root / "solution.js"
                source = code
                command = [executable, "--check", str(path)]
            path.write_text(source, encoding="utf-8")
            # Remove compiler/runtime injection options inherited from a local
            # shell; node --check and compile-only tools never run the source.
            environment = {key: value for key, value in os.environ.items()
                           if key not in {"NODE_OPTIONS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"}}
            try:
                with (root / "diagnostic.txt").open("w", encoding="utf-8") as diagnostic:
                    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=diagnostic,
                                            stderr=subprocess.STDOUT, timeout=8, cwd=temporary, env=environment,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.TimeoutExpired):
                return {"status": "FAIL", "summary": "Bounded syntax check could not complete"}
            return {"status": "PASS" if result.returncode == 0 else "FAIL",
                    "summary": f"{language} syntax/compilation check"}
    finally:
        _COMPILERS.release()
