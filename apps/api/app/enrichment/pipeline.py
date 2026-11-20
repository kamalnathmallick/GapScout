"""Enrichment orchestration pipeline for leads and jobs with budget caps."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.anthropic_client import AnthropicClient
from app.enrichment.cost_guard import CostCapExceededError, check_workspace_daily_cap
from app.enrichment.reviews import extract_place_review_themes
from app.enrichment.website import audit_place_website
from app.models import Lead, Place, SearchJob
from app.scoring.pipeline import score_workspace_leads

logger = logging.getLogger(__name__)


def enrich_lead(
    session: Session,
    lead_id: uuid.UUID,
    force: bool = False,
    anthropic_client: AnthropicClient | None = None,
) -> dict[str, Any]:
    """Perform website audit and review themes extraction for a single lead."""
    lead = session.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    check_workspace_daily_cap(session, lead.workspace_id)

    place = session.execute(select(Place).where(Place.id == lead.place_id)).scalar_one_or_none()
    if not place:
        raise ValueError(f"Place {lead.place_id} for Lead {lead_id} not found")

    result: dict[str, Any] = {
        "lead_id": str(lead.id),
        "place_id": str(place.id),
        "website_audit": None,
        "review_themes": None,
    }

    # 1. Website audit
    if place.website:
        try:
            audit, cached = audit_place_website(
                session=session,
                place=place,
                force=force,
                anthropic_client=anthropic_client,
            )
            result["website_audit"] = {"data": audit, "cached": cached}
        except CostCapExceededError:
            raise
        except Exception as e:
            logger.warning("Website audit failed for place %s: %s", place.id, e)
            result["website_audit"] = {"error": str(e)}

    # 2. Review themes
    try:
        themes, cached = extract_place_review_themes(
            session=session,
            place=place,
            force=force,
            anthropic_client=anthropic_client,
        )
        result["review_themes"] = {"data": themes, "cached": cached}
    except CostCapExceededError:
        raise
    except Exception as e:
        logger.warning("Review themes extraction failed for place %s: %s", place.id, e)
        result["review_themes"] = {"error": str(e)}

    # 3. Update lead score with the newly populated features
    score_workspace_leads(session, lead.workspace_id, place_ids=[place.id])

    return result


def enrich_job_leads(
    session: Session,
    job_id: uuid.UUID,
    min_rule_score: float = 60.0,
    max_leads_to_enrich: int = 50,
) -> int:
    """Batch enrich high-scoring leads for a job, stopping gracefully if cost cap is hit."""
    job = session.execute(select(SearchJob).where(SearchJob.id == job_id)).scalar_one_or_none()
    if not job:
        return 0

    try:
        check_workspace_daily_cap(session, job.workspace_id)
    except CostCapExceededError as e:
        logger.warning("Daily cost cap reached for workspace %s: %s", job.workspace_id, e)
        return 0

    # Query leads for this job's workspace with high rule score
    leads = (
        session.execute(
            select(Lead)
            .where(
                Lead.workspace_id == job.workspace_id,
                Lead.rule_score >= min_rule_score,
            )
            .order_by(Lead.rule_score.desc())
            .limit(max_leads_to_enrich)
        )
        .scalars()
        .all()
    )

    enriched_count = 0
    client = AnthropicClient()

    for lead in leads:
        try:
            enrich_lead(session, lead.id, force=False, anthropic_client=client)
            enriched_count += 1
        except CostCapExceededError as e:
            logger.warning("Daily cost cap reached during job %s enrichment: %s", job_id, e)
            break
        except Exception as e:
            logger.error("Error enriching lead %s: %s", lead.id, e)

    return enriched_count
