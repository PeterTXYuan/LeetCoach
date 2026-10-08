# LeetCoach Roadmap

## Vision

Don't give me the answer.
Teach me how to discover it.

## UI Baseline (User-approved September 13, 2026)

Preserve this visual format for future UI work unless the user explicitly asks otherwise:
- Separate Hints and Solution strategies cards, white on neutral gray in light mode and charcoal in dark mode.
- LeetCode-style system fonts, 14px body text, restrained weights, compact rounded controls, and subtle borders/shadows.
- Centered green problem-status dot and red selected-approach Close button.
- New controls and badges should fit this style rather than introduce a new visual system.

---

## Current Architecture

Frontend
- React
- TypeScript
- Vite
- Chrome Extension Manifest V3
- Chrome Side Panel
- Active-tab problem detection for `https://leetcode.com/problems/*`
- Versioned per-problem Coach workspaces in `chrome.storage.local`

Backend
- FastAPI
- SQLAlchemy 2.x repositories for stable problem and approach metadata
- Local CORS for Chrome extension and localhost development
- Canonical approach metadata with stable approach IDs
- DB-grounded hint routes using a small LLMProvider boundary
- Solution service abstraction returning approach-specific mock answers
- DB-grounded Starter Code route through the same LLMProvider boundary (offline mock or Groq)
- Manually curated related-problem rows per seeded problem

Database
- Local SQLite (`backend/leetcoach.db`) through SQLAlchemy 2.x
- Alembic revisions `0001` (stable approach metadata) and `0002` (Problem Specification / LLM grounding), plus an explicit repeatable seed command
- Request-scoped sessions; SQLite foreign keys and cascade rules enabled
- Future PostgreSQL migration remains a separate milestone

AI
- Current: deterministic offline MockLLMProvider or live GroqLLMProvider for Hints and Starter Code
- Current: Full Solution remains a three-problem mock example
- Future providers may include OpenAI, Gemini, or OpenRouter

---

## Persistent Coach Workspaces (October 4, 2026)

`chrome.storage.local` stores a versioned `leetcoach-workspaces-v1` map keyed by problem slug. Each workspace saves the selected canonical approach ID, thinking-process expansion, section preference, and a hint entry for each approach. A hint entry holds the generated batch separately from `visibleHintCount`; Reset Hints hides the cards without deleting the batch. Clicking Get First Hint afterward reuses the saved response with no backend or LLM request. Returning from another problem or reopening the side panel restores the selected approach, visible hint count, thinking state, and section. Closing an alternative hides that approach's hints while restoring any previously visible primary-approach hints.

The extension waits for storage hydration before showing a detected problem's Coach controls or writing defaults, so a saved workspace is not overwritten during startup. Stored shapes and slug/approach keys are validated; missing, obsolete, corrupt, or unavailable storage falls back to a clean in-memory workspace. A failed storage read disables writes for that panel session so a temporary outage cannot erase previously saved data. Stale selected IDs are discarded after the current DB-backed analysis loads. Whole-map writes are serialized to keep later state from being overwritten by a slower earlier write. The Manifest V3 `storage` permission was added. Theme remains in its existing `localStorage` key.

Starter Code now lives in the same versioned workspace record. Each problem stores per-canonical-approach language, level, disclosure and result visibility, plus validated responses keyed by language and level. Changing options displays a matching cached result without a request; an uncached combination still requires Generate. Hiding code or closing its options conceals the result without deleting current-policy cache. Switching problems or reopening the side panel restores choices and visible code. Older v1 records without starter fields hydrate normally, preserving hints; corrupt or obsolete-policy starter entries are discarded individually. Generated full answers, Recognition Signals reveal, and loaded Practice cards remain session-only. The same-problem non-LeetCode-tab behavior still keeps them mounted while the side panel stays open.

---

## SQLite Schema And Workflows (September 30, 2026)

Architecture at the September 30 database milestone: FastAPI routes → SQLAlchemy repositories and request-scoped sessions → local SQLite. The later hint-provider milestone also uses SQLite for both hint routes. There is no automatic fixture fallback or startup migration/seeding.

Schema:
- `problems`: internal integer primary key, unique slug, title, constrained difficulty, and concise factual summary.
- `problem_constraints`: ordered factual constraints, unique by problem/order.
- `problem_examples`: ordered input/output examples with optional explanations, unique by problem/order.
- `problem_submission_templates`: one base LeetCode-style template per problem and supported language. These define submission signatures and are not the progressive Starter Code feature.
- `approaches`: internal integer primary key, problem foreign key, existing string `approach_key`, name/pattern/summary, primary flag, display order, and JSON thinking steps. Enforces unique `(problem_id, approach_key)`. The seed validates exactly one primary approach per curated problem.
- `recognition_signal_sets`: one per approach with an optional short quote.
- `recognition_signal_bullets`: text and explicit positive display order, unique per signal set.
- `related_problems`: source problem foreign key, target slug/title/difficulty, optional reason, constrained `easier / similar / harder` category, and display order. Targets are simple external cards, not graph nodes or prerequisites; target slug is unique within the source problem.

From `backend/`, initialize or upgrade and seed:

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload
```

Use `py` instead of `python` on Windows if needed. The default file is `backend/leetcoach.db`; `LEETCOACH_DATABASE_URL` can select another SQLite file. Relative paths resolve from `backend/` for the API, migrations, and seed command alike. Database/journal files are ignored by Git.

For schema changes, edit the models, run `python -m alembic revision --autogenerate -m "describe change"`, review the generated migration, then run `python -m alembic upgrade head` and `python -m alembic check`. Migrations `0001` and `0002` create schema; `python -m app.seed` loads data separately. Downgrade is destructive and is tested using disposable databases.

Seed behavior: one transaction, lookups by stable natural keys, updates existing rows without replacing their internal IDs, and inserts missing rows. Each problem present in `app/stable_data.py` exactly syncs its constraints, examples, submission templates, approaches, recognition signals, and related cards. Children absent from the source are deleted. Ordered rows retain IDs by display position; templates retain IDs by language; related cards retain IDs by slug even when moved between categories. Repeating the command adds no duplicates and refreshes curated fields. Problem rows outside the current seeded dataset and their children remain untouched. The separate `app/mock_data.py` remains the guidance source for the original three fully mocked problems.

At that September 30 milestone, hint text, starter templates, and full answers were mocked. Thinking steps were stored with approach metadata in SQLite. Later provider milestones moved Hints and Starter Code to SQLite-grounded mock/Groq generation; Full Solution remains mocked.

Problem Specification gives both providers factual, local grounding rather than opening a LeetCode URL, relying on memory, guessing constraints, or inventing a function signature. The database owns problem facts, submission shells, and canonical approach identity. `find_problem_context` assembles the selected approach and language-specific template for Starter Code; the hint routes retain their language-free DB context loader. Full solutions, explanations, and complexity discussion remain future work.

Future PostgreSQL path: add the PostgreSQL driver/configuration in a separate milestone, apply and test the portable SQLAlchemy/Alembic schema against that dialect, and transfer local rows with foreign-key/sequence verification (or seed a fresh database). Public problem slugs and canonical approach keys stay unchanged. SQLite-specific connection settings are isolated in `database.py`; PostgreSQL is not installed or deployed now.

---

## Completed

- Progressive Starter Code levels redesigned (October 8, 2026): Level 1 is **Kickstart**, with a useful approach-specific executable starting step, concise TODO, and no main algorithm. Level 2 retains that setup and adds initial control flow or supporting state. Level 3 adds major loops/branches and intermediate calculations while leaving central lookups, comparisons, updates, duplicate handling, pointer movement, or answer construction unfinished. Groq receives these distinctions explicitly; the deterministic fallback now follows them for all 41 canonical approaches and four languages, including the representative Two Sum, 3Sum, and Min Stack progressions. Validation rejects template-only or generic Level 1 output and invalid `if (/* TODO */)` placeholders, while retaining signature, syntax, commented-solution, and unfinished-work checks. Starter policy version increments from 2 to 3, dropping old Starter Code on hydration but retaining hints, selected approach, language, level, and other workspace preferences. Regeneration remains explicit. UI level names/descriptions changed without redesign or route/schema changes.
- Starter Code teaching-quality refinement (October 8, 2026): Groq now receives explicit Minimal, Guided, and Strong Scaffold teaching rules. Level 3 may show control flow and intermediate calculations, but must leave the selected approach's central decisions, updates, and answer construction for the student. Practical validation rejects changed signatures, malformed Python or braces, obvious commented-out algorithms, decorative-only TODOs, early returns before the unfinished placeholder, and a complete hash-map lookup/update/return sequence. The existing safe offline fallback handles rejected provider output. Offline scaffolds now use approach-appropriate variables and structures, including typed Java/C++ collections, shared Min Stack fields, and targeted outlines for hash maps, two pointers, sliding windows, binary search, trees, linked lists, and stacks. Starter responses carry `policyVersion: 2`; saved older code is discarded on hydration while selected approach, language/level, options visibility, thinking state, and hints remain. Regeneration remains a user click, never an automatic request. There was no schema migration or change to Full Solutions or Hints generation.
- Starter Code response resilience (October 8, 2026): an HTTP 200 from Groq can still contain invalid JSON or a scaffold that fails signature/unfinished-code checks. Harmless extra JSON fields and a single outer Markdown code fence are now accepted. If Groq output is unusable or its request times out, the endpoint returns a safe unfinished offline scaffold with `isAiGenerated: false`, `usedFallback: true`, and a clear notice instead of failing the student. The fallback is cached, but its UI offers an explicit Try AI generation again action. Provider failures are logged with context and exception category only; raw model text and secrets are not logged or returned.
- Real LLM Progressive Starter Code + persistent cache (October 7, 2026): the existing POST contract now loads the exact problem, selected canonical approach, facts, thinking steps, and requested language's submission template from SQLite for all 20 curated problems and 41 approaches. `LLMProvider.generate_starter_code` uses a deterministic offline mock or a structured Groq JSON request. Validation requires the original class and all entry-point signatures, an unfinished TODO and fail-loud placeholder, and rejects fences/malformed output; provider errors yield sanitized 502/503 responses. Full Solution and Hints behavior are unchanged. The prior seven-approach static starter service remains as a legacy fixture, but the route no longer uses it. No schema migration or backend generated-code cache was added.
- Starter responses and UI choices now persist in the existing `leetcoach-workspaces-v1` map, keyed by slug, canonical approach ID, language, and level. Cached combinations reappear when selected and never trigger another request; Hide starter code and Close starter code options only affect visibility. Tests cover old-hint hydration, bad-cache isolation, problem switch/remount reuse, and aborted response isolation. Mock scaffolds give three distinct unfinished levels for all 492 combinations; actual Groq teaching quality still needs human review. That milestone passed 49 backend tests, 81 frontend tests, and the production build with its final offline suite.

- Problem Specification / LLM grounding (October 4, 2026): migration `0002` adds required title/difficulty/summary fields plus ordered constraint/example tables and language-keyed submission templates. All 20 problems have concise algorithm-neutral specifications, representative examples, and LeetCode-style Python/Java/JavaScript/C++ shells. Exact-sync seeding covers every new child type while preserving retained IDs. An internal repository helper loads a complete problem + language template + canonical approach context; public API and frontend behavior are unchanged.
- 20-problem SQLite catalog (October 1, 2026): expanded stable editorial coverage to the requested 20 problems, with 41 canonical approaches, exactly one primary approach per problem, 84 ordered recognition-signal bullets, and 68 manually curated related cards. Three related categories are intentionally empty where no useful choice was available. Stable DB seed data now lives in `app/stable_data.py`, separate from mock guidance/code fixtures. No schema or Alembic migration was needed.
- Exact-sync seeding (October 1, 2026): stale approaches and related cards are now deleted within each seeded problem, while retained DB IDs and unrelated problem rows/children are preserved. Regression tests cover repeat seeding, source-content updates, category moves, partial/empty related lists, stale recognition cleanup, and removed child rows. No API or frontend changes.
- SQLite stable-data migration (September 30, 2026): migrated all three supported problems, seven approaches, seven recognition signal sets with 16 ordered bullets, and nine related-problem cards. Analysis and related-problem GET endpoints now read SQLite with unchanged API shapes; canonical `approach.id` remains a string, never an internal DB key. The original fixtures are retained for seeding and mock guidance.
- Recognition Signals (September 21, 2026): placed inside Solutions between Summary and Generate Answer, visible only for an explicitly selected canonical approach. It uses the existing section divider, a small green lightbulb icon, and a neutral Reveal recognition signals button, without an approach badge.
- Each of the seven seeded approaches owns structured `recognitionSignals: { quote?, bullets }` metadata: two or three beginner-friendly cues about recognizing the approach from the statement, plus a short statement excerpt. Metadata is included in the existing problem-analysis response; revealing/hiding it makes no new request.
- Recognition disclosure resets on approach/problem changes and closing an approach; it stays intact across section switches and temporary visits to non-LeetCode tabs. Missing metadata from older backends hides the section without breaking Coach.
- Added eight frontend recognition tests and backend coverage of all seven approach payloads. Tests verify placement inside Solutions and navigation state preservation. The initial built-app preview against FastAPI checked keyboard reveal/hide and light/dark styling at narrow sidebar width.
- Same-problem tab restoration (September 21, 2026): temporarily visiting a non-LeetCode browser tab no longer destroys the problem workspace. Returning to the same slug restores Coach, Practice, Progress, or About and preserves approaches, hints, starter code, thinking, answers, and loaded related problems in the open side-panel session. That milestone started a different slug at Coach; the later persistent-workspace milestone restores a previously visited slug's saved section and Coach state. Deliberate Progress/About selections made while away take precedence for the last problem.
- Practice now mirrors Coach's composition with the current problem title card above a separate Related problems card, containing Easier / Similar / Harder groups and leaving room for additional Practice sections.
- Practice: Related Problems (September 19, 2026). `GET /api/problems/{slug}/related` returns `slug` and grouped `easier`, `similar`, and `harder` arrays; unknown problems return 404.
- Added nine manually curated related-problem entries: one per group for each of the three seeded problems. Each has a canonical slug, title, LeetCode difficulty, and short reason. Groups reflect relative practice challenge, rather than a computed difficulty ranking.
- Focused related-problems API, hook, Practice panel, and card components. Requests start only while Practice is active; successful responses are cached by slug for the mounted session. Leaving Practice or changing problems aborts pending requests and ignores stale responses; failures offer Retry, and empty/unavailable groups have explicit messages.
- Practice cards use the existing light/dark surfaces and compact Open Problem buttons, opening `https://leetcode.com/problems/{slug}/` in a new tab. Coach state and navigation behavior remain intact.
- Added 15 frontend Practice tests and two backend tests for seeded coverage, grouped data, 404s, lazy fetching, cancellation, retry, empty groups, response validation, and correct external URLs. Browser preview against the real endpoint verified long titles and light/dark layouts at 320px without horizontal overflow.
- Global section navigation (September 19, 2026): reusable `SectionNav` presents Coach / Practice / Progress / About for detected LeetCode problem URLs, and Progress / About otherwise. Navigation is owned by the extension, outside the problem UI; entering a detected problem defaults to Coach.
- Compact full-width 36px pill navbar follows the theme toggle, with subtle theme-aware surfaces, a rounded active segment, 180ms transitions, reduced-motion support, and arrow/Home/End keyboard navigation.
- Coach stays mounted while switching sections, preserving selected approaches, hints, starter disclosure/settings/code, thinking process, full answers, and pending requests. Actual problem changes retain the existing reset behavior.
- Added Practice and Progress placeholders and a short About page. Replaced the large no-problem welcome/explanation cards with Progress and a simple Open LeetCode action; guidance explanation now lives in About.
- Added four navigation regression tests covering Coach state preservation, pending requests, problem detection transitions, and keyboard navigation. Built-app fixture preview verified light/dark navigation and no horizontal overflow at 320px.
- Starter Code opens from a neutral Get starter code button; language, levels, and orange generation controls stay hidden initially. Closing the options cancels pending requests and hides visible code while keeping its cache. Its approach badge uses the same green branch icon as Hints.
- Progressive Starter Code (September 19, 2026): independent card between Hints and Solution strategies, preserving the approved light/dark styling.
- Three explicit guidance levels: Kickstart approach-specific setup, Guided initial flow, and Strong Scaffold major structure with meaningful algorithm TODOs. Placeholder exceptions keep unfinished scaffolds from silently behaving like solutions.
- Separate, independently authored starter templates for all seven canonical approaches, all four answer languages (Python, Java, JavaScript, C++), and all three levels: 84 combinations. Full solution templates are not used to generate starter code.
- `POST /api/problems/{slug}/approaches/{approach_id}/starter-code` accepts `language` and an integer `level` from 1 to 3. Unknown problems/approaches return 404, unsupported languages 400, and invalid levels 422.
- Starter requests use the selected stable `approach.id`, or the canonical primary ID before selection. A numbered badge identifies the target without revealing the strategy name.
- Starter generation is explicit: language/level changes clear stale results without requesting code. Problem/approach changes and Clear cancel requests and discard late responses. Code labels identify the generated language and level.
- Added 27 frontend starter-code regression tests and six backend tests covering all 84 combinations, validation, approach-specific scaffolding, and all 21 Python starter snippets.
- Inset the language dropdown chevron 14px from the right edge and colored the hint-approach icon with LeetCode's theme-specific Submit green.
- Fixed the Python repeated-pair-removal example's empty-string return expression; all seven Python examples compile and pair-removal behavior is regression tested.
- Hint state and cache identity now use the canonical selected-or-primary approach ID. Closing an alternative cancels pending hints and restores the primary context; reset hints hides the next-hint control.
- Added an icon and numbered approach badge beside Hints, resolved from canonical IDs and matching the approach selector's display numbering without revealing strategy names.
- Changing solution language clears the answer/error and cancels any in-flight request without automatically generating; displayed code is labeled with its response language.
- Added eight frontend regression tests covering default/selected hints, closing and resetting approaches, late responses, and solution-language changes, plus two backend snippet tests.
- Project planning and MVP requirements
- Initial Chrome extension side panel home UI
- LeetCode-inspired light and dark side panel themes
- Active LeetCode problem URL detection from the side panel
- Prominent problem title display with tab-title normalization and slug-title fallback
- Hidden internal slug tracking for backend lookup
- Side panel refresh on active-tab switches and tab URL updates
- Minimal FastAPI backend with `GET /health`
- Mock problem analysis endpoint at `GET /api/problems/{slug}`
- Seeded local analyses for `two-sum`, `valid-parentheses`, and `longest-substring-without-repeating-characters`
- Multi-approach backend response shape using `approaches[]`
- Stable canonical approach IDs using `approach.id`
- Exactly one primary approach per seeded problem
- Approach ordering with `displayOrder`
- Mock hints stored on the exact approach they belong to
- Dataset validation for missing primary approach, multiple primary approaches, and duplicate approach IDs
- Default primary hint endpoint at `GET /api/problems/{slug}/hints`
- Approach-specific hint endpoint at `GET /api/problems/{slug}/approaches/{approach_id}/hints`
- Hint service layer in `backend/app/services/hint_service.py`
- Frontend hint API module and lazy hint hook
- Progressive hint disclosure above the approach selector
- Hint reset, retry, stale-response protection, and request cancellation
- Approach selector buttons that do not reveal approach names before selection
- Selected approach details reveal name, pattern, and summary only after selection
- Thinking process remains collapsed until explicitly opened
- Switching approaches collapses the thinking process
- Switching problems resets selected approach, thinking state, and hint state
- Cleaner React component structure for problem header, hint panel, approach selector, approach details, thinking process, and analysis status
- Accessibility attributes for approach selection and expandable thinking process
- Backend connection, unsupported problem, loading, and success states preserved
- Approach-specific mock solution endpoint at `POST /api/problems/{slug}/approaches/{approach_id}/solution`
- Mock answer generation for Python, Java, JavaScript, and C++
- Generated answers tied to the selected stable `approach.id`
- Generate Answer UI shown only after selecting an approach
- Generated answer warning, code block, explanation, time complexity, and space complexity
- Generated answer reset when switching approach or LeetCode problem
- UI polish separating progressive Hints from solution-strategy Approaches
- Subtle reduced-motion-aware reveal animations for hints, selected approaches, thinking process, and generated answers
- Hint-card spacing/readability polish and selected-approach collapse behavior
- CSS-only hint and approach section spacing polish for wider, calmer reading cards
- New-device handoff summary generated as Markdown and PDF under `docs/`
- Static answers labeled as curated mock examples, with `isAiGenerated: false` in the solution response.
- Centered and reduced the detected-problem green dot, added a clear divider between progressive guidance and solution strategies, and styled the selected-approach Close button red with hover and keyboard-focus states.
- Replaced the divider and shared outer card with two independent cards for Hints and Solution strategies; selected approach details, answers, and thinking remain inside the strategy card. Light mode uses white cards on neutral gray; dark mode uses charcoal surfaces.
- Matched LeetCode's inspected problem-page system font stack, 14px body text, 24px semibold problem title, lighter control weights, neutral palette, and subtle card shadows. Inspected rendered content with Defuddle after its direct URL request returned 403; font and color values came from browser computed styles and loaded stylesheets.
- Simple README instructions for extension and backend development

---

## Important Files Changed

- `.gitignore`: ignores generated log files, virtual environments, and SQLite DB/journal files.
- `backend/app/main.py`: FastAPI routes; analysis, related, and hint endpoints use the SQLAlchemy session dependency; code-generation routes retain mock services.
- `backend/app/database.py`: shared URL configuration, engine, SQLite foreign-key settings, and request-scoped sessions.
- `backend/app/models.py`: stable metadata schema with canonical approach keys separate from internal IDs.
- `backend/app/seed.py`: transactional repeatable exact-sync of curated children within seeded problems.
- `backend/app/stable_data.py`: 20-problem stable catalog, recognition signals, related cards, and source validation.
- `backend/app/mock_data.py`: retained original problem fixtures, mock hints, and seed validation.
- `backend/app/services/problem_repository.py`: DB lookups and API serialization.
- `backend/alembic.ini` and `backend/alembic/`: schema migration environment and first revision.
- `backend/tests/test_database.py`: isolated migrated-database regression coverage.
- `backend/app/llm/`: provider contract, output validation, deterministic mock, Groq implementation, and environment-based factory for hints.
- `backend/app/services/hint_service.py`: retained legacy mock hint lookup, no longer used by the hint routes.
- `backend/app/services/solution_service.py`: approach-specific mock solution service with supported-language validation.
- `backend/app/services/__init__.py`: service package marker.
- `src/api/problemAnalysis.ts`: frontend analysis response types and validation for `isPrimary` and `displayOrder`.
- `src/api/approachHints.ts`: hint API client and response validation.
- `src/api/approachSolution.ts`: generated-answer API client, request body, response validation, and unsupported-language error mapping.
- `src/hooks/useApproachHints.ts`: lazy hint loading, caching, reset behavior, retry behavior, cancellation, and stale-response protection.
- `src/hooks/useApproachSolution.ts`: lazy generated-answer loading, retry behavior, cancellation, and stale-response protection.
- `src/App.tsx`: coordinates active problem, analysis state, selected approach, thinking expansion, and child components.
- `src/components/ProblemHeader.tsx`: detected problem heading.
- `src/components/HintPanel.tsx`: progressive hint disclosure UI.
- `src/components/ApproachSelector.tsx`: numbered approach buttons with `aria-pressed`.
- `src/components/ApproachDetails.tsx`: selected approach name, pattern, and summary.
- `src/components/GenerateAnswer.tsx`: language selector, generate button, answer warning, code block, explanation, and complexity display.
- `src/components/ThinkingProcess.tsx`: show/hide thinking-process steps with `aria-expanded`.
- `src/components/AnalysisStatus.tsx`: loading, not-found, error, and success composition.
- `src/styles.css`: styles for hint cards, component layout, approach selection, generated answers, reveal animations, and thinking-process controls.
- `docs/LeetCoach-new-device-handoff.md`: portable project handoff summary for continuing on another device.
- `docs/LeetCoach-new-device-handoff.pdf`: PDF version of the new-device handoff.
- `scripts/make_handoff_pdf.py`: dependency-free local script used to generate the handoff PDF.
- `roadmap.md`: PM handoff for the current milestone.

---

## Canonical Approach And Hint Data Flow

Backend
- Each problem owns a stable list of approaches.
- Each DB approach has an internal numeric ID and a canonical string key unique within its problem. The API exposes the canonical key as `id`, plus `isPrimary`, `displayOrder`, and `thinkingSteps`.
- `GET /api/problems/{slug}` reads SQLite and returns sorted approach metadata and recognition signals without hint arrays or internal IDs.
- `GET /api/problems/{slug}/related` reads the curated SQLite card rows, grouped by `easier / similar / harder`.
- Both hint routes now load problem facts and canonical approaches from SQLite. Starter/full-answer templates remain in their existing mock services. A database-only approach can receive hints, but not mock code templates.
- `GET /api/problems/{slug}/hints` resolves the one canonical primary approach and returns only its `approachId` and hints.
- `GET /api/problems/{slug}/approaches/{approach_id}/hints` verifies the approach belongs to that exact problem before returning hints.
- The route passes only the selected canonical approach and DB facts to `LLMProvider`; the provider does not choose or infer an approach independently. It generates all three hints in one call, validates exactly three nonempty strings, and the frontend reveals them individually.

Frontend
- `useActiveProblem` detects the active LeetCode problem and provides the slug and display title.
- `useProblemAnalysis` fetches canonical approach metadata for the detected slug.
- `App.tsx` owns `selectedApproachId` and the thinking-process expanded state.
- `HintPanel` appears above approach buttons and fetches hints only when the user clicks `Get first hint`.
- With no selected approach, `useApproachHints` calls the primary hint endpoint.
- With a selected approach, `useApproachHints` calls the approach-specific hint endpoint.
- The hook stores the returned `approachId`, reveals hints one at a time, and clears incompatible hint data when the selected approach changes.
- `GenerateAnswer` appears only after an approach is selected.
- `useApproachSolution` posts `slug`, selected `approach.id`, and selected language to the backend only when the user clicks `Generate answer`.
- Switching approaches or LeetCode problems clears the generated answer.
- Changing language does not automatically regenerate; the user must click `Generate answer` again.
- Changing language also clears the previous answer and retry context and cancels its request. Each answer displays its returned language above the code.
- The same stable `approach.id` connects hints, thinking process, generated answers, future starter code, and future LLM prompts.

Generated Answer Flow
- `POST /api/problems/{slug}/approaches/{approach_id}/solution` validates that the problem exists.
- The backend validates that the requested approach belongs to that exact problem.
- The backend validates the requested language: `python`, `java`, `javascript`, or `cpp`.
- `solution_service.py` receives the canonical problem object, canonical approach object, and language.
- The mock service returns code that matches the selected approach, not a generic problem-level answer.
- Future LLM replacement should keep this same contract: problem metadata plus selected canonical approach plus language produces an approach-specific answer. The LLM must not choose or rename the approach.

---

## Manual Test

- Run `npm run build` and confirm it succeeds.
- From `backend/`, install dependencies with `pip install -r requirements.txt` if needed.
- From `backend/`, run `uvicorn app.main:app --reload`.
- Visit `http://localhost:8000/health` and confirm `{"status":"ok"}`.
- Visit `http://localhost:8000/api/problems/two-sum` and confirm it returns sorted `approaches[]` with `isPrimary` and `displayOrder`, but no `hints`.
- Visit `http://localhost:8000/api/problems/two-sum/hints` and confirm it returns `approachId: "hash-map"` with three hints.
- Visit `http://localhost:8000/api/problems/two-sum/approaches/brute-force/hints` and confirm it returns only `brute-force` hints.
- Send `POST http://localhost:8000/api/problems/two-sum/approaches/hash-map/solution` with `{"language":"python"}` and confirm it returns hash-map style code.
- Send `POST http://localhost:8000/api/problems/two-sum/approaches/brute-force/solution` with `{"language":"python"}` and confirm it returns brute-force style code.
- Send `POST http://localhost:8000/api/problems/two-sum/approaches/hash-map/solution` with `{"language":"ruby"}` and confirm it returns 400.
- Visit `http://localhost:8000/api/problems/not-seeded/hints` and confirm it returns 404 with the local-dataset fallback detail.
- Visit `http://localhost:8000/api/problems/two-sum/approaches/not-real/hints` and confirm it returns 404 with the approach fallback detail.
- Send `POST http://localhost:8000/api/problems/not-seeded/approaches/hash-map/solution` and confirm it returns 404.
- Send `POST http://localhost:8000/api/problems/two-sum/approaches/not-real/solution` and confirm it returns 404.
- Load `dist/` as an unpacked Chrome extension.
- Open `https://leetcode.com/problems/two-sum/` and open the LeetCoach side panel.
- Confirm the detected problem view is ordered as title, hints, starter code, approaches, selected approach details/Generate Answer, then thinking process.
- Generate starter code for each level and confirm progressively more structure appears while Level 3 still requires meaningful algorithm work.
- Teaching-quality review, Two Sum / Hash Map / Java: Kickstart should provide a typed map but no loop; Guided should add the loop/current value without calculating the complement; Strong Scaffold may calculate the complement, but the student must implement map lookup, index construction, and insertion.
- Teaching-quality review, 3Sum / Two Pointers / Python: Kickstart should sort and initialize results; Guided should add the outer loop and left/right pointers without the inner loop or triplet sum; Strong Scaffold may add the inner loop, sum, and comparison branch, but the student must move pointers, record triplets, and handle duplicates.
- Teaching-quality review, Min Stack / Paired Minimums / Java: Kickstart should retain all five signatures and add shared values storage; Guided should add a shared minimum tracker; Strong Scaffold should give an initial operation branch but leave push/pop/top/getMin and minimum synchronization for the student. Old policy-2 code should disappear without deleting hints or UI choices; no new generation occurs until the button is clicked.
- Confirm starter requests use the primary approach before selection and the selected canonical ID afterward, including after closing an alternative approach.
- Change starter language/level and confirm an uncached combination shows no code or automatic request; click Generate Starter Code to load it. Revisit a cached combination and confirm its own code appears without another request.
- Hide starter code or close its options and confirm the result disappears while its cache survives; switch approaches/problems and reopen the panel to confirm each context restores only its own saved choices/code. Confirm late aborted results never appear in a new context.
- Confirm no hint, approach name, pattern, or thinking process is revealed automatically.
- Click `Get first hint` and confirm exactly one hint appears.
- Click `Show next hint` and confirm each click reveals exactly one additional hint.
- Click `Reset hints` and confirm the hints hide without clearing the selected approach.
- Request hints before selecting an approach, then select the primary approach and confirm compatible hints remain.
- Request hints before selecting an approach, then select a different approach and confirm hints reset.
- Select an approach first, then click `Get first hint` and confirm the approach-specific hint endpoint is used.
- Confirm Generate Answer is hidden before an approach is selected.
- Select an approach and confirm Generate Answer appears below the selected approach details.
- Select Python and click `Generate answer`; confirm the warning appears above a readable code block.
- Switch from `Approach 2` to `Approach 1` on Two Sum and confirm the generated answer clears.
- Generate an answer for both Two Sum approaches and confirm the code matches the selected approach.
- Change the language after generating an answer and confirm no new request happens until clicking `Generate answer` again.
- Click `Show thinking process`, switch approaches, and confirm the thinking process collapses.
- Navigate to another supported LeetCode problem and confirm selected approach, thinking process, and hints reset.
- Confirm the generated answer also clears when navigating to another LeetCode problem.
- Confirm Hints and Approaches are visually distinct but still match the LeetCoach theme.
- Confirm revealed hint cards have comfortable spacing, padding, and line height.
- Confirm hint cards use more available horizontal width and the approach section has clearer label/title/body/button spacing.
- Confirm revealed hints, selected approach details, thinking process, and generated answers appear with a quick subtle animation.
- Confirm clicking the selected approach again, or using `Close`, clears selected approach details and hides Generate Answer.
- If reduced motion is enabled at the OS/browser level, confirm reveal animations are disabled or minimized.
- Stop the backend and confirm the side panel shows a retryable backend connection error.

---

## Verified This Milestone

- October 8 redesigned Starter Code levels: 52 backend tests, 87 frontend tests, and `npm run build` pass. Backend coverage validates all 492 deterministic approach/language/level combinations, Level 1 executable setup, representative progression and remaining work, exact multi-method signatures, bad commented solutions, bare-template Kickstart, and invalid Java placeholder conditions. Frontend coverage verifies the Kickstart label/descriptions, fallback, and policy-3 cache behavior without hint loss. All 123 JavaScript scaffolds passed `node --check`; all 123 Java scaffolds compiled with `javac` using minimal local ListNode/TreeNode stubs; generated Python scaffolds passed AST parsing in the backend suite. No live Groq calls were made. C++ compiler checks and human review of live Groq teaching quality remain pending.
- October 8 teaching-quality refinement: 51 backend tests, 86 frontend tests, and the production build pass with fake Groq responses and no live Groq calls. The backend suite exercises all 492 offline problem/approach/language/level combinations and focused bad/accepted outputs; the frontend suite covers stale policy cache removal without hint or preference loss. All 123 generated JavaScript snippets passed Node syntax checks, and representative Two Sum, 3Sum, and Min Stack Java Level 3 snippets compiled with `javac`. Manual live-Groq teaching review is still pending.
- October 8 Starter Code response resilience: 49 backend tests, 84 frontend tests, and the production build pass with fake Groq responses, including valid responses with harmless formatting differences, malformed 200 responses, provider timeouts, safe offline fallback, and explicit retry after panel remount. No live Groq request is made by these tests.
- October 7 Starter Code provider/cache milestone: `py -B -m unittest discover -s backend/tests -q` passed 49 backend tests; `npm test` passed 81 frontend tests; `npm run build` passed. The backend suite covers all 41 canonical approaches across 20 problems, each in four languages and three levels using an offline mock, plus mocked Groq structured output/failure handling. The final suite makes no live Groq calls.

- October 4 persistent-workspace milestone: `npm test` passed 78 frontend tests, including ten new storage/hydration regressions for problem switches, panel remount, cached hint disclosure/reset, separate approach caches, non-LeetCode tab switching, stale in-flight responses, corrupt/unavailable storage, and stale canonical IDs. `npm run build` passed. Backend tests were not needed because API contracts and backend code did not change.
- October 4 hint-quality refinement: Groq is instructed to return three one-idea questions, without naming a technique, providing a solution sequence, or copying approach metadata. Shared output handling keeps the first complete sentence and limits successive hints to 10/14/18 words and 75/100/120 characters; overlong single-sentence responses use a short fallback nudge. Groq hints that are commands, contain code formatting, or directly name the selected approach/pattern also use a short fallback question. Offline mock hints are shorter and no longer announce the approach pattern early. A manual Groq check for Two Sum returned short questions without code or a full algorithm. No frontend/API contract changed. Backend tests: 50 passed; frontend tests: 68 passed; build passed.
- October 4 LLM hint milestone: `MockLLMProvider` and `GroqLLMProvider` share `generate_hints(context)`. The mock is deterministic and offline; Groq reads `GROQ_API_KEY` and `LEETCOACH_LLM_MODEL` only from environment or ignored `backend/.env` and is selected by `LEETCOACH_LLM_PROVIDER=groq` (default `mock`). No real Groq calls were run. Missing configuration returns sanitized 503, provider failure returns 503, and invalid output returns 502.
- Hint grounding is SQLite Problem facts (slug, title, difficulty, summary, ordered constraints/examples) plus the selected canonical Approach (key, name, pattern, summary, thinking steps, recognition signals). It does not require a submission template, use fixture-based hint IDs, fetch LeetCode URLs, or send other approaches. The 17 newer DB-backed problems are eligible for hints through the same flow.
- `py -B -m unittest discover -s backend/tests`: 47 backend tests passed. `npm test`: 68 frontend tests passed. `npm run build`: passed. Provider tests fake Groq calls, verify one request, strict output and timeout handling, and use no API key.
- September 30 database milestone: backend coverage verifies migration upgrade/downgrade, model consistency, all seeded API payloads, lookups independent of fixtures, persistence after reopening SQLite, seed idempotency/internal ID stability, transaction rollback, uniqueness, foreign keys, cascading deletion, and unchanged mock guidance responses.
- `npm test`: 68 frontend regression tests passed, including Recognition Signals, same-problem section/workspace restoration, Coach, Starter Code, navigation, and Practice coverage.
- `py -B -m unittest discover -s backend/tests`: all 35 backend tests passed, including `0001 ↔ 0002` migration coverage, all 20 Problem Specifications, ordered constraints/examples, 80 submission templates, exact-sync/repeat seeding with stable IDs, schema constraints, internal context loading, stable-data API parity, recognition metadata, related-problem endpoints, guidance boundaries, all 84 existing starter responses, and existing Python answer/starter compilation.
- Local `alembic upgrade head`, `alembic check`, and repeat `app.seed` runs succeeded. SQLite now contains 20 problem specs, 49 ordered constraints, 32 examples, and 80 submission templates alongside the existing 41 approaches / signal sets, 84 signal bullets, and 68 related cards.
- All 21 JavaScript starter snippets passed Node syntax checks.
- Built-app browser preview against the real starter endpoint verified Java Level 3, separate card placement, and light/dark layouts at 420px and 320px. Narrow layouts keep code overflow inside its scrollable block.
- `npm run build` succeeds.
- `python -m compileall app` succeeds from `backend/`.
- The seeded mock dataset reports exactly one primary approach per problem.
- `GET /health` returns status 200.
- The main problem-analysis endpoint still works.
- The default hint endpoint returns the primary approach hints.
- The approach-specific hint endpoint returns the requested approach hints.
- The generated-answer endpoint returns an approach-specific response for valid problem, approach, and language.
- Two Sum `hash-map` and `brute-force` return different mock code and complexity values.
- Unsupported solution languages return 400.
- Mock solution coverage exists for every seeded approach and supported language.
- UI-only polish build passed with no backend/API/hook changes.
- CSS-only hint and approach spacing polish build passed.
- Separate guidance/strategy cards and LeetCode-style typography build passed; browser preview with the seeded problem fixtures verified light/dark cards, hint reveal, approach selection, and centered status dot.
- Selected approach can be collapsed without changing backend/API contracts.
- Invalid problem slugs return 404.
- Invalid approach IDs return 404.
- The local dev server was stopped after verification.

---

## Known Limitations

- Practice offers manually curated related problems stored in SQLite for all 20 seeded problems. Opening a related problem does not imply full mock guidance is available for it. Progress remains a placeholder; no learning-history persistence is implemented yet.
- Chrome side-panel interactions still need manual browser verification after reloading the unpacked extension.
- Stable metadata and both Hints and Starter Code grounding use SQLite. Full Solution still uses in-memory templates and fixture-based problem/approach validation.
- Hints and Starter Code use a deterministic mock provider by default; live generation requires Groq configuration and a working network connection. Starter validation catches common leakage and syntax problems, but cannot prove arbitrary code is pedagogically incomplete. Live Groq outputs still need human review at each level.
- Generated answers are static mock strings, not generated by an AI provider.
- Full Solutions remain fully mocked only for Two Sum, Valid Parentheses, and Longest Substring Without Repeating Characters (seven approaches total). All 20 DB problems support Hints and Starter Code; the offline Starter Code mock uses deterministic DB-grounded scaffolds and Groq can generate richer ones when configured.
- No PostgreSQL, authentication, cloud deployment, or user history yet.
- The extension assumes the local backend is available at `http://localhost:8000`.

---

## Next Recommended Milestone

- Evaluate live hint quality and safety with a manually reviewed Groq run after configuring a key; keep the mock provider for offline development and tests.
- Expand curated coverage only with matching guidance templates; preserve canonical approach keys and the existing API contracts.

---

## Future Features

- LLM Full Solution integration when its mock-to-provider transition is explicitly scoped
- Interview follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
