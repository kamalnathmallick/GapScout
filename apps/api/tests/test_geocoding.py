"""Tests for Nominatim geocoding service and caching."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.services.geocoding import GeocodingError, geocode_area


def test_geocode_area_success_and_caching() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = [
        {
            "boundingbox": ["12.9500", "12.9900", "77.6200", "77.6600"],
            "display_name": "Indiranagar, Bengaluru, Karnataka, India",
        }
    ]
    mock_client.get.return_value = mock_resp

    # First call: hits HTTP client
    bbox1 = geocode_area("Indiranagar Test 1", client=mock_client)
    assert bbox1.min_lat == 12.95
    assert bbox1.max_lat == 12.99
    assert bbox1.min_lon == 77.62
    assert bbox1.max_lon == 77.66
    assert mock_client.get.call_count == 1

    # Second call for same query: hits cache, client not called again
    bbox2 = geocode_area("Indiranagar Test 1", client=mock_client)
    assert bbox2.center_lat == bbox1.center_lat
    assert mock_client.get.call_count == 1


def test_geocode_area_not_found_raises_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = []
    mock_client.get.return_value = mock_resp

    with pytest.raises(GeocodingError, match="Could not find coordinates"):
        geocode_area("NonexistentLocation12345XYZ", client=mock_client)
