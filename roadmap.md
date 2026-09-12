# LeetCoach Roadmap

## Vision

Don't give me the answer.
Teach me how to discover it.

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

Database
- Planned: SQLite for local MVP
- Planned: SQLAlchemy and Alembic for future PostgreSQL migration

AI
- Current: static mock guidance only
- Planned: mock AI provider interface before any real LLM integration
- Future providers may include OpenAI, Gemini, or OpenRouter

---

## Completed

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
- Confirm the detected problem view is ordered as title, hints, approaches, selected approach details, then thinking process.
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
- Selected approach can be collapsed without changing backend/API contracts.
- Invalid problem slugs return 404.
- Invalid approach IDs return 404.
- The local dev server was stopped after verification.

---

## Known Limitations

- Chrome side-panel interactions still need manual browser verification after reloading the unpacked extension.
- The backend still uses in-memory mock data.
- Hints are static mock strings, not generated by an AI provider.
- Generated answers are static mock strings, not generated by an AI provider.
- No SQLite, SQLAlchemy, Alembic, PostgreSQL, authentication, user history, or starter code yet.
- The extension assumes the local backend is available at `http://localhost:8000`.

---

## Next Recommended Milestone

- Add focused tests for backend dataset validation, hint endpoints, solution endpoint behavior, URL parsing, API response normalization, and React hook behavior.
- After tests are in place, introduce SQLite with SQLAlchemy models for problems, approaches, related problems, and starter templates.
- Keep the stable `approach.id` contract unchanged when moving from mock data to database-backed data.

---

## Future Features

- SQLite persistence
- SQLAlchemy models
- Alembic migrations
- Mock AI provider abstraction
- Starter code with progressive guidance levels
- Related questions
- Interview follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
