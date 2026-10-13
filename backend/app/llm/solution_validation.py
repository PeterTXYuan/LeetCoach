"""Structural checks for complete, DB-grounded full-solution responses.

These checks reject obvious malformed output; they cannot prove algorithmic
correctness and never execute provider code in the API process.
"""
import ast
import re
from typing import Any

from pydantic import BaseModel, Field, StrictStr, ValidationError, field_validator

from app.llm.base import ProviderOutputError


class SolutionFields(BaseModel):
    code: StrictStr = Field(min_length=1, max_length=30000)
    explanation: StrictStr = Field(min_length=1, max_length=5000)
    timeComplexity: StrictStr = Field(min_length=1, max_length=120)
    spaceComplexity: StrictStr = Field(min_length=1, max_length=120)

    @field_validator("code", "explanation", "timeComplexity", "spaceComplexity")
    @classmethod
    def nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Empty solution field")
        return stripped


def validate_solution(raw: Any, template: str, language: str) -> dict[str, str]:
    """Preserve LeetCode entry points and reject obvious incomplete code."""
    try:
        fields = SolutionFields.model_validate(raw)
    except ValidationError as exc:
        raise ProviderOutputError("Invalid solution fields") from exc

    code = fields.code
    if "```" in code or re.search(r"\b(?:TODO|FIXME|NotImplementedError|UnsupportedOperationException)\b", code, re.I):
        raise ProviderOutputError("Incomplete or fenced full solution")
    if re.search(r"\b(?:throw|raise)\b[^\n]*(?:complete|implement|placeholder|todo)", code, re.I):
        raise ProviderOutputError("Unfinished solution branch")

    signatures = [line.strip().rstrip(" {") for line in template.splitlines() if "(" in line]
    output_lines = [line.strip().rstrip(" {") for line in code.splitlines()]
    if not signatures or any(output_lines.count(signature) != 1 for signature in signatures):
        raise ProviderOutputError("Full solution changed a submission signature")
    class_line = next((line.strip().rstrip(" {") for line in template.splitlines()
                       if line.strip().startswith("class ")), None)
    if class_line and output_lines.count(class_line) != 1:
        raise ProviderOutputError("Full solution changed the submission class")

    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ProviderOutputError("Invalid Python solution syntax") from exc
        if any(isinstance(node, ast.Pass) or
               (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and node.value.value is Ellipsis) for node in ast.walk(tree)):
            raise ProviderOutputError("Unimplemented Python solution branch")
    else:
        # Ignore comments and quoted text for simple delimiter checks.
        cleaned = re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.DOTALL)
        cleaned = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', cleaned)
        if any(re.search(re.escape(signature) + r"\s*\{\s*\}", cleaned)
               for signature in signatures):
            raise ProviderOutputError("Unimplemented solution method")
        for opening, closing in (("{", "}"), ("(", ")")):
            depth = 0
            for char in cleaned:
                if char == opening:
                    depth += 1
                elif char == closing:
                    depth -= 1
                    if depth < 0:
                        raise ProviderOutputError("Broken solution structure")
            if depth:
                raise ProviderOutputError("Broken solution structure")
        if language == "javascript" and "function" not in code:
            raise ProviderOutputError("JavaScript submission entry point is missing")

    return fields.model_dump()
