from backend.app.services.llm.base import GeneratedAnswer, ProviderUnavailableError


class DisabledProvider:
    name = "disabled"
    configured = False

    async def generate(self, *, system_prompt: str, user_prompt: str) -> GeneratedAnswer:
        raise ProviderUnavailableError("The generation provider is disabled")
