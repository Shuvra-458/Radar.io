import asyncio
import random
import re
from typing import Awaitable, Callable, TypeVar

from groq import APIStatusError
from langchain_groq import ChatGroq
from rich import print as rprint

from app.config import LLM_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT_S

T = TypeVar("T")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_RETRY_AFTER_RE = re.compile(r"try again in([\d.]+)s", re.IGNORECASE)

def _is_retryable(exc: Exception) -> bool:
    """Groq raises APIStatusError with the HTTP status on `.status_code`."""
    if isinstance(exc, APIStatusError):
        return exc.status_code in RETRYABLE_STATUS
    return False

def _extract_retry_after(exc: Exception) -> float | None:
    m = _RETRY_AFTER_RE.search(str(exc))
    if m:
        return float(m.group(1)) + 0.5
    return None

async def llm_with_retry(
    call: Callable[[], Awaitable[T]],
    *,
    attempts: int = 6,
    base_delay: float = 1.0,
    max_delay: float = 20.0
) -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return await call()
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or i == attempts - 1:
                raise
            hinted = _extract_retry_after(e)
            if hinted:
                delay = min(hinted, max_delay)
            else:
                delay = min(base_delay * (2 ** i), max_delay)
                delay += random.uniform(0, 0.5)
            rprint(f"[yellow]  ⚠ LLM error (attempt {i+1}/{attempts}), "
                   f"retrying in {delay:.1f}s: {str(e)[:100]}[/yellow]")

            await asyncio.sleep(delay)

    raise last_exc

_PREFERRED = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

def _resolve_default_model() -> str:
    try:
        from groq import Groq
        from app.config import GROQ_API_KEY
        client = Groq(api_key=GROQ_API_KEY)
        available = {m.id for m in client.models.list().data}
        for name in _PREFERRED:
            if name in available:
                return name

    except Exception as e:
        rprint(f"[yellow]model resolution failed ({e}), using {LLM_MODEL}[/yellow]")
    return LLM_MODEL

_DEFAULT_MODEL = _resolve_default_model()

def make_llm(model: str | None = None, temperature: float = LLM_TEMPERATURE) -> ChatGroq:
    """
    Makes Request to the Groq LLM.
    """
    return ChatGroq(
        model=model or _DEFAULT_MODEL,
        temperature=temperature,
        timeout=LLM_TIMEOUT_S,
        max_retries=2,
    )

