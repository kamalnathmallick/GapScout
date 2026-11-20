"""Review themes enrichment module with caching and Claude-powered analysis."""

import hashlib
import logging
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.anthropic_client import AnthropicClient
from app.models import Enrichment, Lead, LeadFeature, Place, PlaceReview

logger = logging.getLogger(__name__)


class ReviewThemesAudit(BaseModel):
    """Structured review themes and pitch angle produced by Claude."""

    complaint_themes: list[str] = Field(
        default_factory=list, description="Top recurring customer complaints"
    )
    praise_themes: list[str] = Field(
        default_factory=list, description="Top customer compliments and praises"
    )
    owner_response_behavior: str = Field(
        description="Assessment of how the owner engages with reviews"
    )
    one_line_pitch_angle: str = Field(
        description="A compelling, personalized one-line hook or sales pitch"
    )


REVIEWS_SYSTEM_PROMPT = """You are a sales intelligence analyst analyzing customer reviews.
Review the provided recent customer reviews and produce:
1. Top recurring complaint themes (e.g. slow service, billing issues)
2. Top praise themes (e.g. ambiance, staff friendliness)
3. Owner response behavior (e.g. responds defensively, offers refunds, never replies)
4. A personalized, high-converting one-line pitch angle for B2B outreach.

Be factual and reference only concrete issues mentioned in the reviews. Do not hallucinate."""


def extract_place_review_themes(
    session: Session,
    place: Place,
    force: bool = False,
    anthropic_client: AnthropicClient | None = None,
) -> tuple[dict[str, Any], bool]:
    """Analyze up to 30 recent reviews for a place and extract pain themes and pitch angle."""
    reviews = (
        session.execute(
            select(PlaceReview)
            .where(PlaceReview.place_id == place.id)
            .order_by(PlaceReview.published_at.desc().nulls_last())
            .limit(30)
        )
        .scalars()
        .all()
    )

    if not reviews:
        return {"error": "No reviews available for this place"}, False

    # Format reviews into untrusted text
    formatted_reviews_list: list[str] = []
    for i, r in enumerate(reviews, 1):
        rating_str = f"{r.rating}/5" if r.rating is not None else "No rating"
        replied_str = "Owner replied" if r.owner_replied else "No owner reply"
        text = (r.review_text or "").strip()
        formatted_reviews_list.append(f"Review {i} [{rating_str}, {replied_str}]: {text}")

    formatted_reviews = "\n".join(formatted_reviews_list)
    content_hash = hashlib.sha256(formatted_reviews.encode("utf-8")).hexdigest()

    # 1. Check cache
    if not force:
        cached = session.execute(
            select(Enrichment).where(
                Enrichment.place_id == place.id,
                Enrichment.kind == "review_themes",
                Enrichment.content_hash == content_hash,
            )
        ).scalar_one_or_none()

        if cached:
            logger.info("Cache hit for review themes (place %s)", place.id)
            return cached.content, True

    # 2. Query Claude via client
    client = anthropic_client or AnthropicClient()
    prompt_context = (
        f"Business Name: {place.name}\n"
        f"Category: {place.normalized_category or place.category}\n"
        f"Address: {place.address}\n\n"
        f"Customer Reviews Sample (up to 30 recent reviews):\n"
        f"{formatted_reviews}"
    )

    audit_res, _, _ = client.generate_structured_output(
        session=session,
        workspace_id=place.workspace_id,
        kind="review_themes",
        system_prompt=REVIEWS_SYSTEM_PROMPT,
        untrusted_content=prompt_context,
        schema_cls=ReviewThemesAudit,
    )

    payload = audit_res.model_dump()

    # 3. Upsert Enrichment record
    enrichment = session.execute(
        select(Enrichment).where(
            Enrichment.place_id == place.id,
            Enrichment.kind == "review_themes",
            Enrichment.content_hash == content_hash,
        )
    ).scalar_one_or_none()

    if not enrichment:
        enrichment = Enrichment(
            workspace_id=place.workspace_id,
            place_id=place.id,
            kind="review_themes",
            content=payload,
            content_hash=content_hash,
            model=client.default_model,
        )
        session.add(enrichment)
    else:
        enrichment.content = payload

    # 4. Update lead_features with number_of_review_pain_themes
    lead = session.execute(
        select(Lead).where(
            Lead.workspace_id == place.workspace_id,
            Lead.place_id == place.id,
        )
    ).scalar_one_or_none()

    if lead:
        lead_feat = session.execute(
            select(LeadFeature).where(
                LeadFeature.lead_id == lead.id,
                LeadFeature.feature_version == "v1",
            )
        ).scalar_one_or_none()
        if lead_feat and isinstance(lead_feat.features, dict):
            new_features = dict(lead_feat.features)
            new_features["number_of_review_pain_themes"] = len(audit_res.complaint_themes)
            lead_feat.features = new_features

    session.commit()
    return payload, False
