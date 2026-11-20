"""Website audit enrichment module with caching, safe fetching, and LLM analysis."""

import hashlib
import logging
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.anthropic_client import AnthropicClient
from app.enrichment.safe_fetcher import fetch_website_safely
from app.models import Enrichment, Lead, LeadFeature, Place

logger = logging.getLogger(__name__)


class LLMWebsiteAudit(BaseModel):
    """Structured website evaluation produced by Claude."""

    headline: str = Field(description="Short summary of web storefront")
    clarity_score: int = Field(ge=1, le=5, description="Value proposition clarity 1-5")
    cta_presence: int = Field(ge=1, le=5, description="Call to action effectiveness 1-5")
    mobile_readiness: int = Field(ge=1, le=5, description="Mobile friendliness 1-5")
    top_issues: list[str] = Field(default_factory=list, description="Top issues observed")
    overall_score: int = Field(ge=0, le=100, description="Overall digital maturity score 0-100")


class WebsiteAuditEnrichment(BaseModel):
    """Combined deterministic and AI website audit."""

    url: str
    deterministic: dict[str, Any]
    audit: LLMWebsiteAudit


WEBSITE_SYSTEM_PROMPT = """You are a senior digital consultant auditing a business website.
Based on the text content extracted from their homepage, evaluate:
1. Clarity of value proposition (1-5)
2. Call to action presence (booking, ordering, contact) (1-5)
3. Mobile readiness signals (1-5)
4. Up to 3 concrete issues or opportunities for improvement
5. An overall digital maturity score from 0 to 100.

Be concise, realistic, and commercially oriented."""


def audit_place_website(
    session: Session,
    place: Place,
    force: bool = False,
    anthropic_client: AnthropicClient | None = None,
) -> tuple[dict[str, Any], bool]:
    """Run safe website audit or return cached result if content has not changed."""
    if not place.website:
        return {"error": "Place has no website to audit"}, False

    # 1. Fetch website safely with SSRF protection & size limits
    try:
        signals = fetch_website_safely(place.website)
    except Exception as e:
        logger.warning("Could not safely fetch website %s: %s", place.website, e)
        return {"error": f"Failed to fetch website: {e}"}, False

    cleaned_text = signals["cleaned_text"]
    content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

    # 2. Cache check by (place_id, kind, content_hash)
    if not force:
        cached = session.execute(
            select(Enrichment).where(
                Enrichment.place_id == place.id,
                Enrichment.kind == "website_audit",
                Enrichment.content_hash == content_hash,
            )
        ).scalar_one_or_none()

        if cached:
            logger.info("Cache hit for website audit (place %s)", place.id)
            return cached.content, True

    # 3. Request LLM audit
    client = anthropic_client or AnthropicClient()
    prompt_context = (
        f"Business Name: {place.name}\n"
        f"Category: {place.normalized_category or place.category}\n"
        f"URL: {place.website}\n\n"
        f"Homepage Content:\n{cleaned_text}"
    )

    audit_res, _, _ = client.generate_structured_output(
        session=session,
        workspace_id=place.workspace_id,
        kind="website_audit",
        system_prompt=WEBSITE_SYSTEM_PROMPT,
        untrusted_content=prompt_context,
        schema_cls=LLMWebsiteAudit,
    )

    payload = {
        "url": signals["url"],
        "deterministic": {
            "https": signals["https"],
            "load_time_ms": signals["load_time_ms"],
            "mobile_viewport": signals["mobile_viewport"],
            "has_contact_form": signals["has_contact_form"],
            "has_booking_link": signals["has_booking_link"],
            "social_links": signals["social_links"],
        },
        "audit": audit_res.model_dump(),
    }

    # 4. Upsert Enrichment cache record
    enrichment = session.execute(
        select(Enrichment).where(
            Enrichment.place_id == place.id,
            Enrichment.kind == "website_audit",
            Enrichment.content_hash == content_hash,
        )
    ).scalar_one_or_none()

    if not enrichment:
        enrichment = Enrichment(
            workspace_id=place.workspace_id,
            place_id=place.id,
            kind="website_audit",
            content=payload,
            content_hash=content_hash,
            model=client.default_model,
        )
        session.add(enrichment)
    else:
        enrichment.content = payload

    # 5. Update lead_features with website_audit_score if lead exists
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
            new_features["website_audit_score"] = audit_res.overall_score
            lead_feat.features = new_features

    session.commit()
    return payload, False
