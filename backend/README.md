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

The seed command runs in one transaction and currently syncs 20 problem specifications, 41 approaches, 41 recognition signal sets (84 ordered bullets), and 68 related cards. Stable editorial data lives in `app/stable_data.py`, independently of the three-problem mock guidance fixtures. For each problem present in the curated source, constraints, examples, submission templates, approaches, and related cards exactly match that source: missing children are inserted, existing children are updated, and stale children are deleted. Approach deletion also removes its recognition metadata; obsolete ordered rows are cleaned up. Retained records keep their internal IDs, including related cards moved between categories, and repeated runs create no duplicates. Problem rows outside the current seeded dataset and all their children are left untouched. This is a local editorial bootstrap, not a concurrent import service.

For schema changes, edit `app/models.py`, then run:

```bash
python -m alembic revision --autogenerate -m "describe schema change"
# Review the generated migration before applying it.
python -m alembic upgrade head
python -m alembic check
```

`python -m alembic current` reports the applied revision. `0001` creates stable approach metadata; `0002` adds Problem Specification / LLM-grounding data. A downgrade to `base` drops these tables and their data; upgrade/downgrade round trips are tested only on disposable test databases. Back up local data before destructive schema work.

## Schema

- `problems`: internal integer `id`, unique `slug`, human title, constrained difficulty, and concise algorithm-neutral summary.
- `problem_constraints`: ordered factual constraints, unique by `(problem_id, display_order)`.
- `problem_examples`: ordered input/output examples with optional explanations, unique by `(problem_id, display_order)`.
- `problem_submission_templates`: one LeetCode-style base template per problem/language, constrained to `python`, `java`, `javascript`, and `cpp`. These are factual function/class shells, separate from progressive Starter Code.
- `approaches`: internal integer `id`, problem foreign key, canonical `approach_key`, name, pattern, summary, primary flag, display order, and JSON thinking steps. `(problem_id, approach_key)` is unique; public `approach.id` is always the string key. Seed validation enforces exactly one primary approach per seeded problem.
- `recognition_signal_sets`: one per approach, with an optional quote.
- `recognition_signal_bullets`: signal-set foreign key, text, and positive display order unique within that set.
- `related_problems`: source problem foreign key, external target slug/title/difficulty, optional reason, `easier / similar / harder` category, and display order. A target slug is unique per source problem and need not be a supported Coach problem.

SQLite foreign keys are enabled on every connection, with cascading deletion of owned metadata. Request-scoped SQLAlchemy sessions close after each response. Ordered problem facts and recognition/related entries are loaded in stored display order.

`app.services.problem_repository.find_problem_context(...)` is an internal future-LLM boundary. It loads the problem specification, ordered constraints/examples, one requested-language submission template, and one canonical approach. It does not call an LLM or add a public endpoint.

## Endpoints

- `GET /health`
- `GET /api/problems/{slug}`
- `GET /api/problems/{slug}/related`
- `GET /api/problems/{slug}/hints` (primary approach)
- `GET /api/problems/{slug}/approaches/{approach_id}/hints`
- `POST /api/problems/{slug}/approaches/{approach_id}/solution` with `{"language":"python"}`
- `POST /api/problems/{slug}/approaches/{approach_id}/starter-code` with `{"language":"java","level":2}`

`GET /api/problems/{slug}` and `GET /api/problems/{slug}/related` preserve their previous JSON shapes and unknown-problem 404 responses. Problem Specification rows remain internal for future grounding and are not added to the frontend payloads in this milestone.

Both hint routes and the starter-code/full-solution POST routes remain in their current mock services, including their fixture-based problem/approach validation. Their content is not stored in SQLite. Adding a problem only to the DB does not yet add guidance templates. `/health` remains a process health check, not a database readiness check.

The analysis response includes `recognitionSignals` on each canonical approach: an optional `quote` string and a `bullets` string array. All 41 seeded approaches have two or three short recognition cues. This metadata is stored directly with its approach and revealed locally in Coach, without an additional endpoint or request.

Starter code uses canonical approach IDs and independently curated templates, separate from full answers. Supported languages are `python`, `java`, `javascript`, and `cpp`. Levels are 1 (Minimal), 2 (Guided), and 3 (Strong Scaffold); every level retains TODOs and placeholder exceptions. All seven approaches across the three seeded problems are covered.

Starter responses include `slug`, `approachId`, `language`, `level`, `levelName`, `code`, `notice`, and `isAiGenerated: false`. Unknown problems/approaches return 404, unsupported languages return 400, and malformed or out-of-range levels return 422.

Related-problem responses include `slug` and three arrays: `easier`, `similar`, and `harder`. Each entry has `slug`, `title`, `difficulty` (`Easy`, `Medium`, or `Hard`), and an optional `reason`. All 20 seeded problems have manually curated SQLite rows from `app/stable_data.py`; an unknown source problem returns 404. A category may be empty when there is no useful recommendation. Group placement is editorial and does not compute prerequisites or learning paths. Related targets can be outside the Coach dataset.

## Tests

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

On Windows, use `py` if `python` is not on PATH. The suite checks the 20-problem catalog and specifications, all 80 language templates, full-answer snippets, all 84 starter-code combinations for the original three problems, request validation, and approach-specific progressive structure. Database tests create temporary file-backed SQLite databases through the real Alembic migrations, seed them, override the API session dependency, and dispose of them afterward. They do not require or alter your local database. Coverage includes `0001 ↔ 0002` migration behavior, ordered facts, payload parity, internal context loading, persistence, uniqueness, foreign keys/cascades, rollback, exact-sync seeding, retained IDs, and migration/model consistency.

## Future PostgreSQL path

The SQLAlchemy models use portable relational types and keep SQLite connection settings isolated in `database.py`. A later PostgreSQL milestone will add its driver, configure a PostgreSQL URL, run and verify Alembic migrations against that dialect, and transfer existing rows with foreign keys and sequences checked (or seed a fresh dataset). Preserve the public slugs and approach keys throughout. PostgreSQL, authentication, cloud deployment, and real LLM providers are not part of this milestone.
