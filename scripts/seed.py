"""Seed the demo workspace with 20 fake Bangalore places.

Idempotent: rerunning updates the same rows via the provider unique key.
Run after `make migrate`: `make seed`.
"""

import sys
from typing import Any
from urllib.parse import urlparse

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, inspect, select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal, engine
from app.models import Place, Workspace

DEMO_WORKSPACE = "GapScout Demo"
PROVIDER = "seed"

# name, category, lat, lon, rating, reviews, website, email, price_level
RAW_PLACES: list[tuple[str, str, float, float, float, int, str | None, str | None, int | None]] = [
    (
        "Indiranagar Coffee Co",
        "cafe",
        12.9784,
        77.6408,
        4.6,
        320,
        "https://indiranagarcoffee.example",
        "hello@indiranagarcoffee.example",
        2,
    ),
    (
        "100ft Restaurant",
        "restaurant",
        12.9740,
        77.6412,
        4.2,
        890,
        "https://100ft.example",
        "book@100ft.example",
        3,
    ),
    (
        "Iron House Gym",
        "gym",
        12.9802,
        77.6350,
        4.0,
        210,
        "https://ironhouse.example",
        "join@ironhouse.example",
        1,
    ),
    ("Blossom Salon", "salon", 12.9760, 77.6450, 3.8, 95, None, None, 2),
    (
        "Smile Studio Dental",
        "dental_clinic",
        12.9725,
        77.6380,
        4.7,
        410,
        "https://smilestudio.example",
        "care@smilestudio.example",
        3,
    ),
    (
        "Ace Coaching Centre",
        "coaching_centre",
        12.9830,
        77.6420,
        4.1,
        150,
        "https://acecoaching.example",
        "admissions@acecoaching.example",
        2,
    ),
    (
        "Domlur Cafe",
        "cafe",
        12.9610,
        77.6385,
        4.3,
        275,
        "https://domlurcafe.example",
        "hi@domlurcafe.example",
        2,
    ),
    ("Koramangala Kitchen", "restaurant", 12.9350, 77.6240, 4.4, 1200, None, None, 3),
    (
        "Halasuru Fitness",
        "gym",
        12.9755,
        77.6250,
        3.9,
        88,
        "https://halasurufitness.example",
        None,
        1,
    ),
    (
        "CMH Road Salon",
        "salon",
        12.9780,
        77.6300,
        4.2,
        130,
        "https://cmhroad.example",
        "hello@cmhroad.example",
        2,
    ),
    (
        "Indiranagar Dental Care",
        "dental_clinic",
        12.9700,
        77.6430,
        4.5,
        260,
        "https://idcare.example",
        "front@idcare.example",
        3,
    ),
    ("Vidyaranya Coaching", "coaching_centre", 12.9680, 77.6320, 3.7, 64, None, None, 1),
    (
        "Third Wave Coffee",
        "cafe",
        12.9790,
        77.6435,
        4.8,
        540,
        "https://thirdwave.example",
        "indiranagar@thirdwave.example",
        2,
    ),
    (
        "Nagarjuna Restaurant",
        "restaurant",
        12.9765,
        77.6285,
        4.6,
        1500,
        "https://nagarjuna.example",
        "reserve@nagarjuna.example",
        3,
    ),
    (
        "Cult Fit Indiranagar",
        "gym",
        12.9735,
        77.6460,
        4.4,
        700,
        "https://cultfit.example",
        "support@cultfit.example",
        2,
    ),
    ("Bounce Salon", "salon", 12.9810, 77.6380, 3.6, 45, None, None, 1),
    (
        "Perfect 32 Dental",
        "dental_clinic",
        12.9748,
        77.6340,
        4.9,
        620,
        "https://perfect32.example",
        "smile@perfect32.example",
        3,
    ),
    (
        "Base Coaching",
        "coaching_centre",
        12.9820,
        77.6470,
        4.0,
        110,
        "https://basecoaching.example",
        "info@basecoaching.example",
        2,
    ),
    (
        "Glen's Bakehouse",
        "cafe",
        12.9690,
        77.6415,
        4.5,
        980,
        "https://glens.example",
        "hello@glens.example",
        2,
    ),
    (
        "Toit",
        "restaurant",
        12.9750,
        77.6355,
        4.7,
        3200,
        "https://toit.example",
        "events@toit.example",
        3,
    ),
]


def _domain(website: str | None) -> str | None:
    if not website:
        return None
    host = urlparse(website).hostname or ""
    return host.removeprefix("www.") or None


def _row(workspace_id: Any, index: int, data: tuple[Any, ...]) -> dict[str, Any]:
    name, category, lat, lon, rating, reviews, website, email, price_level = data
    return {
        "workspace_id": workspace_id,
        "provider": PROVIDER,
        "provider_place_id": f"seed-{index:03d}",
        "name": name,
        "category": category,
        "normalized_category": category,
        "address": f"{name}, Indiranagar, Bengaluru, Karnataka",
        "phone_e164": f"+91804100{index:04d}",
        "website": website,
        "website_domain": _domain(website),
        "email": email,
        "rating": rating,
        "review_count": reviews,
        "price_level": price_level,
        "location": WKTElement(f"POINT({lon} {lat})", srid=4326),
        "opening_hours": {"monday": "09:00-21:00"},
        "is_closed": False,
        "raw": {"seed": True, "area": "Indiranagar"},
        "last_seen_at": func.now(),
    }


def seed() -> int:
    if not inspect(engine).has_table("places"):
        print("Schema missing. Run `make migrate` first.")
        return 1

    with SessionLocal() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.name == DEMO_WORKSPACE))
        if workspace is None:
            workspace = Workspace(name=DEMO_WORKSPACE)
            session.add(workspace)
            session.flush()

        for index, data in enumerate(RAW_PLACES, start=1):
            row = _row(workspace.id, index, data)
            update_columns = {
                key: value
                for key, value in row.items()
                if key not in {"workspace_id", "provider", "provider_place_id"}
            }
            session.execute(
                insert(Place)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["workspace_id", "provider", "provider_place_id"],
                    set_=update_columns,
                )
            )

        session.commit()

    with SessionLocal() as session:
        total = session.scalar(
            select(func.count()).select_from(Place).where(Place.provider == PROVIDER)
        )

    print(f"Seed complete: workspace '{DEMO_WORKSPACE}', {total} places (idempotent upsert).")
    return 0


if __name__ == "__main__":
    sys.exit(seed())
