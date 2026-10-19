# Policy 9 linked guidance implementation (offline)

## Result

Coach now uses one `POST /api/problems/{slug}/approaches/{approach_id}/guidance` request per problem, canonical approach key, and language. In Groq mode that single request returns L1, L2, L3, and the matching full answer as one validated Policy 9 bundle with a generation ID. A Starter Code request caches the full answer but leaves it hidden; Generate Answer reveals the matching cached answer. Regenerate from either section replaces the entire bundle after success, while failure preserves the prior one. Language selectors and Starter Code level remain independent. Hints, selections, navigation, and preferences survive the cache migration.

The Groq instruction asks for the same implementation completed in stages, with short L2/L3 comments explaining supplied loops and state. It disallows comment-only answers to TODOs. The new operation has a 30-second timeout, 10,000 completion-token cap, and no SDK retry. It rejects a length-truncated finish. The response contains prompt/completion/total token counts, latency, output size, and finish reason when supplied by the SDK. Production observation omits raw source; raw capture remains an explicit evaluation-only option.

## Validation and safe execution

- The three starter versions pass the existing signature, syntax, reachable fail-loud TODO, unsafe-loop, and commented-solution checks. Policy 9 removes only the blocking statement-count progression gate. Additional checks require retained named state, a majority of prior working setup/control-flow lines, and new working structure at each starter stage, without requiring any statement-count increase. Regression families cover Two Sum, Java 3Sum, JavaScript Min Stack, Python Binary Search, and Python Reverse Linked List.
- The full answer passes required-field, signature, placeholder, and syntax checks. Recognizable TODOs, `pass`, ellipses, placeholder exceptions, and empty placeholder returns for guaranteed-answer Two Sum are rejected.
- Representative correctness cases run **only** in the existing WSL bubblewrap sandbox for supported Python and C++ problem/language pairs. The focused offline test confirmed a correct Two Sum answer passes and an intentionally incorrect answer fails in that isolated runner on this device. A fixture failure rejects the entire bundle. An unsupported pair or unavailable sandbox produces `NOT_RUN` with an explanation; generated code never runs directly in FastAPI or on the host as a fallback.
- These checks are evidence, not proof: the fixtures cover a limited set of inputs and problems; structural lineage cannot establish semantic equivalence or pedagogical quality; missing compilers lead to structural checks only. No live Groq output was reviewed in this milestone.

## Compatibility and cache behavior

The old independent Starter Code Policy 8 and Full Solution endpoints remain available for historical evaluation, but Coach no longer calls them. Policy 8 starter and independent full-answer cache entries cannot establish Policy 9 lineage and are dropped on hydration. Policy 9 bundles are validated per slug, canonical approach ID, and language in the existing workspace key. Runtime disclosure still collapses on panel remount, approach change, and same-tab navigation; extension and browser-tab switching in the open panel preserve it. Concurrent Starter/Answer clicks join one request. A late response after a disclosure collapse can cache the complete bundle but cannot reopen either section.

Offline mock mode retains all existing Starter Code coverage. Its response is marked `starterOnlyMock`, and the original curated full answer is included only where one already exists; it is explicitly presented as an independent fixture rather than a linked Groq continuation.

## Offline verification

| Check | Result |
| --- | --- |
| Backend `py -B -m unittest discover -s tests -q` | 130 passed; focused Policy 9 suite passed 12/12 |
| Frontend `npm test` | 99 passed |
| Frontend `npm run build` | Passed |
| `git diff --check` | Passed |
| Real Groq requests | 0 |

The backend suite's evaluation tests use fake provider clients even when their simulated logs say “live.” A future bounded real-Groq run should review all four actual outputs for comments, progression, answer correctness, acceptance rate, token use, and latency before catalog-scale release.
