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

Backend
- FastAPI
- In-memory mock problem analysis dataset
- Local CORS for Chrome extension and localhost development

Database
- Planned: SQLite for local MVP
- Planned: SQLAlchemy and Alembic for future PostgreSQL migration

AI
- Planned: Mock provider behind a swappable provider interface
- Current milestone uses static mock guidance only

---

## Completed

- Project planning and MVP requirements
- Initial Chrome extension side panel home UI
- LeetCode-inspired light and dark side panel themes
- Active LeetCode problem URL detection from the side panel
- Prominent problem title display with tab-title normalization and slug-title fallback
- Hidden internal slug tracking for future backend lookup
- Side panel refresh on active-tab switches and tab URL updates
- Minimal FastAPI backend with `GET /health`
- Mock problem analysis endpoint at `GET /api/problems/{slug}`
- Seeded local analyses for `two-sum`, `valid-parentheses`, and `longest-substring-without-repeating-characters`
- Multi-approach backend response shape using `approaches[]`
- Frontend response normalization for current `approaches[]` data and legacy single-pattern data
- Progressive disclosure UI: choose an approach first, then optionally reveal its thinking process
- Active-problem layout hides the welcome hero to save side-panel space
- Higher-contrast side-panel colors and larger typography
- Frontend fetch flow for loading, success, not-found, and backend-error states
- Retry action for backend connection errors after the local server starts
- Simple README instructions for extension and backend development

---

## Data Flow

- The side panel reads the active Chrome tab with `chrome.tabs.query`.
- `src/problemUrl.ts` validates `https://leetcode.com/problems/*`, extracts the slug, and normalizes the display title.
- `src/useActiveProblem.ts` refreshes the active problem when tabs change or URLs update.
- `src/useProblemAnalysis.ts` requests `http://localhost:8000/api/problems/{slug}` when a slug is detected.
- `src/api/problemAnalysis.ts` maps 200 responses to a `ProblemAnalysis` object with `approaches[]`, 404 responses to the local-dataset fallback, and network failures to the backend connection-error state.
- `src/App.tsx` renders numbered approach buttons first. It reveals approach name, pattern, and summary only after selection, and reveals thinking steps only after the user clicks `Show thinking process`.
- Switching detected slugs resets the selected approach and collapses thinking steps.

---

## Important Files Changed

- `backend/app/main.py`: FastAPI app, CORS, health endpoint, multi-approach in-memory analyses, and 404 fallback.
- `backend/requirements.txt`: Backend dependencies.
- `backend/README.md`: Backend setup and run instructions.
- `src/api/problemAnalysis.ts`: Frontend API client and multi-approach response types.
- `src/useProblemAnalysis.ts`: React hook for backend analysis state management and retry.
- `src/App.tsx`: Approach selection, selected approach details, thinking-process toggle, and conditional welcome hero.
- `src/styles.css`: Higher contrast themes, larger typography, approach buttons, selected approach layout, and progressive disclosure styling.
- `public/manifest.json`: Adds narrow `http://localhost:8000/*` host permission.
- `roadmap.md`: PM handoff and manual test instructions.

---

## Manual Test

- Run `npm run build` and confirm it succeeds.
- From `backend/`, install dependencies with `pip install -r requirements.txt`.
- From `backend/`, run `uvicorn app.main:app --reload`.
- Visit `http://localhost:8000/health` and confirm `{"status":"ok"}`.
- Visit `http://localhost:8000/api/problems/two-sum` and confirm it returns an `approaches` array with `brute-force` and `hash-map`.
- Visit `http://localhost:8000/api/problems/valid-parentheses` and confirm it returns multiple approaches.
- Visit `http://localhost:8000/api/problems/longest-substring-without-repeating-characters` and confirm it returns three approaches.
- Visit an unknown slug such as `http://localhost:8000/api/problems/total-waviness-of-numbers-in-range-ii` and confirm the 404 detail says the problem is not available yet.
- Load `dist/` as an unpacked Chrome extension.
- Open `https://leetcode.com/problems/two-sum/`, open the LeetCoach side panel, and confirm it initially shows `Choose an approach` with `Approach 1` and `Approach 2`.
- Confirm the `LeetCoach MVP` welcome hero is hidden while a problem is detected.
- Navigate away from a problem page and confirm the welcome hero returns.
- Confirm the initial buttons do not reveal names like `Brute Force` or `Hash Map`.
- Click `Approach 1` and confirm it reveals approach name, pattern, and summary, but not thinking steps.
- Click `Show thinking process` and confirm only Approach 1 thinking steps appear.
- Click `Hide thinking process` and confirm the steps collapse.
- Click `Approach 2` and confirm the previous thinking process is collapsed automatically.
- Navigate to `https://leetcode.com/problems/valid-parentheses/` and confirm the selected approach resets.
- Navigate to an unsupported but detected problem and confirm the local-dataset fallback displays.
- Stop the backend and confirm the side panel shows `Unable to connect to the local LeetCoach backend.`
- Restart the backend, click `Retry`, and confirm the analysis loads without navigating away.

---

## Next

- Add focused tests for URL parsing, title normalization, backend 404 behavior, multi-approach response shape, and frontend API state mapping.
- Add SQLite with SQLAlchemy models for problems and approaches after the API contract stabilizes.
- Keep progressive disclosure intact when replacing the in-memory dictionary with database-backed lookup.

---

## Future Features

- Alembic migrations
- Mock AI provider abstraction
- Starter code
- Hints
- Related questions
- Follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
