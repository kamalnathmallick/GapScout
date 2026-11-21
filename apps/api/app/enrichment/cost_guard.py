"""Cost tracking and workspace daily budget enforcement for LLM operations."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LLMUsageLog

logger = logging.getLogger(__name__)

# Model pricing in USD per 1,000,000 tokens
MODEL_PRICING: dict[str, dict[str, float]] = {
    "flash": {"prompt": 0.15, "completion": 0.60},
    "pro": {"prompt": 1.25, "completion": 5.00},
    "gemini": {"prompt": 0.15, "completion": 0.60},
    "haiku": {"prompt": 0.80, "completion": 4.00},
    "sonnet": {"prompt": 3.00, "completion": 15.00},
    "default": {"prompt": 0.50, "completion": 2.00},
}


class CostCapExceededError(RuntimeError):
    """Raised when an operation would exceed the workspace's daily spending limit."""

    pass


def calculate_cost_usd(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate USD cost for a given token usage."""
    model_lower = model_name.lower()
    if "flash" in model_lower:
        pricing = MODEL_PRICING["flash"]
    elif "sonnet" in model_lower:
        pricing = MODEL_PRICING["sonnet"]
    elif "pro" in model_lower:
        pricing = MODEL_PRICING["pro"]
    elif "haiku" in model_lower:
        pricing = MODEL_PRICING["haiku"]
    elif "gemini" in model_lower:
        pricing = MODEL_PRICING["gemini"]
    else:
        pricing = MODEL_PRICING["default"]

    prompt_cost = (prompt_tokens / 1_000_000.0) * pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * pricing["completion"]
    return round(prompt_cost + completion_cost, 6)


def get_workspace_today_spend(session: Session, workspace_id: uuid.UUID) -> float:
    """Calculate the total USD spent by this workspace today (UTC)."""
    now = datetime.now(UTC)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=UTC)

    spend = session.execute(
        select(func.coalesce(func.sum(LLMUsageLog.cost_usd), 0.0)).where(
            LLMUsageLog.workspace_id == workspace_id,
            LLMUsageLog.created_at >= start_of_today,
        )
    ).scalar_one()

    return float(spend)


def check_workspace_daily_cap(
    session: Session,
    workspace_id: uuid.UUID,
    daily_cap_usd: float | None = None,
) -> float:
    """Ensure workspace has not exceeded its daily LLM spending limit."""
    if daily_cap_usd is None:
        settings = get_settings()
        daily_cap_usd = float(settings.llm_daily_cost_cap_usd)

    current_spend = get_workspace_today_spend(session, workspace_id)
    if current_spend >= daily_cap_usd:
        msg = (
            f"Workspace {workspace_id} has exceeded its daily LLM cost cap "
            f"(${current_spend:.4f} >= ${daily_cap_usd:.2f}). Further LLM enrichment is paused."
        )
        logger.warning(msg)
        raise CostCapExceededError(msg)

    return current_spend


def record_llm_usage(
    session: Session,
    workspace_id: uuid.UUID,
    model: str,
    kind: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Record LLM token consumption and cost in llm_usage_logs."""
    cost_usd = calculate_cost_usd(model, prompt_tokens, completion_tokens)
    log_entry = LLMUsageLog(
        workspace_id=workspace_id,
        model=model,
        kind=kind,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )
    session.add(log_entry)
    session.flush()
    return cost_usd
