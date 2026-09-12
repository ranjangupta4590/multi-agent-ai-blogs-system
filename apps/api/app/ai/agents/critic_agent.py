"""Agent 9: Critic Agent - Evaluates draft quality and issues score from 0.0 to 10.0."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions
from app.core.config import settings


class CriticAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("CriticAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        content = state.get("content", "")
        title = state.get("title", "")
        seo_analysis = state.get("seo_analysis", {})
        revision_count = state.get("revision_count", 0)
        accumulated_cost = state.get("total_cost_usd", 0.0)

        system_prompt = (
            "You are a demanding executive editor-in-chief. Evaluate the blog post on a scale of 0.0 to 10.0. "
            "Assess depth, clarity, accuracy, formatting, engagement, and actionable value. "
            "Return a rigorous score and a list of specific issues that need improvement."
        )

        user_prompt = (
            f"Title: {title}\n"
            f"Current Revision Cycle: {revision_count}\n"
            f"SEO Score: {seo_analysis.get('score', 'N/A')}\n\n"
            f"Article Draft:\n{content[:4000]}\n\n"
            "Critic evaluation: provide critical assessment and scoring."
        )

        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "issues": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["score", "issues"],
        }

        eval_result = await self.call_llm_structured(
            system_prompt, user_prompt, schema, LLMOptions(temperature=0.2), accumulated_cost
        )

        score = float(eval_result.get("score", 8.5))
        issues = eval_result.get("issues", [])

        # Check against passing threshold
        needs_revision = (score < settings.CRITIC_PASSING_SCORE) and (revision_count < settings.MAX_REVISION_CYCLES)

        return {
            "critic_evaluation": {
                "score": score,
                "issues": issues,
                "strengths": eval_result.get("strengths", []),
                "needs_revision": needs_revision,
            },
            "critic_score": score,
            "critic_issues": issues,
            "needs_revision": needs_revision,
            "current_step": "CriticAgent_Completed",
        }
