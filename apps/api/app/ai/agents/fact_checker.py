"""Agent 7: Fact Checker - Audits draft claims against verified grounding sources."""
from typing import Any, Dict, List
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class FactChecker(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("FactChecker", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        content = state.get("content", "")
        sources = state.get("sources", [])
        accumulated_cost = state.get("total_cost_usd", 0.0)

        sources_summary = "\n".join([
            f"[{s.get('domain')}]: {s.get('title')} - {s.get('snippet', '')}"
            for s in sources
        ])

        system_prompt = (
            "You are an uncompromising, independent fact checker. Extract key factual assertions "
            "from the article draft and audit them against the verified source corpus. "
            "Assign each claim a status: VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or CONTRADICTED."
        )

        user_prompt = (
            f"Article Draft:\n{content[:4000]}\n\n"
            f"Source Evidence Corpus:\n{sources_summary}\n\n"
            "Analyze and verify the factual assertions."
        )

        schema = {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string"},
                            "status": {"type": "string", "enum": ["VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"]},
                            "confidence": {"type": "number"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "accuracy_rating": {"type": "number"},
            },
            "required": ["claims", "accuracy_rating"],
        }

        fact_check_result = await self.call_llm_structured(
            system_prompt, user_prompt, schema, LLMOptions(temperature=0.1), accumulated_cost
        )

        claims = fact_check_result.get("claims", state.get("claims", []))
        return {
            "claims": claims,
            "fact_check_rating": fact_check_result.get("accuracy_rating", 95.0),
            "current_step": "FactChecker_Completed",
        }
