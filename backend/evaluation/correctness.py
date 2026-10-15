"""Independent fixtures and bounded execution outside the FastAPI process.

Generated Python/C++ runs only inside a bubblewrap namespace in WSL. The
namespace has no network or writable host mounts. Unsupported runtimes are
reported as NOT_RUN; this module never falls back to host execution.
"""
import ast
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


FIXTURES = {
    "two-sum": [
        {"input": [[2, 7, 11, 15], 9], "pairs": [[0, 1]]},
        {"input": [[3, 3], 6], "pairs": [[0, 1]]},
        {"input": [[-3, 4, 3, 90], 0], "pairs": [[0, 2]]},
        {"input": [[1, 5, 1, 5], 6], "pairs": [[0, 1], [0, 3], [1, 2], [2, 3]]},
    ],
    "3sum": [
        {"input": [-1, 0, 1, 2, -1, -4], "expected": [[-1, -1, 2], [-1, 0, 1]]},
        {"input": [0, 1, 1], "expected": []},
        {"input": [0, 0, 0, 0], "expected": [[0, 0, 0]]},
        {"input": [-2, 0, 0, 2, 2], "expected": [[-2, 0, 2]]},
    ],
    "valid-parentheses": [
        {"input": "()[]{}", "expected": True},
        {"input": "([{}])", "expected": True},
        {"input": "(]", "expected": False},
        {"input": "([)]", "expected": False},
        {"input": "", "expected": True},
    ],
    "longest-substring-without-repeating-characters": [
        {"input": "abcabcbb", "expected": 3},
        {"input": "bbbbb", "expected": 1},
        {"input": "pwwkew", "expected": 3},
        {"input": "", "expected": 0},
        {"input": "abcdef", "expected": 6},
        {"input": "abba", "expected": 2},
    ],
    "binary-search": [
        {"input": [[-1, 0, 3, 5, 9, 12], 9], "expected": 4},
        {"input": [[-1, 0, 3, 5, 9, 12], 2], "expected": -1},
        {"input": [[1], 1], "expected": 0},
        {"input": [[1], 2], "expected": -1},
        {"input": [[1, 3, 5], 1], "expected": 0},
        {"input": [[1, 3, 5], 5], "expected": 2},
        {"input": [[], 3], "expected": -1},
    ],
    "min-stack": [
        {"operations": [["push", -2], ["push", 0], ["push", -3], ["getMin", -3],
                         ["pop"], ["top", 0], ["getMin", -2], ["push", -2],
                         ["getMin", -2], ["pop"], ["getMin", -2]]},
        {"operations": [["push", 5], ["push", 3], ["push", 3], ["getMin", 3],
                         ["pop"], ["getMin", 3], ["pop"], ["getMin", 5]]},
    ],
    "reverse-linked-list": [
        {"input": [1, 2, 3, 4, 5], "expected": [5, 4, 3, 2, 1]},
        {"input": [1, 2], "expected": [2, 1]},
        {"input": [], "expected": []},
    ],
}


PYTHON_PRELUDE = """from typing import List, Optional
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
"""

PYTHON_DRIVER = r'''
import json as _json
_cases = _json.loads(CASES_JSON)
_results = []
for _case in _cases:
    try:
        if SLUG == "two-sum":
            _nums, _target = _case["input"]
            _got = Solution().twoSum(_nums[:], _target)
            _valid = isinstance(_got, (list, tuple)) and len(_got) == 2 and all(
                isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(_nums) for i in _got
            ) and _got[0] != _got[1] and sorted(_got) in _case["pairs"]
        elif SLUG == "3sum":
            _got = Solution().threeSum(_case["input"][:])
            _normalized = sorted(set(tuple(sorted(t)) for t in _got))
            _valid = _normalized == sorted(tuple(t) for t in _case["expected"]) and len(_got) == len(_normalized)
        elif SLUG == "valid-parentheses":
            _got = Solution().isValid(_case["input"])
            _valid = type(_got) is bool and _got == _case["expected"]
        elif SLUG == "longest-substring-without-repeating-characters":
            _got = Solution().lengthOfLongestSubstring(_case["input"])
            _valid = type(_got) is int and _got == _case["expected"]
        elif SLUG == "binary-search":
            _nums, _target = _case["input"]
            _got = Solution().search(_nums[:], _target)
            _valid = type(_got) is int and _got == _case["expected"]
        elif SLUG == "min-stack":
            _stack = MinStack()
            _valid = True
            for _operation in _case["operations"]:
                _got = getattr(_stack, _operation[0])(*(_operation[1:2] if _operation[0] == "push" else []))
                if _operation[0] in ("getMin", "top") and _got != _operation[1]:
                    _valid = False
                    break
        elif SLUG == "reverse-linked-list":
            _head = None
            for _value in reversed(_case["input"]):
                _head = ListNode(_value, _head)
            _head = Solution().reverseList(_head)
            _values, _seen = [], set()
            while _head is not None and len(_values) <= len(_case["input"]):
                if id(_head) in _seen:
                    break
                _seen.add(id(_head))
                _values.append(_head.val)
                _head = _head.next
            _valid = _head is None and _values == _case["expected"]
        else:
            _valid = False
        _results.append({"status": "PASS" if _valid else "FAIL", "input": _case, "actual": repr(_got)[:180] if '_got' in locals() else None})
    except Exception as _exc:
        _results.append({"status": "FAIL", "input": _case, "error": type(_exc).__name__ + ": " + str(_exc)[:180]})
print("LEETCOACH_RESULT=" + _json.dumps(_results))
'''


def probe_sandbox() -> tuple[bool, str]:
    if not shutil.which("wsl"):
        return False, "WSL is unavailable"
    command = ["wsl", "--exec", "bwrap", "--unshare-all", "--ro-bind", "/usr", "/usr",
               "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
               "--ro-bind", "/bin", "/bin", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--tmpfs", "/work", "--clearenv",
               "--die-with-parent", "--new-session", "/usr/bin/python3", "-I", "-c", "print('ready')"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False, "WSL bubblewrap probe did not complete"
    return (result.returncode == 0 and result.stdout.strip() == "ready",
            "WSL bubblewrap with isolated network and mounts" if result.returncode == 0
            else "WSL bubblewrap namespace is unavailable")


def _wsl_path(path: Path) -> str:
    result = subprocess.run(["wsl", "--exec", "wslpath", "-a", str(path.resolve())],
                            capture_output=True, text=True, timeout=10, check=True)
    return result.stdout.strip()


def _sandbox_run(source: str, extension: str, command: str, output_dir: Path,
                 fixtures: list | None = None) -> dict:
    with tempfile.TemporaryDirectory(dir=output_dir) as temporary:
        source_path = Path(temporary) / f"case.{extension}"
        source_path.write_text(source, encoding="utf-8")
        try:
            linux_source = _wsl_path(source_path)
            args = ["wsl", "--exec", "bwrap", "--unshare-all", "--ro-bind", "/usr", "/usr",
                    "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                    "--ro-bind", "/bin", "/bin", "--proc", "/proc", "--dev", "/dev",
                    "--tmpfs", "/tmp", "--tmpfs", "/work", "--ro-bind", linux_source,
                    f"/work/case.{extension}", "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                    "--setenv", "HOME", "/tmp", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                    "--die-with-parent", "--new-session", "--chdir", "/work",
                    "/bin/bash", "-lc", command]
            completed = subprocess.run(args, capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return {"status": "FAIL", "cases": [], "summary": "Sandbox execution exceeded 20 seconds"}
        except (OSError, subprocess.CalledProcessError):
            return {"status": "NOT_RUN", "cases": [], "summary": "Sandbox invocation failed"}
    output = completed.stdout[-65536:]
    if "LEETCOACH_RESULT=" not in output:
        summary = "Compilation failed" if extension == "cpp" and "COMPILE_OK" not in output else "No bounded test result"
        return {"status": "FAIL", "cases": [], "summary": summary,
                "diagnostic": (completed.stderr or output)[-1000:]}
    try:
        raw_results = output.rsplit("LEETCOACH_RESULT=", 1)[1]
        if extension == "cpp":
            verdicts = [line.strip() for line in raw_results.splitlines() if line.strip()]
            if not fixtures or len(verdicts) != len(fixtures) or any(
                verdict not in {"PASS", "FAIL"} for verdict in verdicts
            ):
                raise ValueError("Incomplete C++ test output")
            tests = [{"status": verdict, "input": fixture} for verdict, fixture in zip(verdicts, fixtures)]
        else:
            tests = json.loads(raw_results.splitlines()[0])
    except (ValueError, IndexError):
        return {"status": "FAIL", "cases": [], "summary": "Malformed bounded test result"}
    return {"status": "PASS" if tests and all(item["status"] == "PASS" for item in tests) else "FAIL",
            "cases": tests, "summary": f"{sum(item['status'] == 'PASS' for item in tests)}/{len(tests)} fixtures passed"}


def check_syntax(code: str, language: str, output_dir: Path) -> dict:
    if language == "python":
        try:
            ast.parse(code)
            return {"status": "PASS", "summary": "Python AST parses"}
        except SyntaxError as exc:
            return {"status": "FAIL", "summary": f"Python syntax at line {exc.lineno}"}
    if language == "javascript":
        if not shutil.which("node"):
            return {"status": "NOT_RUN", "summary": "Node.js syntax checker unavailable"}
        with tempfile.TemporaryDirectory(dir=output_dir) as temporary:
            path = Path(temporary) / "case.js"
            path.write_text(code, encoding="utf-8")
            try:
                result = subprocess.run(["node", "--check", str(path)], capture_output=True,
                                        text=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                return {"status": "NOT_RUN", "summary": "Node.js syntax check unavailable"}
        return {"status": "PASS" if result.returncode == 0 else "FAIL",
                "summary": "JavaScript syntax check" if result.returncode == 0 else "JavaScript syntax error",
                "diagnostic": result.stderr[-500:] if result.returncode else ""}
    if language == "java":
        if not shutil.which("javac"):
            return {"status": "NOT_RUN", "summary": "Java compiler unavailable"}
        with tempfile.TemporaryDirectory(dir=output_dir) as temporary:
            path = Path(temporary) / "Solution.java"
            path.write_text("import java.util.*;\n" + code, encoding="utf-8")
            try:
                result = subprocess.run(["javac", "-proc:none", "-encoding", "UTF-8",
                                         "-d", temporary, str(path)], capture_output=True,
                                        text=True, timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                return {"status": "NOT_RUN", "summary": "Java compilation unavailable"}
        return {"status": "PASS" if result.returncode == 0 else "FAIL",
                "summary": "Java compilation" if result.returncode == 0 else "Java compilation error",
                "diagnostic": result.stderr[-500:] if result.returncode else ""}
    return {"status": "NOT_RUN", "summary": "C++ compilation is included in isolated correctness when a fixture exists"}


def execute_solution(slug: str, language: str, code: str, output_dir: Path,
                     sandbox_available: bool) -> dict:
    if slug not in FIXTURES:
        return {"status": "NOT_RUN", "cases": [], "summary": "No independent oracle for this problem"}
    if language not in {"python", "cpp"}:
        return {"status": "NOT_RUN", "cases": [],
                "summary": f"No isolated {language} runtime is available on this device"}
    if not sandbox_available:
        return {"status": "NOT_RUN", "cases": [], "summary": "Adequate execution sandbox unavailable"}
    if language == "python":
        source = (PYTHON_PRELUDE + "\n" + code + "\n" +
                  f"SLUG = {slug!r}\nCASES_JSON = {json.dumps(FIXTURES[slug])!r}\n" + PYTHON_DRIVER)
        return _sandbox_run(source, "py", "ulimit -t 6; ulimit -v 393216; "
                            "/usr/bin/python3 -I /work/case.py 2>&1 | head -c 65536", output_dir)
    if slug == "two-sum":
        checks = """
    vector<pair<vector<int>, int>> inputs = {{{2,7,11,15},9},{{3,3},6},{{-3,4,3,90},0},{{1,5,1,5},6}};
    for (auto item : inputs) {
        auto nums = item.first; auto result = Solution().twoSum(nums, item.second);
        bool ok = result.size()==2 && result[0]>=0 && result[1]>=0 && result[0]<(int)nums.size()
            && result[1]<(int)nums.size() && result[0]!=result[1]
            && nums[result[0]]+nums[result[1]]==item.second;
        cout << (ok ? \"PASS\" : \"FAIL\") << endl;
    }
"""
        count = 4
    elif slug == "3sum":
        checks = """
    vector<vector<int>> inputs = {{-1,0,1,2,-1,-4},{0,1,1},{0,0,0,0},{-2,0,0,2,2}};
    vector<vector<vector<int>>> expected = {{{-1,-1,2},{-1,0,1}}, {}, {{0,0,0}}, {{-2,0,2}}};
    for (size_t i=0; i<inputs.size(); ++i) {
        auto nums=inputs[i]; auto got=Solution().threeSum(nums);
        for (auto &triplet:got) sort(triplet.begin(), triplet.end());
        sort(got.begin(), got.end());
        bool unique = adjacent_find(got.begin(), got.end()) == got.end();
        cout << ((unique && got == expected[i]) ? \"PASS\" : \"FAIL\") << endl;
    }
"""
        count = 4
    else:
        return {"status": "NOT_RUN", "cases": [], "summary": "No C++ harness for this problem"}
    source = ("#include <bits/stdc++.h>\nusing namespace std;\n" + code + "\n"
              + 'int main() { cout << "LEETCOACH_RESULT=" << endl;\n' + checks + "}\n")
    command = ("ulimit -t 10; ulimit -v 786432; "
               "g++ -std=c++17 -O0 -o /work/case /work/case.cpp 2>&1 && "
               "printf 'COMPILE_OK\\n' && /work/case | head -c 65536")
    return _sandbox_run(source, "cpp", command, output_dir, FIXTURES[slug])
