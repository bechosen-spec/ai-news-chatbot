"""OpenAI Responses API adapter with strict structured output and bounded retries."""

import asyncio
import json

import httpx
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.services.llm.base import (
    GeneratedAnswer,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citation_ids": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "citation_ids", "limitations"],
    "additionalProperties": False,
}


class OpenAIResponsesProvider:
    name = "openai-responses"

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client

    @property
    def configured(self) -> bool:
        return self.settings.llm_api_key is not None

    @staticmethod
    def _extract_output_text(payload: dict) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str):
            return direct
        for output in payload.get("output", []):
            if output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
                if content.get("type") == "refusal":
                    raise ProviderResponseError("The generation provider refused the request")
        raise ProviderResponseError("The generation provider returned no structured answer")

    async def generate(self, *, system_prompt: str, user_prompt: str) -> GeneratedAnswer:
        if not self.configured:
            raise ProviderUnavailableError("The generation provider is not configured")
        body = {
            "model": self.settings.llm_model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_output_tokens": self.settings.llm_max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "grounded_news_answer",
                    "strict": True,
                    "schema": ANSWER_SCHEMA,
                }
            },
        }
        client = self.client or httpx.AsyncClient(
            timeout=self.settings.llm_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
        )
        close_client = self.client is None
        try:
            for attempt in range(self.settings.llm_retry_limit):
                try:
                    response = await client.post(
                        f"{self.settings.llm_base_url.rstrip('/')}/responses", json=body
                    )
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt + 1 < self.settings.llm_retry_limit:
                            await asyncio.sleep(0.25 * (2**attempt))
                            continue
                    response.raise_for_status()
                    raw_text = self._extract_output_text(response.json())
                    return GeneratedAnswer.model_validate(json.loads(raw_text))
                except httpx.TimeoutException as error:
                    if attempt + 1 >= self.settings.llm_retry_limit:
                        raise ProviderTimeoutError("The generation provider timed out") from error
                    await asyncio.sleep(0.25 * (2**attempt))
                except (
                    httpx.HTTPError,
                    json.JSONDecodeError,
                    ValidationError,
                    ValueError,
                ) as error:
                    if (
                        isinstance(error, httpx.HTTPStatusError)
                        and error.response.status_code < 500
                    ):
                        raise ProviderResponseError(
                            "The generation provider rejected the request "
                            f"({error.response.status_code})"
                        ) from error
                    if attempt + 1 >= self.settings.llm_retry_limit:
                        raise ProviderResponseError(
                            "The generation provider returned an invalid response"
                        ) from error
                    await asyncio.sleep(0.25 * (2**attempt))
            raise ProviderResponseError("The generation provider failed")
        finally:
            if close_client:
                await client.aclose()
