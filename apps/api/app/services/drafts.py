"""Outreach draft generator with grounded citations, channel length caps, and mandatory opt-out."""

import logging
import re
import urllib.parse
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.gemini_client import GeminiClient
from app.models import Enrichment, Lead, OfferProfile, OutreachDraft, Place
from app.services.dnc import is_lead_dnc

logger = logging.getLogger(__name__)

MAX_CHAT_CHARS = 450
MAX_EMAIL_WORDS = 120

OPT_OUT_EMAIL = "Reply STOP or unsubscribe to not hear from us again."
OPT_OUT_CHAT = "Reply STOP to opt out."


class DNCBlockedError(ValueError):
    """Raised when attempting to draft outreach for a DNC lead."""

    pass


def clean_phone_for_whatsapp(phone: str | None) -> str | None:
    """Strip all non-numeric characters for wa.me links (requires country code without +)."""
    if not phone:
        return None
    cleaned = re.sub(r"\D", "", phone)
    return cleaned if len(cleaned) >= 8 else None


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def enforce_length_caps(channel: str, body: str) -> str:
    """Enforce strict length limits and guarantee opt-out line is preserved."""
    channel = channel.lower()
    if channel == "chat":
        opt_out = OPT_OUT_CHAT
        if len(body) > MAX_CHAT_CHARS:
            allowed_body_len = MAX_CHAT_CHARS - len(opt_out) - 5
            truncated = body[:allowed_body_len].rstrip()
            # Ensure not ending mid-sentence if possible
            last_punc = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
            if last_punc > 50:
                truncated = truncated[: last_punc + 1]
            body = f"{truncated}\n\n{opt_out}"
        elif opt_out not in body:
            body = f"{body.rstrip()}\n\n{opt_out}"
    else:
        # Email cap <= 120 words
        opt_out = OPT_OUT_EMAIL
        words = body.split()
        if len(words) > MAX_EMAIL_WORDS:
            opt_out_words = opt_out.split()
            max_content_words = MAX_EMAIL_WORDS - len(opt_out_words) - 1
            body = " ".join(words[:max_content_words]).rstrip(".,;:") + f".\n\n{opt_out}"
        elif opt_out not in body:
            body = f"{body.rstrip()}\n\n{opt_out}"

    return body.strip()


def build_deterministic_draft(
    place: Place,
    offer_profile: OfferProfile | None,
    enrichments: dict[str, Any],
    channel: str,
    tone: str = "direct",
) -> str:
    """Generate grounded, hallucination-free outreach draft using verified facts."""
    biz_name = place.name
    category = place.normalized_category or place.category or "business"
    offer_name = offer_profile.name if offer_profile else "growth consulting"
    offer_desc = (
        offer_profile.offer_description
        if (offer_profile and offer_profile.offer_description)
        else "help local businesses acquire more customers"
    )

    # Pick 1 grounded citation
    citation = ""
    review_themes = enrichments.get("review_themes")
    website_audit = enrichments.get("website_audit")

    if review_themes and review_themes.get("one_line_pitch_angle"):
        citation = review_themes["one_line_pitch_angle"]
    elif review_themes and review_themes.get("complaint_themes"):
        first_complaint = review_themes["complaint_themes"][0]
        citation = f"noticed recent customer feedback mentioning {first_complaint.lower()}"
    elif website_audit and website_audit.get("audit", {}).get("top_issues"):
        first_issue = website_audit["audit"]["top_issues"][0]
        citation = f"saw that your website could benefit from addressing {first_issue.lower()}"
    elif not place.website:
        citation = "noticed your business currently doesn't have an official website listed on Maps"
    elif place.rating and place.rating < 4.0:
        citation = (
            f"saw your current Google rating is {place.rating:.1f}/5 across "
            f"{place.review_count or '[N]'} reviews"
        )
    else:
        citation = (
            f"saw {biz_name} has built a solid local presence with "
            f"{place.review_count or '[N]'} reviews"
        )

    if channel.lower() == "chat":
        if tone == "casual":
            body = (
                f"Hi from GapScout! In {place.address or 'your area'}, "
                f"{citation}. We {offer_desc}. Open to a quick 5-min chat this week?\n\n"
                f"{OPT_OUT_CHAT}"
            )
        else:
            body = (
                f"Hello, I came across {biz_name}. I {citation}. We specialize in {offer_name} to "
                f"{offer_desc}. Open to seeing how we could help? Let me know.\n\n"
                f"{OPT_OUT_CHAT}"
            )
    else:
        # Cold email
        if tone == "consultative":
            body = (
                f"Hi {biz_name} team,\n\n"
                f"I was researching established {category}s in your area and {citation}.\n\n"
                f"Through our {offer_name}, we {offer_desc}. We help businesses like yours resolve "
                f"these exact bottlenecks without upfront risk.\n\n"
                f"Would you be open to a brief 10-minute call on Tuesday to discuss ideas?\n\n"
                f"Best regards,\n"
                f"GapScout Team\n\n"
                f"{OPT_OUT_EMAIL}"
            )
        else:
            body = (
                f"Hi {biz_name} team,\n\n"
                f"Quick question for you: I {citation}.\n\n"
                f"We help local {category}s with {offer_desc}.\n\n"
                f"Are you taking on new initiatives this quarter? "
                f"Happy to send over a 2-minute breakdown if relevant.\n\n"
                f"Best,\n"
                f"GapScout\n\n"
                f"{OPT_OUT_EMAIL}"
            )

    return enforce_length_caps(channel, body)


def generate_and_save_draft(
    session: Session,
    lead_id: uuid.UUID,
    channel: str,
    tone: str = "direct",
    custom_offer: str | None = None,
) -> dict[str, Any]:
    """Generate, validate, and record an outreach draft without sending."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    place = session.get(Place, lead.place_id)
    if not place:
        raise ValueError(f"Place for lead {lead_id} not found")

    # 1. Enforce DNC blocking
    if is_lead_dnc(session, lead, place):
        raise DNCBlockedError(
            f"Lead '{place.name}' is on the DNC list. Outreach drafts are strictly prohibited."
        )

    # 2. Fetch Offer Profile
    offer_profile = session.execute(
        select(OfferProfile).where(OfferProfile.workspace_id == lead.workspace_id)
    ).scalar_one_or_none()

    if custom_offer and offer_profile:
        offer_profile.offer_description = custom_offer

    # 3. Fetch enrichments (if any)
    enrichment_rows = (
        session.execute(select(Enrichment).where(Enrichment.place_id == place.id)).scalars().all()
    )
    enrichments_map: dict[str, Any] = {e.kind: e.content for e in enrichment_rows}

    # 4. Generate draft body
    client = GeminiClient()
    body = None

    if client.api_key and client.api_key.strip() not in ("", "placeholder", "test-key"):
        # Gemini-generated draft with length constraints
        channel_constraint = (
            f"STRICT LIMIT: Must be under {MAX_CHAT_CHARS} characters including opt-out."
            if channel == "chat"
            else f"STRICT LIMIT: Must be under {MAX_EMAIL_WORDS} words including opt-out."
        )
        opt_out_rule = OPT_OUT_CHAT if channel == "chat" else OPT_OUT_EMAIL

        system_prompt = (
            f"You are an expert B2B copywriter crafting a personalized cold outreach {channel}.\n"
            f"{channel_constraint}\n"
            "Mandatory requirement: Cite exactly one verified finding about the business. "
            "Do not invent facts or metrics; if unknown, use [N].\n"
            f"The message MUST end with this exact sentence on its own line: '{opt_out_rule}'"
        )
        prompt_content = (
            f"Business: {place.name}\n"
            f"Category: {place.normalized_category or place.category}\n"
            f"Offer: {offer_profile.offer_description if offer_profile else 'B2B Growth'}\n"
            f"Tone: {tone}\n"
            f"Review Themes: {enrichments_map.get('review_themes', {})}\n"
            f"Website Audit: {enrichments_map.get('website_audit', {})}"
        )
        try:
            from pydantic import BaseModel, Field

            class LLMDraftOut(BaseModel):
                body: str = Field(description="The complete draft message")

            draft_model, _, _ = client.generate_structured_output(
                session=session,
                workspace_id=lead.workspace_id,
                kind="outreach_draft",
                system_prompt=system_prompt,
                untrusted_content=prompt_content,
                schema_cls=LLMDraftOut,
            )
            body = draft_model.body
        except Exception as e:
            logger.warning("Gemini draft generation failed, falling back to deterministic: %s", e)
            body = None

    if not body:
        body = build_deterministic_draft(
            place=place,
            offer_profile=offer_profile,
            enrichments=enrichments_map,
            channel=channel,
            tone=tone,
        )

    # 5. Enforce caps and opt-out guarantee
    final_body = enforce_length_caps(channel, body)

    # 6. Save draft in database
    draft = OutreachDraft(
        workspace_id=lead.workspace_id,
        lead_id=lead.id,
        channel=channel,
        body=final_body,
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)

    # 7. Generate non-automated mailto and wa.me deep links
    mailto_link = None
    if place.email:
        subj = urllib.parse.quote(f"Quick question regarding {place.name}")
        encoded_body = urllib.parse.quote(final_body)
        mailto_link = f"mailto:{place.email}?subject={subj}&body={encoded_body}"

    wa_link = None
    phone_clean = clean_phone_for_whatsapp(place.phone_e164)
    if phone_clean:
        encoded_text = urllib.parse.quote(final_body)
        wa_link = f"https://wa.me/{phone_clean}?text={encoded_text}"

    return {
        "id": draft.id,
        "lead_id": lead.id,
        "channel": channel,
        "body": final_body,
        "word_count": count_words(final_body),
        "char_count": len(final_body),
        "mailto_link": mailto_link,
        "wa_link": wa_link,
        "created_at": draft.created_at,
    }
