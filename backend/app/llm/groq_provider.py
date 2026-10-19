"""Structured Groq requests for progressive hints and starter code."""
import json
import re
import time

from app.llm.base import (
    ProviderOutputError, ProviderUnavailableError, StarterOutputDiagnostic,
    StarterProviderDiagnostic, SHORT_FALLBACK_HINTS,
    validate_hints, validate_starter_code,
)
from app.llm.starter_diagnostics import observe, provider_reason, starter_raw_capture
from app.llm.starter_contract import assemble_starter_plan, starter_slots, trusted_starter
from app.llm.solution_validation import validate_solution
from app.llm.starter_batch import model_context, validate_starter_batch


SYSTEM_PROMPT = (
    "You are LeetCoach. Write three tiny, progressively stronger nudges for a beginner, "
    "using only the database facts supplied. The selected canonical approach is fixed: "
    "teach only that approach, but do not copy its name, pattern, summary, recognition "
    "signals, or thinking steps verbatim. Do not switch approaches or invent facts. "
    "Return a JSON object with exactly one key, hints, containing exactly three strings. "
    "Each hint must be one short question, at most 18 words and 120 characters. "
    "Hint 1: at most 10 words and 75 characters. Ask only what makes an answer valid; "
    "do not mention a calculation, strategy, or data structure. "
    "Hint 2: at most 14 words and 100 characters. Ask about a useful observation, "
    "without revealing the key transformation or a data structure. "
    "Hint 3: at most 18 words and 120 characters. Suggest one small next thought, "
    "without telling the learner exactly what to calculate, store, or return. "
    "Never state the full algorithm, a solution recipe, code, pseudocode, formulas, "
    "complexity, or a data-structure name. Avoid 'first/then' instructions, lists, and "
    "long explanations. Do not use external URLs or a memorized problem statement."
)

LEGACY_STARTER_SYSTEM_PROMPT = (
    "Add one small, useful step to LeetCoach's trusted unfinished Starter Code. "
    "Use only the selected canonical approach and the supplied scaffold; follow starterDesign if present. "
    "Choose an editableSlots ID. Return one JSON object with slot and either code, guidance, or both. "
    "Example: {\"slot\":\"todo-1\",\"code\":\"gap = target - current\","
    "\"guidance\":\"What earlier value might help here?\"}. "
    "Code is one new local declaration or intermediate assignment, on one source line. "
    "Guidance is one short conceptual TODO question without comment markers. "
    "For Kickstart add setup; for Guided add a useful intermediate; for Strong Scaffold "
    "build on the existing structure. Do not duplicate existing code, change signatures or "
    "control flow, switch approaches, or give a complete algorithm."
)

STARTER_SYSTEM_PROMPT = """You are LeetCoach, an AI coding tutor.
Using the problem description, examples, constraints, selected algorithm approach, and LeetCode code template, generate three progressively more helpful Starter Code versions in the requested language.
Level 1 — Kickstart: Add a small amount of useful setup. Leave most of the algorithm for the student.
Level 2 — Guided: Add initial algorithm structure, such as variables, loops, or helper setup. Leave important decisions unfinished.
Level 3 — Strong Scaffold: Provide most of the algorithm structure, but leave the central logic or operations for the student to complete.
Rules:
1. Follow only the selected approach and keep a compatible design across levels.
2. Preserve every required class, constructor, method signature, and return type from the template. Additional helpers must be private or named with a leading underscore.
3. Use syntactically valid code with meaningful TODO comments.
4. Leave genuine algorithm work unfinished at every level. Never provide a complete solution.
5. Make each level progressively more helpful.
6. Incomplete execution paths must fail clearly with an exception, not loop forever or silently return misleading results. Placeholders must be reachable.
7. Never use pass or an empty/default result as unfinished logic; do not label already-complete code as TODO.
8. Keep TODO paths reachable. Avoid fake conditions and loops that cannot advance or stop.
9. Explain intent in comments, but never hide executable answer steps or a complete algorithm there.
10. Each level must retain and extend the useful structure of the previous level.
Return only JSON containing level1, level2, and level3, each holding complete source code, without Markdown fences."""

LINKED_GUIDANCE_PROMPT = """You are LeetCoach. Return exactly one JSON object with level1, level2,
level3 (complete starter-code strings), and solution (an object with code, explanation,
timeComplexity, spaceComplexity strings). Use the supplied problem facts, selected approach,
and exact LeetCode submission signatures. Produce ONE implementation in four successive stages:
L1 offers useful setup; L2 adds variables and initial flow; L3 adds most control flow but
leaves meaningful algorithm work; solution completes L3. Preserve working code, variable
names, data structures, and helpers as each stage adds code. Do not replace the algorithm
between stages. In L2/L3, add short comments explaining the purpose of provided loops,
state, and branches so a student who opens L3 directly can follow it. Comments must not
give executable answers for the missing steps or hide a complete solution.
Every starter has a meaningful TODO and a reachable explicit exception on unfinished paths.
No silent pass, empty/default placeholder return, fake condition, unreachable TODO,
non-progressing loop, or complete algorithm in comments. The full solution has no TODO,
placeholder, unfinished branch, or exception used as a placeholder. Give correct code and
brief complexity explanations for the selected approach. Return JSON only, no code fences."""


def _starter_design(context: dict) -> str | None:
    if context["problem"]["slug"] != "min-stack":
        return None
    approach_id = context["approach"]["id"]
    if approach_id == "paired-minimums":
        return ("Use one stack of (value, minimum-so-far) pairs in every level. "
                "At Kickstart, declare the pair stack; at Guided, build on that same stack; "
                "at Strong Scaffold, add structure while leaving minimum calculation and "
                "stack operations for the learner. Do not switch to parallel arrays.")
    if approach_id == "scan-for-minimum":
        return "Use one ordinary value stack in every level; getMin scans its stored values."
    return None

SOLUTION_SYSTEM_PROMPT = (
    "You are LeetCoach's final full-answer step. Return one JSON object with string fields "
    "code, explanation, timeComplexity, and spaceComplexity. Use only the supplied problem "
    "facts, constraints, examples, and the one selected canonical approach. Implement that "
    "approach completely in the requested language (python, java, javascript, or cpp); do not "
    "substitute a different technique. Treat submissionTemplate as authoritative: preserve "
    "the exact class, every required method signature, parameter type/order, and return type, "
    "including all operations of design problems. Handle important edge cases and use valid "
    "language syntax and data structures. Code should be directly submittable to LeetCode, "
    "with no Markdown fences, TODOs, placeholders, pseudocode, or unimplemented branches. "
    "Explain the central idea, why it works, important state, progression, and edge cases "
    "briefly and clearly. Give time and auxiliary-space complexity for the actual code; "
    "account for sorting, recursion depth, and data structures. Return no other prose."
)


def _remove_outer_code_fence(code: str) -> str:
    """Accept a single accidental Markdown wrapper without changing code inside it."""
    match = re.fullmatch(r"\s*```(?:python|java|javascript|js|cpp|c\+\+)?\s*\n(.*?)\n```\s*",
                         code, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else code


class GroqLLMProvider:
    is_ai_generated = True

    def __init__(self, api_key: str, model: str, client=None):
        self.model = model
        if client is None:
            from groq import Groq
            client = Groq(api_key=api_key, max_retries=0, timeout=20.0)
        self.client = client

    def generate_hints(self, context: dict) -> list[str]:
        # Only the selected approach and canonical problem facts reach Groq.
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
        except Exception as exc:
            raise ProviderUnavailableError("Hint provider unavailable") from exc

        try:
            content = response.choices[0].message.content
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("Expected an object")
            hints = validate_hints(payload.get("hints"))
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise ProviderOutputError("Invalid hint provider output") from exc
        approach = context.get("approach", {})
        labels = {
            str(approach.get(key, "")).replace("-", " ").lower()
            for key in ("id", "name", "pattern")
        } - {""}
        return [
            hint if hint.endswith("?") and "`" not in hint
            and not any(label in hint.lower() for label in labels)
            else SHORT_FALLBACK_HINTS[index]
            for index, hint in enumerate(hints)
        ]

    def generate_starter_code(self, context: dict, language: str, level: int) -> str:
        """Policy-6 rollback operation; the primary API uses generate_starter_batch."""
        baseline = trusted_starter(context, language, level)
        payload = {"context": context, "language": language, "level": level,
                   "baselineScaffold": baseline,
                   "editableSlots": [{"id": slot["id"], "existingTodo": slot["existingTodo"]}
                                     for slot in starter_slots(baseline)]}
        design = _starter_design(context)
        if design:
            payload["starterDesign"] = design
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": LEGACY_STARTER_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except Exception as exc:
            raise StarterProviderDiagnostic(provider_reason(exc)) from exc
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError, KeyError) as exc:
            raise StarterOutputDiagnostic("Invalid starter code provider output", "INVALID_OUTPUT_TYPE",
                                          "response") from exc
        if starter_raw_capture.get():
            observe({"kind": "raw_response", "content": content})
        return self.parse_starter_content(content, context, language, level, baseline=baseline)

    def generate_starter_batch(self, context: dict, language: str) -> dict[str, str]:
        payload = model_context(context, language)
        started = time.perf_counter()
        try:
            observe({"kind": "request", "contract": "starter-batch-v8"})
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": STARTER_SYSTEM_PROMPT},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                response_format={"type": "json_object"}, temperature=0.2,
                max_completion_tokens=10000,
            )
        except Exception as exc:
            raise StarterProviderDiagnostic(provider_reason(exc)) from exc
        finally:
            observe({"kind": "provider_timing", "durationMs": round((time.perf_counter() - started) * 1000, 1)})
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError, KeyError) as exc:
            raise StarterOutputDiagnostic("Invalid starter batch", "INVALID_OUTPUT_TYPE", "response") from exc
        if starter_raw_capture.get():
            observe({"kind": "raw_response", "content": content})
        usage = getattr(response, "usage", None)
        if usage:
            observe({"kind": "usage", **{key: getattr(usage, key, None)
                                         for key in ("prompt_tokens", "completion_tokens", "total_tokens")}})
        if not isinstance(content, str) or len(content) > 80000:
            raise StarterOutputDiagnostic("Invalid starter batch", "INVALID_OUTPUT_TYPE", "response")
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError, RecursionError) as exc:
            raise StarterOutputDiagnostic("Invalid starter batch", "INVALID_JSON", "parsing") from exc
        return validate_starter_batch(parsed, context, language, check_compilers=False)

    def generate_guidance_bundle(self, context: dict, language: str) -> dict:
        payload = model_context(context, language)
        started = time.perf_counter()
        observe({"kind": "request", "contract": "linked-guidance-v9"})
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": LINKED_GUIDANCE_PROMPT},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                response_format={"type": "json_object"}, temperature=0.2,
                max_completion_tokens=10000, timeout=30.0,
            )
        except Exception as exc:
            raise StarterProviderDiagnostic(provider_reason(exc)) from exc
        latency = round((time.perf_counter() - started) * 1000, 1)
        try:
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason
        except (AttributeError, IndexError, TypeError, KeyError) as exc:
            raise StarterOutputDiagnostic("Invalid linked guidance response", "INVALID_OUTPUT_TYPE", "response") from exc
        usage = getattr(response, "usage", None)
        metrics = {"promptTokens": getattr(usage, "prompt_tokens", None),
                   "completionTokens": getattr(usage, "completion_tokens", None),
                   "totalTokens": getattr(usage, "total_tokens", None),
                   "latencyMs": latency, "outputChars": len(content) if isinstance(content, str) else 0,
                   "finishReason": finish_reason}
        observe({"kind": "linked_usage", **metrics})
        if finish_reason == "length":
            raise StarterOutputDiagnostic("Linked guidance was truncated", "TOKEN_LIMIT_TRUNCATION", "response")
        if finish_reason not in ("stop", None):
            raise StarterOutputDiagnostic("Linked guidance did not complete", "INCOMPLETE_RESPONSE", "response")
        if not isinstance(content, str) or len(content) > 160000:
            raise StarterOutputDiagnostic("Invalid linked guidance response", "INVALID_OUTPUT_TYPE", "response")
        if starter_raw_capture.get():
            observe({"kind": "raw_response", "content": content})
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError, RecursionError) as exc:
            raise StarterOutputDiagnostic("Invalid linked guidance JSON", "INVALID_JSON", "parsing") from exc
        return {"output": parsed, "usage": metrics}

    @staticmethod
    def parse_starter_content(content, context: dict, language: str, level: int,
                              baseline: str | None = None, allow_legacy: bool = False) -> str:
        """Assemble the current edit contract; replay may inspect old full-file captures."""
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError) as exc:
            raise StarterOutputDiagnostic("Invalid starter code provider output", "INVALID_JSON", "parsing") from exc
        if not isinstance(parsed, dict):
            raise StarterOutputDiagnostic("Invalid starter code provider output", "INVALID_OUTPUT_TYPE", "parsing")
        try:
            template = context["problem"]["submissionTemplate"]["code"]
        except (AttributeError, TypeError, KeyError) as exc:
            raise StarterOutputDiagnostic("Invalid starter code provider output", "INVALID_OUTPUT_TYPE",
                                          "context") from exc
        if allow_legacy:
            if "code" not in parsed:
                raise StarterOutputDiagnostic("Invalid starter code provider output", "MISSING_CODE_FIELD", "parsing")
            if not isinstance(parsed["code"], str):
                raise StarterOutputDiagnostic("Invalid starter code provider output", "INVALID_OUTPUT_TYPE", "parsing")
            return validate_starter_code(_remove_outer_code_fence(parsed["code"]),
                                         template, language, level)
        return assemble_starter_plan(parsed, baseline or trusted_starter(context, language, level),
                                     template, language, level)

    def generate_solution(self, context: dict, language: str) -> dict[str, str]:
        payload = {"context": context, "language": language}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SOLUTION_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
        except Exception as exc:
            raise ProviderUnavailableError("Solution provider unavailable") from exc
        try:
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return validate_solution(parsed, context["problem"]["submissionTemplate"]["code"], language)
        except (AttributeError, IndexError, TypeError, ValueError, KeyError) as exc:
            raise ProviderOutputError("Invalid solution provider output") from exc
