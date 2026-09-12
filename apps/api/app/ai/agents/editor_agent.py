"""Agent 10: Editor Agent - Refines and revises draft to address critic issues."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class EditorAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("EditorAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        content = state.get("content", "")
        issues = state.get("critic_issues", [])
        revision_count = state.get("revision_count", 0)
        accumulated_cost = state.get("total_cost_usd", 0.0)

        issues_formatted = "\n".join([f"- {iss}" for iss in issues])

        system_prompt = (
            "You are a meticulous senior revision editor. Elevate and polish the article draft, "
            "directly and systematically resolving every editorial issue raised by the critic. "
            "Ensure prose is seamless, engaging, and maintains technical authority without losing citations."
        )

        user_prompt = (
            f"Critic Issues Identified:\n{issues_formatted}\n\n"
            f"Original Draft:\n{content}\n\n"
            "Produce the revised, elevated article now."
        )

        resp = await self.call_llm(
            system_prompt, user_prompt, LLMOptions(temperature=0.5, max_tokens=4000), accumulated_cost
        )

        new_revision_count = revision_count + 1
        new_content = resp.content
        words = len(new_content.split())

        return {
            "content": new_content,
            "word_count": words,
            "revision_count": new_revision_count,
            "current_version": state.get("current_version", 1) + 1,
            "total_cost_usd": accumulated_cost + resp.estimated_cost_usd,
            "current_step": f"EditorAgent_Revision_{new_revision_count}_Completed",
        }
