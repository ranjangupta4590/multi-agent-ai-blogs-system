"""Anthropic Claude provider adapter implementing LLMProvider."""
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from app.ai.gateway.budget import calculate_cost
from app.ai.gateway.interface import (
    HealthStatus,
    LLMMessage,
    LLMOptions,
    LLMProvider,
    LLMResponse,
    TokenUsage,
)
from app.core.errors import ProviderUnavailableError
from app.core.logging import logger


class ClaudeProvider(LLMProvider):
    """Anthropic Claude Adapter using the Messages API."""

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "Claude"

    def get_models(self) -> List[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> LLMResponse:
        opts = options or LLMOptions()
        model = opts.model or "claude-3-5-sonnet-20241022"
        start_time = time.time()

        # Separate system message from conversation
        system_text = ""
        conversation = []
        for m in messages:
            if m.role == "system":
                system_text += (m.content + "\n\n")
            else:
                conversation.append({"role": m.role, "content": m.content})

        if not conversation:
            conversation.append({"role": "user", "content": "Begin."})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": conversation,
            "max_tokens": opts.max_tokens,
            "temperature": opts.temperature,
        }
        if system_text.strip():
            payload["system"] = system_text.strip()

        try:
            async with httpx.AsyncClient(timeout=opts.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.error(f"Claude error {resp.status_code}: {resp.text}")
                    raise ProviderUnavailableError("Claude", f"API returned status {resp.status_code}")

                data = resp.json()
                content = ""
                for part in data.get("content", []):
                    if part.get("type") == "text":
                        content += part.get("text", "")

                usage_data = data.get("usage", {})
                prompt_tokens = usage_data.get("input_tokens", 0)
                completion_tokens = usage_data.get("output_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens

                latency_ms = int((time.time() - start_time) * 1000)
                cost = calculate_cost(model, prompt_tokens, completion_tokens)

                return LLMResponse(
                    content=content,
                    provider=self.provider_name,
                    model=model,
                    usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    ),
                    estimated_cost_usd=cost,
                    latency_ms=latency_ms,
                    finish_reason=data.get("stop_reason", "end_turn"),
                    raw_response=data,
                )
        except httpx.HTTPError as e:
            logger.error(f"Claude network error: {e}")
            raise ProviderUnavailableError("Claude", f"Network error communicating with Claude: {e}")

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None
    ) -> Dict[str, Any]:
        opts = options or LLMOptions()
        augmented = list(messages)
        augmented.append(LLMMessage(
            role="user",
            content=f"\nYou must return ONLY valid JSON matching this schema with no conversational prefix:\n{json.dumps(schema)}"
        ))
        res = await self.generate(augmented, opts)
        cleaned = res.content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode Claude structured response: {e}")
            return {"raw": res.content, "error": "Invalid JSON produced by model"}

    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        res = await self.generate(messages, options)
        for paragraph in res.content.split("\n\n"):
            yield paragraph + "\n\n"

    async def health_check(self) -> HealthStatus:
        start_time = time.time()
        # Light prompt to check connectivity
        try:
            res = await self.generate([LLMMessage(role="user", content="ping")], LLMOptions(max_tokens=5, timeout=10.0))
            latency_ms = int((time.time() - start_time) * 1000)
            return HealthStatus(is_healthy=True, latency_ms=latency_ms, message="Claude API reachable")
        except Exception as e:
            return HealthStatus(is_healthy=False, latency_ms=0, message=str(e))
