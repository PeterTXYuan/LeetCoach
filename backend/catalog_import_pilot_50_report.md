# Catalog Importer pilot: 40 curated problems to 50

## Outcome

**Imported: 10 of 10 candidates. Blocked: 0.** Ten reviewed files under `backend/catalog/problems/` add 12 canonical approaches, 19 original examples, 34 factual constraint entries, and 40 four-language submission templates. No importer, Policy 9, prompt, validator, or database schema code changed. No Groq request was made for this pilot.

The permanent 40-problem seed remains in Python and was not changed. The new batch uses the existing `validate → plan → apply` workflow. The first plan listed ten `create` operations and no updates or child deletions. The first apply created ten rows; the second apply reported all ten `unchanged`. A final wording review tightened three descriptions; those three rows were updated in place with no child deletions, and the last apply again reported all ten `unchanged`.

## Source review and provenance

Each linked public problem page was viewed individually to confirm number, title, difficulty, task rules, constraints, and the relevant submission entry points. The JSON stores the canonical page URL, a fixed review timestamp, `manual_review`, and `original_editorial`. Descriptions, examples, explanations, approaches, thinking steps, and recognition signals were written for LeetCoach; the files do not reproduce LeetCode's problem statements or sample explanations. The numeric limits and functional entry points are facts from the pages. No official license to redistribute LeetCode's text is claimed. No automated scraping, GraphQL collection, or third-party problem corpus was used. See [LeetCode terms](https://leetcode.com/terms/) for the source site's restrictions.

| JSON file / official source | Number | Difficulty | Examples | Constraints | Approaches |
| --- | ---: | --- | ---: | ---: | ---: |
| [move-zeroes.json](catalog/problems/move-zeroes.json) · [source](https://leetcode.com/problems/move-zeroes/) | 283 | Easy | 2 | 3 | 1 |
| [merge-intervals.json](catalog/problems/merge-intervals.json) · [source](https://leetcode.com/problems/merge-intervals/) | 56 | Medium | 2 | 3 | 1 |
| [subsets.json](catalog/problems/subsets.json) · [source](https://leetcode.com/problems/subsets/) | 78 | Medium | 2 | 3 | 2 |
| [combination-sum.json](catalog/problems/combination-sum.json) · [source](https://leetcode.com/problems/combination-sum/) | 39 | Medium | 2 | 5 | 1 |
| [binary-tree-level-order-traversal.json](catalog/problems/binary-tree-level-order-traversal.json) · [source](https://leetcode.com/problems/binary-tree-level-order-traversal/) | 102 | Medium | 2 | 2 | 1 |
| [validate-binary-search-tree.json](catalog/problems/validate-binary-search-tree.json) · [source](https://leetcode.com/problems/validate-binary-search-tree/) | 98 | Medium | 2 | 2 | 1 |
| [reorder-list.json](catalog/problems/reorder-list.json) · [source](https://leetcode.com/problems/reorder-list/) | 143 | Medium | 2 | 3 | 1 |
| [implement-trie-prefix-tree.json](catalog/problems/implement-trie-prefix-tree.json) · [source](https://leetcode.com/problems/implement-trie-prefix-tree/) | 208 | Medium | 1 | 3 | 1 |
| [course-schedule.json](catalog/problems/course-schedule.json) · [source](https://leetcode.com/problems/course-schedule/) | 207 | Medium | 2 | 5 | 2 |
| [clone-graph.json](catalog/problems/clone-graph.json) · [source](https://leetcode.com/problems/clone-graph/) | 133 | Medium | 2 | 5 | 1 |

No page supplied an authoritative execution time or memory limit, so those fields remain `null`. Move Zeroes' in-place rule is recorded as mandatory; its minimize-operations follow-up is explicitly optional. Reorder List preserves node values and rewires links. Validate Binary Search Tree uses strict inequalities over entire subtrees. Combination Sum permits unlimited reuse but not ordering duplicates. Course Schedule's dependency direction and cycle condition are explicit. Clone Graph records the connected, undirected, unique-value node contract and empty graph case. The four-language templates preserve LeetCode's `TreeNode`, `ListNode`, `Trie` class methods, and graph `Node`/JavaScript `_Node` interfaces; supplied node definitions are described in comments rather than duplicated as executable declarations. No missing fact or permission was filled in by guesswork.

Related cards point to verified existing catalog problems or another problem in this pilot. The importer treats a missing JSON file as out of scope; it does not delete a problem row.

## Verification

From `backend/`, repeat the workflow with:

```powershell
py -B -m app.catalog_import validate --input-dir catalog/problems
py -B -m app.catalog_import plan --input-dir catalog/problems
py -B -m app.catalog_import apply --input-dir catalog/problems
```

Run Alembic migrations and the original 40-problem seed first on a fresh database; `plan` and `apply` require those rows. For this already-imported batch, `plan` now reports ten `unchanged` entries.

- `py -B -m app.catalog_import validate --input-dir catalog/problems`: **10 reviewed files valid**.
- `py -B -m app.catalog_import plan --input-dir catalog/problems`: **10 create, 0 update, 0 delete** before apply.
- `py -B -m app.catalog_import apply --input-dir catalog/problems`: **10 create** on first run, **10 unchanged** on second.
- `py -B -m unittest discover -s tests -p test_catalog_pilot_50.py -v`: **1 passed**. A fresh migrated, seeded temporary database reached exactly **50 Problem rows and 200 templates**. The test checked all four context languages per new problem, exactly one primary approach, stable IDs after re-import, legacy row IDs and content unchanged, and `PRAGMA foreign_key_check = []`. It also exercised DB-backed analysis, related cards, hints, and a mocked Policy 9 guidance request with the new context. The Policy 9 provider and bundle validation were mocked for that integration check; this does not assert quality of live generated code.
- `py -B -m unittest discover -s tests`: **146 passed**. Evaluation harness tests use fakes and temporary files; no real Groq call was initiated for this pilot.
- `git diff --check`: **passed**. New JSON and test/report files are untracked, so this command does not inspect their contents until staged; importer validation and the test read all ten JSON files.

The developer's ignored local `backend/leetcoach.db` already contained two synthetic importer rows (`synthetic-array-check` and `synthetic-tree-check`) before this batch. It therefore has **52 physical Problem rows** after import: 40 original + 10 pilot + 2 pre-existing synthetic. Foreign keys are clean. The importer did not remove those unrelated rows. A fresh database contains exactly the intended 50 real catalog rows.

## Limits and next checks

Mocked provider integration confirms context and route wiring, not Groq teaching quality or full-answer correctness. The existing Policy 9 live evaluation can be run separately after review. Public page content and snippet shells can change later; the stored verification timestamp is deliberately fixed and future edits should repeat the manual source review. The two old synthetic rows in the ignored developer database should be handled separately if a physically exact 50-row local database is desired; this pilot intentionally made no deletion outside the reviewed batch.
