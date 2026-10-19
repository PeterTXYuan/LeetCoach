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

`app/llm/base.py` defines the provider operation and strict three-hint validation. Each displayed hint is limited to one sentence; the three levels allow at most 10/14/18 words and 75/100/120 characters. An overlong explanation is replaced with a short safe nudge if its first sentence is also too long. `MockLLMProvider` uses only the supplied DB context and makes no network calls. `GroqLLMProvider` sends one structured JSON request with a selected-approach-only teaching instruction, asks for three short questions rather than solution steps, and uses a 20-second timeout without SDK retries. If Groq still returns a command, code formatting, or the selected approach's name/pattern, that hint is replaced with a short question. Missing configuration returns HTTP 503; provider outages return 503; malformed output returns 502. Errors exposed to the extension do not contain prompts, raw provider responses, or the API key. Coach now uses the linked Policy 9 operation described below; older independent operations remain for historical evaluation and rollback.

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
- `POST /api/problems/{slug}/approaches/{approach_id}/starter-code/batch` with `{"language":"java"}`
- Coach Policy 9: `POST /api/problems/{slug}/approaches/{approach_id}/guidance` with `{"language":"java"}`
- Legacy, opt-in: `POST /api/problems/{slug}/approaches/{approach_id}/starter-code` with `{"language":"java","level":2}`

`GET /api/problems/{slug}` and `GET /api/problems/{slug}/related` preserve their previous JSON shapes and unknown-problem 404 responses. Problem Specification rows remain internal for future grounding and are not added to the frontend payloads in this milestone.

Hints, Starter Code, and Full Solution resolve canonical problem/approach IDs and factual context from SQLite, then use the configured mock/Groq provider. `/health` remains a process health check, not a database readiness check.

The analysis response includes `recognitionSignals` on each canonical approach: an optional `quote` string and a `bullets` string array. All 41 seeded approaches have two or three short recognition cues. This metadata is stored directly with its approach and revealed locally in Coach, without an additional endpoint or request.

### Linked Coach guidance policy 9

Coach uses the new `/guidance` POST. One Groq JSON-object request returns `level1`, `level2`, `level3`, and a `solution` object (`code`, `explanation`, `timeComplexity`, `spaceComplexity`) for the same canonical approach and language. The response adds `policyVersion: 9`, `generationId`, `kind: linked`, `warnings` (scoped to a level, solution, or bundle), and `verification` (`PASS`, `FAIL`, or `NOT_RUN`). The provider caps completion at 10,000 tokens, allows 30 seconds, and disables SDK retries. It records prompt/completion/total tokens, latency, output character count, and finish reason for later evaluation; production does not log raw generated code. A length-truncated response is rejected.

Malformed fields, changed LeetCode submission signatures, and syntax errors detected by an available parser/compiler still reject the entire bundle. Heuristic teaching checks—sparse setup, possible answer leaks, unsafe unfinished loops, stage-design changes, or recognizable unfinished full-answer paths—return visible warnings instead of suppressing generated code. Where a representative fixture and supported runtime exist, `evaluation.correctness` executes the full answer only inside the existing WSL bubblewrap sandbox; a failed fixture returns `FAIL` and a prominent warning. Unsupported problems, languages, or unavailable sandbox return `NOT_RUN`, never host execution. A warning means the code needs review before running; passing a few fixtures does not prove general correctness.

The extension stores one Policy 9 bundle per slug/canonical approach/language, reveals the full answer only after its button is clicked, and replaces all four outputs together on regeneration. Old independent caches are not imported into the new bundle, but hints and user preferences remain. Offline mock returns `kind: starterOnlyMock`; it retains all Starter Code coverage and only includes a separately curated full answer where one already exists. The older independent endpoints below remain available for historical evaluation and rollback, but Coach does not call them.

### Historical Starter Code policy 8: one Groq request, three levels

The historical route is `POST /api/problems/{slug}/approaches/{approach_id}/starter-code/batch`, with `{"language":"java"}` (also `python`, `javascript`, `cpp`). The response contains `slug`, `approachId`, `language`, `policyVersion: 8`, `isAiGenerated`, `usedFallback: false`, `notice`, and complete unfinished source strings `level1`, `level2`, `level3`.

Groq starts from the original SQLite submission template. One short system prompt and one compact context send the complete verified description, all available examples and constraints, official complexity instructions, the selected canonical approach's name/summary/thinking steps, and only the requested language template. Provenance, duplicated summaries, other approaches and deterministic scaffolds are omitted. Missing verified descriptions fail explicitly before a provider call; a brief summary is never substituted. The request uses JSON-object mode, temperature 0.2, a 10,000 completion-token cap, a 20-second SDK timeout and zero retries. The model authors setup, control flow, helpers and partial implementation at all three levels.

`app/llm/starter_batch.py` protects signatures and required methods, checks reachable fail-loud unfinished work, catches obvious completed recipes and unsafe loops, checks strictly increasing assistance with a simple executable-structure score, and rejects obvious approach/design contradictions. Normal loops, branches, library operations, indexing and private/nested helpers are allowed. Python is parsed with AST. Available native tools additionally check Java with `javac -proc:none`, JavaScript with `node --check`, and C++ with `g++ -fsyntax-only`. Compiler subprocesses are bounded by time, source size and concurrency; generated programs are never executed by the API. If a tool is unavailable, structural checks remain active; this is not a correctness proof. Offline tests also compile representative C++ files in the existing isolated WSL sandbox on this device.

Every level must validate before any batch is returned. A malformed or rejected batch returns 502 with safe typed diagnostics; provider failures return 503; missing verified context returns 409. Unknown IDs/templates return 404, unsupported languages 400, malformed bodies 422. No internal retry or automatic deterministic fallback occurs in the new path. Mock mode remains explicitly offline (`isAiGenerated: false`) and adapts the existing fixtures into complete, unfinished batches.

The extension persists each batch under problem slug → canonical approach ID → `language:8` in its existing local workspace. The first Generate fetches all three levels; selecting a cached level makes no request. A language requires its own batch. Regenerate always requests a fresh batch and replaces the prior three levels atomically on success. On failure the previous batch remains visible and persisted. Pending work is canceled/ignored on language, problem, approach, hide, collapse or unmount; changing only the level reuses the same pending request. Duplicate generation is blocked. Policy 7 and older Starter Code entries are dropped during hydration, even if stored under a Policy 8 key; Hints, Full Solutions, selected approaches, language/level choices, and other workspace settings remain. Old in-memory results are also rejected. The global workspace storage key is unchanged.

### Temporary policy-6 rollback

The old single-level endpoint and additive-edit implementation remain behind `LEETCOACH_ENABLE_LEGACY_STARTER=true` (default false, see `.env.example`). It returns policy 6 and retains its old deterministic fallback behavior. With the flag disabled it returns 409. Use a previous frontend build or an explicit legacy client when rolling back; enabling this flag does not make the policy-8 UI request old data or call both paths. The old regression suites explicitly enable the rollback flag. Existing historical single-level evaluation uses policy 6; it must not be used to measure the new batch workflow.

### Prepared batch verification (do not run live without separate authorization)

From `backend/`, this dry-run validates the frozen 8-request / 24-level matrix without constructing a provider:

```powershell
py -B -m evaluation.starter_v2 --dry-run --max-calls 8 --output-dir evaluation_runs/starter_v2_dry
```

Prepared future live command, **not executed during implementation**:

```powershell
py -B -m evaluation.starter_v2 --live --max-calls 8 --pace-seconds 12 --capture-raw --output-dir evaluation_runs/starter_v2_live
```

The matrix spans Two Sum, 3Sum, Binary Search, Min Stack, Reverse Linked List, Maximum Depth, Number of Islands and Climbing Stairs across all four languages. Each row generates all three levels in one request. The harness records actual SDK call observations, API results, rejection reasons, per-level syntax/structural checks, human-review markers for progression/leakage/incomplete paths, latency and available token usage. Provider outages/rate limits stop the run; no automatic retries occur. Raw capture is explicit and output remains gitignored. Compare request and level denominators separately with the prior 19 single-level cases. This implementation does not establish better live model reliability.

Related-problem responses include `slug` and three arrays: `easier`, `similar`, and `harder`. Each entry has `slug`, `title`, `difficulty` (`Easy`, `Medium`, or `Hard`), and an optional `reason`. All 20 seeded problems have manually curated SQLite rows from `app/stable_data.py`; an unknown source problem returns 404. A category may be empty when there is no useful recommendation. Group placement is editorial and does not compute prerequisites or learning paths. Related targets can be outside the Coach dataset.

## Tests

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

On Windows, use `py` if `python` is not on PATH. The suite checks the 20-problem catalog and specifications, all 80 language templates, full-answer snippets, all 164 mock Starter Code batches (492 levels), and the retained legacy scaffolds. Batch regressions test interface preservation, unfinished work, progression, normal library operations, recursive helpers, and representative compilation across all four languages. Providers are mocked; no real Groq calls are required. Database tests use disposable migrated SQLite files and preserve exact-sync, stable-ID and unrelated-row guarantees. Coverage includes revisions `0001` through `0003`, ordered facts, API parity, persistence, uniqueness, cascades, rollback, and migration/model consistency. Historical evaluation tests also inspect the existing local seeded DB, which must be migrated to head as described above.

## Live LLM evaluation

The separate `evaluation/` package tests the existing FastAPI generation endpoints with a deterministic 31-case matrix (10 Hints, 9 Starter Code, 12 Full Solutions). It validates every slug, canonical approach, and requested language against the seeded SQLite database before any generation call. Dry-run is the default and sends **zero** Groq requests:

```powershell
cd backend
py -B -m evaluation.run_evaluation --dry-run
py -B -m evaluation.run_evaluation --live --max-calls 31 --pace-seconds 12
```

Live mode requires the configured Groq model and `GROQ_API_KEY` from the environment or ignored `backend/.env`; it forces `LEETCOACH_LLM_PROVIDER=groq` inside that process. Use `--feature hints`, `--feature starter`, or `--feature solution` to select a subset, and `--output-dir PATH` to choose a report directory. A 503 stops the batch; after a cooldown, continue only unrun cases with `--live --resume-json PATH_TO_mvp_evaluation.json`. The total `--max-calls` budget includes calls from earlier invocations. There are no automatic retries. The API sanitizes upstream errors, so a 503 cannot be identified as a rate limit versus another provider outage from this endpoint alone.

Each run writes `mvp_evaluation.json` and `mvp_evaluation_report.md` under ignored `backend/evaluation_runs/<run-id>/` by default. The JSON retains generated outputs, HTTP status, duration, structural checks, separate failure categories, independent fixture outcomes, and human-review flags; the Markdown report includes all returned hint batches and a readiness recommendation. These historical independent endpoints do not expose provider token usage, so their reports mark token usage and cost unavailable; the new Policy 9 `/guidance` response does include usage metadata. To refresh validation and report wording from saved responses without making any Groq call, run `py -B -m evaluation.reassess PATH_TO_mvp_evaluation.json`; optional `--observations-json PATH` attaches preliminary editorial notes.

Generated Python and C++ Full Solutions run only inside a bounded WSL2 bubblewrap namespace with no network and no writable host mounts. A Linux namespace probe determines availability. JavaScript and Java receive syntax or compiler checks where installed, but executable correctness is `NOT_RUN` without an adequate isolated runtime. No generated code is executed inside FastAPI or the evaluation driver process. The independent fixtures cover representative examples and edge cases; passing them does not prove general correctness or teaching quality.

## Future PostgreSQL path

The SQLAlchemy models use portable relational types and keep SQLite connection settings isolated in `database.py`. A later PostgreSQL milestone will add its driver, configure a PostgreSQL URL, run and verify Alembic migrations against that dialect, and transfer existing rows with foreign keys and sequences checked (or seed a fresh dataset). Preserve the public slugs and approach keys throughout. PostgreSQL, authentication, and cloud deployment remain outside this milestone.
