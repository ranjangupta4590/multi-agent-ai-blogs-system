"""Autonomous 11-agent blog generation workflow orchestrator."""
import asyncio
import time
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from app.ai.agents import (
    ResearchPlanner,
    Researcher,
    SourceValidator,
    ContentStrategist,
    OutlineAgent,
    WriterAgent,
    FactChecker,
    SEOAgent,
    CriticAgent,
    EditorAgent,
    PublisherAgent,
)
from app.ai.gateway.gateway import LLMGateway, llm_gateway
from app.core.config import settings
from app.core.logging import logger


class BlogGenerationWorkflow:
    """
    Orchestrates the end-to-end 11-agent pipeline.
    Maintains workflow state, emits progress events, and executes conditional revision loops.
    """

    def __init__(self, gateway: Optional[LLMGateway] = None):
        self.gateway = gateway or llm_gateway
        self.research_planner = ResearchPlanner(self.gateway)
        self.researcher = Researcher(self.gateway)
        self.source_validator = SourceValidator(self.gateway)
        self.content_strategist = ContentStrategist(self.gateway)
        self.outline_agent = OutlineAgent(self.gateway)
        self.writer = WriterAgent(self.gateway)
        self.fact_checker = FactChecker(self.gateway)
        self.seo_agent = SEOAgent(self.gateway)
        self.critic = CriticAgent(self.gateway)
        self.editor = EditorAgent(self.gateway)
        self.publisher = PublisherAgent(self.gateway)

    async def execute_step(
        self,
        step_number: int,
        agent_name: str,
        agent_fn: Callable[[Dict[str, Any]], Any],
        state: Dict[str, Any],
        event_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single agent step with timing, telemetry, and event callback."""
        start_time = time.time()
        if event_callback:
            await self._safe_callback(event_callback, {
                "step_number": step_number,
                "agent_name": agent_name,
                "status": "RUNNING",
                "timestamp": time.time(),
            })

        logger.info(f"[Workflow Step {step_number}] Starting agent '{agent_name}'")
        output = await agent_fn(state)
        duration_ms = int((time.time() - start_time) * 1000)

        # Merge output into state
        state.update(output)

        if event_callback:
            await self._safe_callback(event_callback, {
                "step_number": step_number,
                "agent_name": agent_name,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "step_summary": output.get("current_step", ""),
                "timestamp": time.time(),
            })

        logger.info(f"[Workflow Step {step_number}] Completed '{agent_name}' in {duration_ms}ms")
        return state

    async def _safe_callback(self, cb: Callable, event: Dict[str, Any]) -> None:
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(event)
            else:
                cb(event)
        except Exception as e:
            logger.warning(f"Event callback error: {e}")

    async def run(
        self,
        initial_state: Dict[str, Any],
        event_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full 11-agent pipeline from topic to publishing review.
        """
        state = dict(initial_state)
        state.setdefault("revision_count", 0)
        state.setdefault("total_cost_usd", 0.0)
        state.setdefault("current_version", 1)

        # Step 1: Research Planner
        await self.execute_step(1, "ResearchPlanner", self.research_planner.run, state, event_callback)

        # Step 2: Researcher
        await self.execute_step(2, "Researcher", self.researcher.run, state, event_callback)

        # Step 3: Source Validator
        await self.execute_step(3, "SourceValidator", self.source_validator.run, state, event_callback)

        # Step 4: Content Strategist
        await self.execute_step(4, "ContentStrategist", self.content_strategist.run, state, event_callback)

        # Step 5: Outline Agent
        await self.execute_step(5, "OutlineAgent", self.outline_agent.run, state, event_callback)

        # Step 6: Writer
        await self.execute_step(6, "WriterAgent", self.writer.run, state, event_callback)

        # Step 7: Fact Checker
        await self.execute_step(7, "FactChecker", self.fact_checker.run, state, event_callback)

        # Step 8: SEO Agent
        await self.execute_step(8, "SEOAgent", self.seo_agent.run, state, event_callback)

        # Step 9: Critic
        await self.execute_step(9, "CriticAgent", self.critic.run, state, event_callback)

        # Step 10: Conditional Revision Loop (Editor -> Critic)
        # Prevents infinite loops by bounding with MAX_REVISION_CYCLES
        revision_step = 10
        while state.get("needs_revision", False) and state.get("revision_count", 0) < settings.MAX_REVISION_CYCLES:
            logger.info(
                f"Critic score ({state.get('critic_score')}) below threshold ({settings.CRITIC_PASSING_SCORE}). "
                f"Starting revision cycle {state.get('revision_count') + 1}."
            )
            # Editor step
            await self.execute_step(revision_step, "EditorAgent", self.editor.run, state, event_callback)
            revision_step += 1
            # Re-run Critic
            await self.execute_step(revision_step, "CriticAgent", self.critic.run, state, event_callback)
            revision_step += 1

        # Step 11: Publisher Agent (Human review gate)
        final_step = revision_step
        await self.execute_step(final_step, "PublisherAgent", self.publisher.run, state, event_callback)

        state["workflow_completed"] = True
        return state
