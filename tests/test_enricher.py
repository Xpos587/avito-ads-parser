"""
Tests for API enricher module.

Following SRP: focused testing of enrichment logic only.
Using mocks to avoid actual API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.enricher import (
    APIError,
    AuthError,
    EnrichmentStats,
    RateLimitError,
    enrich_all_ads,
    enrich_batch,
)


class TestEnrichmentStats:
    """Test EnrichmentStats dataclass."""

    def test_empty_stats(self):
        """Test stats with no data."""
        stats = EnrichmentStats()
        assert stats.total_sent == 0
        assert stats.total_success == 0
        assert stats.total_failed == 0
        assert stats.success_rate() == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = EnrichmentStats(total_sent=100, total_success=80, total_failed=20)
        assert stats.success_rate() == 80.0

    def test_success_rate_zero_sent(self):
        """Test success rate when nothing sent."""
        stats = EnrichmentStats()
        assert stats.success_rate() == 0.0


class TestEnrichBatch:
    """Test batch enrichment."""

    @pytest.mark.asyncio
    async def test_successful_enrichment(self, api_success_response):
        """Test successful API enrichment."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = api_success_response

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()
        titles = ["Test Title"]

        result = await enrich_batch(titles, mock_client, stats)

        assert len(result) == 1
        assert result[0]["marka"] == "jcb"
        assert stats.total_success == 1

    @pytest.mark.asyncio
    async def test_auth_error(self):
        """Test authentication error handling."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()

        with pytest.raises(AuthError):
            await enrich_batch(["Test"], mock_client, stats)

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Test rate limit with retry."""
        mock_response_429 = Mock(spec=httpx.Response)
        mock_response_429.status_code = 429

        mock_response_200 = Mock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"processed_data": []}

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])

        stats = EnrichmentStats()
        _ = await enrich_batch(["Test"], mock_client, stats, retry=2)

        assert stats.rate_limit_hits == 1
        assert stats.retry_count == 1

    @pytest.mark.asyncio
    async def test_server_error_retry(self):
        """Test server error with retry."""
        mock_response_500 = Mock(spec=httpx.Response)
        mock_response_500.status_code = 500

        mock_response_200 = Mock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"processed_data": []}

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[mock_response_500, mock_response_200])

        stats = EnrichmentStats()
        await enrich_batch(["Test"], mock_client, stats, retry=2)

        assert stats.retry_count == 1

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test timeout error handling."""
        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats, retry=1)

        assert result == []
        assert stats.timeout_errors == 1

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of non-JSON response."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats)

        assert result == []
        assert stats.other_errors == 1

    @pytest.mark.asyncio
    async def test_empty_processed_data(self):
        """Test handling of empty processed_data."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"processed_data": []}

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats)

        assert result == []

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test behavior when all retries are exhausted."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats, retry=3)

        assert result == []
        assert stats.total_failed == 1

    @pytest.mark.asyncio
    async def test_unexpected_status_code(self):
        """Test handling of unexpected status code (lines 141-144)."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 418  # I'm a teapot
        mock_response.text = "Unexpected error"

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats)

        assert result == []
        assert stats.other_errors == 1

    @pytest.mark.asyncio
    async def test_timeout_exhausted_retries(self):
        """Test timeout with all retries exhausted (lines 153-160)."""
        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        stats = EnrichmentStats()
        result = await enrich_batch(["Test"], mock_client, stats, retry=1)

        assert result == []
        assert stats.timeout_errors == 1
        assert stats.total_failed == 1


class TestEnrichAllAds:
    """Test full enrichment pipeline."""

    @pytest.mark.asyncio
    async def test_successful_enrichment(self, sample_ads_df):
        """Test successful enrichment of all ads."""
        api_response = {
            "processed_data": [
                {
                    "title": sample_ads_df.iloc[0]["title"],
                    "marka": "jcb",
                    "model": "JS 220",
                    "group0": "гидравлический компонент",
                }
            ]
        }

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = api_response

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("src.enricher.httpx.AsyncClient", return_value=mock_client):
            ads_list = sample_ads_df.to_dict("records")

            result, stats = await enrich_all_ads(
                ads_list,
                batch_size=2,
                rate_limit_delay=0.0,
            )

            # Only the enriched item is returned
            assert len(result) == 1
            assert result[0]["marka"] == "jcb"
            assert stats.total_sent == 2
            assert stats.total_success == 1

    @pytest.mark.asyncio
    async def test_batch_splitting(self):
        """Test that ads are split into correct batch sizes."""

        # Create API response that returns all items
        def create_response(count):
            return {
                "processed_data": [
                    {"title": f"Item {i}", "marka": "test", "group0": "test"} for i in range(count)
                ]
            }

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call: 200 items, second call: 50 items
            count = 200 if call_count == 1 else 50
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.json.return_value = create_response(count)
            return mock_response

        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("src.enricher.httpx.AsyncClient", return_value=mock_client):
            # Create 250 ads (more than batch size of 200)
            ads_list = [{"title": f"Ad {i}"} for i in range(250)]

            result, stats = await enrich_all_ads(
                ads_list,
                batch_size=200,
                rate_limit_delay=0.0,
            )

            # Should make 2 API calls
            assert call_count == 2
            assert stats.total_sent == 250
            assert len(result) == 250


class TestAPIErrors:
    """Test custom API exceptions."""

    def test_api_error_is_exception(self):
        """Test APIError base class."""
        error = APIError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Too many requests")
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_auth_error(self):
        """Test AuthError."""
        error = AuthError("Invalid API key")
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)
