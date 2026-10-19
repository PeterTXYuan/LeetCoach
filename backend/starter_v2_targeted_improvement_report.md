# Starter Code v2: targeted follow-up

October 18, 2026. This change uses the [eight saved Groq responses](evaluation_runs/starter_v2_live/) for **offline replay only**. No new Groq calls, commits, or pushes were made. The three levels still come from one request and are validated as one batch.

| Change | Previous failure addressed |
|---|---|
| Added four short Starter Code prompt rules covering silent placeholders, dead/fake control flow, commented answers, and increasing guidance. | Two Sum `pass`; 3Sum empty result and stalled loop; Binary Search fake condition; Min Stack stale TODO; Reverse List and Climbing Stairs answer comments; Maximum Depth level regression. Fresh-model effect is unverified. |
| Recognize C++ `throw runtime_error(...)` and `throw std::runtime_error(...)` as fail-loud placeholders. | Number of Islands Levels 1–2 were wrongly rejected despite valid C++ code. |
| Count TODOs in Python function docstrings as meaningful TODOs, while keeping the signature, reachability, and fail-loud checks. | Reverse Linked List Level 1 was wrongly rejected solely because its TODO was in a docstring. |
| Reject a contiguous block of at least three commented executable statements; keep prose and isolated examples allowed. | Reverse Linked List Level 2 and Climbing Stairs Level 3 hid complete algorithms in comments. |
| Added a portable fixture copied exactly from all eight raw JSON responses, plus regression tests for each of the 24 levels and all eight batch decisions. | Protects the identified failure classifications without relying on the ignored evaluation artifacts or making network calls. |

Offline replay after the change:

| Case | Level 1 / 2 / 3 | Batch | Remaining issue |
|---|---|---|---|
| Two Sum / Python | Pass / `SILENT_UNFINISHED_METHOD` / Pass | Rejected | L2 still has `pass`; L3 leaves only a small return task. |
| 3Sum / Java | Pass / `MISSING_UNFINISHED_PLACEHOLDER` / `UNSAFE_UNFINISHED_LOOP` | Rejected | L2 returns an empty result; L3 cannot advance pointers. |
| Binary Search / C++ | Pass / Pass / `UNREACHABLE_PLACEHOLDER` | Rejected | L3 has a dead `false` branch. |
| Min Stack / JavaScript | `SILENT_UNFINISHED_METHOD` / Pass / Pass | Rejected | L1 labels already-complete initialization as TODO. |
| Reverse Linked List / Python | **Pass** / `COMMENTED_OUT_ALGORITHM` / `UNREACHABLE_CODE` | Rejected | L2 gives the answer in comments; L3 raises before pointer updates. |
| Maximum Depth / Java | Pass / Pass / Pass | `INVALID_LEVEL_PROGRESSION` | L3 removes useful L2 structure. |
| Number of Islands / C++ | **Pass / Pass** / `MISSING_UNFINISHED_PLACEHOLDER` | Rejected | L3 silently omits DFS neighbor visits and can return a wrong count. |
| Climbing Stairs / JavaScript | Pass / Pass / `COMMENTED_OUT_ALGORITHM` | Rejected | The formerly API-valid L3 contains the full recurrence, cache write, and return as comments. |

The old captured responses now yield **0/8 accepted batches** for the right safety reasons. This replay is not a measure of how often the revised prompt will succeed on fresh Groq generations. The validator remains heuristic: it cannot prove that code is pedagogically useful or detect every disguised answer, and it deliberately retains the existing checks against silent results, unreachable work, unsafe loops, and poor progression. Previously cached Policy 7 batches are not revalidated on hydration; decide whether to invalidate those caches before release.

Verification: **117 backend tests passed**, **104 frontend tests passed**, `npm run build` passed, and `git diff --check` passed. The fixture's parsed code fields exactly match the eight saved Groq JSON responses.
