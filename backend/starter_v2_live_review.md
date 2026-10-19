# Starter Code v2 live review — October 18, 2026

Ran `py -B -m evaluation.starter_v2 --live --max-calls 8 --pace-seconds 12 --capture-raw --output-dir evaluation_runs/starter_v2_live` with the configured `openai/gpt-oss-120b` Groq model. The evaluator made **exactly 8 real calls**, one per problem/approach/language, with no retries or fallback. Its [JSON results](evaluation_runs/starter_v2_live/starter_v2.json) and eight [raw responses](evaluation_runs/starter_v2_live/) are retained locally.

**API-valid batches: 1/8 (12.5%). Human-reviewed batches meeting all teaching requirements: 0/8.** Groq returned all 24 requested levels as JSON. All 24 passed syntax checks and preserved their LeetCode submission signatures; 14/24 passed the per-level structural validator. Seven requests returned HTTP 502 from local validation. There were no Groq HTTP failures or timeouts; provider times ranged from 2.0 to 3.6 seconds. The accepted batch exposes its complete answer in comments, which the validator missed.

In the table, **pass/fail** refers to per-level structural validation; syntax and signatures passed for every row. A batch also requires increasing guidance across all three levels.

| Problem / language | Level 1 | Level 2 | Level 3 | Human review and batch result |
|---|---|---|---|---|
| Two Sum / Python | Pass: small signature and fail-loud TODO | Fail: `SILENT_UNFINISHED_METHOD` (`pass` in the loop) | Pass: map lookup and storage; only the return pair remains | Levels add structure, but L2 uses a no-op and L3 leaves only a one-line task. **Rejected.** |
| 3Sum / Java | Pass: signature and TODO | Fail: `MISSING_UNFINISHED_PLACEHOLDER`; silently returns an empty list | Fail: `UNSAFE_UNFINISHED_LOOP`; no pointer update can end the loop | Guidance increases, but L2 can give a wrong answer and L3 can hang. **Rejected.** |
| Binary Search / C++ | Pass: signature and throw | Pass: bounds and midpoint with fail-loud TODO | Fail: `UNREACHABLE_PLACEHOLDER`; `else if (/* TODO */ false)` makes the leftward branch dead | Guidance increases and remains unfinished, but L3's control flow is misleading. **Rejected.** |
| Min Stack / JavaScript | Fail: `SILENT_UNFINISHED_METHOD`; constructor says TODO although it already initializes the stack | Pass: minimum calculation and unfinished methods | Pass: `push`/`pop` done; `top`/`getMin` remain | Approach and progression are sound; L1 has a stale, misleading TODO. **Rejected.** |
| Reverse Linked List / Python | Fail: `MISSING_MEANINGFUL_TODO`; TODO is in a docstring rather than a comment | Pass structurally, but comments spell out the entire reversal loop | Fail: `UNREACHABLE_CODE`; the pointer updates follow an unconditional raise | L2 reveals the algorithm in comments; L3 gives the central missing assignment as an example. **Rejected.** |
| Maximum Depth / Java | Pass: base case and throw | Pass: both recursive calls, with the final formula given in a TODO | Pass individually, but resets to an empty helper | Batch fails `INVALID_LEVEL_PROGRESSION`: L3 offers less usable structure than L2. **Rejected.** |
| Number of Islands / C++ | Fail: `MISSING_UNFINISHED_PLACEHOLDER` | Fail: same reason, despite a fail-loud DFS helper | Fail: same reason; DFS silently omits neighbor exploration | L1/L2 are **false validator rejections**: `throw runtime_error(...)` compiles but is not in the accepted throw pattern. L3 really is unsafe: it counts land cells rather than islands. **Rejected.** |
| Climbing Stairs / JavaScript | Pass: minimal fail-loud scaffold | Pass: memo and recursive helper with TODO | Pass: base cases/cache, but the remaining complete recurrence, store, and return are written in comments | Increasing structure and valid API response, yet L3 leaks the entire answer. **Human review fails.** |

Three representative **actual Groq outputs** follow. They are copied from the raw response fields without editing.

**Reverse Linked List, Python, Level 2:** syntactically valid and unfinished at runtime, but its commented “example steps” disclose the core algorithm.

```python
import typing
from typing import Optional
# Definition for singly-linked list node is assumed to be provided by the platform.

class Solution:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        """Iterative reversal with scaffolded loop.
        TODO: Complete the loop body.
        """
        if head is None:
            return None

        prev = None
        curr = head
        while curr is not None:
            # TODO: Save the next node, reverse the current pointer, and advance.
            # Example steps (uncomment and complete as needed):
            # next_node = curr.next
            # curr.next = prev
            # prev = curr
            # curr = next_node
            raise NotImplementedError("Loop body not completed")
        # After the loop, 'prev' points to the new head.
        return prev
```

**Number of Islands, C++, Level 2:** meaningful unfinished DFS; the local validator rejects the valid `runtime_error` throw.

```cpp
#include <vector>
#include <stdexcept>
using namespace std;

class Solution {
public:
    int numIslands(vector<vector<char>>& grid) {
        if (grid.empty() || grid[0].empty()) return 0;
        int m = grid.size();
        int n = grid[0].size();
        int islands = 0;
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < n; ++j) {
                if (grid[i][j] == '1') {
                    ++islands;
                    _dfs(grid, i, j); // mark the whole island
                }
            }
        }
        return islands;
    }

private:
    void _dfs(vector<vector<char>>& grid, int row, int col) {
        // TODO: perform depth‑first flood fill to mark visited land cells
        throw runtime_error("NotImplemented: _dfs");
    }
};
```

**Climbing Stairs, JavaScript, Level 3:** accepted by the API, but the three commented lines supply the entire missing solution.

```javascript
var climbStairs = function(n) {
    const memo = {};

    function dfs(steps) {
        // Base case: exactly at the top – one valid sequence (do nothing more)
        if (steps === 0) return 1;
        // Base case: overshoot – no valid sequence
        if (steps < 0) return 0;

        // Return cached result if we have computed it before
        if (memo.hasOwnProperty(steps)) {
            return memo[steps];
        }

        // TODO: combine the results of taking 1 step and taking 2 steps
        // const result = dfs(steps - 1) + dfs(steps - 2);
        // memo[steps] = result;
        // return result;

        // Placeholder to remind the student to finish the implementation
        throw new Error("NotImplementedException: recursion logic not completed");
    }

    return dfs(n);
};
```

**Assessment.** Groq responded reliably and used the right approaches and signatures, but this prompt/validator combination is not ready for users: most batches fail delivery, several unfinished paths silently return a wrong result or can loop forever, and comments sometimes hand students the answer. The failures are generation or validation issues, not timeout or Groq availability issues.

**Recommended fixes for review:** (1) make the model avoid `pass`, silent placeholder returns, dead branches, non-progressing loops, and commented complete algorithms; preserve genuine L1→L2→L3 progression; (2) recognize fail-loud C++ `runtime_error` and decide whether a Python docstring TODO is acceptable; (3) add checks or focused human review for answer recipes in comments and cases where a later level removes earlier scaffolding. This report makes no implementation changes and does not start another live run.
