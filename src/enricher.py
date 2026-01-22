"""
API Enricher for Avito Ads.

Enriches advertisement titles using the top505.ru API.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
_ = load_dotenv()

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/api_log.txt"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "https://top505.ru/api/item_batch"
API_KEY = os.getenv("TOP505_API_KEY", "")
if not API_KEY:
    raise ValueError(
        "TOP505_API_KEY environment variable is not set. "
        "Please set it in a .env file or your environment."
    )

# HTTP Status Codes
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500


@dataclass
class EnrichmentStats:
    """Statistics for API enrichment."""

    total_sent: int = 0
    total_success: int = 0
    total_failed: int = 0
    rate_limit_hits: int = 0
    timeout_errors: int = 0
    other_errors: int = 0
    retry_count: int = 0

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_sent == 0:
            return 0.0
        return (self.total_success / self.total_sent) * 100


class APIError(Exception):
    """Base exception for API errors."""

    pass


class RateLimitError(APIError):
    """Raised when rate limit is hit."""

    pass


class AuthError(APIError):
    """Raised when authentication fails."""

    pass


def _get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


async def enrich_batch(
    titles: list[str],
    client: httpx.AsyncClient,
    stats: EnrichmentStats,
    retry: int = 3,
) -> list[dict[str, Any]]:
    """
    Enrich a batch of titles via the API.

    Args:
        titles: List of titles to enrich.
        client: HTTP client for making requests.
        stats: Statistics object to track results.
        retry: Number of retries on failure.

    Returns:
        List of enriched data dictionaries.
    """
    payload = {
        "source": "1c",
        "data": [{"title": t, "day": _get_today_date()} for t in titles],
    }

    for attempt in range(retry):
        try:
            stats.total_sent += len(titles)

            response = await client.post(
                API_URL,
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=30.0,
            )

            if response.status_code == HTTP_OK:
                try:
                    data = response.json()
                    processed = data.get("processed_data", [])
                    stats.total_success += len(processed)
                    logger.info(f"Successfully enriched {len(processed)}/{len(titles)} items")
                    return processed
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    stats.other_errors += 1
                    return []

            elif response.status_code == HTTP_UNAUTHORIZED:
                logger.error("Authentication failed - check API key")
                stats.other_errors += len(titles)
                raise AuthError("Invalid API key")

            elif response.status_code == HTTP_RATE_LIMIT:
                stats.rate_limit_hits += 1
                wait_time = 2 ** (attempt + 1)  # Exponential backoff
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
                stats.retry_count += 1
                continue

            elif response.status_code >= HTTP_SERVER_ERROR:
                logger.warning(f"Server error {response.status_code}, retrying...")
                await asyncio.sleep(1)
                stats.retry_count += 1
                continue

            else:
                logger.error(f"Unexpected status code: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                stats.other_errors += len(titles)
                return []

        except AuthError:
            # Re-raise auth errors immediately
            raise
        except httpx.TimeoutException:
            stats.timeout_errors += len(titles)
            logger.warning(f"Timeout on attempt {attempt + 1}/{retry}")
            if attempt < retry - 1:
                await asyncio.sleep(1)
                stats.retry_count += 1
                continue

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            stats.other_errors += len(titles)
            return []

    # All retries exhausted
    stats.total_failed += len(titles)
    logger.error(f"Failed to enrich batch after {retry} attempts")
    return []


async def enrich_all_ads(
    ads: list[dict[str, Any]],
    batch_size: int = 200,
    rate_limit_delay: float = 0.5,
) -> tuple[list[dict[str, Any]], EnrichmentStats]:
    """
    Enrich all ads via the API with rate limiting.

    Args:
        ads: List of ad dictionaries with 'title' field.
        batch_size: Number of items per batch (max 200).
        rate_limit_delay: Delay between batches in seconds.

    Returns:
        Tuple of (enriched ads list, statistics).
    """
    stats = EnrichmentStats()
    results = []

    async with httpx.AsyncClient() as client:
        for i in range(0, len(ads), batch_size):
            batch = ads[i : i + batch_size]
            titles = [a["title"] for a in batch]

            total_batches = (len(ads) + batch_size - 1) // batch_size
            current_batch = i // batch_size + 1
            logger.info(f"Processing batch {current_batch}/{total_batches}")

            enriched = await enrich_batch(titles, client, stats)

            # Merge original ad data with enriched data
            for j, enriched_item in enumerate(enriched):
                merged = {**batch[j], **enriched_item}
                results.append(merged)

            # Rate limiting delay
            if i + batch_size < len(ads):
                await asyncio.sleep(rate_limit_delay)

    # Log final statistics
    logger.info("=== Enrichment Complete ===")
    logger.info(f"Total sent: {stats.total_sent}")
    logger.info(f"Total success: {stats.total_success}")
    logger.info(f"Total failed: {stats.total_failed}")
    logger.info(f"Success rate: {stats.success_rate():.1f}%")
    logger.info(f"Rate limit hits: {stats.rate_limit_hits}")
    logger.info(f"Timeout errors: {stats.timeout_errors}")
    logger.info(f"Other errors: {stats.other_errors}")
    logger.info(f"Total retries: {stats.retry_count}")

    return results, stats
