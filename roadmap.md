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
- Planned: FastAPI

Database
- Planned: SQLite for local MVP
- Planned: SQLAlchemy and Alembic for future PostgreSQL migration

AI
- Planned: Mock provider behind a swappable provider interface

---

## Completed

- Project planning
- MVP requirements
- Extension architecture direction
- Initial Chrome extension side panel home UI
- Vite build setup for the side panel extension bundle
- Basic project hygiene with ignored generated files and dependencies
- Simple README for the initial open-source project landing page
- LeetCode-inspired light and dark side panel themes
- Active LeetCode problem URL detection from the side panel
- Problem slug display for supported `leetcode.com/problems/*` tabs
- Side panel refresh on active-tab switches and tab URL updates

---

## In Progress

- Pattern data milestone planning

---

## Next

- Add a local frontend pattern-data placeholder for seeded problems
- Decide whether the next implementation should introduce FastAPI immediately or mock pattern responses in the extension first
- Keep using slug-only lookup as the handoff contract

---

## Important Files Changed

- `src/problemUrl.ts`: Pure URL parser for supported LeetCode problem pages.
- `src/useActiveProblem.ts`: React hook that reads the active Chrome tab and refreshes on tab activation/navigation updates.
- `src/App.tsx`: Side panel UI now shows detected status, problem slug, or the waiting state.
- `src/styles.css`: Added detected-state styling for the status card.

---

## Manual Test

- Run `npm run build` and confirm it succeeds.
- Load the generated `dist/` folder as an unpacked Chrome extension.
- Open `https://leetcode.com/problems/two-sum/`.
- Click the LeetCoach extension icon to open the side panel.
- Confirm the panel says the problem page is detected and shows `two-sum`.
- Navigate to another problem such as `https://leetcode.com/problems/valid-parentheses/`.
- Confirm the side panel updates to `valid-parentheses`.
- Navigate away from a LeetCode problem page and confirm the waiting state returns with the “Open LeetCode” button.

---

## Future Features

- Pattern lookup from SQLite
- Mock AI thinking process responses
- Starter code
- Hints
- Related questions
- Follow-up questions
- OpenAI, Gemini, or OpenRouter provider integration
- PostgreSQL migration
- User accounts and learning history
