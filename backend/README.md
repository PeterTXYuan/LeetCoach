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

The MVP uses an in-memory problem dataset. SQLite, SQLAlchemy, Alembic, authentication, and real LLM providers are intentionally not included yet.
