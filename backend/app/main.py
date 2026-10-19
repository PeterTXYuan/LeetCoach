import logging
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_session
from app.llm.base import (
    ProviderConfigurationError, ProviderOutputError, ProviderUnavailableError, StarterOutputDiagnostic,
    STARTER_CODE_POLICY_VERSION, LEGACY_STARTER_CODE_POLICY_VERSION,
    LINKED_GUIDANCE_POLICY_VERSION,
    STARTER_LEVEL_NAMES, SUPPORTED_STARTER_LANGUAGES,
    validate_hints, validate_starter_code,
)
from app.llm.provider_factory import get_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.starter_diagnostics import failure_metadata, observe
from app.llm.solution_validation import validate_solution
from app.llm.starter_batch import model_context, validate_starter_batch
from app.llm.linked_guidance import validate_linked_bundle, check_linked_correctness
from app.services.problem_repository import (
    find_hint_problem_context, find_problem_analysis, find_problem_context, find_related_problems,
)
from app.services.solution_service import CURATED_MOCK_WARNING

app = FastAPI(title="LeetCoach API")
logger = logging.getLogger(__name__)

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


class StarterBatchRequest(BaseModel):
    language: str


@app.post("/api/problems/{slug}/approaches/{approach_id}/guidance")
def generate_linked_guidance(
    slug: str, approach_id: str, request: StarterBatchRequest,
    session: Session = Depends(get_session),
):
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail="This problem is not available in the local LeetCoach dataset yet.")
    if not any(item["id"] == approach_id for item in analysis["approaches"]):
        raise HTTPException(status_code=404, detail="This approach is not available for the requested LeetCoach problem.")
    language = request.language.lower()
    if language not in SUPPORTED_STARTER_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported guidance language.")
    context = find_problem_context(session, slug, approach_id, language)
    if context is None:
        raise HTTPException(status_code=404, detail="Submission template is not available.")
    try:
        model_context(context, language)
        provider = get_llm_provider()
        if provider.is_ai_generated:
            generated = provider.generate_guidance_bundle(context, language)
            bundle = validate_linked_bundle(generated["output"], context, language)
            verification = check_linked_correctness(slug, language, bundle["solution"]["code"])
            if verification["status"] == "FAIL":
                bundle["warnings"].append({
                    "scope": "solution", "code": "CORRECTNESS_FIXTURE_FAILED",
                    "message": "The full answer failed representative test cases. Review or regenerate it."
                })
            kind = "linked"
            usage = generated["usage"]
        else:
            # The offline fixtures predate linked generation. Never claim lineage.
            batch = validate_starter_batch(provider.generate_starter_batch(context, language),
                                           context, language)
            bundle = {**batch, "solution": None, "warnings": []}
            try:
                bundle["solution"] = provider.generate_solution(context, language)
            except ProviderUnavailableError:
                pass
            verification = {"status": "NOT_RUN", "summary": "Offline curated responses are separate fixtures"}
            kind = "starterOnlyMock"
            usage = None
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Guidance provider is not configured.")
    except (ProviderUnavailableError, ProviderOutputError) as exc:
        diagnostic = failure_metadata(exc)
        observe({"kind": "failure", **diagnostic})
        logger.warning("Linked guidance rejected slug=%s approach=%s language=%s reason=%s",
                       slug, approach_id, language, diagnostic["reason"])
        raise HTTPException(status_code=503 if isinstance(exc, ProviderUnavailableError) else 502,
                            detail={"message": "Guidance could not be generated. Previous content is retained.",
                                    **diagnostic})
    return {"slug": slug, "approachId": approach_id, "language": language,
            "policyVersion": LINKED_GUIDANCE_POLICY_VERSION, "generationId": str(uuid4()),
            "kind": kind, "isAiGenerated": provider.is_ai_generated,
            "notice": ("Starter code leaves work for you; the matching full answer stays hidden."
                       if kind == "linked" else "Offline mock starter code; its curated answer is separate."),
            "verification": verification, "usage": usage, **bundle}


UNAVAILABLE_DETAIL = "This problem is not available in the local LeetCoach dataset yet."
APPROACH_UNAVAILABLE_DETAIL = (
    "This approach is not available for the requested LeetCoach problem."
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/problems/{slug}")
def get_problem_analysis(slug: str, session: Session = Depends(get_session)):
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    return analysis


def generate_db_hints(problem_context: dict, approach: dict):
    context = {"problem": problem_context["problem"], "approach": approach}
    try:
        hints = validate_hints(get_llm_provider().generate_hints(context))
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Hint provider is not configured.")
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="Hint provider is temporarily unavailable.")
    except ProviderOutputError:
        raise HTTPException(status_code=502, detail="Hint provider returned invalid hints.")
    return {
        "slug": problem_context["problem"]["slug"],
        "approachId": approach["id"],
        "hints": hints,
    }


@app.get("/api/problems/{slug}/hints")
def get_problem_hints(slug: str, session: Session = Depends(get_session)):
    problem_context = find_hint_problem_context(session, slug)
    if problem_context is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    approach = next(
        (item for item in problem_context["approaches"] if item["isPrimary"]), None
    )
    if approach is None:
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)
    return generate_db_hints(problem_context, approach)


@app.get("/api/problems/{slug}/related")
def get_problem_related(slug: str, session: Session = Depends(get_session)):
    related = find_related_problems(session, slug)
    if related is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    return related


@app.get("/api/problems/{slug}/approaches/{approach_id}/hints")
def get_problem_approach_hints(
    slug: str, approach_id: str, session: Session = Depends(get_session)
):
    problem_context = find_hint_problem_context(session, slug)
    if problem_context is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    approach = next(
        (item for item in problem_context["approaches"] if item["id"] == approach_id), None
    )
    if approach is None:
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)
    return generate_db_hints(problem_context, approach)


@app.post("/api/problems/{slug}/approaches/{approach_id}/solution")
def generate_problem_approach_solution(
    slug: str, approach_id: str, request: SolutionRequest,
    session: Session = Depends(get_session),
):
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    if not any(approach["id"] == approach_id for approach in analysis["approaches"]):
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)
    language = request.language.lower()
    if language not in SUPPORTED_STARTER_LANGUAGES:
        raise HTTPException(status_code=400,
                            detail="Unsupported language. Supported languages: python, java, javascript, cpp.")
    context = find_problem_context(session, slug, approach_id, language)
    if context is None:
        raise HTTPException(status_code=404, detail="Full solution is not available for this approach yet.")
    try:
        provider = get_llm_provider()
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Full solution provider is not configured.")
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="Full solution provider is temporarily unavailable.")
    try:
        solution = validate_solution(
            provider.generate_solution(context, language),
            context["problem"]["submissionTemplate"]["code"], language,
        )
    except ProviderUnavailableError:
        detail = ("No curated offline full solution exists for this approach. Configure Groq to generate one."
                  if not provider.is_ai_generated else
                  "Full solution provider is temporarily unavailable.")
        raise HTTPException(status_code=503, detail=detail)
    except ProviderOutputError:
        raise HTTPException(status_code=502, detail="Full solution provider returned invalid output.")
    return {
        "slug": slug, "approachId": approach_id, "language": language,
        "isAiGenerated": provider.is_ai_generated,
        "warning": ("Full solution revealed. Try solving the problem yourself before relying on this answer."
                    if provider.is_ai_generated else CURATED_MOCK_WARNING),
        **solution,
    }


@app.post("/api/problems/{slug}/approaches/{approach_id}/starter-code")
def get_problem_starter_code(
    slug: str, approach_id: str, request: StarterCodeRequest,
    session: Session = Depends(get_session),
):
    if os.environ.get("LEETCOACH_ENABLE_LEGACY_STARTER", "").lower() != "true":
        raise HTTPException(status_code=409, detail="Use the Starter Code batch endpoint. Policy 6 is disabled.")
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    if not any(approach["id"] == approach_id for approach in analysis["approaches"]):
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)
    language = request.language.lower()
    if language not in SUPPORTED_STARTER_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, java, javascript, cpp.",
        )
    context = find_problem_context(session, slug, approach_id, language)
    if context is None:
        raise HTTPException(status_code=404, detail="Starter code is not available for this approach yet.")
    try:
        provider = get_llm_provider()
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Starter code provider is not configured.")
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="Starter code provider is temporarily unavailable.")
    except ProviderOutputError:
        raise HTTPException(status_code=502, detail="Starter code provider returned invalid output.")
    used_fallback = False
    try:
        code = validate_starter_code(
            provider.generate_starter_code(context, language, request.level),
            context["problem"]["submissionTemplate"]["code"], language, request.level,
        )
    except (ProviderUnavailableError, ProviderOutputError) as exc:
        if not provider.is_ai_generated:
            if isinstance(exc, ProviderUnavailableError):
                raise HTTPException(status_code=503, detail="Starter code provider is temporarily unavailable.")
            raise HTTPException(status_code=502, detail="Starter code provider returned invalid output.")
        # A provider can return HTTP 200 but still produce unusable code. Keep
        # the student moving without accepting a changed signature or answer.
        diagnostic = failure_metadata(exc)
        logger.warning("Groq starter code rejected slug=%s approach=%s language=%s level=%s "
                       "failure_stage=%s reason=%s fallback_used=true",
                       slug, approach_id, language, request.level,
                       diagnostic["stage"], diagnostic["reason"])
        observe({"kind": "failure", **diagnostic})
        try:
            code = MockLLMProvider().generate_starter_code(context, language, request.level)
        except ProviderOutputError:
            raise HTTPException(status_code=502, detail="Starter code could not be generated.")
        used_fallback = True
    if provider.is_ai_generated and not used_fallback:
        observe({"kind": "accepted", "stage": "accepted", "reason": None})
    result = {
        "slug": slug, "approachId": approach_id, "language": language,
        "level": request.level, "levelName": STARTER_LEVEL_NAMES[request.level],
        "policyVersion": LEGACY_STARTER_CODE_POLICY_VERSION,
        "isAiGenerated": provider.is_ai_generated and not used_fallback,
        "code": code,
        "notice": (
            "AI starter code could not be used. This offline scaffold is still unfinished; "
            "complete its TODOs, or try AI generation again."
            if used_fallback else
            "Starter code, not a full solution. Complete the TODOs and replace the placeholder before running."
        ),
    }
    if used_fallback:
        result["usedFallback"] = True
    return result


@app.post("/api/problems/{slug}/approaches/{approach_id}/starter-code/batch")
def get_problem_starter_batch(
    slug: str, approach_id: str, request: StarterBatchRequest,
    session: Session = Depends(get_session),
):
    analysis = find_problem_analysis(session, slug)
    if analysis is None:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL)
    if not any(item["id"] == approach_id for item in analysis["approaches"]):
        raise HTTPException(status_code=404, detail=APPROACH_UNAVAILABLE_DETAIL)
    language = request.language.lower()
    if language not in SUPPORTED_STARTER_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported starter language.")
    context = find_problem_context(session, slug, approach_id, language)
    if context is None:
        raise HTTPException(status_code=404, detail="Submission template is not available.")
    try:
        model_context(context, language)  # Fail explicitly before a paid request.
        provider = get_llm_provider()
        batch = provider.generate_starter_batch(context, language)
        # Compile/parse once at the API boundary for every provider, without
        # ever running a generated program.
        batch = validate_starter_batch(batch, context, language)
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Starter code provider is not configured.")
    except (ProviderUnavailableError, ProviderOutputError) as exc:
        diagnostic = failure_metadata(exc)
        observe({"kind": "failure", **diagnostic})
        logger.warning("Starter batch rejected slug=%s approach=%s language=%s stage=%s reason=%s",
                       slug, approach_id, language, diagnostic["stage"], diagnostic["reason"])
        status = 503 if isinstance(exc, ProviderUnavailableError) else 502
        if diagnostic["stage"] == "context": status = 409
        raise HTTPException(status_code=status, detail={
            "message": "Starter code could not be generated. Please retry; previous code is retained.",
            **diagnostic,
        })
    observe({"kind": "accepted", "stage": "accepted", "reason": None})
    return {"slug": slug, "approachId": approach_id, "language": language,
            "policyVersion": STARTER_CODE_POLICY_VERSION, "isAiGenerated": provider.is_ai_generated,
            "usedFallback": False,
            "notice": ("Starter code, not a full solution. Complete the TODOs before running."
                       if provider.is_ai_generated else
                       "Offline mock starter code. Complete the TODOs before running."),
            **batch}
