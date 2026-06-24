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
- Prominent problem title display for supported `leetcode.com/problems/*` tabs
- Hidden internal slug tracking for future backend lookup
- Side panel refresh on active-tab switches and tab URL updates
- Detected-problem UI polish with tab-title normalization and slug-title fallback

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

- `src/problemUrl.ts`: Pure URL parser for supported LeetCode problem pages, tab-title normalization, and human-readable slug fallback.
- `src/useActiveProblem.ts`: React hook that reads the active Chrome tab and refreshes on tab activation/navigation updates.
- `src/App.tsx`: Side panel UI now shows a prominent problem title, minimal placeholder, or the waiting state.
- `src/styles.css`: Added detected-problem card and large title styling.

---

## Manual Test

- Run `npm run build` and confirm it succeeds.
- Load the generated `dist/` folder as an unpacked Chrome extension.
- Open `https://leetcode.com/problems/two-sum/`.
- Click the LeetCoach extension icon to open the side panel.
- Confirm the panel shows a green detected icon and the title `1. Two Sum`.
- Confirm the slug `two-sum` is not shown as the primary title.
- Navigate to another problem such as `https://leetcode.com/problems/valid-parentheses/`.
- Confirm the side panel title updates to `20. Valid Parentheses`.
- Open a newer problem such as `https://leetcode.com/problems/total-waviness-of-numbers-in-range-ii/`.
- Confirm a tab title like `3753. Total Waviness of Numbers in Range II - LeetCode` is displayed without the trailing `- LeetCode`.
- Navigate away from a LeetCode problem page and confirm the waiting state returns with the "Open LeetCode" button.

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
