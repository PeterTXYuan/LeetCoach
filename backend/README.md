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

## Hint provider

Both hint GET routes now load the problem facts and canonical selected approach from SQLite, then ask one `LLMProvider` call for all three progressive hints. The primary route uses the DB primary flag; the approach route uses the exact public `approach.id` key. The hint context contains title, difficulty, summary, ordered constraints/examples, approach name/pattern/summary, thinking steps, and recognition signals. It does not require a language or submission template, and it sends no LeetCode URL. The response remains `{slug, approachId, hints}`; the frontend reveals the three returned hints one at a time.

Copy `.env.example` to `backend/.env` for local configuration. Environment variables already set in the shell take precedence over this file. `backend/.env` is ignored by Git.

| Variable | Purpose |
| --- | --- |
| `LEETCOACH_LLM_PROVIDER` | `mock` (default) for offline deterministic hints, or `groq` for live hints. |
| `LEETCOACH_LLM_MODEL` | Groq model ID, required when `groq` is selected. |
| `GROQ_API_KEY` | Groq API key, required when `groq` is selected. Leave blank for mock mode. |

`app/llm/base.py` defines the provider operation and strict three-hint validation. Each displayed hint is limited to one sentence; the three levels allow at most 10/14/18 words and 75/100/120 characters. An overlong explanation is replaced with a short safe nudge if its first sentence is also too long. `MockLLMProvider` uses only the supplied DB context and makes no network calls. `GroqLLMProvider` sends one structured JSON request with a selected-approach-only teaching instruction, asks for three short questions rather than solution steps, and uses a 20-second timeout without SDK retries. If Groq still returns a command, code formatting, or the selected approach's name/pattern, that hint is replaced with a short question. Missing configuration returns HTTP 503; provider outages return 503; malformed output returns 502. Errors exposed to the extension do not contain prompts, raw provider responses, or the API key. Starter Code and Full Solution still use the original three-problem mock services.

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

Both hint routes and the starter-code route resolve canonical problem/approach IDs from SQLite and use the configured provider. The full-solution POST route still uses its existing mock fixtures. `/health` remains a process health check, not a database readiness check.

The analysis response includes `recognitionSignals` on each canonical approach: an optional `quote` string and a `bullets` string array. All 41 seeded approaches have two or three short recognition cues. This metadata is stored directly with its approach and revealed locally in Coach, without an additional endpoint or request.

Starter code uses canonical approach IDs and SQLite submission shells, separate from full answers. The offline provider builds deterministic unfinished scaffolds; Groq can generate them when configured. Supported languages are `python`, `java`, `javascript`, and `cpp`. Levels are 1 (Kickstart: useful approach-specific setup), 2 (Guided: initial flow), and 3 (Strong Scaffold: major structure with central decisions unfinished). All 41 approaches across the 20 seeded problems are covered. Each level retains TODOs and fail-loud unfinished behavior.

Starter responses include `slug`, `approachId`, `language`, `level`, `levelName`, `code`, `notice`, `policyVersion: 4`, and `isAiGenerated` according to the provider; fallback responses also include `usedFallback: true`. Unknown problems/approaches return 404, unsupported languages return 400, and malformed or out-of-range levels return 422.

Related-problem responses include `slug` and three arrays: `easier`, `similar`, and `harder`. Each entry has `slug`, `title`, `difficulty` (`Easy`, `Medium`, or `Hard`), and an optional `reason`. All 20 seeded problems have manually curated SQLite rows from `app/stable_data.py`; an unknown source problem returns 404. A category may be empty when there is no useful recommendation. Group placement is editorial and does not compute prerequisites or learning paths. Related targets can be outside the Coach dataset.

## Tests

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

On Windows, use `py` if `python` is not on PATH. The suite checks the 20-problem catalog and specifications, all 80 language templates, full-answer snippets, all 84 starter-code combinations for the original three problems, request validation, and approach-specific progressive structure. Database tests create temporary file-backed SQLite databases through the real Alembic migrations, seed them, override the API session dependency and hint provider, and dispose of them afterward. They do not require or alter your local database. Hint tests use only mock/fake providers and never call Groq or require `GROQ_API_KEY`. Coverage includes `0001 ↔ 0002` migration behavior, ordered facts, payload parity, internal context loading, persistence, uniqueness, foreign keys/cascades, rollback, exact-sync seeding, retained IDs, and migration/model consistency.

## Live LLM evaluation

The separate `evaluation/` package tests the existing FastAPI generation endpoints with a deterministic 31-case matrix (10 Hints, 9 Starter Code, 12 Full Solutions). It validates every slug, canonical approach, and requested language against the seeded SQLite database before any generation call. Dry-run is the default and sends **zero** Groq requests:

```powershell
cd backend
py -B -m evaluation.run_evaluation --dry-run
py -B -m evaluation.run_evaluation --live --max-calls 31 --pace-seconds 12
```

Live mode requires the configured Groq model and `GROQ_API_KEY` from the environment or ignored `backend/.env`; it forces `LEETCOACH_LLM_PROVIDER=groq` inside that process. Use `--feature hints`, `--feature starter`, or `--feature solution` to select a subset, and `--output-dir PATH` to choose a report directory. A 503 stops the batch; after a cooldown, continue only unrun cases with `--live --resume-json PATH_TO_mvp_evaluation.json`. The total `--max-calls` budget includes calls from earlier invocations. There are no automatic retries. The API sanitizes upstream errors, so a 503 cannot be identified as a rate limit versus another provider outage from this endpoint alone.

Each run writes `mvp_evaluation.json` and `mvp_evaluation_report.md` under ignored `backend/evaluation_runs/<run-id>/` by default. The JSON retains generated outputs, HTTP status, duration, structural checks, separate failure categories, independent fixture outcomes, and human-review flags; the Markdown report includes all returned hint batches and a readiness recommendation. Current endpoints do not expose provider token usage, so the reports mark token usage and cost unavailable. To refresh validation and report wording from saved responses without making any Groq call, run `py -B -m evaluation.reassess PATH_TO_mvp_evaluation.json`; optional `--observations-json PATH` attaches preliminary editorial notes.

Generated Python and C++ Full Solutions run only inside a bounded WSL2 bubblewrap namespace with no network and no writable host mounts. A Linux namespace probe determines availability. JavaScript and Java receive syntax or compiler checks where installed, but executable correctness is `NOT_RUN` without an adequate isolated runtime. No generated code is executed inside FastAPI or the evaluation driver process. The independent fixtures cover representative examples and edge cases; passing them does not prove general correctness or teaching quality.

## Future PostgreSQL path

The SQLAlchemy models use portable relational types and keep SQLite connection settings isolated in `database.py`. A later PostgreSQL milestone will add its driver, configure a PostgreSQL URL, run and verify Alembic migrations against that dialect, and transfer existing rows with foreign keys and sequences checked (or seed a fresh dataset). Preserve the public slugs and approach keys throughout. PostgreSQL, authentication, and cloud deployment remain outside this milestone.
