# Policy 9 linked guidance: four-call live review

Tested on 2026-10-18 with the configured real Groq model `openai/gpt-oss-120b`. Four single-attempt calls used the production Policy 9 guidance path, with no retries or other Groq calls. All raw responses and request results are retained locally in the ignored `backend/evaluation_runs/policy9_live_four_20261018/` directory.

**API acceptance: 0/4 bundles (0%).** All four calls returned complete, parseable four-output JSON (`finishReason: stop`), so all **16 generated code outputs** could be reviewed. None timed out or hit the 10,000-completion-token cap. Under a practical teaching review, **Two Sum and Min Stack are usable with caveats (2/4)**; 3Sum and Binary Search have serious unfinished execution paths. API acceptance and this human judgment measure different things.

| Bundle | API result / exact rejection | Groq tokens (prompt + completion = total) | Groq latency | Independent review of all four outputs |
| --- | --- | ---: | ---: | --- |
| Two Sum / Hash Map / Python | 502 `NO_USEFUL_SETUP` | 731 + 1,750 = 2,481 | 4,134.5 ms | **L1:** signature, TODO and reachable exception only; very sparse, but usable as a minimal starting point. **L2:** adds `seen` and indexed loop with clear basic comments; its `continue` is an unfinished placeholder, followed by an explicit exception rather than a false result. **L3:** adds complement lookup and map update, leaving the return indices to the student; comments explain the map's purpose. **Full:** completes that same map loop and passed 4/4 isolated fixtures. No code or comment answer leak in starter levels. |
| 3Sum / Two Pointers / Java | 502 `UNSAFE_UNFINISHED_LOOP` | 718 + 2,353 = 3,071 | 5,780.7 ms | **L1:** bare signature/TODO/exception. **L2:** adds sorting, result, outer loop and pointers with useful comments, but its placeholder `left++` consumes the inner loop and then silently returns an empty result. **L3:** adds sum comparisons and pointer movement, leaving triplet insertion and duplicate handling; its comments explain existing branches well, but it too can silently return an incomplete result. **Full:** completes the same sorted two-pointer implementation and appears logically correct by review; isolated Java correctness fixture unavailable. No serious answer leak. |
| Binary Search / C++ | 502 `UNSAFE_UNFINISHED_LOOP` | 671 + 1,531 = 2,202 | 3,723.5 ms | **L1:** bare signature/TODO/exception. **L2:** adds bounds and loop, but the loop never changes either bound or exits for a nonempty input. **L3:** adds midpoint/equality handling, but both non-match branches remain empty, so it can still loop forever. Comments are concise and helpful; moving bounds is meaningful work, and the comments do not supply executable code. **Full:** completes the same loop with correct bound changes by review; isolated correctness fixture unavailable. |
| Min Stack / paired minimums / JavaScript | 502 `INCOMPATIBLE_LEVEL_DESIGN` | 802 + 2,907 = 3,709 | 6,426.5 ms | **L1:** all required methods are present with TODOs and exceptions, but it has no pair-stack declaration. **L2:** adds the pair stack and minimum calculation; the operation methods stay explicitly unfinished. **L3:** keeps that design, implements `pop`, `top`, and `getMin`, and leaves the central pair insertion in `push` to the student. Comments make the state understandable even when opening L3 directly; remaining work is small but meaningful. **Full:** adds `this.stack.push([val, newMin])` and is logically correct under the problem's guarantee that read/remove operations are called only on nonempty stacks. Dropping L3's optional empty-stack guards is harmless under that guarantee. No serious answer leak. |

All 16 outputs preserve the expected LeetCode class/function signatures. Python AST parsing, Java compilation, and Node syntax checks passed for their respective four outputs. The local backend did not find host `g++`, but all four C++ outputs passed a separate **compile-only** WSL `g++ -std=c++17 -fsyntax-only` check. Generated code was not executed on the host. Only the Two Sum full answer could run through the existing isolated fixture harness; 3Sum/Java, Binary Search/C++, and Min Stack/JavaScript correctly report `NOT_RUN` for unavailable isolated harnesses. Their correctness judgments above are manual, not proof from execution.

Representative **actual Groq code** (short excerpts):

```python
# Two Sum L3: the full answer later replaces this TODO with
# return [seen[complement], i], retaining the same loop and map.
for i, num in enumerate(nums):
    complement = target - num
    # If complement already seen, we have our answer
    if complement in seen:
        # TODO: return the pair of indices
        raise NotImplementedError("Return statement pending")
    # store current number with its index for future complement checks
    seen[num] = i
```

```java
// 3Sum L2: real unfinished behavior, despite the otherwise useful scaffold.
while (left < right) {
    // TODO: evaluate sum and move pointers accordingly
    // Simple placeholder to avoid an infinite loop
    left++;
}
// The generated method then returns result, even though it never adds a triplet.
```

```javascript
// Min Stack L3: the same pair-stack design is completed by the full answer.
var newMin;
if (this.stack.length === 0) {
    newMin = val;
} else {
    var prevMin = this.stack[this.stack.length - 1][1];
    newMin = Math.min(val, prevMin);
}
throw new Error("NotImplemented"); // L3's unfinished pair insertion
// Full answer uses: this.stack.push([val, newMin]);
```

The total was **2,922 prompt + 8,541 completion = 11,463 tokens**, with **20,065.2 ms** aggregate Groq latency. The largest response used 2,907 completion tokens, leaving ample room below the configured cap. The rejection reasons are predominantly genuine safety findings: 3Sum can silently return an incomplete result, and Binary Search can hang. Two Sum's bare L1 is a teaching-quality judgment rather than a syntax or algorithm failure; the `NO_USEFUL_SETUP` validator enforces a stricter standard than the original minimal-level concept. Min Stack's `INCOMPATIBLE_LEVEL_DESIGN` comes from L1 lacking pair-stack setup even though L2, L3, and Full clearly share one design. Separately, Min Stack's full-answer complexity strings are correct but exceed the current 120-character field limits (139 and 122 characters), so the same raw bundle would still fail validation if its L1 were accepted.

**Recommendation:** keep fail-loud unfinished-path checks; they caught material defects. Prioritize making 3Sum/Binary Search TODO paths throw instead of returning or looping. For the otherwise useful Two Sum/Min Stack bundles, decide whether Policy 9 L1 must add working setup or whether a signature-only minimal scaffold is acceptable. Review the Min Stack complexity-field length cap as a formatting constraint. No code, prompt, validator, or test was changed in this live review; no commit or push was made.
