"""Account endpoints: data export (JSON/CSV) and right-to-be-forgotten deletion."""

import csv
import io
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.models import (
    DoNotContact,
    Lead,
    OutreachDraft,
    Place,
    SearchJob,
    User,
    Workspace,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/account", tags=["account"])


class DeleteAccountRequest(BaseModel):
    confirmation: str = "DELETE MY DATA"


@router.get("/export")
def export_account_data(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    format: Literal["json", "csv"] = "json",
) -> Any:
    """Export all public and operational data associated with this workspace in JSON or CSV.

    Supports data export requirements under data protection regulations (DPDP / GDPR).
    """
    places = list(db.scalars(select(Place).where(Place.workspace_id == workspace.id)).all())
    jobs = list(db.scalars(select(SearchJob).where(SearchJob.workspace_id == workspace.id)).all())
    leads = list(db.scalars(select(Lead).where(Lead.workspace_id == workspace.id)).all())
    dnc_list = list(
        db.scalars(select(DoNotContact).where(DoNotContact.workspace_id == workspace.id)).all()
    )
    drafts = list(
        db.scalars(select(OutreachDraft).where(OutreachDraft.workspace_id == workspace.id)).all()
    )

    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            [
                "record_type",
                "id",
                "name_or_category",
                "contact_email",
                "phone",
                "website",
                "rating",
                "review_count",
                "status_or_reason",
                "score",
            ]
        )
        for p in places:
            writer.writerow(
                [
                    "place",
                    str(p.id),
                    p.name,
                    p.email or "",
                    p.phone_e164 or "",
                    p.website or "",
                    p.rating or "",
                    p.review_count,
                    p.category or "",
                    "",
                ]
            )
        for lead in leads:
            writer.writerow(
                [
                    "lead",
                    str(lead.id),
                    str(lead.place_id),
                    "",
                    "",
                    "",
                    "",
                    "",
                    lead.status,
                    lead.final_score or lead.rule_score or "",
                ]
            )
        for d in dnc_list:
            writer.writerow(
                [
                    "dnc",
                    str(d.id),
                    d.domain or "",
                    d.email or "",
                    d.phone or "",
                    "",
                    "",
                    "",
                    d.reason or "Opt-out",
                    "",
                ]
            )
        csv_bytes = out.getvalue()
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="gapscout_export_{workspace.id}.csv"'
            },
        )

    return {
        "export_metadata": {
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "user_email": user.email,
            "export_version": "1.0",
        },
        "search_jobs_count": len(jobs),
        "places_count": len(places),
        "leads_count": len(leads),
        "dnc_count": len(dnc_list),
        "drafts_count": len(drafts),
        "places": [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "phone": p.phone_e164,
                "website": p.website,
                "email": p.email,
                "rating": p.rating,
                "review_count": p.review_count,
            }
            for p in places
        ],
        "leads": [
            {
                "id": str(lead.id),
                "place_id": str(lead.place_id),
                "status": lead.status,
                "rule_score": lead.rule_score,
                "ml_score": lead.ml_score,
                "final_score": lead.final_score,
                "notes": lead.notes,
            }
            for lead in leads
        ],
        "do_not_contact": [
            {
                "id": str(d.id),
                "email": d.email,
                "domain": d.domain,
                "phone": d.phone,
                "reason": d.reason,
            }
            for d in dnc_list
        ],
    }


@router.delete("/data", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_account_data(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    req: DeleteAccountRequest | None = None,
) -> MessageResponse:
    """Delete all workspace data (Right to be Forgotten).

    Cascades deletion to all jobs, places, reviews, leads, and outreach drafts.
    Requires confirmation text 'DELETE MY DATA' if request body is provided.
    """
    if req and req.confirmation.strip() != "DELETE MY DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation text must be 'DELETE MY DATA' to execute permanent data deletion.",
        )

    workspace_name = workspace.name
    db.delete(workspace)
    db.commit()

    return MessageResponse(
        message=f"All data for workspace '{workspace_name}' has been permanently deleted.",
        status="deleted",
    )
