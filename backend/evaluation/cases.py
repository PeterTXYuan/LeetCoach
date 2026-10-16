"""Deterministic first-round matrix; every identity is checked against SQLite."""
from dataclasses import asdict, dataclass

from app.services.problem_repository import find_problem_analysis, find_problem_context


@dataclass(frozen=True)
class EvaluationCase:
    feature: str
    slug: str
    approach_id: str
    language: str | None = None
    level: int | None = None

    @property
    def key(self) -> str:
        suffix = f"-{self.language}" if self.language else ""
        suffix += f"-level-{self.level}" if self.level else ""
        return f"{self.feature}-{self.slug}-{self.approach_id}{suffix}"

    @property
    def endpoint(self) -> str:
        return f"/api/problems/{self.slug}/approaches/{self.approach_id}/" + (
            "hints" if self.feature == "hints" else
            "starter-code" if self.feature == "starter" else "solution"
        )

    def to_dict(self) -> dict:
        return {"id": self.key, **asdict(self), "endpoint": self.endpoint}


CASES = (
    # One request yields the entire three-hint batch.
    EvaluationCase("hints", "two-sum", "brute-force"),
    EvaluationCase("hints", "two-sum", "hash-map"),
    EvaluationCase("hints", "3sum", "sort-and-two-pointers"),
    EvaluationCase("hints", "valid-parentheses", "stack"),
    EvaluationCase("hints", "longest-substring-without-repeating-characters", "sliding-window-set"),
    EvaluationCase("hints", "binary-search", "binary-search"),
    EvaluationCase("hints", "min-stack", "paired-minimums"),
    EvaluationCase("hints", "maximum-depth-of-binary-tree", "depth-first-search"),
    EvaluationCase("hints", "reverse-linked-list", "iterative-pointers"),
    EvaluationCase("hints", "number-of-islands", "depth-first-flood-fill"),
    # Three directly comparable progressions, nine requests in total.
    EvaluationCase("starter", "two-sum", "hash-map", "python", 1),
    EvaluationCase("starter", "two-sum", "hash-map", "python", 2),
    EvaluationCase("starter", "two-sum", "hash-map", "python", 3),
    EvaluationCase("starter", "3sum", "sort-and-two-pointers", "java", 1),
    EvaluationCase("starter", "3sum", "sort-and-two-pointers", "java", 2),
    EvaluationCase("starter", "3sum", "sort-and-two-pointers", "java", 3),
    EvaluationCase("starter", "min-stack", "paired-minimums", "javascript", 1),
    EvaluationCase("starter", "min-stack", "paired-minimums", "javascript", 2),
    EvaluationCase("starter", "min-stack", "paired-minimums", "javascript", 3),
    # Executable oracles emphasize Python; other languages exercise API and syntax paths.
    EvaluationCase("solution", "two-sum", "brute-force", "python"),
    EvaluationCase("solution", "two-sum", "hash-map", "python"),
    EvaluationCase("solution", "two-sum", "hash-map", "javascript"),
    EvaluationCase("solution", "two-sum", "hash-map", "java"),
    EvaluationCase("solution", "two-sum", "hash-map", "cpp"),
    EvaluationCase("solution", "3sum", "sort-and-two-pointers", "python"),
    EvaluationCase("solution", "3sum", "sort-and-two-pointers", "cpp"),
    EvaluationCase("solution", "valid-parentheses", "stack", "python"),
    EvaluationCase("solution", "longest-substring-without-repeating-characters", "sliding-window-set", "python"),
    EvaluationCase("solution", "binary-search", "binary-search", "python"),
    EvaluationCase("solution", "min-stack", "paired-minimums", "python"),
    EvaluationCase("solution", "reverse-linked-list", "iterative-pointers", "python"),
)


PREVIOUS_STARTER_FALLBACK_IDS = (
    "starter-two-sum-hash-map-python-level-1",
    "starter-two-sum-hash-map-python-level-2",
    "starter-3sum-sort-and-two-pointers-java-level-1",
    "starter-3sum-sort-and-two-pointers-java-level-2",
    "starter-3sum-sort-and-two-pointers-java-level-3",
    "starter-min-stack-paired-minimums-javascript-level-1",
    "starter-min-stack-paired-minimums-javascript-level-3",
)


# Post-contract comparison: the original nine plus four previously used
# algorithm/language regression cases. Selected only by an explicit CLI flag.
CONTRACT_STARTER_CASES = (
    *(case for case in CASES if case.feature == "starter"),
    EvaluationCase("starter", "binary-search", "binary-search", "cpp", 1),
    EvaluationCase("starter", "binary-search", "binary-search", "cpp", 2),
    EvaluationCase("starter", "binary-search", "binary-search", "cpp", 3),
    EvaluationCase("starter", "maximum-depth-of-binary-tree", "depth-first-search", "python", 2),
)


# Frozen before the final live run. These six identities are present in SQLite,
# span four languages and six distinct algorithm families, and are absent from
# the original nine and the four repeated regression cases.
FINAL_MVP_FRESH_CASES = (
    EvaluationCase("starter", "group-anagrams", "frequency-signature", "java", 1),
    EvaluationCase("starter", "number-of-islands", "depth-first-flood-fill", "python", 1),
    EvaluationCase("starter", "climbing-stairs", "memoized-recursion", "javascript", 2),
    EvaluationCase("starter", "reverse-linked-list", "iterative-pointers", "python", 2),
    EvaluationCase("starter", "daily-temperatures", "monotonic-stack", "cpp", 3),
    EvaluationCase("starter", "search-in-rotated-sorted-array", "modified-binary-search", "python", 3),
)

FINAL_MVP_STARTER_CASES = (*CONTRACT_STARTER_CASES, *FINAL_MVP_FRESH_CASES)


def validate_matrix(session, cases=CASES) -> list[str]:
    """Inspect the live seed; never silently evaluate a nonexistent fixture."""
    errors: list[str] = []
    for case in cases:
        analysis = find_problem_analysis(session, case.slug)
        if not analysis:
            errors.append(f"{case.key}: problem absent from SQLite")
            continue
        if case.approach_id not in {item["id"] for item in analysis["approaches"]}:
            errors.append(f"{case.key}: canonical approach absent from SQLite")
        if case.feature in {"starter", "solution"} and not find_problem_context(
            session, case.slug, case.approach_id, case.language
        ):
            errors.append(f"{case.key}: submission template absent from SQLite")
    if len({case.key for case in cases}) != len(cases):
        errors.append("evaluation matrix contains duplicate case IDs")
    return errors
