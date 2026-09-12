"""Agent 6: Writer Agent - Drafts long-form, authoritative blog content with source citations."""
from typing import Any, Dict
from app.ai.agents.base import BaseAgent
from app.ai.gateway.interface import LLMOptions


class WriterAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("WriterAgent", gateway)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("topic", "")
        brand_voice = state.get("brand_voice", "Professional, clear, authoritative")
        outline_text = state.get("outline_text", "")
        sources = state.get("sources", [])
        claims = state.get("claims", [])
        accumulated_cost = state.get("total_cost_usd", 0.0)

        sources_context = "\n".join([
            f"[Source {i+1}]: {s.get('title')} ({s.get('domain')}) - {s.get('url')}"
            for i, s in enumerate(sources)
        ])

        system_prompt = (
            "You are an elite, award-winning technology and business writer. "
            "Write a thorough, deeply engaging, authoritative article in Markdown format. "
            "Incorporate factual claims and attribute facts with citations like [Source 1], [Source 2]. "
            "Do not write fluff or filler. Use clear headings (H1, H2, H3), bullet points, and code or architecture diagrams if relevant."
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Brand Voice: {brand_voice}\n\n"
            f"Outline:\n{outline_text}\n\n"
            f"Available Sources for Citations:\n{sources_context}\n\n"
            "Produce the complete, comprehensive article draft now."
        )

        resp = await self.call_llm(
            system_prompt, user_prompt, LLMOptions(temperature=0.6, max_tokens=4000), accumulated_cost
        )

        content = resp.content
        words = len(content.split())
        reading_time = max(1, round(words / 200))

        # Derive title from content or topic
        title = f"{topic}: The Definitive Enterprise Guide"
        lines = content.strip().splitlines()
        for line in lines:
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break

        return {
            "title": title,
            "content": content,
            "word_count": words,
            "estimated_reading_time": reading_time,
            "generated_by_provider": resp.provider,
            "generated_by_model": resp.model,
            "total_cost_usd": accumulated_cost + resp.estimated_cost_usd,
            "current_step": "WriterAgent_Completed",
        }
