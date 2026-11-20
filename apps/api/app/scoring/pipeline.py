"""Lead scoring pipeline for feature extraction, rule scoring, and database persistence."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HexMetric, Lead, LeadFeature, OfferProfile, Place
from app.scoring.config import load_scoring_config
from app.scoring.features import FEATURE_VERSION, extract_lead_features
from app.scoring.rules import score_lead

logger = logging.getLogger(__name__)


def score_workspace_leads(
    session: Session,
    workspace_id: uuid.UUID,
    place_ids: list[uuid.UUID] | None = None,
) -> int:
    """Score leads for places in a workspace and persist Lead & LeadFeature records."""
    config = load_scoring_config()

    # 1. Fetch workspace offer profile
    offer_profile = session.execute(
        select(OfferProfile).where(OfferProfile.workspace_id == workspace_id)
    ).scalar_one_or_none()

    # 2. Fetch places
    query = select(Place).where(
        Place.workspace_id == workspace_id,
        Place.is_closed.is_(False),
    )
    if place_ids:
        query = query.where(Place.id.in_(place_ids))

    places = session.execute(query).scalars().all()
    if not places:
        return 0

    # 3. Pre-fetch hex metrics for this workspace into a lookup map
    hex_metrics_rows = (
        session.execute(select(HexMetric).where(HexMetric.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    hex_map: dict[str, HexMetric] = {h.h3_index: h for h in hex_metrics_rows}

    scored_count = 0

    for place in places:
        hex_metric = hex_map.get(place.h3_r8) if place.h3_r8 else None

        # Extract features
        features = extract_lead_features(
            session=session,
            place=place,
            hex_metric=hex_metric,
            nearest_competitor_dist_m=None,
        )

        # Calculate scores
        score_data = score_lead(
            features=features,
            place=place,
            offer_profile=offer_profile,
            config=config,
        )

        # Upsert Lead record
        lead = session.execute(
            select(Lead).where(
                Lead.workspace_id == workspace_id,
                Lead.place_id == place.id,
            )
        ).scalar_one_or_none()

        if not lead:
            lead = Lead(
                workspace_id=workspace_id,
                place_id=place.id,
                status="new",
                rule_score=score_data["rule_score"],
                final_score=score_data["final_score"],
                score_breakdown=score_data["score_breakdown"],
            )
            session.add(lead)
            session.flush()
        else:
            lead.rule_score = score_data["rule_score"]
            lead.final_score = score_data["final_score"]
            lead.score_breakdown = score_data["score_breakdown"]
            session.flush()

        # Upsert LeadFeature record (v1)
        lead_feature = session.execute(
            select(LeadFeature).where(
                LeadFeature.lead_id == lead.id,
                LeadFeature.feature_version == FEATURE_VERSION,
            )
        ).scalar_one_or_none()

        if not lead_feature:
            lead_feature = LeadFeature(
                workspace_id=workspace_id,
                lead_id=lead.id,
                feature_version=FEATURE_VERSION,
                features=features,
            )
            session.add(lead_feature)
        else:
            lead_feature.features = features

        scored_count += 1

    session.commit()
    logger.info("Successfully scored %d leads for workspace %s", scored_count, workspace_id)
    return scored_count
