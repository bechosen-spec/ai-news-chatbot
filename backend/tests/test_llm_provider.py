import asyncio
import json

import httpx
import pytest

from backend.app.core.config import Settings
from backend.app.services.llm import ProviderResponseError
from backend.app.services.llm.openai import OpenAIResponsesProvider


def test_openai_provider_retries_and_validates_structured_output():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(500, json={"error": {"message": "temporary"}})
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "answer": "A grounded answer.",
                                        "citation_ids": ["S1"],
                                        "limitations": [],
                                    }
                                ),
                            }
                        ],
                    }
                ]
            },
        )

    settings = Settings(llm_provider="openai", llm_api_key="test-secret", llm_retry_limit=2)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAIResponsesProvider(settings, client=client)
    answer = asyncio.run(provider.generate(system_prompt="system", user_prompt="user"))
    asyncio.run(client.aclose())
    assert answer.citation_ids == ["S1"]
    assert len(calls) == 2
    assert calls[0]["text"]["format"]["type"] == "json_schema"
    assert calls[0]["text"]["format"]["strict"] is True


def test_openai_provider_rejects_invalid_schema_response():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"output_text": '{"answer":"missing fields"}'})
        )
    )
    provider = OpenAIResponsesProvider(
        Settings(llm_provider="openai", llm_api_key="test-secret", llm_retry_limit=1),
        client=client,
    )
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.generate(system_prompt="system", user_prompt="user"))
    asyncio.run(client.aclose())
