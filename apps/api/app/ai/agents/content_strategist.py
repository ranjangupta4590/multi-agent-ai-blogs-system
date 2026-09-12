"""Agent 4: Content Strategist - Establishes angle, audience hooks, and narrative framework."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class ContentStrategist(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("ContentStrategist", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("topic", "")
        target_audience = state.get("target_audience", "Technical professionals")
        brand_voice = state.get("brand_voice", "Authoritative, insightful, clear")
        claims = state.get("claims", [])
        accumulated_cost = state.get("total_cost_usd", 0.0)

        system_prompt = (
            "You are a master digital editorial strategist. Determine the unique angle, "
            "narrative hook, key takeaways, and audience retention strategy for this article."
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Target Audience: {target_audience}\n"
            f"Brand Voice: {brand_voice}\n"
            f"Verified Claims: {len(claims)} claims available\n\n"
            "Develop a comprehensive content strategy."
        )

        schema = {
            "type": "object",
            "properties": {
                "editorial_angle": {"type": "string"},
                "target_takeaways": {"type": "array", "items": {"type": "string"}},
                "narrative_hook": {"type": "string"},
                "tone_guidelines": {"type": "string"},
            },
            "required": ["editorial_angle", "target_takeaways", "narrative_hook"],
        }

        strategy = await self.call_llm_structured(
            system_prompt, user_prompt, schema, LLMOptions(temperature=0.5), accumulated_cost
        )

        return {
            "content_strategy": strategy,
            "current_step": "ContentStrategist_Completed",
        }
