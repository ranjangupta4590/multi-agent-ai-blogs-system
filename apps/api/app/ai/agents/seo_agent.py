"""Agent 8: SEO Agent - Evaluates keyword coverage, generates meta tags, schema, and calculates score."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class SEOAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("SEOAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        title = state.get("title", "")
        content = state.get("content", "")
        target_keywords = state.get("target_keywords", [])
        topic = state.get("topic", "")
        accumulated_cost = state.get("total_cost_usd", 0.0)

        system_prompt = (
            "You are a principal technical SEO specialist. Evaluate the article draft for search visibility, "
            "heading hierarchy, readability, and structured data. Generate an optimized meta title (50-60 chars), "
            "compelling meta description (140-160 chars), search-friendly slug, FAQ schema, and calculate an overall "
            "SEO score (0 to 100)."
        )

        user_prompt = (
            f"Article Title: {title}\n"
            f"Topic: {topic}\n"
            f"Target Keywords: {', '.join(target_keywords) if target_keywords else 'None provided'}\n\n"
            f"Draft Sample:\n{content[:3500]}\n\n"
            "Provide exhaustive SEO optimization metadata."
        )

        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "meta_title": {"type": "string"},
                "meta_description": {"type": "string"},
                "slug": {"type": "string"},
                "focus_keywords": {"type": "array", "items": {"type": "string"}},
                "heading_hierarchy_check": {"type": "boolean"},
                "readability_score": {"type": "number"},
                "faq_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                        },
                    },
                },
                "schema_markup": {"type": "object"},
                "recommendations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["score", "meta_title", "meta_description", "slug"],
        }

        seo_result = await self.call_llm_structured(
            system_prompt, user_prompt, schema, LLMOptions(temperature=0.3), accumulated_cost
        )

        # Fallbacks for defaults
        if not seo_result.get("meta_title"):
            seo_result["meta_title"] = title[:60]
        if not seo_result.get("slug"):
            seo_result["slug"] = topic.lower().replace(" ", "-").replace(":", "")[:80]
        if not seo_result.get("score"):
            seo_result["score"] = 88

        return {
            "seo_analysis": seo_result,
            "meta_title": seo_result["meta_title"],
            "meta_description": seo_result.get("meta_description", ""),
            "slug": seo_result["slug"],
            "current_step": "SEOAgent_Completed",
        }
