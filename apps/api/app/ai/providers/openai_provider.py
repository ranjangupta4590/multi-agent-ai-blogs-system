"""OpenAI provider adapter implementing LLMProvider."""
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


class OpenAIProvider(LLMProvider):
    """OpenAI Adapter using direct async HTTP to the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def get_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> LLMResponse:
        opts = options or LLMOptions()
        model = opts.model or "gpt-4o"
        start_time = time.time()

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
        }
        if opts.json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=opts.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.error(f"OpenAI error {resp.status_code}: {resp.text}")
                    raise ProviderUnavailableError("OpenAI", f"API returned status {resp.status_code}")

                data = resp.json()
                content = data["choices"][0]["message"]["content"] or ""
                finish_reason = data["choices"][0].get("finish_reason", "stop")

                usage_data = data.get("usage", {})
                prompt_tokens = usage_data.get("prompt_tokens", 0)
                completion_tokens = usage_data.get("completion_tokens", 0)
                total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

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
                    finish_reason=finish_reason,
                    raw_response=data,
                )
        except httpx.HTTPError as e:
            logger.error(f"OpenAI network error: {e}")
            raise ProviderUnavailableError("OpenAI", f"Network error communicating with OpenAI: {e}")

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None
    ) -> Dict[str, Any]:
        opts = options or LLMOptions()
        opts.json_mode = True
        schema_instruction = f"\nYou must output valid JSON matching this schema:\n{json.dumps(schema)}"
        augmented_messages = list(messages)
        augmented_messages.append(LLMMessage(role="user", content=schema_instruction))

        response = await self.generate(augmented_messages, opts)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode structured response: {e}")
            return {"raw": response.content, "error": "Invalid JSON produced by model"}

    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        opts = options or LLMOptions()
        model = opts.model or "gpt-4o"
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=opts.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise ProviderUnavailableError("OpenAI", f"Stream returned status {response.status_code}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    line_data = line[6:].strip()
                    if line_data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line_data)
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> HealthStatus:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    return HealthStatus(is_healthy=True, latency_ms=latency_ms, message="OpenAI API reachable")
                return HealthStatus(is_healthy=False, latency_ms=latency_ms, message=f"Status {resp.status_code}")
        except Exception as e:
            return HealthStatus(is_healthy=False, latency_ms=0, message=str(e))
