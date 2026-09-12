"""BaseAgent abstraction ensuring all agents interface exclusively through LLMGateway."""
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.ai.gateway.gateway import LLMGateway, llm_gateway
from app.ai.gateway.interface import LLMMessage, LLMOptions, LLMResponse
from app.core.logging import logger


class BaseAgent(ABC):
    """
    Abstract base agent.
    All agents depend on LLMGateway and remain completely agnostic to the underlying provider.
    """

    def __init__(self, name: str, gateway: Optional[LLMGateway] = None):
        self.name = name
        self.gateway = gateway or llm_gateway

    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's task given current workflow state, returning updated state slice."""
        pass

    def sanitize_untrusted_input(self, raw_text: str) -> str:
        """
        Prompt Injection Defense: Wrap untrusted external data (e.g. web pages)
        in strict data boundaries so the model treats it solely as factual text.
        """
        # Escape potential delimiter breaking
        cleaned = raw_text.replace("</untrusted_external_content>", "")
        return f"<untrusted_external_content>\n{cleaned}\n</untrusted_external_content>"

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        options: Optional[LLMOptions] = None,
        accumulated_cost: float = 0.0,
    ) -> LLMResponse:
        """Execute an LLM call through the gateway."""
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        logger.info(f"Agent '{self.name}' invoking LLM via active provider '{self.gateway.active_provider_name}'")
        return await self.gateway.generate(messages, options, accumulated_article_cost=accumulated_cost)

    async def call_llm_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None,
        accumulated_cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Execute a structured LLM call through the gateway."""
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        logger.info(f"Agent '{self.name}' invoking structured LLM via active provider '{self.gateway.active_provider_name}'")
        return await self.gateway.generate_structured(
            messages, schema, options, accumulated_article_cost=accumulated_cost
        )
