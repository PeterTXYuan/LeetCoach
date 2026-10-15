"""Safe starter failure metadata and opt-in, request-local evaluation observations."""
from contextvars import ContextVar
from typing import Callable

from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.llm.base import ProviderOutputError, ProviderUnavailableError


# Only the local evaluation harness installs an observer. Production never retains raw text.
starter_observer: ContextVar[Callable[[dict], None] | None] = ContextVar(
    "starter_observer", default=None
)
starter_raw_capture: ContextVar[bool] = ContextVar("starter_raw_capture", default=False)


def observe(event: dict) -> None:
    observer = starter_observer.get()
    if observer is not None:
        observer(event)


def provider_reason(exc: Exception) -> str:
    """Classify by SDK exception type/status, never by exception message."""
    if isinstance(exc, (TimeoutError, APITimeoutError)):
        return "PROVIDER_TIMEOUT"
    if isinstance(exc, RateLimitError) or getattr(exc, "status_code", None) == 429:
        return "PROVIDER_RATE_LIMITED"
    if isinstance(exc, APIConnectionError):
        return "PROVIDER_TRANSPORT_ERROR"
    if isinstance(exc, APIStatusError):
        return "PROVIDER_HTTP_ERROR"
    return "UNKNOWN_FAILURE"


def failure_metadata(exc: Exception) -> dict:
    if isinstance(exc, ProviderUnavailableError):
        return {"stage": getattr(exc, "stage", "provider"),
                "reason": getattr(exc, "reason", "UNKNOWN_FAILURE"),
                "certainty": "confirmed" if hasattr(exc, "reason") else "unknown"}
    if isinstance(exc, ProviderOutputError):
        return {"stage": getattr(exc, "stage", "unknown"),
                "reason": getattr(exc, "reason", "UNKNOWN_FAILURE"),
                "certainty": "confirmed" if hasattr(exc, "reason") else "unknown"}
    return {"stage": "unknown", "reason": "UNKNOWN_FAILURE", "certainty": "unknown"}
