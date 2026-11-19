"""Tests for defensive CSV and JSON parsing in GosomScraperProvider."""

from pathlib import Path

from app.providers.base import RawPlace
from app.providers.gosom import GosomScraperProvider

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "gosom_results.csv"


def test_parse_real_sample_csv() -> None:
    provider = GosomScraperProvider()
    csv_text = SAMPLE_CSV_PATH.read_text(encoding="utf-8")
    raw_places = provider.parse_csv_to_raw_places(csv_text)

    # 8 places in the Indiranagar sample fixture
    assert len(raw_places) == 8

    dtos = [provider.to_place_dto(rp) for rp in raw_places]
    assert len(dtos) == 8

    # Verify first place: ARAKU Coffee
    araku = next((p for p in dtos if "ARAKU Coffee" in p.name), None)
    assert araku is not None
    assert araku.provider == "gosom"
    assert araku.provider_place_id == "ChIJu3MeVd0XrjsRej9BlCg4hv4"
    assert araku.rating == 4.0
    assert araku.review_count == 2775
    assert araku.latitude is not None and abs(araku.latitude - 12.969946) < 0.001
    assert araku.longitude is not None and abs(araku.longitude - 77.639173) < 0.001
    assert araku.is_closed is False
    assert araku.opening_hours is not None
    assert "Friday" in araku.opening_hours
    assert len(araku.reviews) == 5
    assert araku.reviews[0].author_name == "Anupama Pandey"
    assert araku.reviews[0].rating == 5


def test_defensive_parsing_malformed_json_and_missing_fields() -> None:
    provider = GosomScraperProvider()

    malformed_csv = (
        "title,place_id,user_reviews,open_hours,emails,price_range,review_rating,"
        "review_count,status\n"
        'Broken Cafe,,{not valid json},"{"Monday": invalid}",[malformed email],$$$,'
        "4.5,12,Permanently closed\n"
    )

    raw_places = provider.parse_csv_to_raw_places(malformed_csv)
    assert len(raw_places) == 1

    dto = provider.to_place_dto(raw_places[0])
    assert dto.name == "Broken Cafe"
    # Fallback ID was generated because place_id was empty
    assert dto.provider_place_id.startswith("fallback_")
    # Malformed reviews gracefully become empty list
    assert dto.reviews == []
    # Malformed hours gracefully become None
    assert dto.opening_hours is None
    # Price level parsed from $$$
    assert dto.price_level == 3
    assert dto.rating == 4.5
    assert dto.review_count == 12
    # Status detected as closed
    assert dto.is_closed is True


def test_defensive_parsing_unicode_and_owner_replies() -> None:
    provider = GosomScraperProvider()

    raw_row = {
        "title": "Café Über ☕ & Brunch 🎉",
        "place_id": "test_id_123",
        "category": "Coffee shop",
        "latitude": "12.95",
        "longitude": "77.65",
        "price_range": "₹₹",
        "user_reviews": (
            '[{"Name": "Rahul S", "Rating": 5, "Description": "Great café! ✨", '
            '"reply_text_original": "Thank you for visiting!"}]'
        ),
        "emails": '["owner@cafe-uber.example.com", "info@cafe-uber.example.com"]',
        "status": "Operational",
    }

    raw_place = RawPlace(provider="gosom", provider_place_id="test_id_123", data=raw_row)
    dto = provider.to_place_dto(raw_place)

    assert dto.name == "Café Über ☕ & Brunch 🎉"
    assert dto.price_level == 2
    assert dto.email == "owner@cafe-uber.example.com"
    assert len(dto.reviews) == 1
    assert dto.reviews[0].author_name == "Rahul S"
    assert dto.reviews[0].text == "Great café! ✨"
    assert dto.reviews[0].owner_replied is True
    assert dto.is_closed is False
