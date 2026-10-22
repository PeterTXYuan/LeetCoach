# LeetCoach Phase 1 catalog expansion: 20 → 40

Source audit: 2026-10-22 UTC. The official LeetCode question metadata and code snippets for each linked page were checked before writing the seed. Descriptions, summaries, recognition signals, related reasons, and example explanations are original editorial prose. Official example input/output pairs and numeric constraints are preserved in source order. An independently captured digest per problem in `tests/test_catalog_expansion_40.py` guards the 50 input/output pairs and 60 constraint lines against accidental drift.

| Added problem and official source | No. | Difficulty | Examples | Constraints | Approaches |
| --- | ---: | --- | ---: | ---: | ---: |
| [Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/) | 238 | Medium | 2 | 3 | 2 |
| [Top K Frequent Elements](https://leetcode.com/problems/top-k-frequent-elements/) | 347 | Medium | 3 | 4 | 1 |
| [Longest Consecutive Sequence](https://leetcode.com/problems/longest-consecutive-sequence/) | 128 | Medium | 3 | 2 | 1 |
| [Valid Sudoku](https://leetcode.com/problems/valid-sudoku/) | 36 | Medium | 2 | 3 | 1 |
| [Container With Most Water](https://leetcode.com/problems/container-with-most-water/) | 11 | Medium | 2 | 3 | 2 |
| [Evaluate Reverse Polish Notation](https://leetcode.com/problems/evaluate-reverse-polish-notation/) | 150 | Medium | 3 | 2 | 1 |
| [Generate Parentheses](https://leetcode.com/problems/generate-parentheses/) | 22 | Medium | 2 | 1 | 1 |
| [Car Fleet](https://leetcode.com/problems/car-fleet/) | 853 | Medium | 3 | 6 | 1 |
| [Find Minimum in Rotated Sorted Array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/) | 153 | Medium | 3 | 5 | 1 |
| [Search a 2D Matrix](https://leetcode.com/problems/search-a-2d-matrix/) | 74 | Medium | 2 | 4 | 1 |
| [Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/) | 875 | Medium | 3 | 3 | 1 |
| [Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/) | 981 | Medium | 1 | 5 | 1 |
| [Permutation in String](https://leetcode.com/problems/permutation-in-string/) | 567 | Medium | 2 | 2 | 1 |
| [Invert Binary Tree](https://leetcode.com/problems/invert-binary-tree/) | 226 | Easy | 3 | 2 | 1 |
| [Same Tree](https://leetcode.com/problems/same-tree/) | 100 | Easy | 3 | 2 | 1 |
| [Diameter of Binary Tree](https://leetcode.com/problems/diameter-of-binary-tree/) | 543 | Easy | 2 | 2 | 1 |
| [Balanced Binary Tree](https://leetcode.com/problems/balanced-binary-tree/) | 110 | Easy | 3 | 2 | 1 |
| [Rotting Oranges](https://leetcode.com/problems/rotting-oranges/) | 994 | Medium | 3 | 4 | 1 |
| [House Robber](https://leetcode.com/problems/house-robber/) | 198 | Medium | 2 | 2 | 2 |
| [Coin Change](https://leetcode.com/problems/coin-change/) | 322 | Medium | 3 | 3 | 1 |
| **New coverage** | **20** | **4 Easy / 16 Medium** | **50** | **60** | **23** |

All 20 new entries have a comprehensive approach-neutral task restatement, a concise summary, exactly one primary canonical approach, ordered thinking steps, two short recognition signals per approach, and manually selected related cards. Added related cards: 40. All 20 official examples that include an explanation have a paraphrased explanation in the seed; the remaining examples retain a null explanation. The required O(n) rules for Product of Array Except Self and Longest Consecutive Sequence, O(log n) for Find Minimum in Rotated Sorted Array, and O(log(m*n)) for Search a 2D Matrix are labeled required. Product's extra-space and Top K's time-bound follow-ups are labeled optional. Division is explicitly forbidden for Product of Array Except Self. No per-problem execution time or memory limit was asserted without an authoritative source; both columns remain null.

Source gaps and uncertainty: none were found for the requested title, number, difficulty, examples, constraints, or four-language signatures. The audited pages do not state per-problem execution time and memory limits, so those fields are intentionally unset. Thirty examples have no official explanation and therefore retain a null explanation rather than an invented one.

The four-language templates preserve the official Python, Java, JavaScript, and C++ entry-point names, arguments, and return types: 80 new templates total, 160 across the full catalog. The four TreeNode problems state that LeetCode supplies the node type. TimeMap includes its constructor, `set`, and `get` in all four languages. Its C++ shell keeps the public constructor on the `public:` line so the unchanged Policy 9 declaration checker accepts the constructor; this is valid C++ but may require special attention if a generated answer reformats that declaration.

The exact-sync seed now contains 40 problems, 64 approaches, 103 ordered examples, 115 ordered constraints, 160 templates, and 108 related cards. A local database snapshot before seeding and after two seed runs confirmed the original 20 rows, approach IDs, descriptions, ordered facts, and templates were unchanged. No migration was needed; `alembic upgrade head` and both seed runs completed. Source checks also confirmed that every new recognition-signal quote appears on its official problem page.

Offline verification: **138 backend tests passed**, **100 frontend tests passed**, and `npm run build` passed. The new source-identity, official-fact digest, signature, context, mock API, migration, and repeat-seed checks pass. All **92 new approach/language** mock guidance requests returned starter-only bundles; no new curated mock full answers were manufactured. The mock shells are intentionally basic development fixtures. The evaluation-harness tests use fake clients; **no real Groq request was made**. Policy 9 prompts, validators, generation, cache, and warnings were not changed. `git diff --check` passed. No commit or push was made.

Remaining risks: live Groq output may need separate acceptance testing for the larger variety of signatures and algorithms, particularly TimeMap and trees. The isolated correctness runner does not yet have representative fixtures for the 20 additions, so Policy 9 full answers on these problems can report `NOT_RUN`; syntax and static warnings cannot prove correctness. The recommended next step is a bounded, reviewed live evaluation of representative new problems across four languages, followed by adding safe correctness fixtures where feasible.
