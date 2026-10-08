"""Structured Groq requests for progressive hints and starter code."""
import json
import re

from app.llm.base import (
    ProviderOutputError, ProviderUnavailableError, SHORT_FALLBACK_HINTS,
    validate_hints, validate_starter_code,
)


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

STARTER_SYSTEM_PROMPT = (
    "You are LeetCoach. Return a JSON object with a string field named code, containing "
    "unfinished LeetCode starter code in the requested language. Use ONLY the provided problem "
    "facts and selected canonical approach. The submissionTemplate is authoritative: copy every "
    "required class/method signature exactly, including all methods in design problems. Never "
    "switch approaches, invent an entry point, or include Markdown fences. "
    "Teaching rule: each level must add useful implementation help without giving the answer. "
    "Level 1 (Kickstart): preserve the shell and add at least one approach-specific executable "
    "setup step, such as a typed collection, sorted input, result container, or essential state. "
    "Add one or two concise TODOs about the next decision. Do not merely repeat the template "
    "or approach name; leave the main loop and algorithm substantially unwritten. "
    "Level 2 (Guided): retain Level 1's setup and add meaningful state or the initial main "
    "loop/control-flow outline when useful. The central condition, state transitions, and "
    "result construction remain unfinished. Do not implement duplicate skipping or pointer "
    "movement when those are key decisions. "
    "Level 3 (Strong Scaffold): retain earlier setup and add the major loop, branch, or helper "
    "structure plus useful intermediate calculations. Make TODOs precise and actionable at "
    "the missing operation. Leave substantial reasoning about the central lookup, condition, "
    "update, duplicate handling, pointer movement, or answer construction. "
    "For Two Sum with a map, Level 2 may iterate and read the current number; Level 3 may "
    "also calculate its complement, but must not implement map lookup/update or the answer. "
    "For 3Sum with two pointers, Level 1 may sort and initialize results; Level 2 may add "
    "the outer loop and pointers; Level 3 may add the inner loop, sum, and comparison branches "
    "while leaving movement, duplicate handling, and recording for the student. "
    "Never output a complete algorithm, a full solution with a decorative TODO and unreachable "
    "throw/raise, commented-out solution statements, or ready-to-copy pseudocode for the missing "
    "steps. A student must still reason about the core operation. Keep comments short and "
    "educational, preserve language syntax and indentation, never use invalid placeholders "
    "such as if (/* TODO */), and include a TODO plus a fail-loud placeholder on unfinished paths."
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
        payload = {"context": context, "language": language, "level": level}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": STARTER_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except Exception as exc:
            raise ProviderUnavailableError("Starter code provider unavailable") from exc
        try:
            content = response.choices[0].message.content
            parsed = json.loads(content)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("code"), str):
                raise ValueError("Expected a code field")
            return validate_starter_code(
                _remove_outer_code_fence(parsed["code"]),
                context["problem"]["submissionTemplate"]["code"], language, level
            )
        except (AttributeError, IndexError, TypeError, ValueError, KeyError) as exc:
            raise ProviderOutputError("Invalid starter code provider output") from exc
