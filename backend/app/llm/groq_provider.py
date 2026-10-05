"""One structured Groq request for all three progressive hints."""
import json

from app.llm.base import (
    ProviderOutputError, ProviderUnavailableError, SHORT_FALLBACK_HINTS,
    validate_hints,
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


class GroqLLMProvider:
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
