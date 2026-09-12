"""AI Budget Control and Token Cost Estimation."""
from typing import Dict, Tuple
from app.core.config import settings
from app.core.errors import BudgetExceededError

# Rates: (Input cost per 1M tokens in USD, Output cost per 1M tokens in USD)
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Gemini
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    # Claude
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    # Grok
    "grok-2": (2.00, 10.00),
    "grok-2-mini": (0.50, 2.50),
    # Fallback default
    "default": (2.00, 8.00),
}


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate the estimated USD cost for an LLM invocation."""
    pricing = MODEL_PRICING.get(model_name.lower(), MODEL_PRICING["default"])
    input_rate, output_rate = pricing

    input_cost = (prompt_tokens / 1_000_000.0) * input_rate
    output_cost = (completion_tokens / 1_000_000.0) * output_rate
    return round(input_cost + output_cost, 6)


def enforce_article_budget(accumulated_cost: float, new_cost: float = 0.0) -> None:
    """Enforce maximum cost ceiling per article."""
    projected = accumulated_cost + new_cost
    if projected > settings.MAX_COST_PER_ARTICLE_USD:
        raise BudgetExceededError(
            f"Article AI budget cap reached (${settings.MAX_COST_PER_ARTICLE_USD:.2f}). "
            f"Total spent so far: ${accumulated_cost:.4f}. Operation stopped."
        )
