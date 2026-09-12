"""Agent 11: Publisher Agent - Prepares publication bundle and enforces human review gate."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent


class PublisherAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("PublisherAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        title = state.get("title", "")
        content = state.get("content", "")
        slug = state.get("slug", "")
        seo = state.get("seo_analysis", {})
        human_approved = state.get("human_approved", False)

        # Prepare formatted publish package
        publish_package = {
            "title": title,
            "slug": slug,
            "markdown_content": content,
            "meta_description": seo.get("meta_description", ""),
            "meta_title": seo.get("meta_title", title),
            "keywords": seo.get("focus_keywords", []),
            "faq_items": seo.get("faq_items", []),
            "schema_markup": seo.get("schema_markup", {}),
            "human_approval_required": not human_approved,
        }

        target_status = "PUBLISHED" if human_approved else "IN_REVIEW"

        return {
            "publish_package": publish_package,
            "status": target_status,
            "current_step": "PublisherAgent_Completed",
        }
