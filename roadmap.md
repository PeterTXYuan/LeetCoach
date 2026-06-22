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

---

## In Progress

- Content script planning

---

## Next

- Add content script for `leetcode.com/problems/*`
- Detect problem slug from the active LeetCode tab
- Send detected problem context to the side panel
- Create FastAPI backend scaffold

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
