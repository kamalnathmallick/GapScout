"""Schemas for outcome logging, dataset building, and model health."""

from datetime import datetime

from pydantic import BaseModel, Field


class OutcomeLogRequest(BaseModel):
    """Payload to log a lead outreach outcome."""

    outcome: str = Field(description="'replied', 'no_reply', 'meeting', or 'converted'")
    occurred_at: datetime | None = None
    notes: str | None = None


class OutcomeImportRequest(BaseModel):
    """Payload to import outreach outcomes via CSV."""

    csv_content: str = Field(min_length=10, description="Raw CSV text with outcome columns")


class OutcomeImportOut(BaseModel):
    """Result of CSV outcome import."""

    imported: int
    skipped: int
    errors: list[str] = []


class DatasetHealthOut(BaseModel):
    """Health metrics of labelled dataset for ML unlock tracking."""

    total_labelled: int
    positives_count: int
    negatives_count: int
    positive_rate: float
    min_labels_required: int
    min_positives_required: int
    unlocked: bool
    labels_needed: int
    positives_needed: int
