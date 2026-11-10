"""Thin LLM boundary. Every model call returns a validated pydantic object."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import ServiceUnavailable, UpstreamError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_RETRYABLE = {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError"}


class LLM(Protocol):
    def complete_json(
        self, *, task: str, system: str, user: str, schema: type[T], temperature: float = 0.4, max_tokens: int = 1400
    ) -> T: ...


class GroqLLM:
    """Groq chat completions in JSON mode, with repair-on-invalid-output and backoff on transient errors.

    Reasoning models (openai/gpt-oss-*) spend part of the output budget on hidden reasoning, so for those we
    request a low reasoning effort and raise max_tokens to leave room for the JSON answer itself.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float,
        max_retries: int,
        reasoning_effort: str = "low",
    ):
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._reasoning_effort = reasoning_effort
        self._client = None

    def _get_client(self):
        if not self._api_key:
            raise ServiceUnavailable(
                "GROQ_API_KEY is not set. Add it to backend/.env and restart the API.", code="llm_not_configured"
            )
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=self._api_key, timeout=self._timeout_s, max_retries=0)
        return self._client

    def complete_json(
        self, *, task: str, system: str, user: str, schema: type[T], temperature: float = 0.4, max_tokens: int = 1400
    ) -> T:
        client = self._get_client()
        is_reasoning = self._model.startswith("openai/gpt-oss")
        extra = {"extra_body": {"reasoning_effort": self._reasoning_effort}} if is_reasoning else {}
        token_budget = max_tokens * 2 + 800 if is_reasoning else max_tokens

        messages = [
            {"role": "system", "content": system + "\n\nRespond with one valid JSON object and nothing else."},
            {"role": "user", "content": user},
        ]
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            raw = ""
            try:
                started = time.perf_counter()
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=token_budget,
                    response_format={"type": "json_object"},
                    **extra,
                )
                raw = resp.choices[0].message.content or ""
                result = schema.model_validate(json.loads(_FENCE.sub("", raw.strip())))
                log.info("llm task=%s attempt=%d %.2fs", task, attempt, time.perf_counter() - started)
                return result
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = exc
                log.warning("llm task=%s produced invalid output (attempt %d): %s", task, attempt, str(exc)[:200])
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"That output was invalid: {str(exc)[:300]}. Return corrected JSON only."},
                ]
            except Exception as exc:  # provider SDK errors
                last_err = exc
                if type(exc).__name__ not in _RETRYABLE:
                    log.error("llm task=%s failed: %s", task, exc)
                    break
                log.warning("llm task=%s transient error (attempt %d): %s", task, attempt, exc)
                time.sleep(min(2**attempt, 8))
        raise UpstreamError(
            "The language model did not return a usable response. Try again in a moment.", code="llm_failed"
        ) from last_err