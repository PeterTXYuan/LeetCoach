# Policy 9 expanded-catalog live review — Phase 1

Run: 2026-10-22 UTC. Configured provider: real Groq `openai/gpt-oss-120b`; one Policy 9 request per row, SDK retries disabled, 12-second pacing, **12 calls total and no retries**. Each call requested L1, L2, L3, and the matching full answer using the primary canonical approach ID read from the 40-problem SQLite catalog. No prompt, validator, application code, or database changes were made for this evaluation. Raw responses and per-call API JSON are retained locally in ignored `backend/evaluation_runs/catalog_40_policy9_live/`.

**API acceptance: 11/12 (91.7%).** All 12 Groq calls returned a four-part raw response with finish reason `stop`; one response failed API validation. Total reported usage was **8,700 prompt + 22,653 completion = 31,353 tokens**. Mean provider latency was **4.58 s** (range 3.41–6.93 s); total provider latency was 54.97 s, excluding pacing. No call reached the 10,000-completion-token cap.

The API's built-in correctness status was `NOT_RUN` for every accepted row because its fixture catalog does not yet cover these new problems. Separately, this evaluation ran the stored official examples for the three Python and three C++ full solutions **inside the existing WSL bubblewrap sandbox**: **15/15 examples passed across 6/6 solutions**. All 18 Python/C++ starter levels passed syntax checks; the three C++ full solutions also compiled in that sandbox. Java and JavaScript execution was **NOT_RUN** because those runtimes are not available inside this sandbox. Their full-solution assessments below are manual logic review, not execution claims. The API did syntax-check accepted Java/JavaScript source; its C++ `SYNTAX_NOT_CHECKED` warnings were resolved by this separate isolated compile.

## Per-problem review of all 48 outputs

`P/C` means prompt/completion tokens. “Pass n/n” is isolated execution on stored official examples. “Manual” never implies executed correctness. Starter TODOs, stopping exceptions, and incomplete loops were judged as scaffolds, not as runnable submissions.

| # | Problem · primary approach · language | API | L1 | L2 | L3 | Full solution | Warnings; P/C; latency |
|---|---|---|---|---|---|---|---|
| 1 | Product of Array Except Self · `two-pass-products` · Python | 200 | Signature/TODO, very bare | Sets output and left pass; comments describe purpose | Completes left pass, leaves right pass; clear comments | **Pass 2/2**; same two-pass design | `NO_USEFUL_SETUP` L1; 730/1798; 4.33 s |
| 2 | Generate Parentheses · `balanced-backtracking` · Python | 200 | Signature and short docstring | Result/helper scaffold; minimal but useful comments | Adds base case and valid branch conditions; recursive calls remain | **Pass 2/2**; completes the same helper | `MISSING_MEANINGFUL_TODO` L1; 623/1501; 3.61 s |
| 3 | Coin Change · `bottom-up-amounts` · Python | 200 | Signature with brief DP idea | Initializes `dp`; explains zero base case | Adds nested loops; leaves transition and final answer | **Pass 3/3**; same bottom-up DP, but changes `inf` sentinel to `amount + 1` | `MISSING_MEANINGFUL_TODO` L1, `INCOMPATIBLE_LEVEL_DESIGN` L2; 681/1907; 4.48 s |
| 4 | Top K Frequent Elements · `frequency-buckets` · Java | 200 | Signature/TODO | Frequency counting and bucket setup are explained | Fills buckets; leaves collection/return | **NOT_RUN**; manual logic review plausible. Full code changes L3's `List<Integer> result` to `int[] result`, weakening exact continuity | `NO_USEFUL_SETUP` L1; 745/2564; 5.79 s |
| 5 | Time Based Key-Value Store · `per-key-timestamp-search` · Java | **502** | Raw signature-only scaffold, unusable encoding | Raw map/pair scaffold, few comments, unusable encoding | Raw `set` plus search TODO, unusable encoding | **NOT_RUN / not served**. Underlying binary-search idea appears plausible, but source is invalid as returned | `CHANGED_SIGNATURE` rejection; 811/2523; 5.82 s |
| 6 | Diameter of Binary Tree · `postorder-heights` · Java | 200 | Signature/TODO | Height helper and shared maximum, with useful comments | Traverses both sides; leaves diameter update | **NOT_RUN**; manual logic review plausible and consistent | `NO_USEFUL_SETUP` L1, `MISSING_UNFINISHED_PLACEHOLDER` L3; 673/1661; 3.86 s |
| 7 | Permutation in String · `fixed-window-counts` · JavaScript | 200 | Signature, length guard, TODO | Required/window frequency arrays; comments explain initial window | Adds sliding window, leaves comparison helper and final check | **NOT_RUN**; manual logic review plausible and consistent | `INCOMPATIBLE_LEVEL_DESIGN` L2; 649/1851; 4.90 s |
| 8 | Car Fleet · `arrival-times` · JavaScript | 200 | Signature/TODO | Sorts cars and computes arrival times; comments useful | **Too complete:** fleet counting is implemented; only `return fleetCount` remains | **NOT_RUN**; manual logic review plausible and consistent with L3 | No API warning; 800/1683; 4.14 s |
| 9 | Rotting Oranges · `multi-source-bfs` · JavaScript | 200 | Signature/TODO | Queue/fresh-count setup | Initial scan, direction vectors and BFS shell; layer processing remains, with explanatory comments | **NOT_RUN**; manual logic review plausible and consistent | `UNSAFE_UNFINISHED_LOOP` L3; 731/1690; 3.89 s |
| 10 | Find Minimum in Rotated Sorted Array · `right-boundary-binary-search` · C++ | 200 | Signature/TODO | Bounds and interval invariant explained | Loop/mid/branch structure; boundary updates remain | **Pass 3/3**; completes same binary search | `SYNTAX_NOT_CHECKED` ×4 by API; all four compiled in sandbox; 764/2510; 6.93 s |
| 11 | Search a 2D Matrix · `flattened-binary-search` · C++ | 200 | Signature/TODO | Virtual-array binary search shell | Converts midpoint to row/column; comparison and bounds remain | **Pass 2/2**; completes same flattened search | `SYNTAX_NOT_CHECKED` ×4 by API; all four compiled in sandbox; 715/1380; 3.41 s |
| 12 | Evaluate Reverse Polish Notation · `operand-stack` · C++ | 200 | Signature/TODO | Stack/token loop and intended result explained | Parses operands, pops operands; operator calculation remains | **Pass 3/3**; completes same stack evaluation | `SYNTAX_NOT_CHECKED` ×4 by API; all four compiled in sandbox; 778/1585; 3.81 s |

Most accepted bundles follow one design through all four stages, and L2/L3 generally explain the provided logic. The two continuity blemishes are Coin Change's sentinel swap and Top K Frequent Elements' result-container replacement; both preserve the algorithm, but the full answer is not a literal completion of that earlier code. Car Fleet's L3 is a more important teaching defect: all algorithmic work is done, leaving only a trivial return. The API emitted no warning for this. Rotting Oranges' unfinished L3 loop could run forever if pasted as-is, which the API correctly warned about; as an intentionally unfinished scaffold, it is not counted as a generation failure here.

TimeMap is a **generation-format defect, not a validator false positive**. Each of its four source strings contains literal backslash-`n` sequences and **zero actual line breaks** (12, 24, 38, and 40 escaped sequences respectively). For example, the raw L1 begins `import java.util.*;\n\nclass TimeMap {\n...`. That source cannot preserve the required signature as separate lines and cannot compile. Groq returned HTTP-successful JSON, but the API correctly rejected the bundle as `CHANGED_SIGNATURE` and served none of it. There was no retry or fallback.

## Representative actual Groq code

Product of Array Except Self, Python L3: the first pass is supplied and the second remains meaningful work.

```python
class Solution:
    def productExceptSelf(self, nums: list[int]) -> list[int]:
        n = len(nums)
        output = [1] * n
        # First pass: compute left-side products
        left_prod = 1
        for i in range(n):
            output[i] = left_prod
            left_prod *= nums[i]
        # Second pass: compute right-side products and combine
        right_prod = 1
        for i in range(n - 1, -1, -1):
            # TODO: multiply output[i] by right_prod and update right_prod
            raise NotImplementedError("Level3: right pass not completed")
        return output
```

Car Fleet, JavaScript L3: the remaining TODO is only the return, so this level reveals too much.

```javascript
var carFleet = function(target, position, speed) {
    // Pair each car's position with its speed
    const cars = position.map((pos, i) => ({pos, spd: speed[i]}));
    // Sort cars by starting position descending (closest to target first)
    cars.sort((a, b) => b.pos - a.pos);
    // Compute solo arrival times for each car
    const times = cars.map(car => (target - car.pos) / car.spd);
    // Count fleets: a new fleet forms when a car's arrival time is greater than the
    // time of the fleet ahead (currentSlowest). Cars with earlier or equal times
    // merge into that fleet.
    let fleetCount = 0;
    let currentSlowest = 0;
    for (let t of times) {
        if (t > currentSlowest) {
            fleetCount++;
            currentSlowest = t;
        }
        // else: this car joins the fleet ahead
    }
    // TODO: return the total number of fleets
    throw new Error('Not implemented');
};
```

Evaluate Reverse Polish Notation, C++ full answer: the same operand-stack design as L2/L3 completed and passed all three stored official examples in isolation.

```cpp
#include <bits/stdc++.h>
using namespace std;
class Solution {
public:
    int evalRPN(vector<string>& tokens) {
        stack<int> st;
        for (const string& tok : tokens) {
            // Number detection: token may start with '-' or a digit
            if (isdigit(tok[0]) || (tok.size() > 1 && tok[0] == '-')) {
                st.push(stoi(tok));
            } else {
                // Operator handling: pop right then left operand
                int right = st.top(); st.pop();
                int left = st.top(); st.pop();
                int result = 0;
                if (tok == "+") result = left + right;
                else if (tok == "-") result = left - right;
                else if (tok == "*") result = left * right;
                else if (tok == "/") result = left / right; // truncates toward zero
                st.push(result);
            }
        }
        return st.top();
    }
};
```

## Decision and next evaluation

**Conditional GO for a larger evaluation, not a launch-quality correctness claim.** The 11/12 API acceptance and six isolated example passes justify sampling more of the 40-problem catalog. Track malformed escaped-source responses and L3 answer leakage separately; the TimeMap response needs a formatting investigation, and Car Fleet shows that a successful API response can still give away nearly the entire solution. Add isolated Java/JavaScript example execution before reporting measured full-solution correctness in those languages. Keep API `NOT_RUN` distinct from the separate evaluation-only sandbox results. Passing these 15 examples improves confidence only for those six generated answers and does not prove general correctness.
