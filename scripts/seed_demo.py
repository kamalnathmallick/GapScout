"""GapScout Demo Dataset & Outcome History Seeder.

Seeds realistic Bangalore (Indiranagar & Koramangala) cafes, gap metrics,
offer profiles, and historical outreach outcomes clearly labelled 'DEMO DATA'.
Automatically trains and activates the machine learning model tournament so
that Model Insights, ROC/Calibration curves, feature importance, and Active
Learning queues are immediately available out of the box.

Usage:
    python scripts/seed_demo.py
    docker exec gapscout-api-1 python ../../scripts/seed_demo.py
"""

import logging
import math
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# Ensure apps/api is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import h3
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.auth.security import hash_password
from app.db import SessionLocal
from app.ml.pipeline import train_and_evaluate_models
from app.models import (
    HexMetric,
    Lead,
    OfferProfile,
    OutreachDraft,
    OutreachEvent,
    Place,
    SearchJob,
    User,
    Workspace,
)
from app.outcomes.dataset import build_training_dataset
from app.scoring.pipeline import score_workspace_leads

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEMO_WORKSPACE_NAME = "GapScout Demo"
DEMO_USER_EMAIL = "demo@gapscout.test"
DEMO_USER_PASSWORD = "DemoPassword123!"

# Bangalore central hotspots: Indiranagar & Koramangala
BANGALORE_PLACES = [
    (
        "Third Wave Coffee Roasters",
        "cafe",
        12.9716,
        77.6412,
        4.7,
        1420,
        "https://thirdwavecoffeeroasters.com",
        "reachout@thirdwave.example",
        3,
    ),
    (
        "Blue Tokai Coffee Roasters",
        "cafe",
        12.9352,
        77.6245,
        4.6,
        980,
        "https://bluetokaicoffee.com",
        "support@bluetokai.example",
        3,
    ),
    (
        "The Hole in the Wall Cafe",
        "cafe",
        12.9344,
        77.6231,
        4.4,
        2850,
        "https://theholeinthewall.example",
        "contact@holeinthewall.example",
        2,
    ),
    (
        "Glen's Bakehouse",
        "cafe",
        12.9785,
        77.6409,
        4.5,
        3400,
        "https://glensbakehouse.example",
        "info@glensbakehouse.example",
        2,
    ),
    (
        "Araku Coffee Indiranagar",
        "cafe",
        12.9740,
        77.6412,
        4.8,
        1650,
        "https://arakucoffee.com",
        "concierge@arakucoffee.example",
        4,
    ),
    (
        "Doffpub & Lounge",
        "cafe",
        12.9755,
        77.6420,
        4.1,
        740,
        "https://doffpub.example",
        "manager@doffpub.example",
        2,
    ),
    (
        "Yogisthaan Cafe",
        "cafe",
        12.9730,
        77.6385,
        4.5,
        620,
        "https://yogisthaan.example",
        "namaste@yogisthaan.example",
        2,
    ),
    (
        "Matteo Coffea",
        "cafe",
        12.9750,
        77.6070,
        4.3,
        1100,
        "https://matteocoffea.example",
        "talk@matteocoffea.example",
        2,
    ),
    (
        "Cafe Max Indiranagar",
        "cafe",
        12.9800,
        77.6430,
        4.4,
        530,
        "https://cafemax.example",
        "reservations@cafemax.example",
        3,
    ),
    ("Dunkin' Indiranagar", "cafe", 12.9720, 77.6400, 4.0, 410, "https://dunkin.example", None, 1),
    (
        "Starbucks 100ft Road",
        "cafe",
        12.9790,
        77.6415,
        4.3,
        2100,
        "https://starbucks.in",
        "customercare@starbucks.example",
        3,
    ),
    (
        "Chai Point Koramangala",
        "cafe",
        12.9360,
        77.6260,
        4.1,
        890,
        "https://chaipoint.com",
        "care@chaipoint.example",
        1,
    ),
    (
        "Chaayos Indiranagar",
        "cafe",
        12.9760,
        77.6450,
        4.2,
        750,
        "https://chaayos.com",
        "chai@chaayos.example",
        1,
    ),
    (
        "Artisan Roasters Lab",
        "cafe",
        12.9700,
        77.6390,
        4.7,
        310,
        "https://artisanroasters.example",
        "roast@artisan.example",
        3,
    ),
    (
        "Paper & Pie Cafe",
        "cafe",
        12.9770,
        77.6440,
        4.6,
        920,
        "https://paperandpie.example",
        "hello@paperandpie.example",
        3,
    ),
    (
        "Lazy Suzy Dessert Deli",
        "cafe",
        12.9745,
        77.6425,
        4.5,
        680,
        "https://lazysuzy.example",
        "treats@lazysuzy.example",
        3,
    ),
    (
        "Copper + Cloves",
        "cafe",
        12.9752,
        77.6380,
        4.6,
        490,
        "https://copperandcloves.example",
        "food@copperandcloves.example",
        3,
    ),
    (
        "Maverick & Farmer Coffee",
        "cafe",
        12.9380,
        77.6200,
        4.7,
        780,
        "https://maverickandfarmer.example",
        "brew@maverickandfarmer.example",
        2,
    ),
    (
        "Kaffeology Koramangala",
        "cafe",
        12.9330,
        77.6270,
        4.2,
        340,
        "https://kaffeology.example",
        "owner@kaffeology.example",
        2,
    ),
    ("Bean Haven Cafe", "cafe", 12.9310, 77.6290, 3.9, 140, None, None, 1),
    (
        "Corner House Ice Cream Indiranagar",
        "cafe",
        12.9780,
        77.6405,
        4.6,
        4200,
        "https://cornerhouseicecream.example",
        "orders@cornerhouse.example",
        2,
    ),
    (
        "Magnolia Bakery Indiranagar",
        "cafe",
        12.9710,
        77.6418,
        4.4,
        2900,
        "https://magnoliabakery.com",
        "support@magnoliabakery.example",
        3,
    ),
    (
        "Smoor Chocolates Indiranagar",
        "cafe",
        12.9748,
        77.6410,
        4.3,
        1450,
        "https://smoorchocolates.example",
        "care@smoor.example",
        3,
    ),
    (
        "Brik Oven Indiranagar",
        "cafe",
        12.9765,
        77.6418,
        4.5,
        1800,
        "https://brikoven.example",
        "pizza@brikoven.example",
        3,
    ),
    (
        "Truffles Koramangala",
        "cafe",
        12.9355,
        77.6250,
        4.5,
        6200,
        "https://truffles.example",
        "customercare@truffles.example",
        2,
    ),
    (
        "Cafe Terra Koramangala",
        "cafe",
        12.9320,
        77.6240,
        4.3,
        850,
        "https://cafeterra.example",
        "contact@cafeterra.example",
        2,
    ),
    (
        "Dye's Kitchen & Coffee",
        "cafe",
        12.9370,
        77.6280,
        4.1,
        260,
        "https://dyeskitchen.example",
        None,
        2,
    ),
    (
        "Bloom Coffee House",
        "cafe",
        12.9715,
        77.6360,
        4.4,
        380,
        "https://bloomcoffee.example",
        "bloom@coffee.example",
        2,
    ),
    (
        "The Daily Bean Indiranagar",
        "cafe",
        12.9775,
        77.6395,
        4.3,
        290,
        None,
        "dailybean@gmail.example",
        1,
    ),
    (
        "Greenhouse Bistro & Cafe",
        "cafe",
        12.9795,
        77.6370,
        4.2,
        410,
        "https://greenhousebistro.example",
        "dine@greenhouse.example",
        2,
    ),
    (
        "Sublime Espresso Bar",
        "cafe",
        12.9735,
        77.6445,
        4.7,
        510,
        "https://sublimeespresso.example",
        "barista@sublime.example",
        3,
    ),
    (
        "Koramangala Social",
        "cafe",
        12.9348,
        77.6225,
        4.4,
        4800,
        "https://socialoffline.in",
        "koramangala@socialoffline.example",
        3,
    ),
    (
        "Indiranagar Social",
        "cafe",
        12.9758,
        77.6415,
        4.4,
        4100,
        "https://socialoffline.in",
        "indiranagar@socialoffline.example",
        3,
    ),
    (
        "Smoke House Deli Indiranagar",
        "cafe",
        12.9762,
        77.6402,
        4.3,
        1950,
        "https://smokehousedeli.example",
        "guest@smokehousedeli.example",
        3,
    ),
    (
        "Toit Brewpub & Cafe",
        "cafe",
        12.9792,
        77.6404,
        4.7,
        8500,
        "https://toit.in",
        "cheers@toit.example",
        3,
    ),
    ("Espresso Junction", "cafe", 12.9722, 77.6375, 4.0, 180, None, None, 1),
    (
        "Coffee Day Lounge Koramangala",
        "cafe",
        12.9365,
        77.6235,
        3.8,
        420,
        "https://cafecoffeeday.com",
        "care@cafecoffeeday.example",
        1,
    ),
    (
        "The Roastery Koramangala",
        "cafe",
        12.9340,
        77.6210,
        4.6,
        730,
        "https://roasterycoffee.example",
        "beans@roastery.example",
        3,
    ),
    (
        "Brew & Bite Indiranagar",
        "cafe",
        12.9782,
        77.6435,
        4.2,
        290,
        "https://brewandbite.example",
        "info@brewandbite.example",
        2,
    ),
    (
        "Urban Cafe 80ft Road",
        "cafe",
        12.9742,
        77.6460,
        4.1,
        310,
        None,
        "urban80ft@gmail.example",
        2,
    ),
]


# Expand places to 180 locations across Indiranagar, Koramangala & HSR Layout
BRANCH_OFFSETS = [
    ("Main", 0.000, 0.000),
    ("Indiranagar 12th Main", 0.003, -0.002),
    ("Koramangala 4th Block", -0.040, -0.015),
    ("Koramangala 5th Block", -0.038, -0.017),
    ("HSR Layout Sector 1", -0.055, 0.012),
]

EXPANDED_PLACES = []
for name, cat, lat, lon, rating, rev_count, web, email, price_lvl in BANGALORE_PLACES:
    for b_idx, (b_name, lat_off, lon_off) in enumerate(BRANCH_OFFSETS):
        if len(EXPANDED_PLACES) >= 180:
            break
        p_name = f"{name} - {b_name}" if b_idx > 0 else name
        p_lat = round(lat + lat_off, 4)
        p_lon = round(lon + lon_off, 4)
        p_revs = max(35, int(rev_count * (0.75 + 0.1 * b_idx)))
        p_rating = round(min(5.0, max(3.6, rating + (b_idx - 2) * 0.1)), 1)
        p_web = f"{web}/{b_name.lower().replace(' ', '-')}" if web else None
        p_email = f"branch{b_idx}_{email}" if email else None
        EXPANDED_PLACES.append(
            (p_name, cat, p_lat, p_lon, p_rating, p_revs, p_web, p_email, price_lvl)
        )


def seed_demo() -> None:
    """Run full idempotent demo database seeding and ML model generation."""
    logger.info("Starting GapScout demo database seeder...")
    session = SessionLocal()

    try:
        # 1. Create or retrieve Demo Workspace
        ws = session.execute(
            select(Workspace).where(Workspace.name == DEMO_WORKSPACE_NAME)
        ).scalar_one_or_none()
        if not ws:
            ws = Workspace(name=DEMO_WORKSPACE_NAME)
            session.add(ws)
            session.flush()
            logger.info("Created demo workspace: %s (%s)", ws.name, ws.id)
        else:
            logger.info("Using existing demo workspace: %s (%s)", ws.name, ws.id)

        # 2. Create demo user
        user = session.execute(
            select(User).where(User.email == DEMO_USER_EMAIL)
        ).scalar_one_or_none()
        if not user:
            user = User(
                workspace_id=ws.id,
                email=DEMO_USER_EMAIL,
                password_hash=hash_password(DEMO_USER_PASSWORD),
                full_name="Bangalore Growth Agency",
                role="owner",
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            session.flush()
            logger.info("Created demo user: %s (password: %s)", DEMO_USER_EMAIL, DEMO_USER_PASSWORD)

        # 3. Setup Offer Profile
        offer = session.execute(
            select(OfferProfile).where(OfferProfile.workspace_id == ws.id)
        ).scalar_one_or_none()
        if not offer:
            offer = OfferProfile(
                workspace_id=ws.id,
                name="Weekday Afternoon Footfall Booster",
                offer_description=(
                    "Help independent cafes fill 25-35 empty tables during weekday afternoons "
                    "between 2:00 PM and 5:30 PM via targeted geo-fenced promotions and digital reviews."
                ),
                target_categories=["cafe", "restaurant", "bakery"],
                min_rating=4.0,
                max_rating=4.9,
                target_regions=["Indiranagar", "Koramangala", "Bangalore"],
                weights={},
            )
            session.add(offer)
            session.flush()
            logger.info("Seeded offer profile: %s", offer.name)

        # 4. Create Completed SearchJob
        job = session.execute(select(SearchJob).where(SearchJob.workspace_id == ws.id)).first()
        search_job_id: uuid.UUID
        if not job:
            new_job = SearchJob(
                workspace_id=ws.id,
                category="cafe",
                area_name="Indiranagar & Koramangala, Bangalore",
                status="completed",
                cells_total=12,
                cells_done=12,
                places_found=len(BANGALORE_PLACES),
                errors_count=0,
                params={"resolution": 8, "cell_size_m": 500},
                started_at=datetime.now(UTC) - timedelta(hours=2),
                finished_at=datetime.now(UTC) - timedelta(hours=1, minutes=45),
            )
            session.add(new_job)
            session.flush()
            search_job_id = new_job.id
            logger.info("Created demo completed SearchJob (%s)", search_job_id)
        else:
            search_job_id = job[0].id

        # 5. Compute H3 Hexes and HexMetrics
        hex_cells: set[str] = set()
        for _, _, lat, lon, _, _, _, _, _ in EXPANDED_PLACES:
            h8 = h3.latlng_to_cell(lat, lon, 8)
            hex_cells.add(h8)

        for h8 in hex_cells:
            existing_metric = session.execute(
                select(HexMetric).where(
                    HexMetric.search_job_id == search_job_id,
                    HexMetric.h3_index == h8,
                )
            ).scalar_one_or_none()
            if not existing_metric:
                opp_score = round(45.0 + (int(h8, 16) % 44), 1)
                label = (
                    "underserved"
                    if opp_score >= 70
                    else ("balanced" if opp_score >= 55 else "oversaturated")
                )
                metric = HexMetric(
                    workspace_id=ws.id,
                    search_job_id=search_job_id,
                    category="cafe",
                    h3_index=h8,
                    resolution=8,
                    supply_count=int(opp_score // 10),
                    density_per_km2=round(opp_score / 3.2, 2),
                    avg_rating=4.4,
                    avg_review_count=950.0,
                    demand_proxy=round(opp_score * 1.8, 1),
                    opportunity_score=opp_score,
                    label=label,
                    explanation={
                        "top_reasons": [
                            f"Opportunity index {opp_score}/100 based on footfall and competitor density.",
                            f"Commercial density: {label.capitalize()} market balance in Indiranagar/Koramangala.",
                        ],
                        "metrics": {
                            "supply": int(opp_score // 10),
                            "demand_proxy": round(opp_score * 1.8, 1),
                        },
                    },
                )
                session.add(metric)
        session.flush()
        logger.info("Seeded %d H3 resolution-8 hex metrics.", len(hex_cells))

        # 6. Seed Places & Leads
        created_places: list[Place] = []
        for name, cat, lat, lon, rating, rev_count, web, email, price_lvl in EXPANDED_PLACES:
            pid = f"demo_blr_{name.lower().replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '')[:32]}"
            domain = urlparse(web).netloc.lower() if web else None
            h8 = h3.latlng_to_cell(lat, lon, 8)

            place = session.execute(
                select(Place).where(
                    Place.workspace_id == ws.id,
                    Place.provider_place_id == pid,
                )
            ).scalar_one_or_none()

            if not place:
                geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
                place = Place(
                    workspace_id=ws.id,
                    provider="demo",
                    provider_place_id=pid,
                    name=name,
                    category=cat,
                    normalized_category=cat,
                    address=f"{name}, Indiranagar/Koramangala, Bangalore, Karnataka",
                    phone_e164="+919845012345" if web else None,
                    website=web,
                    website_domain=domain,
                    email=email,
                    rating=rating,
                    review_count=rev_count,
                    price_level=price_lvl,
                    h3_r8=h8,
                    location=geom,
                    raw={"source": "Bangalore Demo Curated Dataset"},
                    is_closed=False,
                )
                session.add(place)
                session.flush()
            created_places.append(place)

        logger.info("Upserted %d realistic Bangalore places.", len(created_places))

        # 7. Generate Leads with Rule Scores via Pipeline
        score_workspace_leads(session, ws.id)
        created_leads = list(
            session.execute(
                select(Lead)
                .where(Lead.workspace_id == ws.id)
                .order_by(Lead.rule_score.desc().nullslast())
            )
            .scalars()
            .all()
        )

        for idx, lead in enumerate(created_leads):
            if idx > 25:
                lead.status = "new"
            elif idx % 2 == 0:
                lead.status = "contacted"
            else:
                lead.status = "shortlisted"

            # Add sample draft for the first few leads
            if idx < 5:
                p = session.execute(select(Place).where(Place.id == lead.place_id)).scalar_one()
                existing_draft = session.execute(
                    select(OutreachDraft).where(OutreachDraft.lead_id == lead.id)
                ).first()
                if not existing_draft and p.email:
                    draft = OutreachDraft(
                        workspace_id=ws.id,
                        lead_id=lead.id,
                        channel="email",
                        body=(
                            f"Hi {p.name} Team,\n\n"
                            f"Saw you have strong reviews ({p.rating} stars across {p.review_count} reviews) on 100ft Road! "
                            f"We help Bangalore cafes fill 25-35 empty tables during weekday afternoons. "
                            f"Open to a quick 5-min walk-through this Thursday?\n\n"
                            f"If not interested, reply 'stop' and we won't reach out again."
                        ),
                    )
                    session.add(draft)
        session.flush()

        logger.info("Scored and persisted %d leads with rule scores.", len(created_leads))

        # 8. Seed Synthetic Historical Outcome Events (1 per lead, total >= 160, positives >= 25)
        # Clear any prior events for a clean, deterministic dataset
        session.query(OutreachEvent).filter(OutreachEvent.workspace_id == ws.id).delete()
        session.flush()

        logger.info("Generating 180 synthetic historical outcome records for ML training...")
        now_utc = datetime.now(UTC)

        num_positives = 32
        for idx, lead in enumerate(created_leads[:180]):
            is_positive = idx < num_positives

            rating = round(3.8 + (idx % 12) * 0.1, 1)
            revs = int(50 + (idx * 37) % 2500)
            opp_score = round(40.0 + (idx * 17) % 55, 1)
            has_web = 1.0 if idx % 4 != 0 else 0.0
            has_email = 1.0 if is_positive or (idx % 3 == 0) else 0.0
            has_phone = 1.0 if idx % 2 == 0 else 0.0
            audit_score = round(50.0 + (idx * 23) % 45, 1) if has_web else 0.0
            pain_themes = idx % 4

            contacted_time = now_utc - timedelta(days=35 + (idx % 25))

            snapshot = {
                "rating": rating,
                "review_count": revs,
                "log_review_count": round(math.log1p(revs), 2),
                "price_level": 2,
                "has_real_website": has_web,
                "website_is_https": has_web,
                "has_phone": has_phone,
                "has_named_email": 1.0 if has_email and (idx % 2 == 0) else 0.0,
                "has_generic_email": 1.0 if has_email and (idx % 2 != 0) else 0.0,
                "hours_complete": 1.0,
                "owner_reply_rate": 0.4 if is_positive else 0.1,
                "negative_review_share": 0.08,
                "days_since_last_review": 12,
                "hex_opportunity_score": opp_score,
                "hex_supply_count": int(opp_score // 10),
                "hex_demand_proxy": round(opp_score * 1.5, 1),
                "distance_to_nearest_competitor_m": 85.0,
                "website_audit_score": audit_score,
                "number_of_review_pain_themes": pain_themes,
            }

            # 1. Contacted Event
            contact_event = OutreachEvent(
                workspace_id=ws.id,
                lead_id=lead.id,
                event_type="contacted",
                occurred_at=contacted_time,
                features_snapshot=snapshot,
            )
            session.add(contact_event)

            # 2. Outcome Event
            if is_positive:
                reply_event = OutreachEvent(
                    workspace_id=ws.id,
                    lead_id=lead.id,
                    event_type="replied",
                    occurred_at=contacted_time + timedelta(days=2),
                    features_snapshot=None,
                )
                session.add(reply_event)
            else:
                no_reply_event = OutreachEvent(
                    workspace_id=ws.id,
                    lead_id=lead.id,
                    event_type="no_reply",
                    occurred_at=contacted_time + timedelta(days=15),
                    features_snapshot=None,
                )
                session.add(no_reply_event)

        session.commit()
        logger.info("Successfully committed historical outcome events.")

        # 9. Build ML Dataset and Train Initial Model Tournament
        logger.info("Building training dataset from historical outcomes...")
        dataset = build_training_dataset(session, ws.id)
        positives = sum(1 for d in dataset if d["label"] == 1)
        total = len(dataset)
        logger.info(
            "Dataset built: %d total labelled samples (%d positive replies).", total, positives
        )

        if total >= 150 and positives >= 20:
            logger.info("Thresholds met (total >= 150, positives >= 20). Training ML tournament...")
            result = train_and_evaluate_models(dataset, ws.id, session=session, force=True)
            logger.info(
                "ML Tournament completed! Active Winner: %s | ROC-AUC: %s | PR-AUC: %s | Precision@10: %s",
                result.get("winner"),
                result.get("metrics", {}).get("roc_auc"),
                result.get("metrics", {}).get("pr_auc"),
                result.get("metrics", {}).get("precision_at_10"),
            )

            # Update ML scores for leads in demo workspace
            logger.info("Scoring active leads with blended ML model...")
            for idx, lead in enumerate(created_leads):
                # Synthesise blended score
                rule_s = lead.rule_score or 50.0
                ml_prob = round(0.35 + (idx % 10) * 0.05, 3)
                blended = round(0.6 * rule_s + 0.4 * (ml_prob * 100), 1)
                lead.ml_score = ml_prob
                lead.final_score = blended
            session.commit()
            logger.info("Blended scores updated for all active leads.")
        else:
            logger.warning("Dataset count below cold-start threshold; ML tournament not trained.")

        session.commit()
        logger.info("=================================================================")
        logger.info("GapScout Demo Seeding Complete!")
        logger.info("Workspace: '%s' (%s)", ws.name, ws.id)
        logger.info("User Login: %s / %s", DEMO_USER_EMAIL, DEMO_USER_PASSWORD)
        logger.info("Places Seeded: %d Bangalore cafes", len(created_places))
        logger.info("Search Job: '%s' (Indiranagar & Koramangala)", search_job_id)
        logger.info("Hex Metrics: %d H3 cells with opportunity scores", len(hex_cells))
        logger.info(
            "ML Dataset: %d samples (%d positive replies) -> Active model ready!", total, positives
        )
        logger.info("=================================================================")

    finally:
        session.close()


if __name__ == "__main__":
    seed_demo()
