"""SQLAlchemy 2 models.

Every table that holds user data carries ``workspace_id`` so tenant isolation is
a single filter. Statuses use VARCHAR + CHECK constraints rather than native
enums: adding a value later is a normal migration instead of a type rewrite.
"""

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

LEAD_STATUSES = (
    "new",
    "shortlisted",
    "contacted",
    "replied",
    "meeting",
    "converted",
    "rejected",
    "do_not_contact",
)
JOB_STATUSES = (
    "pending",
    "planning",
    "running",
    "paused",
    "cancelling",
    "cancelled",
    "failed",
    "completed",
)
CELL_STATUSES = (
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
)
HEX_LABELS = ("oversaturated", "balanced", "underserved", "insufficient_data")
ENRICHMENT_KINDS = ("website_audit", "review_themes", "pitch_angle")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    max_cells_per_job: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("250")
    )
    max_places_per_job: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("5000")
    )
    daily_llm_cost_cap_usd: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("2.0")
    )
    data_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("90")
    )
    created_at: Mapped[datetime] = _created_at()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'owner'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    verification_token: Mapped[str | None] = mapped_column(String(255))
    reset_token: Mapped[str | None] = mapped_column(String(255))
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (CheckConstraint("role IN ('owner', 'admin', 'member')", name="role_allowed"),)


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    area_name: Mapped[str | None] = mapped_column(String(255))
    bbox: Mapped[Any | None] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    cells_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cells_done: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    places_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cells: Mapped[list["SearchJobCell"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'planning', 'running', 'paused', 'cancelling', "
            "'cancelled', 'failed', 'completed')",
            name="status_allowed",
        ),
        Index("ix_search_jobs_workspace_status", "workspace_id", "status"),
    )


class SearchJobCell(Base):
    __tablename__ = "search_job_cells"

    id: Mapped[uuid.UUID] = _uuid_pk()
    search_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cell_index: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    job: Mapped["SearchJob"] = relationship(back_populates="cells")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="cell_status_allowed",
        ),
        UniqueConstraint("search_job_id", "cell_index", name="uq_search_job_cells_job_index"),
        Index("ix_search_job_cells_job_status", "search_job_id", "status"),
    )


class Place(Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_place_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    normalized_category: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text)
    phone_e164: Mapped[str | None] = mapped_column(String(20))
    website: Mapped[str | None] = mapped_column(Text)
    website_domain: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    price_level: Mapped[int | None] = mapped_column(SmallInteger)
    location: Mapped[Any | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True)
    )
    h3_r8: Mapped[str | None] = mapped_column(String(15))
    opening_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reviews: Mapped[list["PlaceReview"]] = relationship(
        back_populates="place", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", "provider_place_id", name="uq_places_provider_place"
        ),
        Index("ix_places_workspace_h3_r8", "workspace_id", "h3_r8"),
        Index("ix_places_workspace_category", "workspace_id", "normalized_category"),
        Index("ix_places_workspace_domain", "workspace_id", "website_domain"),
    )


class PlaceReview(Base):
    __tablename__ = "place_reviews"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    review_text: Mapped[str | None] = mapped_column("text", Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_replied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = _created_at()

    place: Mapped[Place] = relationship(back_populates="reviews")

    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)


class HexMetric(Base):
    __tablename__ = "hex_metrics"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    search_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    resolution: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    supply_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    density_per_km2: Mapped[float | None] = mapped_column(Float)
    avg_rating: Mapped[float | None] = mapped_column(Float)
    avg_review_count: Mapped[float | None] = mapped_column(Float)
    demand_proxy: Mapped[float | None] = mapped_column(Float)
    opportunity_score: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(String(20))
    explanation: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "search_job_id", "category", "h3_index", "resolution", name="uq_hex_metrics_cell"
        ),
        CheckConstraint("resolution BETWEEN 7 AND 9", name="resolution_range"),
        CheckConstraint(
            "label IS NULL OR label IN ('oversaturated', 'balanced', 'underserved', "
            "'insufficient_data')",
            name="label_allowed",
        ),
        Index("ix_hex_metrics_workspace_category", "workspace_id", "category", "h3_index"),
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'new'"))
    rule_score: Mapped[float | None] = mapped_column(Float)
    ml_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "place_id", name="uq_leads_workspace_place"),
        CheckConstraint(
            "status IN ('new', 'shortlisted', 'contacted', 'replied', 'meeting', "
            "'converted', 'rejected', 'do_not_contact')",
            name="status_allowed",
        ),
        Index("ix_leads_workspace_status", "workspace_id", "status"),
        Index("ix_leads_workspace_final_score", "workspace_id", "final_score"),
    )


class LeadFeature(Base):
    __tablename__ = "lead_features"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    feature_version: Mapped[str] = mapped_column(String(16), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("lead_id", "feature_version", name="uq_lead_features_version"),
    )


class Enrichment(Base):
    __tablename__ = "enrichments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        UniqueConstraint("place_id", "kind", "content_hash", name="uq_enrichments_cache"),
        CheckConstraint(
            "kind IN ('website_audit', 'review_themes', 'pitch_angle')", name="kind_allowed"
        ),
    )


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (CheckConstraint("channel IN ('email', 'chat')", name="channel_allowed"),)


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    features_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    n_samples: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    feature_list: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    artifact_path: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        Index(
            "uq_model_versions_active",
            "workspace_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )


class DoNotContact(Base):
    __tablename__ = "do_not_contact"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(320))
    domain: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        Index(
            "uq_do_not_contact_email",
            "workspace_id",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        Index(
            "uq_do_not_contact_domain",
            "workspace_id",
            "domain",
            unique=True,
            postgresql_where=text("domain IS NOT NULL"),
        ),
        Index(
            "uq_do_not_contact_phone",
            "workspace_id",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL"),
        ),
        CheckConstraint(
            "email IS NOT NULL OR domain IS NOT NULL OR phone IS NOT NULL",
            name="at_least_one_contact",
        ),
    )


class OfferProfile(Base):
    __tablename__ = "offer_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(120), nullable=False, server_default=text("'Default Offer'")
    )
    offer_description: Mapped[str | None] = mapped_column(Text)
    target_categories: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    min_rating: Mapped[float | None] = mapped_column(Float)
    max_rating: Mapped[float | None] = mapped_column(Float)
    target_regions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("workspace_id", name="uq_offer_profiles_workspace"),)


class LLMUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0.0"))
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (Index("ix_llm_usage_logs_workspace_created", "workspace_id", "created_at"),)
