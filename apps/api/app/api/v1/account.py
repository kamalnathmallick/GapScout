"""Account endpoints: data export and right-to-be-forgotten deletion."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.models import Lead, Place, SearchJob, User, Workspace
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/export")
def export_account_data(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Export all public and operational data associated with this workspace.

    Supports data export requirements under data protection regulations (DPDP / GDPR).
    """
    places = list(db.scalars(select(Place).where(Place.workspace_id == workspace.id)).all())
    jobs = list(db.scalars(select(SearchJob).where(SearchJob.workspace_id == workspace.id)).all())
    leads = list(db.scalars(select(Lead).where(Lead.workspace_id == workspace.id)).all())

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
                "final_score": lead.final_score,
                "notes": lead.notes,
            }
            for lead in leads
        ],
    }


@router.delete("/data", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_account_data(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete all workspace data (Right to be Forgotten).

    Cascades deletion to all jobs, places, reviews, leads, and outreach drafts.
    """
    db.delete(workspace)
    db.commit()
    return MessageResponse(
        message=f"All data for workspace '{workspace.name}' has been permanently deleted.",
        status="deleted",
    )
