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
- Opt-in local MVP evaluation harness with SQLite-validated cases and bounded live Groq calls

Backend
- FastAPI
- SQLAlchemy 2.x repositories for stable problem and approach metadata
- Local CORS for Chrome extension and localhost development
- Canonical approach metadata with stable approach IDs
- DB-grounded hint routes using a small LLMProvider boundary
- DB-grounded Full Solution route through the existing LLMProvider boundary (offline curated mock or Groq)
- DB-grounded Starter Code route through the same LLMProvider boundary (offline mock or Groq)
- Manually curated related-problem rows per seeded problem

Database
- Local SQLite (`backend/leetcoach.db`) through SQLAlchemy 2.x
- Alembic revisions `0001` (stable approach metadata) and `0002` (Problem Specification / LLM grounding), plus an explicit repeatable seed command
- Request-scoped sessions; SQLite foreign keys and cascade rules enabled
- Future PostgreSQL migration remains a separate milestone

AI
- Current: deterministic offline MockLLMProvider or live GroqLLMProvider for Hints, Starter Code, and Full Solution
- Offline Full Solution fixtures cover the original seven approaches across three problems; Groq uses all 20 seeded problems and 41 canonical approaches
- Future providers may include OpenAI, Gemini, or OpenRouter

---

## Persistent Coach Workspaces and Disclosure (October 13, 2026)

`chrome.storage.local` stores the existing versioned `leetcoach-workspaces-v1` map keyed by problem slug. Each workspace saves the selected canonical approach ID, section preference, language/level choices, and validated generated hint, Starter Code, and Full Solution responses. Disclosure is runtime-only: hint counts, Starter Code options/code visibility, full-answer visibility for every language, Recognition Signals, and Thinking Process all hydrate collapsed. An explicit reveal or Generate click reuses a matching cached response without a backend or LLM request. Selected approach details remain visible after reopening the panel.

The extension waits for storage hydration before showing a detected problem's Coach controls or writing defaults, so a saved workspace is not overwritten during startup. Stored shapes and slug/approach keys are validated; missing, obsolete, corrupt, or unavailable storage falls back to a clean in-memory workspace. A failed storage read disables writes for that panel session so a temporary outage cannot erase previously saved data. Stale selected IDs are discarded after the current DB-backed analysis loads. Whole-map writes are serialized to keep later state from being overwritten by a slower earlier write. The Manifest V3 `storage` permission was added. Theme remains in its existing `localStorage` key.

Changing or closing an approach, same-tab navigation/reload, and panel remount collapse all optional guidance without deleting cached responses. Switching extension sections or Chrome tabs in the same open panel preserves each problem's runtime disclosure, including Recognition Signals; two Chrome tabs with the same slug share that slug's workspace. Pending hint, Starter Code, and Full Solution requests are aborted or ignored after a collapse. Older v1 records with saved reveal flags hydrate collapsed while preserving valid content and choices. Corrupt or obsolete-policy cache entries are discarded individually. Loaded Practice cards remain session-only.

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

At that September 30 milestone, hint text, starter templates, and full answers were mocked. Thinking steps were stored with approach metadata in SQLite. Later provider milestones moved all three teaching features to SQLite-grounded mock/Groq generation.

Problem Specification gives both providers factual, local grounding rather than opening a LeetCode URL, relying on memory, guessing constraints, or inventing a function signature. The database owns problem facts, submission shells, and canonical approach identity. `find_problem_context` assembles the selected approach and language-specific template for Starter Code and Full Solution; the hint routes retain their language-free DB context loader.

Future PostgreSQL path: add the PostgreSQL driver/configuration in a separate milestone, apply and test the portable SQLAlchemy/Alembic schema against that dialect, and transfer local rows with foreign-key/sequence verification (or seed a fresh database). Public problem slugs and canonical approach keys stay unchanged. SQLite-specific connection settings are isolated in `database.py`; PostgreSQL is not installed or deployed now.

---

## Completed

- MVP live LLM evaluation (October 14, 2026, Pacific time): added `backend/evaluation/` with a deterministic 31-case matrix against the seeded SQLite catalog, a dry-run default, explicit `--live`, cumulative call cap and resume support, paced FastAPI endpoint requests, independent correctness fixtures, categorized failures, and JSON/Markdown reports under ignored `backend/evaluation_runs/`. Generated Python and C++ run only in bounded WSL bubblewrap namespaces without network or writable host mounts; JavaScript/Java execution is marked NOT_RUN where no isolated runtime exists. A separate reassessment command updates saved response findings without new Groq calls. The baseline used 31 real generation requests: 30 HTTP 200 and one sanitized HTTP 503; seven of nine Starter Code requests returned offline fallback after Groq output rejection; two accepted live AI scaffolds need teaching review. Ten of twelve Full Solutions passed 43/43 independent executable fixtures; JavaScript and Java correctness were not executed, though syntax/compilation checks passed. Evaluation-specific checks and preliminary editorial review flagged solution-recipe leakage in Starter Code comments, inconsistent Min Stack level state, and O(1) auxiliary-space claims for 3Sum implementations that sort. No generated Full Solution failed an executed fixture, but the sample does not prove general correctness. **Recommendation: NO-GO** on scalable ingestion until Starter Code reliability/teaching quality and the provider error are investigated, plus human review and broader correctness coverage. The full local reports are `backend/evaluation_runs/20261015T064805Z-e1ae2d52/mvp_evaluation.json` and `mvp_evaluation_report.md`. The final regression run passed 67 backend tests, 97 frontend tests, and `npm run build`. Next milestone: targeted investigation of these observed issues and a repeat evaluation before catalog expansion; product generation code remains unchanged in this evaluation milestone.
- Coach disclosure reset (October 13, 2026): separated persisted generated content and preferences from runtime reveal state without changing the storage key or API contracts. Approach changes, same-tab navigation/reload, and panel remount collapse hints, Starter Code, full answers, Recognition Signals, and Thinking Process; extension-section and browser-tab switches within an open panel preserve them. A disclosure revision protects against late responses. Focused regressions cover cache reuse, tab navigation, old-storage hydration, and pending requests. All 97 frontend tests and `npm run build` pass.
- Real LLM Full Solution + persistent cache (October 13, 2026): the unchanged `POST /api/problems/{slug}/approaches/{approach_id}/solution` contract now validates problem and canonical approach against SQLite, loads constraints/examples/thinking steps and the language-specific submission template, and calls `LLMProvider.generate_solution`. Groq makes one structured JSON request for complete code, explanation, and time/space complexity. A focused validator requires nonempty bounded fields, exact submission class and every method signature (including Min Stack), valid Python AST or basic structural checks for Java/JavaScript/C++, and rejects fences, TODOs, obvious placeholders, and empty Python branches. Output checks are structural and cannot prove algorithmic correctness or complexity accuracy. Provider configuration/outages return sanitized 503, malformed output 502, and Groq failures never fall back to an unrelated mock answer. The offline mock reuses only seven original curated solutions and returns 503 for other seeded approaches; no database schema or migration changed. The existing workspace caches by slug/approach/language, tracks language and visibility, hides without deletion, restores on panel reopening, and rejects stale/aborted or mismatched responses. Generation remains an explicit click.
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
- `backend/app/main.py`: FastAPI routes; stable-data lookups and all three teaching-feature routes use DB-grounded provider context.
- `backend/app/database.py`: shared URL configuration, engine, SQLite foreign-key settings, and request-scoped sessions.
- `backend/app/models.py`: stable metadata schema with canonical approach keys separate from internal IDs.
- `backend/app/seed.py`: transactional repeatable exact-sync of curated children within seeded problems.
- `backend/app/stable_data.py`: 20-problem stable catalog, recognition signals, related cards, and source validation.
- `backend/app/mock_data.py`: retained original problem fixtures, mock hints, and seed validation.
- `backend/app/services/problem_repository.py`: DB lookups and API serialization.
- `backend/alembic.ini` and `backend/alembic/`: schema migration environment and first revision.
- `backend/tests/test_database.py`: isolated migrated-database regression coverage.
- `backend/app/llm/`: provider contract, hint/starter/full-solution output validation, deterministic mock, Groq implementation, and environment-based factory.
- `backend/app/services/hint_service.py`: retained legacy mock hint lookup, no longer used by the hint routes.
- `backend/app/services/solution_service.py`: retained original seven curated full-solution fixtures for the offline mock provider.
- `backend/app/services/__init__.py`: service package marker.
- `src/api/problemAnalysis.ts`: frontend analysis response types and validation for `isPrimary` and `displayOrder`.
- `src/api/approachHints.ts`: hint API client and response validation.
- `src/api/approachSolution.ts`: generated-answer API client, request body, response validation, and unsupported-language error mapping.
- `src/hooks/useApproachHints.ts`: lazy hint loading, caching, reset behavior, retry behavior, cancellation, and stale-response protection.
- `src/hooks/useApproachSolution.ts`: explicit full-solution loading, per-language visibility/cache reuse, retry, cancellation, and stale-response protection.
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
- Both hint routes and the Starter Code and Full Solution routes load problem facts and canonical approaches from SQLite. The language-specific submission template also comes from SQLite. Offline full-answer fixtures remain available only for the original seven approaches.
- `GET /api/problems/{slug}/hints` resolves the one canonical primary approach and returns only its `approachId` and hints.
- `GET /api/problems/{slug}/approaches/{approach_id}/hints` verifies the approach belongs to that exact problem before returning hints.
- The route passes only the selected canonical approach and DB facts to `LLMProvider`; the provider does not choose or infer an approach independently. It generates all three hints in one call, validates exactly three nonempty strings, and the frontend reveals them individually.

Frontend
- `useActiveProblem` detects the active LeetCode problem and provides the slug and display title.
- `useProblemAnalysis` fetches canonical approach metadata for the detected slug.
- `App.tsx` coordinates selected approach and runtime disclosure from the per-problem workspace.
- `HintPanel` appears above approach buttons and fetches hints only when the user clicks `Get first hint`.
- With no selected approach, `useApproachHints` calls the primary hint endpoint.
- With a selected approach, `useApproachHints` calls the approach-specific hint endpoint.
- The hook stores the returned `approachId`, reveals hints one at a time, and clears incompatible hint data when the selected approach changes.
- `GenerateAnswer` appears only after an approach is selected.
- `useApproachSolution` posts `slug`, selected `approach.id`, and selected language to the backend only when the user clicks `Generate answer`.
- Switching approaches or navigating/reloading the same tab hides all answers; an explicit Generate click reuses the selected combination's cached answer.
- Changing language does not automatically request an answer. A previously visible answer for that language returns from cache; an unrevealed or uncached one requires `Generate answer`.
- Changing language cancels its previous request and retry context. Each answer displays its returned language above the code. Hide answer conceals it but keeps the cache.
- The same stable `approach.id` connects hints, starter code, thinking process, full answers, and provider prompts.

Generated Answer Flow
- `POST /api/problems/{slug}/approaches/{approach_id}/solution` validates that the problem exists.
- The backend validates that the requested approach belongs to that exact problem.
- The backend validates the requested language: `python`, `java`, `javascript`, or `cpp`.
- `find_problem_context` passes the selected DB approach, factual specification, and exact requested-language submission template to the configured `LLMProvider`.
- Groq returns a single structured JSON object; validation checks fields, signatures, placeholders, and basic syntax before the unchanged response shape is sent. The model is instructed to implement the selected approach, not choose another one.
- The offline mock returns one of seven curated answers where available. Missing offline coverage returns 503; a Groq error returns 503 or 502 without silently substituting a mock answer.

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
- Hide starter code or close its options and confirm the result disappears while its cache survives; switch approaches/problems and reopen the panel to confirm saved choices remain but guidance is collapsed. Confirm late aborted results never appear in a new context.
- Confirm no hint, approach name, pattern, or thinking process is revealed automatically.
- Click `Get first hint` and confirm exactly one hint appears.
- Click `Show next hint` and confirm each click reveals exactly one additional hint.
- Click `Reset hints` and confirm the hints hide without clearing the selected approach.
- Request hints before selecting an approach, then select the primary approach and confirm hints collapse but can be revealed again from cache.
- Request hints before selecting an approach, then select a different approach and confirm hints reset.
- Select an approach first, then click `Get first hint` and confirm the approach-specific hint endpoint is used.
- Confirm Generate Answer is hidden before an approach is selected.
- Select an approach and confirm Generate Answer appears below the selected approach details.
- Select Python and click `Generate answer`; confirm the warning appears above a readable code block.
- Switch from `Approach 2` to `Approach 1` on Two Sum and confirm all answers hide until explicitly generated again.
- Generate an answer for both Two Sum approaches and confirm the code matches the selected approach.
- Change the language after generating an answer and confirm no new request happens; a previously revealed matching-language answer reappears, while an unrevealed language stays hidden until clicking `Generate answer`.
- Hide an answer and confirm the code disappears, then click Generate again and confirm the same cached answer returns without another backend request. Reopen the panel and check that every answer is hidden while its cache remains.
- Click `Show thinking process`, switch approaches, and confirm the thinking process collapses.
- Navigate to another supported LeetCode problem and confirm selected approach, thinking process, and hints reset.
- Confirm switching Chrome tabs in one open panel preserves each problem's revealed answer, while same-tab navigation/reload collapses the answer and retains its cache.
- Confirm Hints and Approaches are visually distinct but still match the LeetCoach theme.
- Confirm revealed hint cards have comfortable spacing, padding, and line height.
- Confirm hint cards use more available horizontal width and the approach section has clearer label/title/body/button spacing.
- Confirm revealed hints, selected approach details, thinking process, and generated answers appear with a quick subtle animation.
- Confirm clicking the selected approach again, or using `Close`, clears selected approach details and hides Generate Answer.
- If reduced motion is enabled at the OS/browser level, confirm reveal animations are disabled or minimized.
- Stop the backend and confirm the side panel shows a retryable backend connection error.

---

## Verified This Milestone

- October 13 Full Solution milestone: 61 backend tests pass, including DB resolution for all 20 problems/41 approaches/four languages, mocked one-call Groq JSON for both Two Sum approaches in four languages, signature/placeholder/error validation, isolated Python correctness checks for offline Two Sum/Valid Parentheses and known-good mocked provider payloads for 3Sum, Binary Search, and Min Stack, plus JavaScript syntax and Java compilation of the seven offline answers when the tools are installed. 92 frontend tests pass, including per-language/approach/problem cache restoration, hide/reveal reuse, malformed-cache isolation, and aborted request protection. `npm run build` passes. These tests make no live Groq requests; structural validation and a few offline examples cannot guarantee arbitrary live AI code or complexity claims are correct.
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
- Offline mock full-solution coverage exists for the original seven approaches in all four supported languages; configured Groq can request any of the 41 seeded approaches.
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
- Hints, Starter Code, and Full Solution all use SQLite grounding and the existing mock/Groq provider. Live generation requires Groq configuration and network access. Starter validation cannot prove arbitrary code is pedagogically incomplete; Full Solution validation cannot prove algorithmic correctness, selected-approach fidelity, or complexity accuracy. Human review of live Groq output remains necessary.
- Offline Full Solution coverage remains only Two Sum, Valid Parentheses, and Longest Substring Without Repeating Characters (seven approaches total). The other seeded approaches require configured Groq for full answers; they return 503 in offline mock mode. Hints and Starter Code still cover all 20 seeded problems.
- No PostgreSQL, authentication, cloud deployment, or user history yet.
- The extension assumes the local backend is available at `http://localhost:8000`.

---

## Next Recommended Milestone

- Manually review live Groq Full Solutions across representative problems, approaches, languages, edge cases, and complexity claims after configuring a key. No live Groq Full Solution request was made by the automated suite.
- Expand curated coverage only with matching guidance templates; preserve canonical approach keys and the existing API contracts.

---

## Future Features

- Optional compiler-backed validation for live Java/C++ solutions and broader answer-quality evaluation
- Interview follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
