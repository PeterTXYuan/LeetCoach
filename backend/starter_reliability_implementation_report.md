# Final Starter Code reliability fix — offline implementation report

## Scope and root cause

The prior 19-request live report found three student-visible deterministic defects despite 19/19 syntax checks. Guided Binary Search used a comment-only `while` body in C++; Guided Reverse Linked List used `pass` inside a Python `while`; both placed the only exception after the potentially endless loop. Guided Maximum Depth reused a general thinking step inside the empty-tree base case, where computing child depths is inappropriate. These were baseline generator defects, not model output defects. This milestone changed Starter Code only; it made no live Groq request.

## Fixes and deterministic safety

The Guided loop helper now puts an exception directly after its TODO inside every unfinished `while` loop, while recursive/base-case branches get a base-case TODO and fail-loud path. Strong Scaffold generic loops that formerly used `break` now throw at the unfinished step. Number of Islands Java/C++ visited-grid setup no longer indexes `grid[0]` on an empty grid. Canonical templates still own class/method signatures, the selected approach and data representation, required methods, L1/L2/L3 progression, and all trusted control flow. All levels remain independently requestable, including the paired Min Stack progression.

The 492-case catalog test still covers 41 approaches × 4 languages × 3 levels. Added static loop checks are supplemented by bounded, isolated WSL bubblewrap execution for representative Python and C++ paths: Binary Search with a missing target and empty input, nonempty and empty linked lists, Maximum Depth base/nonempty trees, islands, a stack operation, pair removal, sorted Two Sum, and a recursive base case. Representative Java and JavaScript scaffolds also pass offline syntax/compilation checks. Runtime probes enforce two-second child-process limits; generated code is never executed in the FastAPI process. These tests establish the selected unfinished paths, not a proof that every possible path terminates.

## Groq contract and validator

One Groq request now asks for a small flat JSON object: `{"slot":"todo-1","code":"gap = target - current","guidance":"What earlier value might help?"}`. `code` and `guidance` are individually optional but at least one must produce a new student-visible addition. The old one-edit `edits` envelope remains parseable for offline replay; historical whole-file captures remain replay-only. The short system prompt asks for the canonical approach, a supplied TODO slot, one useful level-appropriate addition, and no completed algorithm. It no longer asks the model to reproduce files, signatures, or a `lines` array.

Executable additions remain one grounded local declaration/intermediate assignment, not a sequence of edits. The validator still rejects unknown slots, duplicate or ungrounded code, changed signatures, return/control-flow statements, state mutation, arbitrary calls, fixed-index reads, unguarded node reads, complete-solution patterns, and syntactically invalid assembled code. Collection constructors, `Map.get`, and `Math.min` remain unsupported until they can be handled safely and usefully without expanding the contract into a large language grammar. The backend inserts at a known TODO and never removes or rewrites trusted lines.

Optional guidance is validated independently. One leading `#`, `//`, or `TODO:` marker is normalized. Redundant, generic, answer-revealing, or malformed optional prose is omitted; valid executable code can still be retained and gets a local `partial_acceptance` / `OPTIONAL_GUIDANCE_OMITTED` observer event. An invalid executable addition never becomes accepted merely because its prose is useful. A guidance-only response gets `isAiGenerated: true` only when a new, validated TODO is actually shown. A wholly rejected response remains HTTP 200 with the safe offline scaffold, `isAiGenerated: false`, `usedFallback: true`, and the established notice. Existing typed failure diagnostics, optional raw capture, endpoint schemas, regeneration, and language/level choices remain compatible.

Starter Code policy version changed from **5 to 6** because the deterministic code and `isAiGenerated` meaning changed. Old Starter Code cache entries are invalidated individually; Hints, Full Solutions, selected approach, and user choices are preserved. Frontend controls and regeneration behavior were not redesigned.

## Offline replay of 13 saved rejected responses

Replay used the exact local raw files from the ignored final MVP run through the updated production parser, with zero provider requests. Four previously rejected plans now pass local validation; nine still reject. This does **not** predict a future live acceptance rate.

| Category | Saved responses | Finding |
| --- | --- | --- |
| Newly accepted | 3Sum Java L3, Binary Search C++ L2, Number of Islands Python L1, Reverse Linked List Python L2 | Optional prose no longer sinks valid code; the islands `# TODO:` prefix is handled; the repaired Reverse Linked List loop remains fail-loud. The 3Sum intermediate is safe but may be marginal in usefulness. |
| Correctly rejected as unsafe or incorrect | Min Stack JavaScript L1, Maximum Depth Python L2, Climbing Stairs JavaScript L2, Daily Temperatures C++ L3 | These respectively change the pair-stack representation, place child work in an empty-tree branch, write an incorrect memo value, or read `pending.top()` without proving the stack nonempty. |
| Correctly rejected as too revealing | Min Stack JavaScript L2 and L3 | The `Math.min` ternary computes the central pair-minimum operation at these levels. |
| Still unsupported, potentially useful in the right slot | Two Sum Python L3 and Group Anagrams Java L1 | `seen.get(complement)` is a read-only lookup but is outside the narrow executable grammar. `new int[26]` is a reasonable array initializer in a per-word frequency loop, but this L1 slot is outside that loop. |
| Still invalid model output | Two Sum Python L1 | The proposed `num` variable does not exist at the chosen slot. |

The replay categorization is editorial, based on the saved raw text and current scaffold placement. It does not alter the prior verification report or inflate accepted AI counts.

## Verification and remaining limits

- Backend: **95 tests passed**, including all 492 deterministic combinations, the new bounded behavior checks, flat/legacy contract cases, optional guidance, fallback, and diagnostic regressions.
- Frontend: **101 tests passed**, including cached guidance regeneration and policy-version behavior.
- Production: `npm run build` passed.
- No live Groq requests were made. Tests used only mocked providers, saved raw text, and offline scaffolds.

Remaining limits: compiler/runtime validation is not performed during production requests; narrow executable edits can reject safe language features; static checks and representative runtime probes cannot prove all behavior; local replay says nothing about how often Groq will follow the new prompt. A separate bounded live verification is needed before catalog scaling. From `backend/`, the recommended command is:

```powershell
py -B -m evaluation.run_evaluation --live --final-mvp-matrix --max-calls 19 --pace-seconds 12 --capture-raw --output-dir evaluation_runs/final_starter_recheck
```

Do not run this command as part of this implementation milestone.
