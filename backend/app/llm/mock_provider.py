"""Offline, deterministic progressive hints based on canonical DB context."""
from app.llm.base import validate_hints


class MockLLMProvider:
    def generate_hints(self, context: dict) -> list[str]:
        approach = context["approach"]
        steps = approach.get("thinkingSteps", [])
        quote = approach.get("recognitionSignals", {}).get("quote")
        hints = [
            "What detail tells you whether an answer is valid?",
            f"Why might “{quote}” matter here?" if quote else
            "Which part of the input could narrow your choices?",
            steps[0] if steps else "What is one small check you could try next?",
        ]
        return validate_hints(hints)
