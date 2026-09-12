"""Agent 5: Outline Agent - Creates comprehensive hierarchical outline with word targets."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class OutlineAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("OutlineAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("topic", "")
        strategy = state.get("content_strategy", {})
        claims = state.get("claims", [])
        accumulated_cost = state.get("total_cost_usd", 0.0)

        system_prompt = (
            "You are an expert editorial architect. Design a comprehensive markdown outline (H1, H2, H3) "
            "with explicit section goals, key arguments, and target word counts."
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Strategy Angle: {strategy.get('editorial_angle', 'In-depth analysis')}\n"
            f"Narrative Hook: {strategy.get('narrative_hook', '')}\n"
            f"Key Claims: {len(claims)} verified facts\n\n"
            "Build the complete outline."
        )

        resp = await self.call_llm(
            system_prompt, user_prompt, LLMOptions(temperature=0.4), accumulated_cost
        )

        return {
            "outline": {"markdown_outline": resp.content},
            "outline_text": resp.content,
            "total_cost_usd": accumulated_cost + resp.estimated_cost_usd,
            "current_step": "OutlineAgent_Completed",
        }
