"""Unit tests for data cleaning, normalisation, duplicate detection, and quality report."""

import uuid
from unittest.mock import MagicMock, patch

import h3
from geoalchemy2.elements import WKTElement

from app.cleaning.duplicates import (
    are_names_fuzzy_match,
    detect_and_merge_duplicates,
    haversine_distance_m,
)
from app.cleaning.email import (
    batch_check_mx_records,
    validate_email_address,
    validate_emails_batch,
)
from app.cleaning.phone import normalize_phone_number
from app.cleaning.pipeline import (
    clean_and_normalize_job_places,
)
from app.cleaning.taxonomy import normalize_category
from app.cleaning.website import normalize_website
from app.models import Place, SearchJob, Workspace


# ==============================================================================
# 1. Category Normalisation Tests (>= 10 messy real-world examples)
# ==============================================================================
def test_category_normalization_messy_examples():
    test_cases = [
        # (raw input, expected normalized output)
        ("Café & Bakery Bar", "cafe"),
        ("Specialty Coffee Shop", "cafe"),
        ("South Indian Family Restaurant", "restaurant"),
        ("Fine Dining & Bistro", "restaurant"),
        ("Anytime Fitness Gym & Club", "gym"),
        ("Ashtanga Yoga & Pilates Studio", "gym"),
        ("Luxury Hair Salon & Spa", "salon"),
        ("Gentlemen's Barber Shop", "salon"),
        ("Smile Orthodontics & Dental Clinic", "dental clinic"),
        ("Dr. Sharma's Dental Care Surgery", "dental clinic"),
        ("IIT-JEE Test Prep & Coaching Institute", "coaching centre"),
        ("Commerce Tuition Classes & Academy", "coaching centre"),
        ("Random Unrelated Heavy Metal Scrap Yard", None),
        ("", None),
        (None, None),
    ]

    for raw, expected in test_cases:
        actual = normalize_category(raw)
        assert actual == expected, f"Failed for category '{raw}': expected {expected}, got {actual}"


# ==============================================================================
# 2. Phone Normalisation Tests (>= 10 messy real-world examples)
# ==============================================================================
def test_phone_normalization_messy_examples():
    test_cases = [
        # (raw phone, expected E.164 with +91 default)
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("080-25251234", "+918025251234"),  # Bangalore landline
        ("+91 (080) 2525-1234", "+918025251234"),
        ("tel:+919876543210", "+919876543210"),
        ("098765 43210", "+919876543210"),
        ("  +91-98765-43210  ", "+919876543210"),
        ("+1 415 555 2671", "+14155552671"),  # US international number
        ("+44 20 7946 0991", "+442079460991"),  # UK international number
        ("98765-43210", "+919876543210"),
        # Invalid cases (must return None)
        ("12345", None),  # Too short
        ("abcdefghij", None),  # Letters
        ("0000000000", None),  # Invalid phone
        ("", None),
        (None, None),
    ]

    for raw, expected in test_cases:
        actual = normalize_phone_number(raw)
        assert actual == expected, f"Failed for phone '{raw}': expected {expected}, got {actual}"


# ==============================================================================
# 3. Website Normalisation Tests (>= 10 messy real-world examples)
# ==============================================================================
def test_website_normalization_messy_examples():
    test_cases = [
        # (raw url, expected clean_url, expected domain, is_social, has_real)
        (
            "https://www.thirdwavecoffee.in/?utm_source=google&utm_medium=cpc&gclid=12345",
            "https://thirdwavecoffee.in/",
            "thirdwavecoffee.in",
            False,
            True,
        ),
        (
            "http://subdomain.bakerycafe.com/menu?ref=gmaps&fbclid=abc",
            "http://subdomain.bakerycafe.com/menu",
            "subdomain.bakerycafe.com",
            False,
            True,
        ),
        (
            "instagram.com/my_specialty_cafe",
            "https://instagram.com/my_specialty_cafe",
            "instagram.com",
            True,
            False,
        ),
        (
            "https://www.facebook.com/pages/BangaloreGym/123456",
            "https://facebook.com/pages/BangaloreGym/123456",
            "facebook.com",
            True,
            False,
        ),
        (
            "https://linktr.ee/bangaloresalon",
            "https://linktr.ee/bangaloresalon",
            "linktr.ee",
            True,
            False,
        ),
        (
            "HTTP://EXAMPLE-DENTAL.COM:8080/home#about",
            "http://example-dental.com/home",
            "example-dental.com",
            False,
            True,
        ),
        (
            "https://cult.fit/gyms/indiranagar?source=maps&sa=X&ved=2ahUKEwj",
            "https://cult.fit/gyms/indiranagar",
            "cult.fit",
            False,
            True,
        ),
        (
            "www.coaching-academy.edu.in",
            "https://coaching-academy.edu.in/",
            "coaching-academy.edu.in",
            False,
            True,
        ),
        (
            "https://wa.me/919876543210?text=Hello",
            "https://wa.me/919876543210",
            "wa.me",
            True,
            False,
        ),
        (
            "https://twitter.com/coffeebar_blr",
            "https://twitter.com/coffeebar_blr",
            "twitter.com",
            True,
            False,
        ),
        # Invalid cases
        (
            "",
            None,
            None,
            False,
            False,
        ),
        (
            "not-a-valid-url-without-dot",
            None,
            None,
            False,
            False,
        ),
    ]

    for raw, exp_url, exp_domain, exp_social, exp_has_real in test_cases:
        res = normalize_website(raw)
        assert res.domain == exp_domain, f"Domain mismatch for '{raw}'"
        assert res.is_social_media_only == exp_social, f"Social mismatch for '{raw}'"
        assert res.has_real_website == exp_has_real, f"Real website mismatch for '{raw}'"
        if exp_url:
            assert res.clean_url == exp_url, f"Clean URL mismatch for '{raw}'"


# ==============================================================================
# 4. Email Normalisation and MX Tests (>= 10 messy real-world examples)
# ==============================================================================
def test_email_validation_messy_examples():
    mock_mx_cache = {
        "example.com": True,
        "company.in": True,
        "nonexistent-domain-xyz-404.com": False,
        "gmail.com": True,
    }

    test_cases = [
        # (raw email, valid_syntax, is_generic, has_valid_mx)
        ("info@example.com", True, True, True),
        ("contact@company.in", True, True, True),
        ("support@company.in", True, True, True),
        ("priya.sharma@company.in", True, False, True),
        ("rahul_verma@example.com", True, False, True),
        ("hello@example.com", True, True, True),
        ("careers@company.in", True, True, True),
        ("ceo@nonexistent-domain-xyz-404.com", True, False, False),
        ("  User.Name+tag@gmail.com  ", True, False, True),
        ("sales@company.in", True, True, True),
        # Invalid syntax examples
        ("not-an-email", False, False, False),
        ("missingatsign.com", False, False, False),
        ("@missingusername.com", False, False, False),
        ("user@.com", False, False, False),
        ("", False, False, False),
        (None, False, False, False),
    ]

    for raw, exp_syntax, exp_generic, exp_mx in test_cases:
        res = validate_email_address(raw, check_mx=True, mx_cache=mock_mx_cache)
        assert res.is_valid_syntax == exp_syntax, f"Syntax validity mismatch for '{raw}'"
        assert res.is_generic == exp_generic, f"Generic mailbox mismatch for '{raw}'"
        assert res.has_valid_mx == exp_mx, f"MX validity mismatch for '{raw}'"


def test_batch_email_and_mx_checking():
    mock_cache = {"fast.com": True}
    with patch("app.cleaning.email.check_domain_mx") as mock_mx:
        mock_mx.side_effect = lambda domain, timeout, cache: domain == "valid.com"
        domains = ["valid.com", "invalid.org", "fast.com"]
        cache = batch_check_mx_records(domains, max_workers=2, mx_cache=mock_cache)

        assert cache["fast.com"] is True
        assert cache["valid.com"] is True
        assert cache["invalid.org"] is False

    emails = ["info@valid.com", "dr.smith@invalid.org", "bad-email"]
    batch_res = validate_emails_batch(emails, mx_cache=cache)
    assert len(batch_res) == 3
    assert batch_res[0].is_valid_syntax and batch_res[0].is_generic and batch_res[0].has_valid_mx
    assert batch_res[1].is_valid_syntax and not batch_res[1].is_generic
    assert not batch_res[1].has_valid_mx
    assert not batch_res[2].is_valid_syntax


# ==============================================================================
# 5. Duplicate Detection and Haversine Distance Tests
# ==============================================================================
def test_haversine_distance():
    # Distance between two known points in Indiranagar, Bangalore (~110 meters)
    lat1, lon1 = 12.971598, 77.641200
    lat2, lon2 = 12.972598, 77.641200
    dist = haversine_distance_m(lat1, lon1, lat2, lon2)
    assert 105.0 < dist < 115.0


def test_fuzzy_name_matching():
    assert are_names_fuzzy_match("Third Wave Coffee Roasters", "Third Wave Coffee", 0.80)
    assert are_names_fuzzy_match("Gold's Gym Indiranagar", "Golds Gym", 0.85)
    assert are_names_fuzzy_match("Cult.fit - Gym in Indiranagar", "Cult Gym Indiranagar", 0.70)
    assert not are_names_fuzzy_match("Starbucks Coffee", "Third Wave Coffee", 0.80)


def test_detect_and_merge_duplicates():
    p1 = MagicMock(spec=Place)
    p1.id = uuid.uuid4()
    p1.name = "Third Wave Coffee"
    p1.location = None
    p1.raw = {"latitude": 12.971598, "longitude": 77.641200}
    p1.website = "https://thirdwavecoffee.in"
    p1.website_domain = "thirdwavecoffee.in"
    p1.phone_e164 = "+919876543210"
    p1.email = None
    p1.rating = 4.5
    p1.review_count = 120
    p1.address = "100 Feet Rd, Indiranagar"
    p1.is_closed = False

    # Second place: very close (~15m away), matching name, has email but missing website
    p2 = MagicMock(spec=Place)
    p2.id = uuid.uuid4()
    p2.name = "Third Wave Coffee Roasters"
    p2.location = None
    p2.raw = {"latitude": 12.971650, "longitude": 77.641250}
    p2.website = None
    p2.website_domain = None
    p2.phone_e164 = None
    p2.email = "hello@thirdwavecoffee.in"
    p2.rating = 4.4
    p2.review_count = 10
    p2.address = None
    p2.is_closed = False

    # Third place: faraway (> 2km away), same name -> NOT a duplicate
    p3 = MagicMock(spec=Place)
    p3.id = uuid.uuid4()
    p3.name = "Third Wave Coffee Koramangala"
    p3.location = None
    p3.raw = {"latitude": 12.935000, "longitude": 77.620000}
    p3.is_closed = False

    places = [p1, p2, p3]
    duplicates_count = detect_and_merge_duplicates(
        places, max_distance_m=50.0, name_similarity_threshold=0.80
    )

    assert duplicates_count == 1
    # Primary (p1) absorbed email from p2
    assert p1.email == "hello@thirdwavecoffee.in"
    # Secondary (p2) flagged as closed duplicate
    assert p2.is_closed is True
    assert p2.raw["is_duplicate"] is True
    assert p2.raw["duplicate_of_id"] == str(p1.id)
    # p3 remains untouched
    assert p3.is_closed is False


# ==============================================================================
# 6. H3 Resolution 8 Computation
# ==============================================================================
def test_h3_resolution_8_computation():
    lat, lon = 12.971598, 77.641200
    expected_hex = h3.latlng_to_cell(lat, lon, 8)
    assert len(expected_hex) == 15
    assert h3.get_resolution(expected_hex) == 8


# ==============================================================================
# 7. End-to-End Pipeline & Data Quality Report on DB
# ==============================================================================
def test_clean_and_normalize_job_places_e2e(db_session):
    # Setup test workspace and search job
    ws = Workspace(name="Cleaning Test WS")
    db_session.add(ws)
    db_session.commit()

    job = SearchJob(
        workspace_id=ws.id,
        category="coffee shop",
        area_name="Indiranagar",
        status="completed",
        cells_total=1,
        cells_done=1,
        places_found=3,
    )
    db_session.add(job)
    db_session.commit()

    # Place 1: Messy raw data
    p1 = Place(
        workspace_id=ws.id,
        provider="gosom",
        provider_place_id="p1_clean",
        name="Blue Tokai Coffee Roasters",
        category="Coffee shop",
        address="Indiranagar, Bangalore",
        phone_e164="080-25251234",
        website="https://bluetokaicoffee.com/?utm_source=google",
        email="info@bluetokaicoffee.com",
        rating=4.6,
        review_count=250,
        location=WKTElement("POINT(77.641200 12.971598)", srid=4326),
        raw={"latitude": 12.971598, "longitude": 77.641200},
    )

    # Place 2: Social media only, generic email, duplicate of p1 (20m away)
    p2 = Place(
        workspace_id=ws.id,
        provider="gosom",
        provider_place_id="p2_clean",
        name="Blue Tokai Coffee",
        category="Cafe",
        address="Indiranagar, Bangalore",
        phone_e164="+91 80 25251234",
        website="https://instagram.com/bluetokaicoffee",
        email="support@bluetokaicoffee.com",
        rating=4.5,
        review_count=15,
        location=WKTElement("POINT(77.641300 12.971650)", srid=4326),
        raw={"latitude": 12.971650, "longitude": 77.641300},
    )

    # Place 3: Permanently closed salon
    p3 = Place(
        workspace_id=ws.id,
        provider="gosom",
        provider_place_id="p3_clean",
        name="Luxe Hair Salon & Spa",
        category="Beauty Parlor",
        address="100ft Rd, Indiranagar",
        phone_e164="9876543210",
        website="http://luxesalon.in",
        email="priya@luxesalon.in",
        rating=3.8,
        review_count=45,
        location=WKTElement("POINT(77.645000 12.975000)", srid=4326),
        raw={"latitude": 12.975000, "longitude": 77.645000, "permanently_closed": True},
    )

    db_session.add_all([p1, p2, p3])
    db_session.commit()

    with patch("app.cleaning.pipeline.batch_check_mx_records") as mock_batch:
        mock_batch.return_value = {
            "bluetokaicoffee.com": True,
            "luxesalon.in": True,
        }

        report = clean_and_normalize_job_places(db_session, job.id)

    # Check report contents
    assert report["total_places"] == 3
    assert report["duplicates_removed"] >= 1
    assert "pct_with_website" in report
    assert "pct_with_phone" in report
    assert "pct_with_email" in report
    assert "pct_rating_coverage" in report

    # Refresh places
    db_session.refresh(p1)
    db_session.refresh(p2)
    db_session.refresh(p3)
    db_session.refresh(job)

    # p1 normalized
    assert p1.normalized_category == "cafe"
    assert p1.phone_e164 == "+918025251234"
    assert p1.website == "https://bluetokaicoffee.com/"
    assert p1.website_domain == "bluetokaicoffee.com"
    assert p1.h3_r8 is not None
    assert p1.raw.get("has_real_website") is True
    assert p1.raw.get("has_generic_email") is True

    # p2 was flagged as duplicate of p1
    assert p2.is_closed is True
    assert p2.raw.get("is_duplicate") is True

    # p3 was permanently closed
    assert p3.is_closed is True
    assert p3.normalized_category == "salon"
    assert p3.raw.get("has_named_email") is True

    # Job params saved quality report
    assert "quality_report" in job.params
    assert job.params["quality_report"]["total_places"] == 3
