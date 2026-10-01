# LeetCoach Backend

Local FastAPI backend using SQLAlchemy 2.x and SQLite for stable editorial data.

## Setup

Create and activate a Python virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed
```

## Run

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Database workflow

Run the setup commands above from `backend/` before starting the API. Alembic owns schema creation; the API does not call `create_all`, run migrations, or seed at startup. The default database is `backend/leetcoach.db`, independent of the current working directory. SQLite database and journal files are ignored by Git.

To choose another local file in PowerShell, set the same environment variable for migrations, seeding, and the server:

```powershell
$env:LEETCOACH_DATABASE_URL = "sqlite:///local-test.db"
py -m alembic upgrade head
py -m app.seed
py -m uvicorn app.main:app --reload
```

Relative SQLite paths resolve from `backend/`; an absolute URL such as `sqlite:///C:/path/to/leetcoach.db` also works. Parent directories must already exist. Restart the server after changing the URL. On Windows, `py` can replace `python` in all commands.

The seed command runs in one transaction and upserts three problems, seven approaches, seven recognition signal sets (16 ordered bullets), and nine related cards. Repeated runs preserve internal IDs and avoid duplicates. They refresh curated content from the retained fixtures, remove obsolete bullet positions, and leave unrelated records alone. They do not delete approaches or related cards removed from the fixtures; remove obsolete records through an explicit later data migration. This is a local editorial bootstrap, not a concurrent import service.

For schema changes, edit `app/models.py`, then run:

```bash
python -m alembic revision --autogenerate -m "describe schema change"
# Review the generated migration before applying it.
python -m alembic upgrade head
python -m alembic check
```

`python -m alembic current` reports the applied revision. The first revision is `0001`. A downgrade to `base` drops these tables and their data; upgrade/downgrade round trips are tested only on disposable test databases. Back up local data before destructive schema work.

## Schema

- `problems`: internal integer `id`, unique `slug`.
- `approaches`: internal integer `id`, problem foreign key, canonical `approach_key`, name, pattern, summary, primary flag, display order, and JSON thinking steps. `(problem_id, approach_key)` is unique; public `approach.id` is always the string key. Seed validation enforces exactly one primary approach per seeded problem.
- `recognition_signal_sets`: one per approach, with an optional quote.
- `recognition_signal_bullets`: signal-set foreign key, text, and positive display order unique within that set.
- `related_problems`: source problem foreign key, external target slug/title/difficulty, optional reason, `easier / similar / harder` category, and display order. A target slug is unique per source problem and need not be a supported Coach problem.

SQLite foreign keys are enabled on every connection, with cascading deletion of owned metadata. Request-scoped SQLAlchemy sessions close after each response. Recognition and related entries are serialized in stored display order.

## Endpoints

- `GET /health`
- `GET /api/problems/{slug}`
- `GET /api/problems/{slug}/related`
- `GET /api/problems/{slug}/hints` (primary approach)
- `GET /api/problems/{slug}/approaches/{approach_id}/hints`
- `POST /api/problems/{slug}/approaches/{approach_id}/solution` with `{"language":"python"}`
- `POST /api/problems/{slug}/approaches/{approach_id}/starter-code` with `{"language":"java","level":2}`

Only `GET /api/problems/{slug}` and `GET /api/problems/{slug}/related` read SQLite in this milestone. They preserve their previous JSON shapes and unknown-problem 404 responses, with no fallback to the dictionaries. Analysis includes approaches, thinking steps, and recognition signals; it excludes hints and internal database IDs.

Both hint routes and the starter-code/full-solution POST routes remain in their current mock services, including their fixture-based problem/approach validation. Their content is not stored in SQLite. Adding a problem only to the DB does not yet add guidance templates. `/health` remains a process health check, not a database readiness check.

The analysis response includes `recognitionSignals` on each canonical approach: an optional `quote` string and a `bullets` string array. The seven seeded approaches have two or three short recognition cues and statement excerpts. This metadata is stored directly with its approach and revealed locally in Coach, without an additional endpoint or request. Quotes come from the corresponding LeetCode problem statement.

Starter code uses canonical approach IDs and independently curated templates, separate from full answers. Supported languages are `python`, `java`, `javascript`, and `cpp`. Levels are 1 (Minimal), 2 (Guided), and 3 (Strong Scaffold); every level retains TODOs and placeholder exceptions. All seven approaches across the three seeded problems are covered.

Starter responses include `slug`, `approachId`, `language`, `level`, `levelName`, `code`, `notice`, and `isAiGenerated: false`. Unknown problems/approaches return 404, unsupported languages return 400, and malformed or out-of-range levels return 422.

Related-problem responses include `slug` and three arrays: `easier`, `similar`, and `harder`. Each entry has `slug`, `title`, `difficulty` (`Easy`, `Medium`, or `Hard`), and an optional `reason`. All three seeded problems have manually curated SQLite rows, seeded from the retained `app/services/related_problem_service.py` fixtures; an unknown source problem returns 404. Group placement is editorial and does not compute prerequisites or learning paths. Related targets can be outside the Coach dataset.

## Tests

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

On Windows, use `py` if `python` is not on PATH. The suite checks full-answer snippets and all 84 starter-code combinations, request validation, and approach-specific progressive structure. Database tests create temporary file-backed SQLite databases through the real Alembic migration, seed them, override the API session dependency, and dispose of them afterward. They do not require or alter your local database. Coverage includes payload parity, DB-only lookups, persistence, canonical ID uniqueness, foreign keys/cascades, rollback, repeat seeding, and migration/model consistency.

## Future PostgreSQL path

The SQLAlchemy models use portable relational types and keep SQLite connection settings isolated in `database.py`. A later PostgreSQL milestone will add its driver, configure a PostgreSQL URL, run and verify Alembic migrations against that dialect, and transfer existing rows with foreign keys and sequences checked (or seed a fresh dataset). Preserve the public slugs and approach keys throughout. PostgreSQL, authentication, cloud deployment, and real LLM providers are not part of this milestone.
