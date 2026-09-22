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

Backend
- FastAPI
- In-memory mock problem dataset
- Local CORS for Chrome extension and localhost development
- Canonical approach metadata with stable approach IDs
- Hint service abstraction reading mock approach-owned hints
- Solution service abstraction returning approach-specific mock answers
- Independent starter-code service with curated progressive scaffolds
- Manually curated related-problem lists per seeded problem

Database
- Planned: SQLite for local MVP
- Planned: SQLAlchemy and Alembic for future PostgreSQL migration

AI
- Current: static mock guidance only
- Planned: mock AI provider interface before any real LLM integration
- Future providers may include OpenAI, Gemini, or OpenRouter

---

## Completed

- Recognition Signals (September 21, 2026): placed inside Solutions between Summary and Generate Answer, visible only for an explicitly selected canonical approach. It uses the existing section divider, a small green lightbulb icon, and a neutral Reveal recognition signals button, without an approach badge.
- Each of the seven seeded approaches owns structured `recognitionSignals: { quote?, bullets }` metadata: two or three beginner-friendly cues about recognizing the approach from the statement, plus a short statement excerpt. Metadata is included in the existing problem-analysis response; revealing/hiding it makes no new request.
- Recognition disclosure resets on approach/problem changes and closing an approach; it stays intact across section switches and temporary visits to non-LeetCode tabs. Missing metadata from older backends hides the section without breaking Coach.
- Added eight frontend recognition tests and backend coverage of all seven approach payloads. Tests verify placement inside Solutions and navigation state preservation. The initial built-app preview against FastAPI checked keyboard reveal/hide and light/dark styling at narrow sidebar width.
- Same-problem tab restoration (September 21, 2026): temporarily visiting a non-LeetCode browser tab no longer destroys the problem workspace. Returning to the same slug restores Coach, Practice, Progress, or About and preserves approaches, hints, starter code, thinking, answers, and loaded related problems in the open side-panel session. A different slug still starts at Coach and resets problem-specific state; deliberate Progress/About selections made while away take precedence.
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
- Starter Code opens from a neutral Get starter code button; language, levels, and orange generation controls stay hidden initially. Hiding it cancels pending requests and clears code. Its approach badge uses the same green branch icon as Hints.
- Progressive Starter Code (September 19, 2026): independent card between Hints and Solution strategies, preserving the approved light/dark styling.
- Three explicit guidance levels: Minimal signatures, Guided variables/data structures, and Strong Scaffold control flow with meaningful algorithm TODOs. Placeholder exceptions keep unfinished scaffolds from silently behaving like solutions.
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

- `.gitignore`: ignores generated log files.
- `backend/app/main.py`: canonical mock problem data, dataset validation, main analysis endpoint, primary hint endpoint, and approach-specific hint endpoint.
- `backend/app/services/hint_service.py`: focused hint lookup service that operates on canonical approach objects.
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
- Each approach has a unique `id`, `isPrimary`, `displayOrder`, `thinkingSteps`, and `hints`.
- `GET /api/problems/{slug}` returns sorted approach metadata without hint arrays.
- `GET /api/problems/{slug}/hints` resolves the one canonical primary approach and returns only its `approachId` and hints.
- `GET /api/problems/{slug}/approaches/{approach_id}/hints` verifies the approach belongs to that exact problem before returning hints.
- The hint service receives the canonical problem and approach context; it does not choose or infer an approach independently.

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
- Confirm starter requests use the primary approach before selection and the selected canonical ID afterward, including after closing an alternative approach.
- Change starter language/level and confirm old code clears without a request; click Generate Starter Code to load the new scaffold.
- Clear starter code, switch approaches, and switch problems; confirm old code and pending results cannot reappear.
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

- `npm test`: 68 frontend regression tests passed, including Recognition Signals, same-problem section/workspace restoration, Coach, Starter Code, navigation, and Practice coverage.
- `py -B -m unittest discover -s backend/tests`: all 11 backend tests passed, covering recognition metadata for all seven approaches, related-problem data/endpoints, all 84 starter responses, and compilation of every Python full-answer and starter example.
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

- Practice currently offers only hard-coded related problems for the three seeded problems. Opening a related problem does not imply Coach guidance is seeded for it. Progress remains a placeholder; no learning-history persistence is implemented yet.
- Chrome side-panel interactions still need manual browser verification after reloading the unpacked extension.
- The backend still uses in-memory mock data.
- Hints are static mock strings, not generated by an AI provider.
- Generated answers are static mock strings, not generated by an AI provider.
- Starter code is curated mock content; only the three seeded problems and their seven approaches are supported.
- No SQLite, SQLAlchemy, Alembic, PostgreSQL, authentication, or user history yet.
- The extension assumes the local backend is available at `http://localhost:8000`.

---

## Next Recommended Milestone

- Extend the existing regression suite with backend dataset validation, endpoint behavior, URL parsing, API normalization, and additional navigation cases.
- After tests are in place, introduce SQLite with SQLAlchemy models for problems, approaches, related problems, and starter templates.
- Keep the stable `approach.id` contract unchanged when moving from mock data to database-backed data.

---

## Future Features

- SQLite persistence
- SQLAlchemy models
- Alembic migrations
- Mock AI provider abstraction
- Interview follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
