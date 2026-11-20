"""Do-Not-Contact (DNC) API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import DoNotContact, Workspace
from app.schemas.dnc import DNCListOut, DNCOut, DNCRequest
from app.services.dnc import add_to_dnc

router = APIRouter(prefix="/dnc", tags=["dnc"])


@router.get("", response_model=DNCListOut)
def list_dnc_entries(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> DNCListOut:
    """List all DNC entries for the workspace."""
    stmt = (
        select(DoNotContact)
        .where(DoNotContact.workspace_id == workspace.id)
        .order_by(DoNotContact.created_at.desc())
    )
    items = list(db.scalars(stmt).all())
    return DNCListOut(items=[DNCOut.model_validate(i) for i in items], total=len(items))


@router.post("", response_model=DNCOut, status_code=status.HTTP_201_CREATED)
def create_dnc_entry(
    req: DNCRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> DNCOut:
    """Add a new contact vector to the DNC list."""
    try:
        entry = add_to_dnc(
            session=db,
            workspace_id=workspace.id,
            email=req.email,
            domain=req.domain,
            phone=req.phone,
            reason=req.reason,
        )
        return DNCOut.model_validate(entry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dnc_entry(
    entry_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove an entry from the DNC list."""
    entry = db.get(DoNotContact, entry_id)
    if not entry or entry.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DNC entry not found.")

    db.delete(entry)
    db.commit()
