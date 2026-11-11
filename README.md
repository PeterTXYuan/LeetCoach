# LeetCoach

LeetCoach is a Chrome side-panel extension for practicing *how* to solve LeetCode problems. It starts with approach-specific hints and progressively more complete starter code; a full answer is available when you choose to reveal it. The extension is backed by a local FastAPI service and a curated SQLite catalog of 60 problems.

This is a local development project, not a hosted extension or a LeetCode integration. Open a supported `leetcode.com/problems/...` page with the backend running, then open LeetCoach from the Chrome toolbar.

## What it does

- **Coach:** Select a canonical approach, reveal short hints one at a time, inspect recognition signals and thinking steps, and request three levels of starter code. A full answer stays hidden until requested.
- **Linked AI guidance:** In Groq mode, one Policy 9 request produces Level 1, Level 2, Level 3, and a full answer for the same problem, approach, and language. Regenerating either section refreshes the whole bundle. Python, Java, JavaScript, and C++ are supported.
- **Practice:** Browse manually curated easier, similar, and harder problems and open them on LeetCode.
- **Persistent workspace:** The extension saves generated responses, selected approaches, and language/level preferences in `chrome.storage.local`. Disclosure resets on panel reopening or approach changes; switching browser tabs within an open panel preserves it.
- **Light and dark themes:** Available from the side-panel header. Progress is currently a placeholder, and About explains the learning flow.

The catalog stores problem specifications, submission templates, approaches, recognition signals, and related problems. Hints and generated code are produced by either the configured Groq provider or offline mock fixtures. Mock mode has complete hand-written guidance for the original three problems; for the rest of the catalog it is useful for development but does not provide a complete linked answer for every combination.

## Architecture

| Part | Responsibility |
| --- | --- |
| Chrome Manifest V3 side panel | Detect the active LeetCode problem, render Coach/Practice, and persist per-problem workspace state. |
| React + TypeScript + Vite | UI, request hooks, local cache, and disclosure controls. |
| FastAPI | Resolve canonical problem/approach IDs and serve analysis, hints, related problems, and guidance. |
| SQLAlchemy + SQLite + Alembic | Store the 60-problem curated catalog; migrations define the schema, the seed loads the original 40, and the reviewed JSON importer loads the next 20. |
| Groq or mock provider | Generate guidance from one selected approach and the requested language's submission template; mock mode works offline. |

The side panel calls `http://localhost:8000` directly. It does not currently connect to a hosted backend. The browser extension requests access to LeetCode problem pages, local backend requests, tabs, side-panel controls, and local storage; see [the manifest](public/manifest.json) for the exact permissions.

## Run locally

Prerequisites: a recent Chrome version with side-panel support, Node.js/npm, and Python. Run the backend and extension in separate terminals.

1. Install and initialize the backend from `backend/`:

   ```bash
   cd backend
   python -m pip install -r requirements.txt
   python -m alembic upgrade head
   python -m app.seed
   python -m app.catalog_import apply --input-dir catalog/problems
   python -m uvicorn app.main:app --reload
   ```

   The server listens at `http://localhost:8000`; `http://localhost:8000/health` should return `{"status":"ok"}`. The default SQLite file is `backend/leetcoach.db`. Migrate and seed before starting the API. On Windows, `py` can replace `python`.

2. In another terminal, install and build the extension from the repository root:

   ```bash
   npm install
   npm run build
   ```

3. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select this repository's `dist/` directory. Open a supported LeetCode problem page and click the LeetCoach toolbar icon to open the side panel. After frontend changes, rebuild and reload the unpacked extension.

The default provider is `mock`, so no API key is required to explore the UI. For live generation, copy `backend/.env.example` to `backend/.env`, set `LEETCOACH_LLM_PROVIDER=groq`, `LEETCOACH_LLM_MODEL`, and `GROQ_API_KEY`, then restart the backend. Shell environment variables take precedence. Keep `backend/.env` private; it is Git-ignored. Groq mode sends the selected problem context and language template to the provider and may be subject to that provider's limits. See [backend setup and API details](backend/README.md).

## Guidance and its limits

The three starter levels are intentionally unfinished. Level 1 exposes basic structure, Level 2 adds useful setup, and Level 3 provides more of the control flow while leaving meaningful work for the learner. The full answer is a separate reveal of the same generated bundle in Groq mode. Generation can return quality warnings. Where an isolated sandbox and a representative fixture are available, the backend checks the full answer and reports `PASS` or `FAIL`; otherwise it reports `NOT_RUN`. These checks are useful signals, not a proof that generated code handles every input. Review and test an answer before submitting it.

Generated guidance is cached locally across restarts. Changing an approach, reopening the panel, or navigating to a problem collapses revealed content without discarding its cached response. Regenerate explicitly to request a new bundle. The data catalog and local workspaces stay on your device, except for problem context sent to Groq when that provider is enabled.

## Development and verification

From the repository root:

```bash
npm test
npm run build
python -m pip install -r backend/requirements-dev.txt
python -B -m unittest discover -s backend/tests
```

The frontend suite uses Vitest. Backend tests cover catalog seeding, API contracts, mock providers, validation, and offline guidance behavior; they do not require live Groq calls. Database tests use temporary migrated SQLite files. The catalog is maintained in [`stable_data.py`](backend/app/stable_data.py), [`verified_problem_specs.py`](backend/app/verified_problem_specs.py), and the seed workflow in [`seed.py`](backend/app/seed.py). See [the roadmap](roadmap.md) for milestones and open work.

## Current scope

The app has 40 curated problems and 64 canonical approaches, with one primary approach per problem. Related-problem links are editorial and may lead outside the supported Coach catalog. There is no account system, hosted sync, or progress tracking yet. The project is not affiliated with LeetCode.
