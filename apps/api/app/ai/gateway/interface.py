"""LLM Gateway interface contracts and data classes."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class LLMOptions:
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: float = 60.0
    json_mode: bool = False


@dataclass
class HealthStatus:
    is_healthy: bool
    latency_ms: int = 0
    message: str = "OK"


class LLMProvider(ABC):
    """Abstract interface implemented by each AI provider adapter."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'OpenAI', 'Gemini', 'Claude', 'Grok')."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> LLMResponse:
        """Generate a response for a sequence of chat messages."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON conforming to the given schema."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        """Stream chunks of response text."""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Execute a lightweight connectivity health check."""
        pass

    @abstractmethod
    def get_models(self) -> List[str]:
        """Return list of supported model identifiers."""
        pass
