"""Centralized LLMGateway orchestrating multi-provider compatibility and single-provider operations."""
from typing import Any, AsyncIterator, Dict, List, Optional
from app.ai.gateway.budget import enforce_article_budget
from app.ai.gateway.interface import (
    HealthStatus,
    LLMMessage,
    LLMOptions,
    LLMProvider,
    LLMResponse,
)
from app.ai.providers.anthropic_provider import ClaudeProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.grok_provider import GrokProvider
from app.ai.providers.mock_provider import MockProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import settings
from app.core.errors import NoProviderConfiguredError, ProviderUnavailableError
from app.core.logging import logger


class LLMGateway:
    """
    Centralized model gateway that decouples all autonomous agents from underlying providers.
    Guarantees complete single-provider operational independence.
    """

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._active_provider_name: Optional[str] = None
        self._active_model_name: Optional[str] = None
        self._fallback_enabled: bool = settings.FALLBACK_ENABLED
        self._fallback_provider_name: Optional[str] = settings.FALLBACK_PROVIDER
        self._bootstrap_providers()

    def _bootstrap_providers(self) -> None:
        """Initialize provider adapters based on configured server-side credentials."""
        if settings.OPENAI_API_KEY:
            self._providers["OpenAI"] = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
        if settings.GEMINI_API_KEY:
            self._providers["Gemini"] = GeminiProvider(api_key=settings.GEMINI_API_KEY)
        if settings.ANTHROPIC_API_KEY:
            self._providers["Claude"] = ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY)
        if settings.XAI_API_KEY:
            self._providers["Grok"] = GrokProvider(api_key=settings.XAI_API_KEY)

        # Determine default active provider
        if settings.ACTIVE_PROVIDER and settings.ACTIVE_PROVIDER in self._providers:
            self._active_provider_name = settings.ACTIVE_PROVIDER
        elif self._providers:
            # Pick first available provider automatically
            self._active_provider_name = next(iter(self._providers.keys()))
        else:
            self._active_provider_name = None

    def register_provider(self, provider: LLMProvider, make_active: bool = False) -> None:
        """Register a provider instance (useful for runtime configuration and tests)."""
        self._providers[provider.provider_name] = provider
        if make_active or not self._active_provider_name:
            self._active_provider_name = provider.provider_name

    def unregister_provider(self, provider_name: str) -> None:
        """Remove a provider registration."""
        self._providers.pop(provider_name, None)
        if self._active_provider_name == provider_name:
            self._active_provider_name = next(iter(self._providers.keys())) if self._providers else None

    def set_active_provider(self, provider_name: str, model_name: Optional[str] = None) -> None:
        """Set the active provider and optional model."""
        if provider_name not in self._providers:
            raise ProviderUnavailableError(provider_name, f"Provider '{provider_name}' is not configured on this server.")
        self._active_provider_name = provider_name
        self._active_model_name = model_name
        logger.info(f"Active AI provider switched to: {provider_name} (Model: {model_name})")

    @property
    def active_provider_name(self) -> Optional[str]:
        return self._active_provider_name

    @property
    def active_model_name(self) -> Optional[str]:
        return self._active_model_name

    def is_operational(self) -> bool:
        """True if at least one AI provider is configured and available."""
        return bool(self._providers and self._active_provider_name)

    def get_configured_providers(self) -> List[str]:
        """Return names of all configured providers."""
        return list(self._providers.keys())

    def get_provider_metadata(self) -> List[Dict[str, Any]]:
        """
        Return safe status metadata for UI. NEVER exposes keys or credentials.
        """
        all_known = ["OpenAI", "Gemini", "Claude", "Grok"]
        result = []
        for name in all_known:
            is_configured = name in self._providers
            is_active = (name == self._active_provider_name)
            models = self._providers[name].get_models() if is_configured else []
            default_m = getattr(settings, f"DEFAULT_{name.upper()}_MODEL", "standard")
            
            result.append({
                "name": name,
                "display_name": f"{name} Provider",
                "is_active": is_active,
                "is_enabled": is_configured,
                "default_model": default_m,
                "connection_status": "CONNECTED" if is_configured else "NOT_CONFIGURED",
                "available_models": models,
            })
        return result

    def _resolve_active_provider(self) -> LLMProvider:
        """Resolve the active provider or raise NoProviderConfiguredError."""
        if not self._active_provider_name or self._active_provider_name not in self._providers:
            if self._providers:
                self._active_provider_name = next(iter(self._providers.keys()))
                return self._providers[self._active_provider_name]
            raise NoProviderConfiguredError(
                "No AI provider configured. Configure at least one AI provider (OpenAI, Gemini, Claude, or Grok) to start generating content."
            )
        return self._providers[self._active_provider_name]

    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None,
        accumulated_article_cost: float = 0.0,
    ) -> LLMResponse:
        """Generate response via active provider with retry and budget enforcement."""
        enforce_article_budget(accumulated_article_cost)
        opts = options or LLMOptions()
        if self._active_model_name and not opts.model:
            opts.model = self._active_model_name

        provider = self._resolve_active_provider()
        try:
            response = await provider.generate(messages, opts)
            enforce_article_budget(accumulated_article_cost, response.estimated_cost_usd)
            return response
        except Exception as primary_error:
            logger.warning(f"Primary provider '{provider.provider_name}' failed: {primary_error}")
            
            # Check if explicit fallback is enabled
            if self._fallback_enabled and self._fallback_provider_name in self._providers:
                fallback = self._providers[self._fallback_provider_name]
                logger.info(f"Attempting configured fallback provider: {fallback.provider_name}")
                response = await fallback.generate(messages, opts)
                return response
            
            # Fallback not enabled or unavailable; propagate clean domain error
            if isinstance(primary_error, (NoProviderConfiguredError, ProviderUnavailableError)):
                raise
            raise ProviderUnavailableError(
                provider.provider_name,
                f"The active provider '{provider.provider_name}' failed: {str(primary_error)}"
            )

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None,
        accumulated_article_cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Generate structured JSON payload via active provider."""
        enforce_article_budget(accumulated_article_cost)
        opts = options or LLMOptions()
        if self._active_model_name and not opts.model:
            opts.model = self._active_model_name

        provider = self._resolve_active_provider()
        try:
            return await provider.generate_structured(messages, schema, opts)
        except Exception as e:
            if self._fallback_enabled and self._fallback_provider_name in self._providers:
                fallback = self._providers[self._fallback_provider_name]
                return await fallback.generate_structured(messages, schema, opts)
            if isinstance(e, (NoProviderConfiguredError, ProviderUnavailableError)):
                raise
            raise ProviderUnavailableError(
                provider.provider_name,
                f"Structured generation on '{provider.provider_name}' failed: {str(e)}"
            )

    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        """Stream chunks from active provider."""
        provider = self._resolve_active_provider()
        async for chunk in provider.stream(messages, options):
            yield chunk

    async def check_provider_health(self, provider_name: str) -> HealthStatus:
        """Run health check against specific provider."""
        if provider_name not in self._providers:
            return HealthStatus(is_healthy=False, latency_ms=0, message="Provider not configured")
        return await self._providers[provider_name].health_check()


# Global singleton instance of the LLM Gateway
llm_gateway = LLMGateway()
