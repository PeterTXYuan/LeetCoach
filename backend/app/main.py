from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_session
from app.mock_data import PROBLEM_ANALYSES
from app.services.problem_repository import find_problem_analysis, find_related_problems

from app.services.hint_service import (
    get_approach_hints,
    get_primary_approach_hints,
)
from app.services.solution_service import (
    UnsupportedLanguageError,
    generate_approach_solution,
)
from app.services.starter_code_service import (
    UnsupportedStarterLanguageError,
    generate_starter_code,
)

app = FastAPI(title="LeetCoach API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|http://localhost(:[0-9]+)?|http://127\.0\.0\.1(:[0-9]+)?)$",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SolutionRequest(BaseModel):
    language: str


class StarterCodeRequest(BaseModel):
    language: str
    level: int = Field(strict=True, ge=1, le=3)


UNAVAILABLE_DETAIL = "This problem is not available in the local LeetCoach dataset yet."
APPROACH_UNAVAILABLE_DETAIL = (
    "This approach is not available for the requested LeetCoach problem."
)


def get_problem_or_404(slug: str):
    """Retained context for the mock-only guidance routes during this milestone."""
    problem = PROBLEM_ANALYSES.get(slug)

    if problem is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)

    return problem


def get_approach_or_404(problem, approach_id: str):
    for approach in problem["approaches"]:
        if approach["id"] == approach_id:
            return approach

    raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/problems/{slug}")
def get_problem_analysis(slug: str, session: Session = Depends(get_session)):
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    return analysis


@app.get("/api/problems/{slug}/hints")
def get_problem_hints(slug: str):
    problem = get_problem_or_404(slug)
    approach_id, hints = get_primary_approach_hints(problem)

    return {
        "slug": problem["slug"],
        "approachId": approach_id,
        "hints": hints,
    }


@app.get("/api/problems/{slug}/related")
def get_problem_related(slug: str, session: Session = Depends(get_session)):
    related = find_related_problems(session, slug)
    if related is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    return related


@app.get("/api/problems/{slug}/approaches/{approach_id}/hints")
def get_problem_approach_hints(slug: str, approach_id: str):
    problem = get_problem_or_404(slug)

    try:
        hints = get_approach_hints(problem, approach_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)

    return {
        "slug": problem["slug"],
        "approachId": approach_id,
        "hints": hints,
    }


@app.post("/api/problems/{slug}/approaches/{approach_id}/solution")
def generate_problem_approach_solution(
    slug: str, approach_id: str, request: SolutionRequest
):
    problem = get_problem_or_404(slug)
    approach = get_approach_or_404(problem, approach_id)

    try:
        return generate_approach_solution(problem, approach, request.language)
    except UnsupportedLanguageError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, java, javascript, cpp.",
        )


@app.post("/api/problems/{slug}/approaches/{approach_id}/starter-code")
def get_problem_starter_code(slug: str, approach_id: str, request: StarterCodeRequest):
    problem = get_problem_or_404(slug)
    approach = get_approach_or_404(problem, approach_id)
    try:
        return generate_starter_code(problem, approach, request.language, request.level)
    except UnsupportedStarterLanguageError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, java, javascript, cpp.",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Starter code is not available for this approach yet.")
