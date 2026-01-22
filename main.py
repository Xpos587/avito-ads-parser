"""
Main entry point for Avito Ads Parser pipeline.

Pipeline: HTML (Avito) -> parsing -> API enrichment -> coverage analysis
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pandas as pd

from src.analyzer import find_missing_coverage, generate_coverage_report
from src.enricher import enrich_all_ads
from src.parser import parse_html_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# File paths
DATA_DIR = Path("data")
HTML_FILES = [DATA_DIR / "site1.html", DATA_DIR / "site2.html"]
OUTPUT_CSV = DATA_DIR / "output.csv"

# Output files
ADS_RAW_CSV = DATA_DIR / "ads_raw.csv"
ADS_ENRICHED_CSV = DATA_DIR / "ads_enriched.csv"
MISSING_COVERAGE_CSV = DATA_DIR / "missing_coverage.csv"


def step1_parse_html() -> pd.DataFrame:
    """
    Step 1: Parse HTML files and extract ads.

    Returns:
        DataFrame with parsed ads.
    """
    logger.info("=== Step 1: Parsing HTML files ===")

    ads = parse_html_files(HTML_FILES)
    logger.info(f"Found {len(ads)} ads across {len(HTML_FILES)} files")

    # Convert to DataFrame and save
    df = pd.DataFrame([ad.to_dict() for ad in ads])
    df.to_csv(ADS_RAW_CSV, index=False)
    logger.info(f"Saved raw ads to {ADS_RAW_CSV}")

    return df


async def step2_enrich_ads(ads_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 2: Enrich ads via API.

    Args:
        ads_df: DataFrame with parsed ads.

    Returns:
        DataFrame with enriched ads.
    """
    logger.info("=== Step 2: Enriching ads via API ===")

    # Convert to list of dicts for API processing
    ads_list = ads_df.to_dict("records")

    # Enrich via API
    enriched_ads, _stats = await enrich_all_ads(
        ads_list,
        batch_size=200,
        rate_limit_delay=0.5,
    )

    # Convert to DataFrame and save
    df = pd.DataFrame(enriched_ads)
    df.to_csv(ADS_ENRICHED_CSV, index=False)
    logger.info(f"Saved enriched ads to {ADS_ENRICHED_CSV}")

    return df


def step3_analyze_coverage(enriched_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 3: Analyze coverage and find missing combinations.

    Args:
        enriched_df: DataFrame with enriched ads.

    Returns:
        DataFrame with missing combinations.
    """
    logger.info("=== Step 3: Analyzing coverage ===")

    # Find missing combinations
    missing_df = find_missing_coverage(
        ADS_ENRICHED_CSV,
        OUTPUT_CSV,
        MISSING_COVERAGE_CSV,
    )

    # Save missing coverage
    missing_df.to_csv(MISSING_COVERAGE_CSV, index=False)
    logger.info(f"Saved missing coverage to {MISSING_COVERAGE_CSV}")

    # Generate and log coverage report
    report = generate_coverage_report(ADS_ENRICHED_CSV, OUTPUT_CSV)
    logger.info("=== Coverage Report ===")
    logger.info(f"Total combinations: {report['total_combinations']}")
    logger.info(f"Covered combinations: {report['covered_combinations']}")
    logger.info(f"Missing combinations: {report['missing_combinations']}")
    logger.info(f"Coverage: {report['coverage_percentage']}%")

    return missing_df


async def run_pipeline() -> None:
    """
    Run the complete pipeline.
    """
    logger.info("Starting Avito Ads Parser Pipeline")
    logger.info("=" * 50)

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    # Step 1: Parse HTML
    ads_df = step1_parse_html()
    if ads_df.empty:
        logger.warning("No ads found in HTML files, exiting")
        return

    # Step 2: Enrich via API
    enriched_df = await step2_enrich_ads(ads_df)

    # Step 3: Analyze coverage
    step3_analyze_coverage(enriched_df)

    logger.info("=" * 50)
    logger.info("Pipeline completed successfully!")
    logger.info("Output files:")
    logger.info(f"  - {ADS_RAW_CSV}")
    logger.info(f"  - {ADS_ENRICHED_CSV}")
    logger.info(f"  - {MISSING_COVERAGE_CSV}")
    logger.info("  - logs/api_log.txt")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
