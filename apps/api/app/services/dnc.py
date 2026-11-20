"""Do-Not-Contact (DNC) service for managing opt-outs and blocking outreach."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DoNotContact, Lead, Place


def is_contact_dnc(
    session: Session,
    workspace_id: uuid.UUID,
    email: str | None = None,
    domain: str | None = None,
    phone: str | None = None,
) -> bool:
    """Check if any contact vector is registered on the workspace DNC list."""
    clauses = []
    if email:
        clauses.append(DoNotContact.email == email.strip().lower())
    if domain:
        clauses.append(DoNotContact.domain == domain.strip().lower())
    if phone:
        clauses.append(DoNotContact.phone == phone.strip())

    if not clauses:
        return False

    stmt = select(DoNotContact).where(
        DoNotContact.workspace_id == workspace_id,
        or_(*clauses),
    )
    result = session.execute(stmt).scalar_one_or_none()
    return result is not None


def is_lead_dnc(session: Session, lead: Lead, place: Place | None = None) -> bool:
    """Determine if a lead is on the DNC list either by status or contact information."""
    if lead.status == "do_not_contact":
        return True

    if not place:
        place = session.get(Place, lead.place_id)

    if not place:
        return False

    return is_contact_dnc(
        session=session,
        workspace_id=lead.workspace_id,
        email=place.email,
        domain=place.website_domain,
        phone=place.phone_e164,
    )


def add_to_dnc(
    session: Session,
    workspace_id: uuid.UUID,
    email: str | None = None,
    domain: str | None = None,
    phone: str | None = None,
    reason: str | None = None,
) -> DoNotContact:
    """Add a contact vector to the workspace DNC list."""
    email_clean = email.strip().lower() if email else None
    domain_clean = domain.strip().lower() if domain else None
    phone_clean = phone.strip() if phone else None

    if not any([email_clean, domain_clean, phone_clean]):
        raise ValueError("At least one contact method (email, domain, phone) must be provided.")

    # Check for existing
    existing = session.execute(
        select(DoNotContact).where(
            DoNotContact.workspace_id == workspace_id,
            or_(
                DoNotContact.email == email_clean if email_clean else False,
                DoNotContact.domain == domain_clean if domain_clean else False,
                DoNotContact.phone == phone_clean if phone_clean else False,
            ),
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    dnc = DoNotContact(
        workspace_id=workspace_id,
        email=email_clean,
        domain=domain_clean,
        phone=phone_clean,
        reason=reason,
    )
    session.add(dnc)
    session.commit()
    session.refresh(dnc)
    return dnc
