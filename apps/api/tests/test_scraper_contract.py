"""Scraper contract tests verifying parsing against recorded gosom scraper outputs."""

from pathlib import Path

import pytest

from app.providers.base import PlaceDTO
from app.providers.gosom import GosomScraperProvider

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RECORDED_CSV_PATH = FIXTURES_DIR / "gosom_results.csv"


@pytest.fixture
def provider() -> GosomScraperProvider:
    return GosomScraperProvider(base_url="http://mock-scraper:8080")


@pytest.fixture
def recorded_csv() -> str:
    assert RECORDED_CSV_PATH.exists(), f"Recorded CSV fixture not found at {RECORDED_CSV_PATH}"
    return RECORDED_CSV_PATH.read_text(encoding="utf-8")


def test_contract_parses_recorded_csv(provider: GosomScraperProvider, recorded_csv: str):
    """Verify that recorded scraper CSV output parses into RawPlace objects adhering to contract."""
    raw_places = provider.parse_csv_to_raw_places(recorded_csv)
    assert len(raw_places) > 0, "Expected non-empty list of places from recorded CSV"

    for raw in raw_places:
        assert raw.provider == "gosom"
        assert raw.provider_place_id, "Place must have a non-empty provider_place_id"
        assert isinstance(raw.data, dict)


def test_contract_maps_to_valid_place_dtos(provider: GosomScraperProvider, recorded_csv: str):
    """Verify all parsed raw places map cleanly to validated PlaceDTO domain instances."""
    raw_places = provider.parse_csv_to_raw_places(recorded_csv)
    dtos: list[PlaceDTO] = [provider.to_place_dto(r) for r in raw_places]

    assert len(dtos) == len(raw_places)

    names = [d.name for d in dtos]
    assert any(names), "At least some places must have valid business names"

    for dto in dtos:
        # Schema invariants
        assert dto.provider == "gosom"
        assert dto.provider_place_id
        assert dto.name
        assert dto.review_count >= 0

        # Coordinates if present must be valid WGS84
        if dto.latitude is not None:
            assert -90.0 <= dto.latitude <= 90.0
        if dto.longitude is not None:
            assert -180.0 <= dto.longitude <= 180.0

        # Rating if present must be within [1.0, 5.0]
        if dto.rating is not None:
            assert 1.0 <= dto.rating <= 5.0

        # Reviews if present must be list of ReviewDTO
        assert isinstance(dto.reviews, list)
        for rev in dto.reviews:
            if rev.rating is not None:
                assert 1 <= rev.rating <= 5


def test_contract_handles_corrupt_or_malformed_csv(provider: GosomScraperProvider):
    """Verify parser resilience against missing headers, null bytes, and malformed rows."""
    malformed_csv = (
        "title,place_id,latitude,longitude,review_rating,user_reviews,open_hours\n"
        'Broken Place,,not_a_float,1000.0,999.0,"not json","{invalid json"\n'
        ",,,\x00,,\n"
        'Valid Mini,cid_999,12.9716,77.5946,4.2,"[]","{}"\n'
    )

    raw_places = provider.parse_csv_to_raw_places(malformed_csv)
    assert len(raw_places) >= 2

    # Verify to_place_dto does not raise exception on corrupt fields
    dtos = [provider.to_place_dto(r) for r in raw_places]
    assert len(dtos) == len(raw_places)

    # Valid mini place parsed correctly
    valid = next(d for d in dtos if d.provider_place_id == "cid_999")
    assert valid.name == "Valid Mini"
    assert valid.latitude == 12.9716
    assert valid.rating == 4.2
    assert valid.reviews == []
