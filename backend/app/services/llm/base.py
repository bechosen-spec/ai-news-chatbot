"""Provider-independent generation contract."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=8_000)
    citation_ids: list[str] = Field(max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderTimeoutError(RuntimeError):
    pass


class ProviderResponseError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    async def generate(self, *, system_prompt: str, user_prompt: str) -> GeneratedAnswer: ...
