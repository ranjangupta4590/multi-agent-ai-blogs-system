"""Tests for the 11-agent blog generation workflow engine."""
import pytest
from app.ai.gateway.gateway import LLMGateway
from app.ai.providers.mock_provider import MockProvider
from app.ai.workflows.workflow_engine import BlogGenerationWorkflow


@pytest.mark.asyncio
async def test_full_11_agent_workflow_execution():
    """Verify that the full workflow runs all 11 agents sequentially using single active provider."""
    gateway = LLMGateway()
    gateway._providers.clear()
    mock_provider = MockProvider("Claude")
    gateway.register_provider(mock_provider, make_active=True)

    workflow = BlogGenerationWorkflow(gateway=gateway)
    events = []

    async def on_event(ev):
        events.append(ev)

    initial_state = {
        "topic": "Zero-Trust Architecture for Cloud Native AI Applications",
        "target_audience": "Chief Information Security Officers and Cloud Architects",
        "brand_voice": "Technical, authoritative, pragmatic",
        "content_goal": "Establish authority and educate on zero-trust LLM deployments",
        "target_keywords": ["zero-trust ai", "cloud native security", "llm gateway"],
    }

    final_state = await workflow.run(initial_state, event_callback=on_event)

    # Assertions on state
    assert final_state.get("workflow_completed") is True
    assert "content" in final_state
    assert len(final_state["content"]) > 100
    assert "title" in final_state
    assert "sources" in final_state
    assert len(final_state["sources"]) > 0
    assert "claims" in final_state
    assert len(final_state["claims"]) > 0
    assert "seo_analysis" in final_state
    assert final_state["seo_analysis"]["score"] > 0
    assert "critic_evaluation" in final_state
    assert "publish_package" in final_state
    assert final_state["status"] == "IN_REVIEW"  # Human review gate preserved!

    # Assert events were fired for all steps
    completed_events = [e for e in events if e.get("status") == "COMPLETED"]
    assert len(completed_events) >= 10
    agent_names_seen = [e["agent_name"] for e in completed_events]
    assert "ResearchPlanner" in agent_names_seen
    assert "Researcher" in agent_names_seen
    assert "SourceValidator" in agent_names_seen
    assert "WriterAgent" in agent_names_seen
    assert "FactChecker" in agent_names_seen
    assert "SEOAgent" in agent_names_seen
    assert "CriticAgent" in agent_names_seen
    assert "PublisherAgent" in agent_names_seen


@pytest.mark.asyncio
async def test_conditional_revision_loop_termination():
    """Verify that when score < threshold, Editor runs and loops do not exceed MAX_REVISION_CYCLES."""
    gateway = LLMGateway()
    gateway._providers.clear()

    # Create mock provider that forces low critic score initially
    class LowScoreMock(MockProvider):
        async def generate_structured(self, messages, schema, options=None):
            all_text = " ".join([m.content.lower() for m in messages])
            if "critic" in all_text or "critique" in all_text:
                return {
                    "score": 6.5,  # below 8.0 threshold
                    "issues": ["Expand security implications", "Clarify source citations"],
                    "strengths": ["Good topic choice"],
                }
            return await super().generate_structured(messages, schema, options)

    gateway.register_provider(LowScoreMock("Gemini"), make_active=True)
    workflow = BlogGenerationWorkflow(gateway=gateway)

    initial_state = {
        "topic": "Next-Gen AI Microservices",
        "target_audience": "Developers",
    }

    final_state = await workflow.run(initial_state)

    # Assert that revision occurred and capped at MAX_REVISION_CYCLES (2)
    assert final_state.get("revision_count") == 2
    assert final_state.get("workflow_completed") is True
