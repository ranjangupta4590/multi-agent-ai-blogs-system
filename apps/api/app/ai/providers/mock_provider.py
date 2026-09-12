"""Mock LLM provider adapter for unit testing and offline development."""
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from app.ai.gateway.interface import (
    HealthStatus,
    LLMMessage,
    LLMOptions,
    LLMProvider,
    LLMResponse,
    TokenUsage,
)


class MockProvider(LLMProvider):
    """Simulated provider delivering deterministic, high-quality blog generation payloads."""

    def __init__(self, provider_name: str = "MockAI", should_fail: bool = False):
        self._name = provider_name
        self.should_fail = should_fail
        self.call_history: List[Dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def get_models(self) -> List[str]:
        return [f"{self._name.lower()}-standard", f"{self._name.lower()}-fast"]

    async def generate(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> LLMResponse:
        self.call_history.append({"messages": messages, "options": options})
        if self.should_fail:
            from app.core.errors import ProviderUnavailableError
            raise ProviderUnavailableError(self._name, "Simulated provider failure")

        last_prompt = messages[-1].content if messages else ""
        content = self._craft_mock_response(last_prompt)

        prompt_tokens = sum(len(m.content.split()) for m in messages) * 2
        completion_tokens = len(content.split()) * 2

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=options.model if options and options.model else "mock-v1",
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            estimated_cost_usd=0.002,
            latency_ms=45,
            finish_reason="stop",
        )

    async def generate_structured(
        self,
        messages: List[LLMMessage],
        schema: Dict[str, Any],
        options: Optional[LLMOptions] = None
    ) -> Dict[str, Any]:
        self.call_history.append({"messages": messages, "schema": schema})
        if self.should_fail:
            from app.core.errors import ProviderUnavailableError
            raise ProviderUnavailableError(self._name, "Simulated provider failure")

        last_prompt = messages[-1].content.lower() if messages else ""

        # Deliver appropriate structured output based on agent context
        if "critic" in last_prompt or "score" in str(schema):
            return {
                "score": 8.8,
                "issues": [
                    "Consider adding a more prominent call-to-action in conclusion.",
                    "Verify latency benchmark figures in section 2.",
                ],
                "strengths": ["Clear narrative structure", "Authoritative technical depth"],
                "recommendation": "APPROVE_WITH_MINOR_TWEAKS",
            }
        elif "seo" in last_prompt or "keywords" in str(schema):
            return {
                "score": 92,
                "meta_title": "Production-Grade AI Systems: Comprehensive Architectural Guide",
                "meta_description": "Discover how to build resilient, multi-agent AI systems with single-provider independence and enterprise security.",
                "slug": "production-grade-ai-systems-guide",
                "focus_keywords": ["multi-agent ai", "ai architecture", "enterprise llm"],
                "heading_hierarchy_check": True,
                "readability_score": 78.5,
                "faq_items": [
                    {
                        "question": "Can multi-agent architectures operate with only one LLM provider?",
                        "answer": "Yes. A centralized model gateway abstracts providers, allowing any single provider to power all agents."
                    }
                ],
                "schema_markup": {
                    "@context": "https://schema.org",
                    "@type": "TechArticle",
                    "headline": "Production-Grade AI Systems Guide"
                },
                "recommendations": ["Expand on cache layer implementation", "Add diagram anchor links"],
            }
        elif "search" in last_prompt or "queries" in str(schema):
            return {
                "queries": [
                    "enterprise multi-agent ai architectures 2026",
                    "llm gateway patterns provider agnostic",
                    "mitigating ssrf in autonomous research agents"
                ],
                "key_questions": [
                    "How to ensure high availability without multi-provider lock-in?",
                    "What are the best practices for source grounding in AI writing?"
                ],
                "recommended_depth": "deep"
            }
        elif "claims" in last_prompt or "validation" in str(schema):
            return {
                "validated_sources": [
                    {
                        "title": "Architectural Patterns for Resilient AI Gateways",
                        "url": "https://example.org/ai-gateways-research",
                        "domain": "example.org",
                        "credibility_score": 0.94,
                        "source_type": "RESEARCH_PAPER"
                    }
                ],
                "claims": [
                    {
                        "claim_text": "Centralized LLM gateways decouple business agents from provider SDKs.",
                        "status": "VERIFIED",
                        "confidence": 0.96
                    }
                ]
            }

        # Generic structured fallback
        return {
            "status": "success",
            "message": "Mock structured response",
            "data": {}
        }

    async def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None
    ) -> AsyncIterator[str]:
        res = await self.generate(messages, options)
        for part in res.content.split(". "):
            yield part + ". "

    async def health_check(self) -> HealthStatus:
        if self.should_fail:
            return HealthStatus(is_healthy=False, latency_ms=0, message="Simulated unhealthy")
        return HealthStatus(is_healthy=True, latency_ms=5, message="Mock provider operational")

    def _craft_mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "outline" in p_lower:
            return (
                "# Comprehensive Outline: Building Resilient AI Blog Systems\n\n"
                "## 1. Introduction & The Single-Provider Imperative (Target: 300 words)\n"
                "- The trap of multi-provider lock-in\n"
                "- Core principles of provider independence\n\n"
                "## 2. Model Gateway Architecture (Target: 500 words)\n"
                "- Centralized dispatch and adapter abstraction\n"
                "- Dynamic routing and zero secret exposure\n\n"
                "## 3. Autonomous 11-Agent Content Pipeline (Target: 600 words)\n"
                "- Research, verification, writing, and editorial critique\n"
                "- Safe revision feedback loops\n\n"
                "## 4. Enterprise Security & SSRF Mitigation (Target: 400 words)\n"
                "- Network-level egress filtering\n"
                "- Immutable audit trails\n\n"
                "## 5. Conclusion & Actionable Takeaways (Target: 250 words)\n"
            )
        elif "write" in p_lower or "article" in p_lower:
            return (
                "# The Modern Architecture of Resilient Multi-Agent AI Systems\n\n"
                "### Abstract\n"
                "Modern autonomous agent systems often suffer from architectural brittleness "
                "when tightly coupled to multiple heterogeneous LLM vendors. This article demonstrates "
                "a robust, provider-agnostic framework capable of full operational autonomy with a single provider [Source 1].\n\n"
                "## 1. The Single-Provider Principle in Practice\n"
                "A common architectural antipattern mandates OpenAI for planning, Claude for writing, "
                "and Gemini for fact-checking. When any single API suffers downtime or billing hiccups, "
                "the entire pipeline halts. In contrast, an enterprise-grade platform standardizes "
                "agent interfaces behind a unified **LLMGateway**, allowing any individual provider "
                "to reliably execute all 11 stages of the workflow.\n\n"
                "## 2. Egress Defense and Autonomous Source Grounding\n"
                "Autonomous research agents must never blindly ingest unvalidated web pages. "
                "By enforcing strict IP address blocklists against loopback and cloud metadata endpoints (e.g. 169.254.169.254), "
                "the system eliminates Server-Side Request Forgery (SSRF) threats while collecting authoritative evidence [Source 2].\n\n"
                "## 3. Conclusion\n"
                "By embracing strict gateway abstractions, comprehensive fact verification, and human-in-the-loop "
                "publishing safeguards, modern organizations can scale authoritative content operations safely."
            )
        elif "revise" in p_lower or "editor" in p_lower:
            return (
                "# The Modern Architecture of Resilient Multi-Agent AI Systems (Revised Edition)\n\n"
                "### Abstract\n"
                "Modern autonomous agent systems often suffer from architectural brittleness "
                "when tightly coupled to multiple heterogeneous LLM vendors. This revised edition provides "
                "concrete benchmarks, expanded security paradigms, and clear actionable takeaways [Source 1].\n\n"
                "## 1. The Single-Provider Principle in Practice\n"
                "A robust model gateway provides complete abstraction, ensuring uninterrupted generation "
                "whether running purely on OpenAI, Gemini, Claude, or Grok."
            )
        return "Comprehensive analysis and generated intelligence completed successfully."
