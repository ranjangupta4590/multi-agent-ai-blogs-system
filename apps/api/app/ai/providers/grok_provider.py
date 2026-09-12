"""xAI Grok provider adapter implementing LLMProvider."""
from typing import List
from app.ai.providers.openai_provider import OpenAIProvider


class GrokProvider(OpenAIProvider):
    """xAI Grok Adapter using OpenAI-compatible API format."""

    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1"):
        super().__init__(api_key=api_key, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return "Grok"

    def get_models(self) -> List[str]:
        return ["grok-2", "grok-2-mini", "grok-beta"]
