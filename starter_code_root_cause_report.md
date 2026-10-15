# LeetCoach Starter Code root-cause investigation — Phase 1

## Executive summary

The original MVP run had **7 fallbacks in 9 Starter Code requests**, but saved only the student-visible fallback. Its seven historical rejection causes therefore remain **unknown**. This investigation added typed, safe diagnostic metadata and repeated exactly those seven combinations with the same configured Groq model. All seven new requests returned HTTP 200 and fell back: **five** failed the required unfinished-placeholder rule and **two** failed the commented-out-algorithm rule. Offline replay of the captured raw model text reproduced all seven reason codes. These are **new reproductions**, not reconstructions of the original responses.

No provider timeout, rate limit, transport error, JSON parse error, or missing code field occurred in this seven-call reproduction. Every newly rejected output had a substantive teaching-contract defect; none is a demonstrated validator false positive. The fallback that students received passed the existing structural validator and available language syntax check in all seven cases, but that does not establish teaching quality. At least one fallback still has a clarity issue.

## Request path and lost evidence

`POST /api/problems/{slug}/approaches/{approach_id}/starter-code` resolves the canonical approach and language template from SQLite, calls `GroqLLMProvider.generate_starter_code()`, then validates the returned code again at the route. Before this change, the provider wrapped all SDK exceptions as `ProviderUnavailableError`, combined malformed JSON and missing fields into `ProviderOutputError`, and most validator branches used the same exception class. The route caught either class, logged only its type, and substituted `MockLLMProvider` code. The evaluator saw the fallback and incorrectly labeled **every** fallback `structural_output`, even if a provider outage might have caused it. The second route validation is redundant for Groq but remains unchanged; a future provider could fail there.

The new diagnostic subclasses preserve those same parent exception categories and rejection points. Logs record slug, canonical approach, language, level, failure stage, reason code, and fallback status. They contain no raw model text, key, or header. A request-local observer gives the evaluation harness the same metadata without changing the public response. Raw model text is saved only with explicit `--live --capture-raw`, under the gitignored `backend/evaluation_runs/` directory. The API schema, status behavior, fallback, prompt, policy version, caching, and validator decisions are unchanged.

## Reproduction results

The prior [MVP run](backend/evaluation_runs/20261015T064805Z-e1ae2d52/mvp_evaluation.json) recorded HTTP 200 plus fallback for each row, but **no rejected Groq text or typed reason**. The [new run](backend/evaluation_runs/20261015T072639Z-0ccdd706/mvp_evaluation.json) used `openai/gpt-oss-120b`, JSON-object response format, temperature 0.2, 20-second timeout, zero SDK retries, a seven-call hard cap, and 12-second pacing. The raw artifact path for each row is in the machine-readable report; those files are local and ignored by Git.

| Reproduction | HTTP / duration | Earliest rejection | Evidence in newly captured Groq code | Assessment |
| --- | ---: | --- | --- | --- |
| Two Sum / hash-map / Python L1 | 200 / 2494 ms | `MISSING_UNFINISHED_PLACEHOLDER` | Ends with ordinary `ValueError`, not `NotImplementedError`; also starts the main pair-search loop at Kickstart. | Genuine defect; a later L1 control-flow rule would also reject it. |
| Two Sum / hash-map / Python L2 | 200 / 2486 ms | `MISSING_UNFINISHED_PLACEHOLDER` | Ends with ordinary `ValueError`; already performs complement lookup and map insertion around a TODO for the return. | Genuine defect and likely too much core logic. |
| 3Sum / two pointers / Java L1 | 200 / 2040 ms | `MISSING_UNFINISHED_PLACEHOLDER` | TODOs are followed by `return result` with no `UnsupportedOperationException`. | Genuine unfinished-path defect. |
| 3Sum / two pointers / Java L2 | 200 / 3411 ms | `MISSING_UNFINISHED_PLACEHOLDER` | Unfinished inner loop breaks, then returns an empty result; no required throw. | Genuine unfinished-path defect; level also contains more structure than its prompt suggests. |
| 3Sum / two pointers / Java L3 | 200 / 2477 ms | `COMMENTED_OUT_ALGORITHM` | Comments supply executable duplicate-skip and result-add statements. | Genuine answer leakage despite throws on unfinished branches. |
| Min Stack / paired minimums / JavaScript L1 | 200 / 2437 ms | `MISSING_UNFINISHED_PLACEHOLDER` | Four operation methods contain TODO comments but no `throw new Error`; calls silently return `undefined`. | Genuine unfinished-path defect. |
| Min Stack / paired minimums / JavaScript L3 | 200 / 3737 ms | `COMMENTED_OUT_ALGORITHM` | Comments supply ready-to-copy minimum calculation, push, pop, top, and getMin statements. | Genuine answer leakage. |

The reason totals are **5 `MISSING_UNFINISHED_PLACEHOLDER` and 2 `COMMENTED_OUT_ALGORITHM`**. Failure stages: **7 validation, 0 provider, 0 parsing, 0 response-shape**. All seven captured files replay through the same parser and validator to the same reason without network calls. Raw capture and replay cannot prove these were the original seven causes because the model is nondeterministic and the first run did not preserve rejected output.

## Three separate quality measures

1. **Groq acceptance:** 0/7 in the targeted reproduction; 2/9 in the historical complete Starter Code matrix. HTTP 200 plus `usedFallback: true` is not accepted AI generation.
2. **Fallback correctness and quality:** all 7 reproduced fallbacks passed the existing validator and available syntax checks (Python AST, Java compilation, or JavaScript syntax). This is a structural/syntax result only. The Two Sum Python L2 fallback asks whether “that complement” was previously seen before introducing a `complement` variable. Its L1 introduces the idea, but a student who starts at L2 could be confused. The deterministic Min Stack fallback itself uses parallel `values`/`minimums` arrays consistently at L1–L3; the historical *mixed* sequence was inconsistent because Groq L2 used a pair stack between fallback L1 and L3. Independent generation can create that cross-level mismatch.
3. **Student-visible quality:** 7/7 served code snippets passed structural/syntax checks, while 7/7 still require human pedagogical review. No automated result here establishes that the scaffold is clear, appropriately progressive, or useful to a beginner.

The harness now reports these with explicit executed-request denominators. `structural_output` is assigned to a fallback only with evidence of response/parsing/validation failure; a typed provider failure is `api_provider`, and an unobservable cause is `evaluation_limitation`. This corrects the previous evaluator **classification**, without changing production generation or retroactively claiming the old failures had these new causes.

## Validator false-positive review

No captured reproduction is a likely false positive. The exact-signature and class checks defend the LeetCode entry point; the TODO and language-specific fail-loud markers prevent a scaffold from silently acting complete; Python AST and brace checks catch malformed shells; Level 1 setup/control-flow and Level 3 control-flow checks enforce the intended progression; and the commented-code, unreachable-placeholder, complete-sequence, and placeholder-condition checks target answer leakage or unusable code.

These are still heuristics. Exact line matching can reject semantically equivalent formatting, such as a method declaration with a trailing inline comment. The Level 1 `if`/`for`/`while` scan can reject a harmless setup guard, not only main algorithm flow. The Java/JavaScript/C++ brace check is not a compiler, and the regex-based solution-leak checks can miss paraphrased instructions. None of those potential false positives explains the seven newly captured rejections. A future correction should be backed by a concrete acceptable scaffold and a regression test before relaxing any rule.

The **earliest** failure is reported. For example, Two Sum L1 first fails the missing-marker check, so the diagnostic does not claim that the later Level 1 control-flow check ran. The raw output supports a separate human observation that its loop would also violate Kickstart.

## Previously accepted outputs with quality issues

- **Two Sum / Python L3** passed because it has the exact signature, TODOs, `NotImplementedError`, valid Python syntax, and no active complete lookup/update/return sequence. Its TODO comments nevertheless tell the student to check `complement` in `seen`, return both indices, then store the current value. The commented-code matcher looks for executable-looking statements, not natural-language answer recipes. A deterministic detector could flag the specific recipe pattern, but semantic leakage across problems needs human or rubric-based judgment.
- **Min Stack / JavaScript L2** passed for the same structural reasons. It commented out two `const` assignments computing the prior and new minimum; the current commented-code regex does not count declarations beginning `const`. It also used one stack of `[value, minimum]` pairs, whereas the fallback L1/L3 used separate arrays. Either design can be valid for the selected approach, but independent generation does not guarantee progression across levels. The evaluator's separate teaching-quality checks already flagged the commented assignments.

## Phase 2 recommendations (not implemented)

| Priority | File | Evidence and proposed change | Regression risk and required test |
| --- | --- | --- | --- |
| 1 | `backend/app/llm/groq_provider.py` | Five new outputs omitted the specified language-specific unfinished marker. Clarify the existing prompt with a short valid example of the required fail-loud placeholder at each language/level; keep the core logic incomplete. | More rigid formatting may reduce variety or cause decorative throws. Live samples and offline validator tests should verify reachable placeholders and meaningful TODOs. |
| 2 | `backend/app/llm/base.py` | The two commented-code failures show a real leakage pattern; the accepted Min Stack L2 shows that `const` declarations escape the matcher. Consider a narrowly expanded commented-statement detector and review whether normal explanatory comments are misclassified. | Broader regexes can reject good teaching comments. Add positive and negative language-specific fixtures before changing acceptance. |
| 3 | `backend/app/llm/groq_provider.py` and `backend/app/llm/base.py` | The accepted Two Sum L3 comments give a complete algorithm recipe. Tighten the prompt against action-by-action TODO recipes, and consider a targeted detector for direct lookup/return/store instructions rather than a generic ban on useful TODOs. | Overblocking can make L3 vague. Test known leaky output and valid short TODOs across approaches. Human review remains necessary. |
| 4 | `backend/app/llm/mock_provider.py` | Two Sum L2 references an unintroduced complement. Introduce that intermediate value or reword the TODO, then review that each level extends the prior one. | Adding calculations may expose too much at L2. Test progressive depth and beginner clarity, plus all 492 deterministic fixtures. |
| 5 | `backend/evaluation/validators.py` and the generation flow | The historical mixed Min Stack levels use incompatible storage designs because levels are independent and can mix live/fallback outputs. Evaluate level-trio consistency, or ground later levels in an explicit stable design choice before deploying. | Cross-level coupling can affect cache keys and request behavior. Test live/fallback mixtures, independent level requests, and per-approach design fidelity. |

## Recommended next step and reproducibility

The evidence is sufficient to begin targeted Phase 2 changes for missing fail-loud markers, commented implementation leakage, and the known fallback wording issue. It is not sufficient to infer the original seven failure reasons or certify the broader catalog's teaching quality. Keep a bounded post-fix live sample and human review before revising readiness claims.

To rerun this exact seven-case matrix from `backend/` (only with an explicitly configured Groq key):

```powershell
py -B -m evaluation.run_evaluation --live --feature starter --previous-starter-fallbacks --max-calls 7 --pace-seconds 12 --capture-raw
```

Without `--live`, the harness is a dry run. Without `--capture-raw`, no raw model text is retained. For a captured file, `py -B -m evaluation.replay_starter RAW_FILE --slug two-sum --approach hash-map --language python --level 1` repeats parsing and validation offline. The structured companion is [starter_code_root_cause_report.json](starter_code_root_cause_report.json). The full local [reproduction JSON](backend/evaluation_runs/20261015T072639Z-0ccdd706/mvp_evaluation.json) includes timings and validation records; raw files remain ignored by Git.
