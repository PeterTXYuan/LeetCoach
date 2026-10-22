# LeetCoach 40-problem pre-push data integrity audit

**Audit date:** 2026-10-22 UTC. **Recommendation: NO-GO for a data-correctness push in the present state.** The SQLite expansion and cardinality are sound, but Group Anagrams has an invalid example output, Reverse Linked List omits an official optional follow-up, and legacy submission shells and displayed statement quotes differ from the current official pages. Three approach choices are explicitly teaching baselines that fail mandatory complexity requirements. This is a data/content review; no Groq call, generation policy change, seed edit, commit, or push was made.

## Evidence and method

I queried LeetCode's own `question(titleSlug)` GraphQL response for **each of the 40 supported slugs** on 2026-10-22. I compared `questionFrontendId`, `titleSlug`, `title`, `difficulty`, HTML problem text, all ordered examples, constraints, and the official `python3`, `java`, `javascript`, and `cpp` code snippets directly with the current seed. All 40 official records were available. I separately queried the 40 distinct off-catalog related-card targets from the same official source. The official page for each supported problem is linked in the table below; the API snapshots and comparison scripts are local, ignored files under `backend/evaluation_runs/catalog_40_pre_push_audit/` and are **not** proposed for Git. These checks did not use earlier reports, test digests, or Groq evaluations as evidence.

For the status table, **FAIL** means at least one confirmed seed/source mismatch or submission-invalid teaching approach, including low-severity literal quote and signature-fidelity differences; it does not mean that every field of that problem is wrong. **PASS** means no discrepancy was found in the reviewed official facts, templates, approaches, signals, and related cards. **UNVERIFIED** would mean official facts could not be checked; no problem-level row needed it because all 40 official records were retrieved. `E/C` gives verified example/constraint counts. `T` = official template declaration differs; `E` = example error; `F` = omitted follow-up; `Q` = nonverbatim text displayed as a statement quote; `B` = teaching-only approach violates a mandatory requirement.

By that strict status definition, **24 PASS, 16 FAIL, 0 problem-level UNVERIFIED**. The bulk of FAIL rows are legacy shell spelling or quote fidelity, not wrong algorithm statements.

| Official problem | E/C | Approaches | Status | Findings |
|---|---:|---:|---|---|
| [1 Two Sum](https://leetcode.com/problems/two-sum/description/) | 3/4 | 2 | FAIL | T |
| [217 Contains Duplicate](https://leetcode.com/problems/contains-duplicate/description/) | 3/2 | 2 | FAIL | T |
| [242 Valid Anagram](https://leetcode.com/problems/valid-anagram/description/) | 2/2 | 2 | FAIL | Q |
| [49 Group Anagrams](https://leetcode.com/problems/group-anagrams/description/) | 3/3 | 2 | FAIL | T, E |
| [125 Valid Palindrome](https://leetcode.com/problems/valid-palindrome/description/) | 3/2 | 2 | PASS | - |
| [167 Two Sum II - Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/description/) | 3/5 | 2 | FAIL | T |
| [15 3Sum](https://leetcode.com/problems/3sum/description/) | 3/2 | 2 | FAIL | T, Q |
| [121 Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/description/) | 2/2 | 2 | FAIL | T, Q |
| [3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/description/) | 3/2 | 3 | PASS | - |
| [424 Longest Repeating Character Replacement](https://leetcode.com/problems/longest-repeating-character-replacement/description/) | 2/3 | 2 | FAIL | Q |
| [20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/description/) | 5/2 | 2 | PASS | - |
| [155 Min Stack](https://leetcode.com/problems/min-stack/description/) | 1/3 | 2 | FAIL | T, B |
| [739 Daily Temperatures](https://leetcode.com/problems/daily-temperatures/description/) | 3/2 | 2 | FAIL | T, Q |
| [704 Binary Search](https://leetcode.com/problems/binary-search/description/) | 2/4 | 2 | FAIL | T, B |
| [33 Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/description/) | 3/5 | 2 | FAIL | T, Q, B |
| [206 Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/description/) | 3/2 | 2 | FAIL | T, F |
| [21 Merge Two Sorted Lists](https://leetcode.com/problems/merge-two-sorted-lists/description/) | 3/3 | 2 | FAIL | T |
| [104 Maximum Depth of Binary Tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/description/) | 2/2 | 2 | FAIL | T |
| [200 Number of Islands](https://leetcode.com/problems/number-of-islands/description/) | 2/4 | 2 | PASS | - |
| [70 Climbing Stairs](https://leetcode.com/problems/climbing-stairs/description/) | 2/1 | 2 | FAIL | Q |
| [238 Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/description/) | 2/3 | 2 | PASS | - |
| [347 Top K Frequent Elements](https://leetcode.com/problems/top-k-frequent-elements/description/) | 3/4 | 1 | PASS | - |
| [128 Longest Consecutive Sequence](https://leetcode.com/problems/longest-consecutive-sequence/description/) | 3/2 | 1 | PASS | - |
| [36 Valid Sudoku](https://leetcode.com/problems/valid-sudoku/description/) | 2/3 | 1 | PASS | - |
| [11 Container With Most Water](https://leetcode.com/problems/container-with-most-water/description/) | 2/3 | 2 | PASS | - |
| [150 Evaluate Reverse Polish Notation](https://leetcode.com/problems/evaluate-reverse-polish-notation/description/) | 3/2 | 1 | PASS | - |
| [22 Generate Parentheses](https://leetcode.com/problems/generate-parentheses/description/) | 2/1 | 1 | PASS | - |
| [853 Car Fleet](https://leetcode.com/problems/car-fleet/description/) | 3/6 | 1 | PASS | - |
| [153 Find Minimum in Rotated Sorted Array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/description/) | 3/5 | 1 | PASS | - |
| [74 Search a 2D Matrix](https://leetcode.com/problems/search-a-2d-matrix/description/) | 2/4 | 1 | PASS | - |
| [875 Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/description/) | 3/3 | 1 | PASS | - |
| [981 Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/description/) | 1/5 | 1 | PASS | - |
| [567 Permutation in String](https://leetcode.com/problems/permutation-in-string/description/) | 2/2 | 1 | PASS | - |
| [226 Invert Binary Tree](https://leetcode.com/problems/invert-binary-tree/description/) | 3/2 | 1 | PASS | - |
| [100 Same Tree](https://leetcode.com/problems/same-tree/description/) | 3/2 | 1 | PASS | - |
| [543 Diameter of Binary Tree](https://leetcode.com/problems/diameter-of-binary-tree/description/) | 2/2 | 1 | PASS | - |
| [110 Balanced Binary Tree](https://leetcode.com/problems/balanced-binary-tree/description/) | 3/2 | 1 | PASS | - |
| [994 Rotting Oranges](https://leetcode.com/problems/rotting-oranges/description/) | 3/4 | 1 | PASS | - |
| [198 House Robber](https://leetcode.com/problems/house-robber/description/) | 2/2 | 2 | PASS | - |
| [322 Coin Change](https://leetcode.com/problems/coin-change/description/) | 3/3 | 1 | PASS | - |

**Coverage:** 40/40 official identities (number, slug, title, difficulty) agree; 103/103 official example slots are present and ordered; 102/103 example input/output pairs agree; 115/115 constraint slots and numeric bounds agree. The 45 stored example explanations were also read for factual contradictions; none was confirmed. The descriptions were read against the official task text, including rules outside the Constraints list: one-based indices and O(1) space in Two Sum II; zero-only-when-no-profit stock trading; the O(log n) search requirements; Min Stack's O(1) operations; Product of Array Except Self's no-division/O(n) rule; Valid Sudoku's partial-board rule; and Car Fleet's arrival-at-target merge rule. Official follow-ups for Two Sum, Valid Anagram, Product of Array Except Self, and Top K are correctly treated as optional. Reverse Linked List is the exception below. LeetCode's public question response did not establish per-problem runtime or memory limits; all seed `timeLimitMs` and `memoryLimitMb` fields remain `null` and those limits are **UNVERIFIED**, not invented.

## Confirmed specification discrepancies

| Severity | Exact seed field/location | Current value | Expected from official page |
|---|---|---|---|
| High | `backend/app/verified_problem_specs.py:66`, `VERIFIED_PROBLEM_SPECS["group-anagrams"]["examples"][2]["output"]` | `[["a"]` | `[["a"]]` (one additional closing bracket). The current value is malformed JSON-like output, despite the example count test passing. |
| Medium | `backend/app/verified_problem_specs.py:157`, `VERIFIED_PROBLEM_SPECS["reverse-linked-list"]["description"]` / absent optional-follow-up metadata | Describes only the required reversal | Preserve the required task and add the official **optional** follow-up: implement both iterative and recursive reversal. The existing two approaches happen to cover both, but the problem specification does not say so. |

I found no incorrect official problem identity, missing official example, missing constraint, invented time/memory limit, or other confirmed task-rule omission. The source descriptions are original restatements rather than verbatim LeetCode text; differences of wording alone were not called errors.

## Submission templates: 160 checked

All 160 shells have the required callable class/function names, method sets, argument counts, and return-type shape. This includes the provided `TreeNode`/`ListNode` structures; Min Stack's constructor plus four methods; and TimeMap's constructor, `set`, and `get` in all four languages. The seed correctly treats LeetCode node declarations as supplied structures, not as user-defined replacements. TimeMap's C++ `public: TimeMap()` being on one line is valid formatting. The new 20 problems' 80 callable declarations matched the current official snippets. The **16 literal declaration differences** below are in the original 20 and are mostly type-spelling or argument-name fidelity, not proven LeetCode rejection:

| Problem/language; seed file line | Current field value (relevant fragment) | Official expected declaration fragment |
|---|---|---|
| Two Sum/Python; `backend/app/stable_data.py:365` | `nums: List[int]`, `-> List[int]` | `nums: list[int]`, `-> list[int]` |
| Contains Duplicate/Python; `backend/app/stable_data.py:374` | `nums: List[int]` | `nums: list[int]` |
| Group Anagrams/Python; `backend/app/stable_data.py:392` | `strs: List[str]`, `-> List[List[str]]` | `strs: list[str]`, `-> list[list[str]]` |
| Two Sum II/Python; `backend/app/stable_data.py:410` | `numbers: List[int]`, `-> List[int]` | `numbers: list[int]`, `-> list[int]` |
| 3Sum/Python; `backend/app/stable_data.py:419` | `nums: List[int]`, `-> List[List[int]]` | `nums: list[int]`, `-> list[list[int]]` |
| Best Time to Buy and Sell Stock/Python; `backend/app/stable_data.py:428` | `prices: List[int]` | `prices: list[int]` |
| Daily Temperatures/Python; `backend/app/stable_data.py:474` | `temperatures: List[int]`, `-> List[int]` | `temperatures: list[int]`, `-> list[int]` |
| Binary Search/Python; `backend/app/stable_data.py:483` | `nums: List[int]` | `nums: list[int]` |
| Search in Rotated Sorted Array/Python; `backend/app/stable_data.py:492` | `nums: List[int]` | `nums: list[int]` |
| Reverse Linked List/Python; `backend/app/stable_data.py:501` | `head: Optional[ListNode] -> Optional[ListNode]` | `head: ListNode | None -> ListNode | None` |
| Merge Two Sorted Lists/Python; `backend/app/stable_data.py:510` | `list1/list2: Optional[ListNode]`, `-> Optional[ListNode]` | `list1/list2: ListNode | None`, `-> ListNode | None` |
| Maximum Depth of Binary Tree/Python; `backend/app/stable_data.py:519` | `root: Optional[TreeNode]` | `root: TreeNode | None` |
| Min Stack/Python, Java, JavaScript, C++; `backend/app/stable_data.py:464-467` | `push(... val ...)` | `push(... value ...)` in the corresponding four official snippets; name/arity/types unchanged. |

These refer to `CURATED_PROBLEM_SPECS[slug]["submissionTemplates"][language]` in every row. As a separate smoke check, evaluating the bare Python seed shells without a LeetCode harness raises `NameError` for 12 of the differing `List`/`Optional` shells; the site may supply those names, so this **does not prove LeetCode submission failure**. Bare `TreeNode`/`ListNode` failures also occur with some *official* snippets when the site-provided structures are absent, and were not counted as seed errors. The current seed validator checks nonempty allowed-language templates, not official declaration identity or standalone annotation resolution.

## All 64 approaches and mandatory complexity

I reviewed each of the 64 seeded `name`, `pattern`, `summary`, `thinkingSteps`, and recognition bullets against its problem's official contract. The described algorithms are mathematically coherent at the editorial level; this is not an execution proof of any later generated implementation. Exactly one approach is primary for every problem. The primary approaches satisfy the mandatory asymptotic requirements as described (for hash-based O(n) approaches, the usual expected-time assumption applies). The three **known legacy baselines** below are mathematically correct for answers but **not valid submission strategies under mandatory complexity rules**, even though their seed summaries already admit this:

| Exact seed location and approach ID | Current strategy | Official requirement / expected product treatment |
|---|---|---|
| `backend/app/stable_data.py:219`, `min-stack/scan-for-minimum` | Scan stack on `getMin`: O(n) | [Min Stack](https://leetcode.com/problems/min-stack/description/) requires **O(1) for each operation**. Keep only as a visibly labelled teaching baseline; never imply a compliant submission. |
| `backend/app/stable_data.py:249`, `binary-search/linear-scan` | Scan array: O(n) | [Binary Search](https://leetcode.com/problems/binary-search/description/) requires **O(log n)** runtime. |
| `backend/app/stable_data.py:263`, `search-in-rotated-sorted-array/linear-scan` | Scan array: O(n) | [Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/description/) requires **O(log n)** runtime. |

Other baseline choices remain eligible for the required task: `product-of-array-except-self/prefix-suffix-arrays` uses O(n) extra space but misses only the **optional** O(1)-extra-space follow-up; `top-k-frequent-elements`' better-than-O(n log n) target is stated in an official **follow-up**, and its curated bucket approach supports it. Two Sum's faster-than-quadratic challenge and Valid Anagram's Unicode case are also optional. No further confirmed approach-math error was found.

**UNVERIFIED judge feasibility (distinct from the three confirmed mandatory violations):** the following correct baselines can be prohibitively slow at official maximum input sizes, although their problem statements do not explicitly forbid their complexity: `two-sum/brute-force` O(n²) at n=10⁴; `contains-duplicate/brute-force`, `best-time-to-buy-and-sell-stock/brute-force`, `daily-temperatures/forward-scan`, and `container-with-most-water/all-line-pairs` O(n²) at n=10⁵; `3sum/brute-force` O(n³) at n=3000; `longest-substring-without-repeating-characters/brute-force-substrings` and `longest-repeating-character-replacement/brute-force-windows` at least quadratic if implemented directly at n=10⁵. The data correctly labels these as baselines in summaries or steps, but a passing LeetCode submission is not established. The recursive/tree or grid approaches may also need iterative implementations in recursion-limited languages at the largest depths; this is an implementation caveat, not a mathematical approach error.

## Recognition signals and related problems

The 130 recognition bullets are approach-specific and consistent with the tasks/approaches on editorial review. Nine stored `quote` fields, however, read as direct statement quotations but are paraphrases or reversed wording. This is a **low-severity quote-fidelity** issue, not an algorithmic defect. The exact fields are `CURATED_PROBLEMS[slug]["approaches"][approach_key]["recognitionSignals"]["quote"]`, located as follows; the suggested expected excerpts are short verbatim substrings from the linked official pages:

| Seed location / approach | Current quote | Official excerpt suitable as replacement |
|---|---|---|
| `backend/app/stable_data.py:77` `valid-anagram/sorting` | `an anagram of t` | `t is an anagram of s` |
| `backend/app/stable_data.py:83` `valid-anagram/frequency-count` | `using all the original letters exactly once` | `t is an anagram of s` |
| `backend/app/stable_data.py:138` `3sum/brute-force` | `three integers such that their sum is zero` | `return all the triplets` |
| `backend/app/stable_data.py:144` `3sum/sort-and-two-pointers` | `unique triplets` | `must not contain duplicate triplets` |
| `backend/app/stable_data.py:153` `best-time-to-buy-and-sell-stock/brute-force` | `choose a single day to buy ... and a different day in the future to sell` | `choosing a single day to buy one stock` |
| `backend/app/stable_data.py:191` `longest-repeating-character-replacement/brute-force-windows` | `replace any character ... at most k times` | `at most k times` |
| `backend/app/stable_data.py:236` `daily-temperatures/forward-scan` | `how many days you have to wait` | `number of days you have to wait` |
| `backend/app/stable_data.py:265` `search-in-rotated-sorted-array/linear-scan` | `return its index` | `return the index of target` |
| `backend/app/stable_data.py:340` `climbing-stairs/memoized-recursion` | `either 1 or 2 steps` | `climb 1 or 2 steps` |

I checked all **108 related cards** for duplicate/self links and compared their target slug, title, and difficulty against official LeetCode identities. All 108 identities agree; 40 distinct target slugs are deliberately outside the supported 40-problem catalog, and all 40 resolve to real official problem pages. The schema stores an external editorial card, not a foreign key to a supported problem, so these links are intentional. The `easier`/`similar`/`harder` groupings are editorial advice, not an assertion that every card's official difficulty must be strictly different; no category inverted Easy/Medium/Hard in the obvious direction. Some affinities are broad (for example Sudoku to Group Anagrams), but that is a recommendation-quality choice, not a factual identity error.

## Database integrity and regression results

Using a **fresh temporary SQLite file**, I ran `alembic upgrade head`, seeded the original 20 as an intermediate state, expanded with the current full seed, and seeded the full catalog again. The final and repeated snapshots were field-for-field equal in all audited row values/IDs for seeded records. All **20 original problem IDs and 41 original approach IDs** survived the expansion. An unrelated `Problem` inserted between full seed runs survived. `PRAGMA foreign_key_check` returned no errors; there were no duplicate unique keys, noncontiguous orders, missing language sets, or problems with other than one primary approach. The resulting totals were **40 problems, 64 approaches, 103 examples, 115 constraints, 160 templates, 108 related cards, 64 recognition-signal sets, and 130 bullets**. The source diff for `backend/app/stable_data.py` and `backend/app/verified_problem_specs.py` adds the new catalog separately; it does not rewrite the original 20 seed entries or their canonical approach keys. The existing local database's original approach IDs remain 1-41. These checks validate seed behavior, not factual correctness of its content.

`py -B -m unittest discover -s backend/tests -q` passed **138 tests**. The test harness's “live” output is from mocked evaluation tests; this audit made no real Groq request. I did not use the passing suite or pre-existing source digests to override the official-page discrepancies above.

## Scaling risks before 100+ problems

- `backend/app/stable_data.py:689-746` validates shape, primary count, approach key/order, and duplicate related slugs, but **not** whether an example output is syntactically well formed, matches the official example, or whether a quoted excerpt is actually in the source. The Group Anagrams error passed existing tests.
- `backend/tests/test_catalog_expansion_40.py:67-131` keeps frozen source digests and expected values that can become stale or reflect the same transcription error. Those tests are useful regression guards, not independent official verification.
- `backend/app/stable_data.py`, `backend/app/verified_problem_specs.py`, `backend/app/catalog_40_facts.py`, and `backend/app/catalog_expansion_40.py` split one catalog across hand-maintained dictionaries. New entries require coordinated identity, examples, descriptions, templates, approaches, related cards, and seed wiring; there is no repeatable source-diff audit in the normal workflow.
- The seed validator accepts any nonempty allowed-language submission shell and any real-looking related card identity. It does not check current official signatures, `List`/`Optional` imports, or external related target existence. Multi-method classes and supplied nodes are especially easy to transcribe incorrectly.
- Some regression tests assert fixed totals of 40, 64, and 160 (for example `backend/tests/test_catalog_expansion_40.py:135-136`, `backend/tests/test_database.py:54-68`, and `backend/tests/test_curated_data.py:38`). They must be updated for expansion, and count-only success will not catch a wrong value in a correctly sized catalog.
- The three noncompliant baseline approaches are present in the normal approach list. Their summaries mention the complexity violation, but a future guidance caller can still select them; if they remain, the UI/API should consistently distinguish “teaching baseline” from “submission-compliant approach.” This is a product/editorial risk, not a schema-integrity failure.

**Push gate:** Correct the malformed Group Anagrams example and record Reverse Linked List's optional follow-up; decide whether to synchronize the 16 legacy declaration differences and nine displayed quotes with current official text. Make the three complexity-violating baseline choices unmistakably teaching-only before representing the entire catalog as submission-ready. Then rerun this official comparison, the fresh seed check, and backend regressions. No questionable seed value was silently modified in this audit.
