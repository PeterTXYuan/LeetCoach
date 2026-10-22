# LeetCoach Policy 9 live quality report — all 40 catalog problems

Phase 1 ran 12 cases; Phase 2 ran each of the remaining 28 once, with exactly seven new requests per language. Both used the configured real Groq model, `openai/gpt-oss-120b`, each problem's SQLite primary canonical approach, one request for L1/L2/L3/Full Solution, and SDK retries disabled. **40 real calls total, no retries.** Phase 2 raw responses and API results are in ignored `backend/evaluation_runs/catalog_40_policy9_phase2/`; Phase 1 artifacts remain in ignored `backend/evaluation_runs/catalog_40_policy9_live/`. The [Phase 1 review](catalog_40_policy9_phase1_live_review.md) has its earlier code excerpts and detailed judgments. This report is the combined evaluation. No application code, prompts, validators, database rows, or internal Full Solution checker were changed; nothing was committed or pushed.

## Results and what was actually tested

| Language | Phase 1 API | Phase 2 API | Combined API | Isolated Full Solutions | Manual-only accepted Full Solutions | Rejected / no served Full Solution |
|---|---:|---:|---:|---:|---:|---:|
| Python | 3/3 | 5/7 | **8/10** | 7 PASS, **1 FAIL** on additional in-constraint stress | 0 | 2 |
| Java | 2/3 | 6/7 | **8/10** | 0; runtime unavailable in sandbox | 8, plausible on review | 2 |
| JavaScript | 3/3 | 7/7 | **10/10** | 0; runtime unavailable in sandbox | 10, plausible on review | 0 |
| C++ | 3/3 | 5/7 | **8/10** | **8 PASS** | 0 | 2 |
| **All** | **11/12** | **23/28** | **34/40 (85%)** | **15 PASS, 1 FAIL, 0 NOT_RUN among 16 executed** | **18 NOT_RUN, manually reviewed** | **6 NOT_RUN; API rejected** |

All **16/16 executed Full Solutions passed their stored official examples**, **40/40 individual examples**: 15/15 in Phase 1 and 25/25 in Phase 2. An additional valid 50×50 all-land Number of Islands case **failed 0/1** with Python `RecursionError`, so its Full Solution is **FAIL for tested correctness**, despite passing both official examples. Counting every isolated case, the result is **40 PASS / 1 FAIL**; counting solutions that passed every case they were run against, **15 PASS / 1 FAIL**. These are representative tests, not proof for all inputs. The six API-rejected bundles were never served and were **NOT_RUN** for correctness; their raw code is syntactically invalid as returned. The 18 accepted Java/JavaScript Full Solutions are **NOT_RUN** for execution, with manual logic assessments only. The API's built-in checker, unchanged here, reported `PASS` for Two Sum, 3Sum, and Min Stack and `NOT_RUN` for the other 31 accepted bundles; the larger execution counts above come from evaluation-only harnesses in the existing WSL bubblewrap sandbox.

Across 40 responses, Groq reported **28,225 prompt tokens**, **77,137 completion tokens**, and **105,362 total tokens**. Mean provider latency was **5.31 s** (range 3.23–9.42 s), total provider latency **212.50 s** excluding pacing and local validation. Every response reported finish reason `stop`; none reached the 10,000-completion-token cap. Phase 2 alone used 74,009 total tokens, with mean provider latency 5.63 s. Phase 1 used 31,353 total tokens, with mean 4.58 s.

## Per-problem review

`P1`/`P2` identify the evaluation phase. `PASS x/y` means isolated execution against stored official examples; `FAIL stress` includes the separate valid stress case. `NOT_RUN · manual` is a review judgment, not execution. Warning counts are from the API response; rejected rows have no served warnings. `P/C` is prompt/completion tokens. All accepted starter levels were reviewed as **unfinished teaching scaffolds**, so TODOs, stopping exceptions, and incomplete loops were not correctness failures.

| Phase | Problem · primary approach · language | API | L1 → L2 → L3 teaching assessment | Full Solution status | Warnings | P/C; latency |
|---|---|---:|---|---|---:|---:|
| P1 | Product of Array Except Self · `two-pass-products` · Python | 200 | Bare signature → left-pass setup → left pass complete, right pass left; clear comments | **PASS 2/2** | 1 | 730/1798; 4.33 s |
| P1 | Generate Parentheses · `balanced-backtracking` · Python | 200 | Signature → helper/result → branch conditions, recursive calls left; useful comments | **PASS 2/2** | 1 | 623/1501; 3.61 s |
| P1 | Coin Change · `bottom-up-amounts` · Python | 200 | Signature → DP base → loops with transition left; Full changes the sentinel value | **PASS 3/3** | 2 | 681/1907; 4.48 s |
| P2 | Two Sum · `hash-map` · Python | 200 | Bare → map/complement loop → only return indices left; L3 gives away nearly all logic | **PASS 3/3** | 1 | 731/1744; 5.31 s |
| P2 | Group Anagrams · `frequency-signature` · Python | 200 | Signature → grouping/helper → count signature, immutable-key conversion left; helper return type changes | **PASS 3/3** | 1 | 700/2570; 5.78 s |
| P2 | 3Sum · `sort-and-two-pointers` · Python | 200 | Signature → sorted outer loop → two pointers, duplicate skipping left; comments thin in L3 but usable | **PASS 3/3** | 1 | 719/1635; 3.99 s |
| P2 | Min Stack · `paired-minimums` · Python | 200 | Five bare methods → pair-stack setup → min calculation/pop, three method bodies left; helpful comments | **PASS 1/1** official; API checker also PASS 2/2 | 3 | 807/3222; 8.95 s |
| P2 | Reverse Linked List · `iterative-pointers` · Python | **502** | All four raw source strings have literal `\n`, no line breaks; unusable | **NOT_RUN**; no served answer | 0 | 662/2731; 8.40 s |
| P2 | Number of Islands · `depth-first-flood-fill` · Python | 200 | Signature → scan/visited → DFS boundary checks, marking/traversal left; comments useful | **FAIL stress**: 2/2 official PASS, 0/1 valid 50×50 case (`RecursionError`) | 1 | 728/2018; 4.66 s |
| P2 | House Robber · `rolling-choices` · Python | **502** | All four raw strings have literal `\n`; unusable | **NOT_RUN**; no served answer | 0 | 650/1414; 5.80 s |
| P1 | Top K Frequent Elements · `frequency-buckets` · Java | 200 | Signature → frequencies/buckets → filling buckets; Full replaces L3's list result with array, weakening continuity | **NOT_RUN · manual plausible** | 1 | 745/2564; 5.79 s |
| P1 | Time Based Key-Value Store · `per-key-timestamp-search` · Java | **502** | All four raw strings have literal `\n`; unusable | **NOT_RUN**; no served answer | 0 | 811/2523; 5.82 s |
| P1 | Diameter of Binary Tree · `postorder-heights` · Java | 200 | Signature → height helper → traversal with diameter update left; good explanation | **NOT_RUN · manual plausible** | 2 | 673/1661; 3.86 s |
| P2 | Contains Duplicate · `hash-set` · Java | 200 | Signature → set/scan → only `return true` left; L3 too complete | **NOT_RUN · manual plausible** | 2 | 639/1998; 4.65 s |
| P2 | Two Sum II · `two-pointers` · Java | **502** | All four raw strings have literal `\n`; unusable | **NOT_RUN**; no served answer | 0 | 763/2005; 5.13 s |
| P2 | Best Time to Buy and Sell Stock · `running-minimum` · Java | 200 | Signature → min/profit state → traversal with profit update left; useful comments | **NOT_RUN · manual plausible** | 1 | 652/1915; 4.44 s |
| P2 | Daily Temperatures · `monotonic-stack` · Java | 200 | Signature → stack/answer → push plus unresolved pop loop; comments explain the invariant | **NOT_RUN · manual plausible** | 3 | 667/1360; 4.60 s |
| P2 | Search in Rotated Sorted Array · `modified-binary-search` · Java | 200 | Signature → bounds/loop → sorted-half test with decision logic left; clear progression | **NOT_RUN · manual plausible** | 1 | 717/1651; 4.29 s |
| P2 | Merge Two Sorted Lists · `iterative-merge` · Java | 200 | Signature → dummy node → merge-loop shell; unfinished non-progressing loop is clearly marked | **NOT_RUN · manual plausible** | 3 | 685/1507; 4.11 s |
| P2 | Balanced Binary Tree · `bottom-up-balance` · Java | 200 | Signature/helper → base and sentinel → only height return left; L3 too complete | **NOT_RUN · manual plausible; deep recursion untested** | 1 | 683/1662; 5.52 s |
| P1 | Permutation in String · `fixed-window-counts` · JavaScript | 200 | Signature → count arrays → sliding window, comparison helper left; useful comments | **NOT_RUN · manual plausible** | 1 | 649/1851; 4.90 s |
| P1 | Car Fleet · `arrival-times` · JavaScript | 200 | Signature → sorted arrival times → counting entirely present, only return left; L3 reveals answer | **NOT_RUN · manual plausible** | 0 | 800/1683; 4.14 s |
| P1 | Rotting Oranges · `multi-source-bfs` · JavaScript | 200 | Signature → queue/count → initial scan and BFS shell; layer work remains; unfinished loop warned | **NOT_RUN · manual plausible** | 1 | 731/1690; 3.89 s |
| P2 | Valid Anagram · `frequency-count` · JavaScript | 200 | Length guard → frequency build → subtraction complete, only redundant final verification left | **NOT_RUN · manual plausible** | 0 | 615/1754; 4.22 s |
| P2 | Valid Palindrome · `two-pointers` · JavaScript | 200 | Signature → pointers → character skipping, comparison left; explanatory comments | **NOT_RUN · manual plausible** | 0 | 660/2117; 5.58 s |
| P2 | Longest Substring Without Repeating Characters · `sliding-window-set` · JavaScript | 200 | Signature → window state → duplicate handling complete, only max-length update left; L3 thin | **NOT_RUN · manual plausible** | 1 | 673/2158; 6.28 s |
| P2 | Longest Repeating Character Replacement · `sliding-window-frequency` · JavaScript | 200 | Signature → counts/window → shrinking; L3 TODO incorrectly asks to recompute max frequency, unlike correct Full | **NOT_RUN · manual plausible**, but L3 explanation conflicts with Full | 0 | 643/1825; 6.82 s |
| P2 | Binary Search · `binary-search` · JavaScript | 200 | Signature → bounds/loop → branch updates complete, only `return mid` left; L3 too complete | **NOT_RUN · manual plausible** | 0 | 658/1194; 6.19 s |
| P2 | Maximum Depth of Binary Tree · `depth-first-search` · JavaScript | 200 | Signature → null case → both recursive depths, only `1 + max` return left; L3 too complete | **NOT_RUN · manual plausible; deep recursion untested** | 0 | 608/1503; 4.29 s |
| P2 | Same Tree · `paired-tree-recursion` · JavaScript | 200 | Signature → null cases → comparison delegates to added helper; helper TODO remains | **NOT_RUN · manual plausible** | 2 | 678/1901; 6.86 s |
| P1 | Find Minimum in Rotated Sorted Array · `right-boundary-binary-search` · C++ | 200 | Signature → bounds → mid/branches, boundary updates left; good comments | **PASS 3/3** | 4 | 764/2510; 6.93 s |
| P1 | Search a 2D Matrix · `flattened-binary-search` · C++ | 200 | Signature → virtual binary search → row/column mapping, comparisons left | **PASS 2/2** | 4 | 715/1380; 3.41 s |
| P1 | Evaluate Reverse Polish Notation · `operand-stack` · C++ | 200 | Signature → stack loop → operand parsing, operator calculation left | **PASS 3/3** | 4 | 778/1585; 3.81 s |
| P2 | Valid Parentheses · `stack` · C++ | **502** | All four raw strings have literal `\n`; unusable | **NOT_RUN**; no served answer | 0 | 679/1896; 8.05 s |
| P2 | Climbing Stairs · `rolling-dynamic-programming` · C++ | 200 | Signature → rolling state → loop, `next` arithmetic left; reasonable but small L3 task | **PASS 2/2** | 6 | 621/1816; 4.49 s |
| P2 | Longest Consecutive Sequence · `sequence-start-set` · C++ | 200 | Signature → set setup → sequence-start loop, advancing count left; comments useful | **PASS 3/3** | 4 | 697/2073; 5.01 s |
| P2 | Valid Sudoku · `row-column-box-sets` · C++ | 200 | Signature → row/column/box sets → conflict checks, set insertion left; helpful but L3 small | **PASS 2/2** | 6 | 1157/3127; 9.42 s |
| P2 | Container With Most Water · `inward-two-pointers` · C++ | **502** | All four raw strings have literal `\n`; unusable | **NOT_RUN**; no served answer | 0 | 655/2686; 6.14 s |
| P2 | Koko Eating Bananas · `speed-binary-search` · C++ | 200 | Signature → speed bounds → binary search complete, hours helper left; meaningful task | **PASS 3/3** | 4 | 710/1692; 5.30 s |
| P2 | Invert Binary Tree · `recursive-swap` · C++ | 200 | Signature → null base → swap/left recursion, right recursion and return left | **PASS 3/3** | 4 | 668/1310; 3.23 s |

## Recurring defects and interpretation

1. **Escaped-source API failures: 6/40.** All six HTTP 502 responses reported `CHANGED_SIGNATURE`, but raw inspection found the same concrete cause: every code field contained literal backslash-`n` sequences and zero real line breaks. This affected Python (2/10), Java (2/10), and C++ (2/10), while JavaScript was 10/10. Groq completed all six requests with finish reason `stop`; these were not timeouts or rate limits. The validator correctly rejected code that would not compile or parse. The defect is response formatting before validation, not a false signature rejection.
2. **L3 sometimes stops after the algorithm is essentially finished.** Car Fleet is the clearest case; Two Sum, Contains Duplicate, Binary Search, Maximum Depth, Valid Anagram, and Balanced Binary Tree show the same pattern to lesser degrees. This is a teaching-quality issue even when the Full Solution is logically sound. L2/L3 comments were generally useful, but a successful API response does not establish educational quality.
3. **A misleading L3 instruction appeared in Longest Repeating Character Replacement.** It tells the student to recompute `maxFreq` on shrink, while the Full Solution intentionally uses a stale maximum in the standard sliding-window method. The Full Solution looks logically sound; the TODO is inconsistent with it.
4. **Number of Islands Full Solution fails a valid input.** Recursive Python DFS passed the two official examples, then raised `RecursionError` on a 50×50 all-land grid, within the catalog's `1 <= m,n <= 300` bounds. The internal checker was `NOT_RUN` for this problem and could not flag it. This is a measured correctness failure, not merely a style concern.
5. **C++ syntax warnings reflect checker coverage.** `SYNTAX_NOT_CHECKED` accounts for 32 of the 66 served warnings because the API has no C++ compiler check there. Phase 1's C++ starter levels and Full Solutions compiled in isolation; Phase 2's accepted C++ Full Solutions compiled and passed examples in isolation. These warnings should not be counted as generated-code failures. Other warning counts: `NO_USEFUL_SETUP` 13, `INCOMPATIBLE_LEVEL_DESIGN` 7, `MISSING_UNFINISHED_PLACEHOLDER` 6, `MISSING_MEANINGFUL_TODO` 3, `UNSAFE_UNFINISHED_LOOP` 3, `INVALID_LEVEL_PROGRESSION` 1, `ADDITIONAL_PUBLIC_ENTRY_POINT` 1. Several flag deliberately unfinished starter logic, which was not penalized under this evaluation's practical standard.

Representative actual output from Number of Islands Full Solution shows the DFS that passed examples but overflowed the stack on the valid stress case:

```python
def dfs(r: int, c: int) -> None:
    if r < 0 or r >= m or c < 0 or c >= n:
        return
    if grid[r][c] != '1' or visited[r][c]:
        return
    visited[r][c] = True
    dfs(r - 1, c)
    dfs(r + 1, c)
    dfs(r, c - 1)
    dfs(r, c + 1)
```

The Longest Repeating Character Replacement L3 contains this actual TODO, while its Full Solution does not recompute `maxFreq`:

```javascript
while ((right - left + 1) - maxFreq > k) {
    const leftIdx = s.charCodeAt(left) - 65;
    freq[leftIdx]--;
    left++;
    // TODO: recompute maxFreq if necessary
    // Placeholder for missing recompute logic
    throw new Error("NotImplemented");
}
```

**Assessment:** The catalog is ready for further targeted evaluation, but these results do **not** support an unqualified launch-quality claim. The API accepted 85%, with a repeated formatting defect across three languages. The isolated tests established 15 fully passing solutions and one real in-constraint failure; the 18 accepted Java/JavaScript solutions remain unexecuted in a safe runtime. Before relying on broad correctness or teaching quality, prioritize the escaped-newline defect, add isolated Java/JavaScript example coverage, test larger valid edge cases, and assess L3 answer leakage separately from API acceptance. This report stops at evaluation and recommendations; no fixes were applied.
