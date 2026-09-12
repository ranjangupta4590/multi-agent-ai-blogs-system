"""Agent 1: Research Planner - Deconstructs topic into targeted search queries."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class ResearchPlanner(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("ResearchPlanner", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("topic", "")
        target_audience = state.get("target_audience", "General audience")
        content_goal = state.get("content_goal", "Educate and inform")
        accumulated_cost = state.get("total_cost_usd", 0.0)

        system_prompt = (
            "You are an elite research director. Your mission is to analyze the user's blog topic "
            "and create a structured research plan with specific search queries, factual questions, "
            "and authoritative source types."
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Target Audience: {target_audience}\n"
            f"Content Goal: {content_goal}\n\n"
            "Return a structured research plan with search queries to gather authoritative evidence."
        )

        schema = {
            "type": "object",
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}},
                "key_questions": {"type": "array", "items": {"type": "string"}},
                "recommended_depth": {"type": "string"},
            },
            "required": ["queries", "key_questions"],
        }

        plan_data = await self.call_llm_structured(
            system_prompt, user_prompt, schema, LLMOptions(temperature=0.3), accumulated_cost
        )

        queries = plan_data.get("queries", [f"{topic} best practices", f"{topic} architecture"])
        return {
            "research_queries": queries,
            "research_questions": plan_data.get("key_questions", []),
            "current_step": "ResearchPlanner_Completed",
        }
