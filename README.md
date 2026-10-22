# LeetCoach

LeetCoach is a Chrome extension that helps users learn how to think through LeetCode problems instead of immediately showing final answers.

## Vision

Don't give me the answer.
Teach me how to discover it.

## MVP

The first milestone focuses on a small working loop:

- Open LeetCoach from the Chrome extension toolbar.
- Show a side panel home experience.
- Detect supported `leetcode.com/problems/*` pages.
- Fetch pattern information from a local backend.
- Show guided thinking steps from a mock AI provider.

## Current Status

The React/TypeScript side panel supports progressive hints, three levels of approach-specific Starter Code, selected-approach thinking steps, and curated full answers. The local SQLite catalog covers 40 problems. The original three problems retain complete mock hints, Starter Code, and Full Solutions in Python, Java, JavaScript, and C++; the expanded catalog uses lightweight offline starter-only shells or configured Policy 9 linked Groq guidance.

After selecting an approach, reveal Recognition Signals inside Solutions, between Summary and Generate Answer, for short clues that connect the problem statement to that approach.

Global navigation shows Coach and Practice when a LeetCode problem is detected, with Progress and About always available. Coach state stays intact across section switches. Practice loads curated Easier, Similar, and Harder problems when opened; each card links to LeetCode. Progress is currently a placeholder.

## Development

Install dependencies:

```bash
npm install
```

Build the extension:

```bash
npm run build
```

The Chrome-loadable extension bundle is generated in `dist/`.

Run the frontend regression tests with `npm test`. For backend tests, install `python -m pip install -r backend/requirements-dev.txt`, then run `python -B -m unittest discover -s backend/tests` from the repository root. On Windows, use `py` if `python` is not on PATH.

## Backend

Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed
```

Run the local FastAPI server:

```bash
uvicorn app.main:app --reload
```

The backend serves health, problem analysis, related problems, hints, starter code, and solutions at `http://localhost:8000`. Stable problem/approach metadata, recognition signals, and related cards use local SQLite through SQLAlchemy. Hints, starter code, and full solutions remain mocked. The seed command can be rerun safely. See [backend/README.md](backend/README.md) for database workflows and endpoint details.
