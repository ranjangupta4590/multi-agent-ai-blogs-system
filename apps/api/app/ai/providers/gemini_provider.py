"""Google Gemini provider adapter implementing LLMProvider."""
import json
import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
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


class GeminiProvider(LLMProvider):
    """Google Gemini Adapter using the Google Generative Language REST API."""

    def __init__(self, api_key: Any, base_url: str = "https://generativelanguage.googleapis.com/v1beta"):
        if isinstance(api_key, str):
            self._api_keys = [k.strip() for k in api_key.split(",") if k.strip()]
        elif isinstance(api_key, (list, tuple)):
            self._api_keys = [str(k).strip() for k in api_key if str(k).strip()]
        else:
            self._api_keys = []
        self._key_index = 0
        self.base_url = base_url.rstrip("/")

    @property
    def api_key(self) -> str:
        """Primary API key for backward compatibility."""
        return self._api_keys[0] if self._api_keys else ""

    @property
    def api_keys(self) -> List[str]:
        """All configured API keys."""
        return list(self._api_keys)

    def _get_next_api_key(self) -> str:
        """Retrieve the next API key in round-robin fashion."""
        if not self._api_keys:
            return ""
        key = self._api_keys[self._key_index % len(self._api_keys)]
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        return key

    @property
    def provider_name(self) -> str:
        return "Gemini"

    def get_models(self) -> List[str]:
        return []

    def _convert_messages(self, messages: List[LLMMessage]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        system_instruction = None
        contents = []

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        # Gemini requires at least one user message
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        return system_instruction, contents

    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> LLMResponse:
        opts = options or LLMOptions()
        model = opts.model
        if not model:
            raise ProviderUnavailableError("Gemini", "A user-configured model is required.")
        if not self._api_keys:
            raise ProviderUnavailableError("Gemini", "No API key configured for Gemini.")
        start_time = time.time()

        system_instruction, contents = self._convert_messages(messages)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": opts.temperature,
                "maxOutputTokens": opts.max_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if opts.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        retryable_statuses = {429, 500, 502, 503, 504}
        max_attempts = max(5, len(self._api_keys) * 2)
        current_key = self._get_next_api_key()

        try:
            async with httpx.AsyncClient(timeout=opts.timeout) as client:
                for attempt in range(1, max_attempts + 1):
                    url = f"{self.base_url}/models/{model}:generateContent?key={current_key}"
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        break
                    if resp.status_code in retryable_statuses and attempt < max_attempts:
                        delay_seconds = min(8, 2 ** attempt)
                        if len(self._api_keys) > 1:
                            prev_masked = current_key[:6] + "..." if len(current_key) > 6 else current_key
                            current_key = self._get_next_api_key()
                            next_masked = current_key[:6] + "..." if len(current_key) > 6 else current_key
                            logger.warning(
                                "Gemini returned status %s on key %s; rotating to next pooled key %s (attempt %s/%s) in %ss",
                                resp.status_code, prev_masked, next_masked, attempt, max_attempts, delay_seconds
                            )
                        else:
                            logger.warning(
                                "Gemini returned transient status %s (high demand/rate limit); retrying request %s/%s in %ss",
                                resp.status_code, attempt, max_attempts, delay_seconds
                            )
                        await asyncio.sleep(delay_seconds)
                        continue
                    error_detail = resp.text[:200] if resp.text else f"status {resp.status_code}"
                    logger.error("Gemini generation failed with status %s: %s", resp.status_code, error_detail)
                    raise ProviderUnavailableError(
                        "Gemini",
                        f"API returned status {resp.status_code} after {attempt} attempt(s): {error_detail}"
                    )

                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                content = ""
                parts = candidate.get("content", {}).get("parts", [])
                if parts:
                    content = parts[0].get("text", "")

                usage_meta = data.get("usageMetadata", {})
                prompt_tokens = usage_meta.get("promptTokenCount", 0)
                completion_tokens = usage_meta.get("candidatesTokenCount", 0)
                total_tokens = usage_meta.get("totalTokenCount", prompt_tokens + completion_tokens)

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
                    finish_reason=candidate.get("finishReason", "STOP"),
                    raw_response=data,
                )
        except httpx.HTTPError as e:
            logger.error(f"Gemini network error: {e}")
            raise ProviderUnavailableError("Gemini", f"Network error communicating with Gemini: {e}")

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None
    ) -> Dict[str, Any]:
        opts = options or LLMOptions()
        opts.json_mode = True
        augmented = list(messages)
        augmented.append(LLMMessage(
            role="user",
            content=f"\nFormat your response as valid JSON adhering to schema:\n{json.dumps(schema)}"
        ))
        res = await self.generate(augmented, opts)
        try:
            return json.loads(res.content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode Gemini structured response: {e}")
            return {"raw": res.content, "error": "Invalid JSON produced by model"}

    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        # Simple stream implementation via generate chunks
        res = await self.generate(messages, options)
        # Yield in sentences / chunks
        for chunk in res.content.split("\n\n"):
            yield chunk + "\n\n"

    async def health_check(self) -> HealthStatus:
        start_time = time.time()
        if not self._api_keys:
            return HealthStatus(is_healthy=False, latency_ms=0, message="No Gemini API keys configured")
        url = f"{self.base_url}/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    key_count_str = f" ({len(self._api_keys)} keys pooled)" if len(self._api_keys) > 1 else ""
                    return HealthStatus(
                        is_healthy=True,
                        latency_ms=latency_ms,
                        message=f"Gemini API reachable{key_count_str}"
                    )
                return HealthStatus(is_healthy=False, latency_ms=latency_ms, message=f"Status {resp.status_code}")
        except Exception as e:
            return HealthStatus(is_healthy=False, latency_ms=0, message=str(e))
