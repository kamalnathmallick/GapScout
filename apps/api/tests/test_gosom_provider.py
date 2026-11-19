"""Tests for GosomScraperProvider HTTP interactions, polling, and timeouts."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.providers.base import SearchOptions
from app.providers.gosom import GosomScraperError, GosomScraperProvider, GosomTimeoutError


def test_create_job_success() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"id": "test-job-uuid-123"}
    mock_client.post.return_value = mock_resp

    provider = GosomScraperProvider(base_url="http://mock-scraper:8080", client=mock_client)
    job_id = provider.create_job("cafes in Indiranagar", SearchOptions(zoom=16, depth=2))

    assert job_id == "test-job-uuid-123"
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "http://mock-scraper:8080/api/v1/jobs"
    assert kwargs["json"]["keywords"] == ["cafes in Indiranagar"]
    assert kwargs["json"]["zoom"] == 16
    assert kwargs["json"]["depth"] == 2


def test_poll_until_complete_with_retries() -> None:
    mock_client = MagicMock(spec=httpx.Client)

    # 1st call: pending, 2nd call: running, 3rd call: completed
    resp1 = MagicMock(status_code=200)
    resp1.raise_for_status.return_value = None
    resp1.json.return_value = {"status": "pending"}

    resp2 = MagicMock(status_code=200)
    resp2.raise_for_status.return_value = None
    resp2.json.return_value = {"status": "running"}

    resp3 = MagicMock(status_code=200)
    resp3.raise_for_status.return_value = None
    resp3.json.return_value = {"Status": "ok", "ID": "job-123"}

    mock_client.get.side_effect = [resp1, resp2, resp3]

    provider = GosomScraperProvider(
        base_url="http://mock-scraper:8080",
        client=mock_client,
        initial_poll_interval=0.01,
        max_poll_interval=0.05,
    )

    result = provider.poll_until_complete("job-123")
    assert result["Status"] == "ok"
    assert mock_client.get.call_count == 3


def test_poll_timeout_raises_gosom_timeout_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    resp = MagicMock(status_code=200)
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"status": "running"}
    mock_client.get.return_value = resp

    provider = GosomScraperProvider(
        base_url="http://mock-scraper:8080",
        client=mock_client,
        timeout=0.05,
        initial_poll_interval=0.01,
    )

    with pytest.raises(GosomTimeoutError):
        provider.poll_until_complete("job-timeout")


def test_poll_failure_status_raises_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    resp = MagicMock(status_code=200)
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"status": "failed"}
    mock_client.get.return_value = resp

    provider = GosomScraperProvider(
        base_url="http://mock-scraper:8080",
        client=mock_client,
        initial_poll_interval=0.01,
    )

    with pytest.raises(GosomScraperError, match="terminated with failure status"):
        provider.poll_until_complete("job-failed")


def test_download_results_success() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    resp = MagicMock(status_code=200)
    resp.raise_for_status.return_value = None
    resp.text = "title,place_id\nTest Cafe,place_1"
    mock_client.get.return_value = resp

    provider = GosomScraperProvider(base_url="http://mock-scraper:8080", client=mock_client)
    csv_text = provider.download_results("job-123")

    assert "Test Cafe" in csv_text
    mock_client.get.assert_called_once_with("http://mock-scraper:8080/api/v1/jobs/job-123/download")
