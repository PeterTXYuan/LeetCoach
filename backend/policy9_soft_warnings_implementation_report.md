# Policy 9 soft-warning implementation report

## Outcome

Policy 9 now returns a complete Groq bundle when its JSON fields, required LeetCode entry points, and available syntax checks are sound. Teaching-quality heuristics no longer turn otherwise usable four-output responses into HTTP 502. The response includes scoped `warnings` beside `verification`, so the Coach page shows a warning with the affected Starter Code level or Full Answer. Both existing Regenerate actions still request and replace all four outputs together; a failed request keeps the earlier bundle.

The four **previously captured** live Groq responses were replayed through the updated endpoint with a fake provider and **zero new Groq calls**:

| Case | Before | After | Warning shown |
| --- | --- | --- | --- |
| Two Sum / Hash Map / Python | 502 `NO_USEFUL_SETUP` | 200, fixture `PASS` (4/4) | L1 has sparse setup |
| 3Sum / Two Pointers / Java | 502 `UNSAFE_UNFINISHED_LOOP` | 200, fixture `NOT_RUN` | L2 and L3 unfinished-loop warnings |
| Binary Search / C++ | 502 `UNSAFE_UNFINISHED_LOOP` | 200, fixture `NOT_RUN` | L2/L3 unfinished-loop warnings; syntax not checked by the backend because host `g++` is unavailable |
| Min Stack / paired minimums / JavaScript | 502 `INCOMPATIBLE_LEVEL_DESIGN` | 200, fixture `NOT_RUN` | L1 does not set up the later stack |

The earlier [live review](policy9_live_four_review.md) remains the source for the actual code, token usage, latency, and human assessment. This replay measures acceptance under the new gate; it does **not** make the 3Sum silent returns or Binary Search loops safe to run. Those warnings are now visible only after the corresponding code is revealed. The full answer still stays hidden until its own Generate button is clicked.

## Validation boundary

- **Hard rejection remains:** missing or malformed response fields, empty/oversized code, Markdown-fenced source, changed required submission signatures/classes, actual syntax or compilation errors where a checker is available, provider errors, and token-limit truncation. Syntax-checker unavailability or timeout is disclosed as `SYNTAX_NOT_CHECKED`, not treated as a code defect.
- **Soft warnings:** minimal or duplicate levels, likely answer leaks, TODOs that can return silently or leave loops without progress, missing pair-stack setup, lost working design, recognizable unfinished full-answer branches, and failed representative fixtures. A failed fixture returns `verification: FAIL` plus `CORRECTNESS_FIXTURE_FAILED`; code execution remains confined to the existing WSL bubblewrap sandbox.
- Full-answer complexity descriptions may now be up to 500 characters under the linked route. This accepts the accurate but slightly verbose Min Stack complexity text from the live response without weakening source/signature/syntax checks. Historical independent Starter Code and Full Solution endpoints keep their existing validators.
- Warnings are additive Policy 9 response data. Existing Policy 9 cached bundles without a `warnings` field remain readable; new warnings persist with their bundle. No cache or policy-version reset was needed.

## Verification and limits

- Backend focused tests cover hard signature/syntax failures, soft sparse setup, unsafe unfinished loops, design changes, unfinished answers, failed fixtures, and syntax-checker unavailability. Frontend tests cover warning placement by level, answer warning/failed-fixture display, and clearing warnings when regeneration replaces the bundle.
- Backend suite: **133 passed**. Frontend suite: **100 passed**. Production build: **passed**. `git diff --check`: **passed** (Git printed only line-ending conversion notices). Backend evaluation tests use fake providers; their simulated "live" log lines did not contact Groq.
- No new real Groq requests, commits, or pushes were made for this change.

This is a deliberate trust tradeoff: a warning is not a correctness guarantee. A user can now see and regenerate imperfect code instead of receiving a blanket failure, but should review warned starter code before executing it and treat an answer with failed fixtures as suspect.
