"""
Coverage Analyzer for Avito Ads.

Analyzes the coverage between enriched ads and target catalog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path


def find_missing_coverage(
    enriched_path: str | Path,
    output_path: str | Path,
    output_missing_path: str | Path,
) -> pd.DataFrame:
    """
    Find missing combinations in the coverage.

    Compares the enriched ads against the target catalog to find
    missing group0 + group1 + group2 combinations.

    Args:
        enriched_path: Path to ads_enriched.csv
        output_path: Path to output.csv (target catalog)
        output_missing_path: Path to save missing_coverage.csv

    Returns:
        DataFrame with missing combinations.
    """
    # Load data
    enriched_df = pd.read_csv(enriched_path)
    output_df = pd.read_csv(output_path)

    # Normalize group columns to string and handle NaN
    group_cols = ["group0", "group1", "group2"]
    for col in group_cols:
        enriched_df[col] = enriched_df[col].fillna("").astype(str)
        output_df[col] = output_df[col].fillna("").astype(str)

    # Get existing combinations from enriched ads
    existing_combinations = enriched_df[group_cols].drop_duplicates().reset_index(drop=True)

    # Get target combinations from output catalog
    target_combinations = output_df[group_cols].drop_duplicates().reset_index(drop=True)

    # Find missing combinations using merge with indicator
    merged = target_combinations.merge(
        existing_combinations,
        on=group_cols,
        how="left",
        indicator=True,
    )

    # Filter for left_only (missing in enriched)
    missing = merged[merged["_merge"] == "left_only"].copy()

    if len(missing) == 0:
        print("No missing coverage found - all combinations are covered!")
        return pd.DataFrame(columns=[*group_cols, "reason"])

    # Enhance with additional info from output catalog
    missing_with_info = missing.merge(
        output_df,
        on=group_cols,
        how="left",
    )

    # Select relevant columns - only use columns that exist
    additional_cols = ["marka", "model"]
    available_cols = [
        col for col in [*group_cols, *additional_cols] if col in missing_with_info.columns
    ]
    result_df = missing_with_info[available_cols].copy()
    result_df = result_df.drop_duplicates()

    # Add missing columns with empty values if needed
    for col in additional_cols:
        if col not in result_df.columns:
            result_df[col] = ""

    # Add reason column
    result_df["reason"] = "отсутствует"

    # Reorder columns to have reason at the end
    result_df = result_df[[*group_cols, "marka", "model", "reason"]]

    # Sort by frequency in output catalog (most common first)
    freq = output_df[group_cols].value_counts().reset_index(name="frequency")
    result_df = result_df.merge(freq, on=group_cols, how="left")
    result_df = result_df.sort_values("frequency", ascending=False)
    result_df = result_df.drop(columns=["frequency"])

    # Save to CSV
    result_df.to_csv(output_missing_path, index=False)

    return result_df


def generate_coverage_report(
    enriched_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """
    Generate a coverage report comparing enriched ads to target catalog.

    Args:
        enriched_path: Path to ads_enriched.csv
        output_path: Path to output.csv (target catalog)

    Returns:
        Dictionary with coverage statistics.
    """
    enriched_df = pd.read_csv(enriched_path)
    output_df = pd.read_csv(output_path)

    # Normalize group columns
    group_cols = ["group0", "group1", "group2"]
    for col in group_cols:
        enriched_df[col] = enriched_df[col].fillna("").astype(str)
        output_df[col] = output_df[col].fillna("").astype(str)

    # Get unique combinations
    enriched_combos = enriched_df[group_cols].drop_duplicates()
    output_combos = output_df[group_cols].drop_duplicates()

    total_combos = len(output_combos)

    # Count how many target combinations are covered by enriched ads
    merged = output_combos.merge(
        enriched_combos,
        on=group_cols,
        how="inner",
        indicator=False,
    )
    covered_combos = len(merged)
    missing_combos = total_combos - covered_combos

    # Calculate coverage percentage
    coverage_pct = (covered_combos / total_combos * 100) if total_combos > 0 else 0

    return {
        "total_combinations": total_combos,
        "covered_combinations": covered_combos,
        "missing_combinations": missing_combos,
        "coverage_percentage": round(coverage_pct, 2),
    }
