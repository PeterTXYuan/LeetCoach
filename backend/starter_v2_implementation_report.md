# Starter v2 implementation report

## Architecture and old/new flow

Policy **7** makes Groq responsible for actual algorithm-specific setup, partial implementation, loops, branches and helpers across all three levels. The original SQLite submission shell is immutable interface context, not a mostly completed algorithm supplied by the backend. No catalog, Problem Specification, schema, Hints generation or Full Solution generation change is part of this milestone.

Old policy 6: selected level → deterministic per-approach scaffold → numbered TODO slot → one-line Groq edit → deterministic fallback on rejection.

New policy 7: problem + canonical approach + language → compact verified DB context + original submission shell → **one Groq request** → JSON `level1`/`level2`/`level3` → validate the entire trio → return/cache one atomic batch. Model rejection does not trigger a retry or a mock scaffold. Mock mode uses the existing offline fixtures through a small batch adapter, independently of the Groq path.

The working tree was clean at the start of this request. The previous 20-problem context work, including `verified_problem_specs.py` and migration `0003`, was present. No pre-existing uncommitted work was found or overwritten. No real Groq request, commit or push was made.

## API contract, version and rollback

Primary endpoint:

```text
POST /api/problems/{slug}/approaches/{approach_id}/starter-code/batch
```

Request: `{"language":"python"}`. The endpoint resolves the slug and stable approach key through SQLite. It never infers the approach from array position.

Response:

```json
{
  "slug": "two-sum",
  "approachId": "hash-map",
  "language": "python",
  "policyVersion": 7,
  "isAiGenerated": true,
  "usedFallback": false,
  "notice": "Starter code, not a full solution. Complete the TODOs before running.",
  "level1": "complete unfinished source",
  "level2": "complete unfinished source",
  "level3": "complete unfinished source"
}
```

Groq JSON-object mode requests only the three source strings. The backend adds identity and truthful metadata. It uses temperature 0.2, a 10,000 completion-token cap, a 20-second SDK timeout and zero SDK retries. Each Generate or Regenerate API call invokes the SDK once, not three times. This milestone adds no shared server cache; the extension owns the user-local persistent batch cache.

The previous `/starter-code` language/level route is retained at policy 6 behind `LEETCOACH_ENABLE_LEGACY_STARTER=true` (default false). It retains the legacy prompt, edit contract and deterministic fallback for explicit rollback. Without the flag it returns 409. A previous frontend build or explicit legacy client is needed for rollback. The policy-7 frontend always calls the batch route and never calls both generation paths. Historical tests explicitly enable legacy mode and retain their safety assertions; historical evaluation checks explicitly remain on policy 6.

## Complete and efficient model context

Both production context loaders and the verified data remain as implemented in the preceding milestone. The new Starter Code prompt filters that context into factual problem information and one separately identified algorithm approach. It includes the complete description, ordered examples with explanations, constraints, official complexity instructions, and only the requested language template. It omits provenance, duplicate problem summaries, other approaches and other languages. No summary is substituted when a verified description is missing: the request fails before an SDK call with `MISSING_VERIFIED_DESCRIPTION`.

The following is an actual payload read from the local SQLite database through `find_problem_context` and `model_context`, the same serialization used by the production Groq request:

```json
{
  "problem": {
    "title": "Two Sum",
    "description": "Given an integer array nums and an integer target, return the zero-based indices of two different array elements whose values sum to target. Exactly one valid pair is guaranteed. An element cannot be chosen twice, even when its value is used twice; either order of the two indices is accepted.",
    "constraints": [
      "2 <= nums.length <= 10^4",
      "-10^9 <= nums[i] <= 10^9",
      "-10^9 <= target <= 10^9",
      "Exactly one valid pair exists."
    ],
    "examples": [
      {
        "input": "nums = [2,7,11,15], target = 9",
        "output": "[0,1]",
        "explanation": "The values at indices 0 and 1 sum to 9."
      },
      {
        "input": "nums = [3,2,4], target = 6",
        "output": "[1,2]",
        "explanation": null
      },
      {
        "input": "nums = [3,3], target = 6",
        "output": "[0,1]",
        "explanation": null
      }
    ],
    "timeComplexityInstruction": "Optional follow-up: find a method faster than O(n^2)."
  },
  "approach": {
    "id": "hash-map",
    "name": "One-pass Hash Map",
    "summary": "Remember previously visited values so complements can be found quickly.",
    "thinkingSteps": [
      "For each value, determine the complement needed to reach the target.",
      "Check whether that complement has already been seen.",
      "Store the current value for later lookups."
    ]
  },
  "language": "python",
  "submissionTemplate": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        pass"
}
```

## Exact production Groq system prompt

```text
You are LeetCoach, an AI coding tutor.
Using the problem description, examples, constraints, selected algorithm approach, and LeetCode code template, generate three progressively more helpful Starter Code versions in the requested language.
Level 1 — Kickstart: Add a small amount of useful setup. Leave most of the algorithm for the student.
Level 2 — Guided: Add initial algorithm structure, such as variables, loops, or helper setup. Leave important decisions unfinished.
Level 3 — Strong Scaffold: Provide most of the algorithm structure, but leave the central logic or operations for the student to complete.
Rules:
1. Follow only the selected approach and keep a compatible design across levels.
2. Preserve every required class, constructor, method signature, and return type from the template. Additional helpers must be private or named with a leading underscore.
3. Use syntactically valid code with meaningful TODO comments.
4. Leave genuine algorithm work unfinished at every level. Never provide a complete solution.
5. Make each level progressively more helpful.
6. Incomplete execution paths must fail clearly with an exception, not loop forever or silently return misleading results. Placeholders must be reachable.
7. Return only JSON containing level1, level2, and level3, each holding complete source code, without Markdown fences.
```

## Mocked Two Sum L1/L2/L3 response

These are the source strings from the offline fake-SDK regression fixture. They are not live Groq output.

### Level 1

```python
from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        # TODO: decide what information belongs in seen.
        raise NotImplementedError("Complete the search")
```

### Level 2

```python
from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for index, value in enumerate(nums):
            # TODO: determine which earlier value could form a pair.
            raise NotImplementedError("Complete each search step")
        raise NotImplementedError("Handle the result")
```

### Level 3

```python
from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for index, value in enumerate(nums):
            complement = target - value
            if complement in seen:
                # TODO: construct the matching indices.
                raise NotImplementedError("Complete the pair result")
            # TODO: record useful information for later values.
            raise NotImplementedError("Complete the state update")
        raise NotImplementedError("Handle the result")
```

## Authoritative interfaces and validator design

`app/llm/starter_batch.py` replaces the old one-line edit contract for the new path. Every source string is nonempty and bounded, contains a meaningful TODO, preserves the required class and all methods/constructors, and leaves reachable executable unfinished work. All three fields must be present and pass before any batch can be returned.

Python AST checks compare required argument names/order, annotations, return annotations, class structure and decorators. Additional helper methods must be private by naming convention; nested helpers are allowed. A small call relationship check permits an entry point to delegate to an unfinished recursive helper, while an unused helper cannot justify a completed entry point. For Java, JavaScript and C++, declaration matching ignores whitespace and masks comments/literals; required signatures must occur exactly once. New public entry points/overloads are rejected, private helpers are allowed, C++ required methods retain public visibility, and replacement of JavaScript's required prototype is rejected.

The validator checks obvious dead placeholders, silent unfinished methods, empty or non-progressing while loops, full lookup/update/return recipes, and a few directly recognizable approach contradictions. It permits ordinary indexing, map operations, arrays, loops, conditions, intermediate calculations and standard-library calls. The primary path does not invoke the old `validate_starter_code` single-line/scaffold teaching restrictions.

Batch progression requires three distinct programs and increasing executable-structure scores, ignoring comments and placeholder throws. Min Stack's shared storage must remain compatible across levels. These are practical heuristics, not semantic proofs. Tests reject reversed/identical levels and preserve useful recursive-helper and normal-library examples.

`app/llm/starter_syntax.py` parses Python with AST and uses available native tools for `javac -proc:none`, `node --check`, and `g++ -fsyntax-only`. Compiler invocations use temporary directories, bounded source size/time/concurrency, Java heap limits, and no generated program execution. C++ nonstandard preprocessor directives/local includes are rejected. Java list/tree node stubs support LeetCode-provided types. On this Windows device there is no native `g++`; production C++ uses structural checks and reports no claim of successful compilation. Offline tests and the separate evaluator can compile C++ in the existing isolated WSL/bubblewrap environment. Compilation cannot establish algorithmic correctness or teaching quality.

## Failure, fallback and diagnostics

- A valid Groq trio returns `isAiGenerated: true`, `usedFallback: false`.
- Mock mode returns all three offline sources with `isAiGenerated: false` and an explicit offline notice.
- Missing IDs/templates return 404; unsupported languages 400; malformed input 422; missing verified context 409; rejected outputs 502; provider/configuration failures 503.
- A single bad level rejects the whole batch. No partial success is cached as a valid trio, no automatic second Groq call occurs, and no legacy deterministic scaffold silently substitutes for Groq.
- Errors contain safe stage/reason codes. Production logs contain identity and reason codes, never raw responses or API keys. Request-local evaluation observers can collect call count, latency, usage and explicitly requested raw captures.

## Frontend cache and Regenerate

The existing `leetcoach-workspaces-v1` storage key is retained. Each problem workspace contains canonical approach entries whose Starter Code settings hold `batches["language:7"]`. One stored object contains all three source files. Old per-level responses and older batch policy versions are ignored during hydration, while Hints, Full Solutions, approach selection and language/level preferences remain.

Generate reuses a cached batch or fetches one batch. Switching levels reveals the corresponding source locally. A different language uses its own cache. Changing the selected level during a pending request does not abort or start another call. A successful Regenerate atomically replaces all three levels for that language and leaves other language batches intact. A failed or malformed regeneration keeps every previous level visible and persisted. Duplicate requests are blocked synchronously, and abort/controller/context checks reject late results after language, problem, approach, hide, collapse or unmount changes. Existing tab-switch/disclosure behavior and visual styling are retained.

## Offline verification

- Full backend suite: `py -B -m unittest discover -s tests -q` — **115 passed** in 70.440 seconds.
- Final focused batch suite: **16 passed**, including the additional check that Python cannot introduce a constructor requiring new arguments for `Solution`.
- Frontend: `npm test` — **104 passed**.
- Production build: `npm run build` — **passed**.
- New mock coverage: **164 approach/language batches / 492 levels**, from the unchanged 20-problem, 41-approach catalog.
- Fake-Groq tests include Two Sum, 3Sum, Binary Search, Min Stack, Reverse Linked List, Maximum Depth, Number of Islands and Climbing Stairs across Python, Java, JavaScript and C++. They cover malformed/missing fields, wrong signatures and constructors, missing methods, extra public entry points, visibility/prototype changes, syntax failures, completed algorithms despite TODOs, unsafe loops, dead markers, inconsistent progression, wrong approaches, missing verified descriptions, no retries/fallback, and bounded evaluation behavior.
- Python AST, Java compilation, JavaScript syntax checking and isolated C++ syntax-only compilation passed for representative scaffolds. No generated program was executed inside FastAPI.
- An AST comparison with HEAD confirmed that `SYSTEM_PROMPT`, `SOLUTION_SYSTEM_PROMPT`, `generate_hints`, and `generate_solution` are unchanged.
- Prepared matrix dry-run: **0 real Groq calls**. Unit tests exercise live CLI branches with a fake SDK/client only; fixture counters labelled as calls are not actual network requests.
- `git diff --check`: passed.

## Remaining risks and next verification

Live generation reliability is **unverified**. The model may still change interfaces, truncate files, produce syntax/type errors, reveal too much, or make weak progressions; the implementation rejects detected defects rather than trying to manufacture an acceptance rate. A three-file response costs more tokens and may encounter the existing 20-second timeout. The syntax/flow checks are deliberately incomplete and may reject valid but unusual scaffolds or miss subtle semantic defects. They do not prove that every unfinished branch terminates, that all computed values are safe, or that all three levels teach the same design. Human inspection is required, especially for base cases, subtle answer leakage and consistency beyond the targeted checks. Additional public helper methods are intentionally disallowed; private/nested helpers remain available.

The new evaluator freezes **8 requests / 24 generated levels** across the eight algorithm families and all four languages, including Min Stack. It records actual observed SDK call counts, API success/failure, validated batches, per-level structural and syntax results, rejection reasons, progression review status, leakage/safety review markers, fallback/error behavior, provider and API latency, and available token usage. No retries occur; provider outages/rate limits stop subsequent requests. These denominators differ from the prior 19 single-level requests and must be reported separately, not compared as if the acceptance rates were equivalent.

Dry-run command executed:

```powershell
py -B -m evaluation.starter_v2 --dry-run --max-calls 8 --output-dir evaluation_runs/starter_v2_dry
```

Recommended future bounded command — **prepared only, not executed**:

```powershell
py -B -m evaluation.starter_v2 --live --max-calls 8 --pace-seconds 12 --capture-raw --output-dir evaluation_runs/starter_v2_live
```

Reports and optional raw captures remain in ignored `backend/evaluation_runs/`. Do not infer improved live reliability from these offline results.

## Files changed and Git status

New code: `app/llm/starter_batch.py`, `app/llm/starter_syntax.py`, `evaluation/starter_v2.py`, and `tests/test_starter_v2.py`. Provider/API changes add the batch operation, policy metadata and opt-in legacy route; the existing mock fixtures are adapted only for offline batches. Frontend edits cover the API, hook, component, workspace persistence and their regression tests. Legacy evaluation/tests now explicitly reference policy 6 rather than accidentally inheriting the current policy. Documentation is updated in `backend/README.md`, `.env.example`, `roadmap.md`, and this report.

Initial status was clean. Current status (before any commit):

```text
 M .env.example
 M README.md
 M app/llm/base.py
 M app/llm/groq_provider.py
 M app/llm/mock_provider.py
 M app/main.py
 M evaluation/validators.py
 M tests/db_test_support.py
 M tests/test_evaluation_harness.py
 M tests/test_starter_phase2.py
 M ../roadmap.md
 M ../src/api/starterCode.ts
 M ../src/coachWorkspaceStorage.ts
 M ../src/components/StarterCode.tsx
 M ../src/hooks/useStarterCode.ts
 M ../tests/guidance.test.tsx
 M ../tests/starterCode.test.tsx
 M ../tests/workspaces.test.tsx
?? app/llm/starter_batch.py
?? app/llm/starter_syntax.py
?? evaluation/starter_v2.py
?? starter_v2_implementation_report.md
?? tests/test_starter_v2.py
```

Suggested commit message: `Generate atomic three-level Starter Code batches with Groq`.

No commit or push was performed.
