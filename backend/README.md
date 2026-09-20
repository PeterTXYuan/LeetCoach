# LeetCoach Backend

Minimal FastAPI backend for local LeetCoach development.

## Setup

Create and activate a Python virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Endpoints

- `GET /health`
- `GET /api/problems/{slug}`
- `GET /api/problems/{slug}/hints` (primary approach)
- `GET /api/problems/{slug}/approaches/{approach_id}/hints`
- `POST /api/problems/{slug}/approaches/{approach_id}/solution` with `{"language":"python"}`
- `POST /api/problems/{slug}/approaches/{approach_id}/starter-code` with `{"language":"java","level":2}`

Starter code uses canonical approach IDs and independently curated templates, separate from full answers. Supported languages are `python`, `java`, `javascript`, and `cpp`. Levels are 1 (Minimal), 2 (Guided), and 3 (Strong Scaffold); every level retains TODOs and placeholder exceptions. All seven approaches across the three seeded problems are covered.

Starter responses include `slug`, `approachId`, `language`, `level`, `levelName`, `code`, `notice`, and `isAiGenerated: false`. Unknown problems/approaches return 404, unsupported languages return 400, and malformed or out-of-range levels return 422.

## Tests

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

On Windows, use `py` if `python` is not on PATH. The suite checks full-answer snippets and all 84 starter-code combinations, request validation, and approach-specific progressive structure.

The MVP uses an in-memory problem dataset. SQLite, SQLAlchemy, Alembic, authentication, and real LLM providers are intentionally not included yet.
