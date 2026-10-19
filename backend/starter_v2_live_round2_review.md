# Starter Code v2, live Round 2 — October 18, 2026

## Run and decision

**NO-GO for general release.** The updated prompt and validator improve API acceptance, but only **2/8 batches (25%)** pass manual teaching review. The API accepted **4/8 (50%)**; two accepted batches reveal crucial answer steps in comments. Groq returned three levels for every request. The eight calls used the configured real `openai/gpt-oss-120b` model, with no mock responses, fallback, or automatic retries. There were no provider errors, timeouts, or rate-limit responses; all four HTTP 502 results came from local validation.

Before the run, Policy **8** was confirmed in the backend batch API and frontend cache key/hydration checks; Policy 7 batches are invalidated. The concise prompt rules against silent unfinished logic, fake control flow, commented-out solutions, and non-progressing levels were present. The validator's C++ `runtime_error` support and commented-algorithm detection were present. The frozen evaluator matrix matches Round 1. This was the only Round 2 run:

```text
py -B -m evaluation.starter_v2 --live --max-calls 8 --pace-seconds 12 --capture-raw --output-dir evaluation_runs/starter_v2_live_round2
```

The ignored [JSON results](evaluation_runs/starter_v2_live_round2/starter_v2.json) and eight `*-raw.txt` responses remain local, separate from [Round 1](evaluation_runs/starter_v2_live/). The generated evaluator report is also in the Round 2 directory. No implementation code, prompt, validator, or test was changed for this review.

| Measure | Round 1 | Round 2 |
|---|---:|---:|
| Real Groq calls | 8 | 8 |
| API-valid complete batches | 1/8 (12.5%) | 4/8 (50%) |
| Human-approved complete batches | 0/8 | 2/8 (25%) |
| Individually structurally valid levels | 14/24 | 17/24 |
| Syntax checks passed | 24/24 | 21/24 |

The Round 2 syntax regression is one malformed Number of Islands response containing literal backslash-`n` sequences in all three code strings. Required method/function names and parameter shapes appear in the other seven responses, but Reverse Linked List also redefines the platform-provided `ListNode`, so its submission interface is not faithful to the template.

## All 24 generated levels

“Structure” is the evaluator's per-level result. “Human” considers the actual code, including answer leakage, progression, and paths that can silently do the wrong thing. The batch column is the local API result, not a Groq HTTP failure.

| Problem / approach / language | Batch | Level | Structure | Syntax | Human review |
|---|---:|---:|---|---|---|
| Two Sum / hash-map / Python | 200 | L1 | PASS | PASS | Minimal fail-loud scaffold; extra input check is unnecessary but harmless. |
|  |  | L2 | PASS | PASS | Loop uses `continue` instead of performing either operation; TODO comments give the exact return expression and map update. |
|  |  | L3 | PASS | PASS | Lookup and map update are implemented; only returning the two indices remains. This is too close to a full answer, especially after L2's comment. **Batch human-rejected.** |
| 3Sum / sort-and-two-pointers / Java | 200 | L1 | PASS | PASS | Signature and fail-loud TODO. |
|  |  | L2 | PASS | PASS | Sorting and outer loop added; missing pair search throws when reached. The empty result for fewer than three numbers is legitimate. |
|  |  | L3 | PASS | PASS | Adds target, two pointers, and branches. Triplet insertion, duplicate handling, and pointer updates remain executable work; every unfinished branch throws. **Batch human-approved.** |
| Binary Search / binary-search / C++ | 200 | L1 | PASS | PASS | Signature and valid `throw runtime_error(...)` placeholder. |
|  |  | L2 | PASS | PASS | Bounds, loop, and midpoint added; unfinished branch logic throws. |
|  |  | L3 | PASS | PASS | Equality return added; both bound updates remain for the student, with a reachable throw. **Batch human-approved.** |
| Min Stack / paired-minimums / JavaScript | 200 | L1 | PASS | PASS | Stack initialized; methods have reachable fail-loud TODOs. |
|  |  | L2 | PASS | PASS | Some methods implemented, but commented lines give the exact minimum calculation and `getMin` return. |
|  |  | L3 | PASS | PASS | The only missing operations are supplied as copyable commented code in `_computeNewMin` and `getMin`. **Batch human-rejected: answer leakage missed by validator.** |
| Reverse Linked List / iterative-pointers / Python | 502 | L1 | FAIL: `CHANGED_CLASS` | PASS | Redefines LeetCode's `ListNode`; the remaining scaffold is fail-loud. |
|  |  | L2 | FAIL: `CHANGED_CLASS` | PASS | Same interface defect. Loop advances without reversing links, then silently returns `prev`; comment gives the missing `curr.next = prev`. |
|  |  | L3 | FAIL: `CHANGED_CLASS` | PASS | Same interface defect. Helper throws, but restructuring L2 into a helper is not a clear increase in guidance. **Batch rejected.** |
| Maximum Depth of Binary Tree / depth-first-search / Java | 502 | L1 | PASS | PASS | Base case and fail-loud TODO. |
|  |  | L2 | PASS | PASS | Recursive calls are present; combining depths remains. One TODO redundantly asks for the already implemented null case. |
|  |  | L3 | PASS | PASS | Executable scaffold barely advances beyond L2; comments provide the complete missing `1 + Math.max(...)` and return. **Batch rejected: `INVALID_LEVEL_PROGRESSION`, with answer leakage.** |
| Number of Islands / depth-first-flood-fill / C++ | 502 | L1 | FAIL: `MISSING_MEANINGFUL_TODO` | FAIL | Entire code value is one line with literal `\n` characters; it is not compilable C++. The source also places the main scan in L1. |
|  |  | L2 | FAIL: `MISSING_MEANINGFUL_TODO` | FAIL | Same escaped-newline defect. If decoded, the four commented `_dfs(...)` calls would give away the missing flood fill. |
|  |  | L3 | FAIL: `MISSING_MEANINGFUL_TODO` | FAIL | Same escaped-newline defect. If decoded, the only neighbor-recursion line is shown in a comment. **Batch rejected.** |
| Climbing Stairs / memoized-recursion / JavaScript | 502 | L1 | PASS | PASS | Minimal fail-loud recursive task. |
|  |  | L2 | PASS | PASS | Memo and helper added; base cases and recurrence are still for the student. |
|  |  | L3 | FAIL: `COMMENTED_OUT_ALGORITHM` | PASS | Base cases and cache lookup are implemented; three comments supply the entire remaining recurrence, cache store, and return. **Batch rejected.** |

All eight batches contain L1, L2, and L3 in the raw model response. Clearly useful progression appears in 3Sum and Binary Search. Two Sum and Min Stack add executable structure but make the remaining task too easy through comments; Maximum Depth adds comments rather than more usable scaffold. Reverse Linked List changes the scaffold design between L2 and L3. Number of Islands cannot be judged as delivered code because all levels are malformed. Climbing Stairs increases structure but comments disclose the entire final step.

## Exact rejection analysis

- **Reverse Linked List — `CHANGED_CLASS`:** the model declares `class ListNode` in all three levels, although LeetCode provides it. This is a genuine template violation, not a false positive. L2 has an additional silent wrong-answer path that the batch validator never reaches because it stops at the class error.
- **Maximum Depth — `INVALID_LEVEL_PROGRESSION`:** L3 does not add substantive executable structure over L2, and its comments give the complete missing formula and return. Genuine rejection.
- **Number of Islands — `MISSING_MEANINGFUL_TODO`:** JSON parsing succeeds, but each code string has **zero actual newline characters** and 31/37/39 literal `\n` sequences (L1/L2/L3). The TODO finder cannot see real comment lines, and the syntax checker rejects all three as unsupported preprocessor directives. This reason masks the more basic malformed-code problem; it is **not** a valid C++ sample incorrectly rejected for `runtime_error` as in Round 1. The updated validator correctly accepts `throw runtime_error(...)` in the valid Binary Search response.
- **Climbing Stairs — `COMMENTED_OUT_ALGORITHM`:** L3 contains the exact recurrence, memo assignment, and return as commented-out source. Genuine rejection.
- **Accepted but human-rejected:** Two Sum L2 shows `[seen[complement], i]` in a comment and L3 leaves only that return; Min Stack L2/L3 show the exact remaining code lines in comments. These are validator **false acceptances**, not false rejections. There is no confirmed false rejection in this round.

No unsafe infinite loop was found in code that can run to completion: unfinished 3Sum and Binary Search branches throw, and Min Stack's unfinished methods throw. Reverse Linked List L2 can silently return an unreversed list. Two Sum L2 silently continues each iteration, although it eventually raises after the loop; this still makes the placeholder misleading. The malformed Islands source cannot execute at all.

## Representative actual Groq outputs

These are copied from the captured raw response fields. The third sample deliberately preserves the literal `\n` characters produced by Groq.

**3Sum / Java / L3 — acceptable strong scaffold:**

```java
import java.util.*;

class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        // Step 1: sort the array
        Arrays.sort(nums);
        List<List<Integer>> result = new ArrayList<>();
        int n = nums.length;
        // Step 2: fix each element and search for a complementary pair
        for (int i = 0; i < n - 2; i++) {
            // Avoid duplicate fixed elements
            if (i > 0 && nums[i] == nums[i - 1]) continue;
            int target = -nums[i];
            int left = i + 1;
            int right = n - 1;
            // Step 3: two‑pointer search for the remaining two numbers
            while (left < right) {
                int sum = nums[left] + nums[right];
                if (sum == target) {
                    // TODO: add the triplet [nums[i], nums[left], nums[right]] to result
                    // and skip over any duplicate values for left and right.
                    throw new UnsupportedOperationException("adding triplet not implemented");
                } else if (sum < target) {
                    // TODO: move left pointer to the right to increase sum
                    throw new UnsupportedOperationException("left pointer move not implemented");
                } else {
                    // TODO: move right pointer to the left to decrease sum
                    throw new UnsupportedOperationException("right pointer move not implemented");
                }
            }
        }
        return result;
    }
}
```

**Min Stack / JavaScript / L3 — API accepted, but remaining answer supplied in comments:**

```javascript
var MinStack = function() {
    // Each element is a pair: [value, minSoFar]
    this.stack = [];
};

MinStack.prototype.push = function(val) {
    const newMin = this._computeNewMin(val);
    this.stack.push([val, newMin]);
};

MinStack.prototype._computeNewMin = function(val) {
    if (this.stack.length === 0) {
        return val;
    }
    // TODO: compute the minimum between val and the previous minimum
    // const prevMin = this.stack[this.stack.length - 1][1];
    // return Math.min(prevMin, val);
    throw new Error("_computeNewMin not implemented");
};

MinStack.prototype.pop = function() {
    if (this.stack.length === 0) {
        throw new Error("pop on empty stack");
    }
    this.stack.pop();
};

MinStack.prototype.top = function() {
    if (this.stack.length === 0) {
        throw new Error("top on empty stack");
    }
    return this.stack[this.stack.length - 1][0];
};

MinStack.prototype.getMin = function() {
    if (this.stack.length === 0) {
        throw new Error("getMin on empty stack");
    }
    // TODO: retrieve the stored minimum from the top pair
    // return this.stack[this.stack.length - 1][1];
    throw new Error("getMin not implemented");
};
```

**Number of Islands / C++ / L1 — actual malformed code string, not decoded:**

```text
#include <vector>\n#include <stdexcept>\nusing namespace std;\n\nclass Solution {\npublic:\n    int numIslands(vector<vector<char>>& grid) {\n        if (grid.empty() || grid[0].empty()) {\n            return 0;\n        }\n        int m = grid.size();\n        int n = grid[0].size();\n        int islands = 0;\n        // Scan the grid; when we see land, we start a new island.\n        for (int i = 0; i < m; ++i) {\n            for (int j = 0; j < n; ++j) {\n                if (grid[i][j] == '1') {\n                    ++islands;\n                    // Flood‑fill this island (implementation pending).\n                    _dfs(grid, i, j);\n                }\n            }\n        }\n        return islands;\n    }\n\nprivate:\n    void _dfs(vector<vector<char>>& grid, int i, int j) {\n        // TODO: depth‑first flood fill to mark all cells of the current island.\n        throw runtime_error(\"DFS not implemented\");\n    }\n};
```

## Prioritized next steps for review

1. Close the **commented-answer gap**, including short one- or two-line executable recipes. Min Stack passed the API while giving away both remaining methods; Two Sum passed with the exact return expression in a comment. Preserve ordinary conceptual hints.
2. Make malformed code strings report a clear **escaped-newline/syntax failure** before or alongside TODO validation. The current Islands error obscures the actual delivery defect. Do not silently turn malformed text into accepted source without revalidating.
3. Guard the submission template and incomplete paths: do not redeclare supplied node classes; reject loops that skip the required operation and return a plausible wrong result, as in Reverse Linked List L2.
4. Enforce genuine executable L1→L2→L3 progression without giving the missing implementation in comments, as Maximum Depth illustrates. Re-test with another strictly capped live round only after targeted changes and offline regression checks.

This report records findings only. No new Groq calls, code fixes, commits, or pushes follow it.
