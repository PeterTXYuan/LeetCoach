# Editorial Generator MVP implementation

## Architecture

`app/editorial_generator.py` reads one manually reviewed JSON fact record at a time. It accepts the existing importer shape, or a facts-only variant with `spec.taskFacts` and no approaches. Source records must carry reviewed provenance, ordered examples and constraints, and all four submission contracts. It sends only the task facts, constraints, examples, and explicit complexity instructions to a local Codex CLI process; it does not send the full repository, template code, or provenance text. The CLI runs in a temporary read-only directory with `--ignore-user-config`, `--ephemeral`, `--output-schema`, and JSONL usage reporting. API-key environment variables are removed from the child process, and preflight requires `codex login status` to identify ChatGPT auth and `codex debug models` to list the exact model and Medium effort. No Groq or OpenAI API key path exists in this generator.

The structured model output contains only summary, description, and approach editorial fields. Python copies the original title, difficulty, number, source fields, limits, constraints, examples, four submission templates, related cards, and provenance into an importer-compatible draft. Approach complexity explanations are placed in the existing approach summary field; no schema migration was needed. The existing importer validates an in-memory copy of each draft. The saved file is deliberately marked `provenance.reviewed: false`, so `app.catalog_import validate` refuses it until a human checks and approves the editorial content. Checkpoints are one ignored draft file per slug; a rerun skips valid completed drafts and a per-problem `report.md` records status and any CLI usage. A failed problem leaves no new draft and does not stop the rest of the batch.

## Exact local commands

From `backend/`:

```powershell
codex --version
codex login status
py -B -m app.editorial_generator --input-dir catalog/problems --output-dir catalog/drafts --slug move-zeroes
py -B -m app.editorial_generator --input-dir catalog/problems --output-dir catalog/drafts
py -B -m unittest discover -s tests -p test_editorial_generator.py -v
py -B -m unittest discover -s tests
```

Use repeated `--slug` flags or `--limit N` for smaller batches. The generator itself invokes `codex exec --json --ephemeral --ignore-user-config --skip-git-repo-check --sandbox read-only -C <temporary-dir> --model gpt-5.6-sol -c 'model_reasoning_effort="medium"' --output-schema <temporary-schema> --output-last-message <temporary-output> -`, with the short factual prompt on stdin. A reviewed draft must be deliberately approved and moved to an importer input directory before `validate → plan → apply`.

## Smoke and validation

- Installed CLI: `codex-cli 0.167.0-alpha.3.2`; `codex login status` reported **Logged in using ChatGPT**. The local model catalog listed `gpt-5.6-sol` and `medium`. No account secret was opened, copied, or stored.
- One actual Codex CLI request was made for **Move Zeroes**. It returned a structured draft in `catalog/drafts/move-zeroes.json` in about 14 seconds. CLI usage: **15,133 input tokens**, **534 output tokens**. Most input tokens appear to be Codex CLI overhead: the supplied factual prompt was short and the working directory contained no repository files. This is an observation, not a separately measured prompt-token breakdown.
- The generated draft passed the existing importer shape check in memory and preserved the original facts and templates. It remains unreviewed and ignored by Git. A human review found a weak title-only summary (`Move Zeroes`); a subsequent small prompt rule and validation check now reject that quality defect for future generations. The smoke draft itself was retained as the actual output for review and should not be imported as-is. No second model request was made.
- Offline tests use fake CLI responses on **all ten 40→50 pilot records** in a separate temporary draft directory. They verify immutable facts and provenance, importer compatibility, the unreviewed import gate, resume/skip, token accounting, exact CLI options, ChatGPT-only preflight, and failures without overwriting approved JSON. These fake outputs test the pipeline, not editorial quality.
- Focused generator tests: **4/4 passed**. Full backend suite: **150/150 passed**. `app.catalog_import validate --input-dir catalog/drafts` rejected the real draft as expected because it is unreviewed. `git diff --check` passed; newly created files are untracked, so its whitespace check applies only to tracked edits.
- Existing `catalog/problems/` files and the local SQLite database were not modified by this milestone. No next-50 records were generated.

## Limits and review duties

The CLI may consume substantial input tokens even for a small factual prompt; ChatGPT plan limits and model availability can change. The generator does not verify the truth of input facts, legal reuse rights, generated algorithm complexity, or prose originality. Its JSON/importer checks only enforce shape and stable contracts. Each draft needs manual editorial, source-permission, and mathematical review before changing `reviewed` to true. The current smoke draft's title-only summary demonstrates why that gate matters. The generator intentionally makes no automated page requests and performs no import or database update.

## Resume reliability follow-up

Draft resume now compares a SHA-256 fingerprint of canonical reviewed input JSON with a per-problem `.checkpoints/<slug>.json` sidecar. JSON whitespace and key order do not change it. A changed input or an older draft with no fingerprint produces a visible **stale** result and leaves the draft intact; the user must move that draft before regenerating. The sidecar also keeps usage for every generation attempt, including a generated response rejected during editorial validation. `report.md` totals all available usage from the sidecars on every run, so a resumed skip does not reset the cumulative count. The old Markdown report is backed up once and its recoverable token rows are migrated with an unknown fingerprint; those drafts remain stale until reviewed. No model, authentication, importer, manual review gate, or database behavior changed.

The existing ignored Move Zeroes smoke draft was checked without a model call: it was reported as stale, its SHA-256 file hash remained `68d84b2256dcc562e10ead8c4f9e1a940241bf57cae9ba30597c3a2c80a6a9bd`, and its original **15,133 input / 534 output tokens** remained in the cumulative report. Focused generator tests: **7 passed**. Full backend suite: **153 passed**. `git diff --check` passed. No new problem, database write, or real Codex/Groq call occurred in this follow-up.
