"""
Tests for coverage analyzer module.

Following SRP: focused testing of coverage analysis logic only.
"""

from __future__ import annotations

import pandas as pd

from src.analyzer import find_missing_coverage, generate_coverage_report


class TestFindMissingCoverage:
    """Test missing coverage detection."""

    def test_find_missing_combinations(self, sample_enriched_df, sample_output_df, tmp_csv_dir):
        """Test finding missing group combinations."""
        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"
        missing_path = tmp_csv_dir / "missing.csv"

        sample_enriched_df.to_csv(enriched_path, index=False)
        sample_output_df.to_csv(output_path, index=False)

        result = find_missing_coverage(enriched_path, output_path, missing_path)

        # Should have 2 missing combinations
        assert len(result) == 2
        assert "reason" in result.columns
        assert all(result["reason"] == "отсутствует")

    def test_full_coverage(self, sample_enriched_df, tmp_csv_dir):
        """Test when all combinations are covered."""
        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"
        missing_path = tmp_csv_dir / "missing.csv"

        # Use same data for both
        sample_enriched_df.to_csv(enriched_path, index=False)
        sample_enriched_df.to_csv(output_path, index=False)

        result = find_missing_coverage(enriched_path, output_path, missing_path)

        # Should return empty DataFrame with correct columns
        assert len(result) == 0
        assert "group0" in result.columns
        assert "reason" in result.columns

    def test_missing_with_nan_groups(self, tmp_csv_dir):
        """Test handling of NaN group values."""
        enriched_df = pd.DataFrame(
            [
                {"group0": "test", "group1": "", "group2": ""},
            ]
        )
        output_df = pd.DataFrame(
            [
                {"group0": "test", "group1": "missing", "group2": ""},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"
        missing_path = tmp_csv_dir / "missing.csv"

        enriched_df.to_csv(enriched_path, index=False)
        output_df.to_csv(output_path, index=False)

        result = find_missing_coverage(enriched_path, output_path, missing_path)

        # Should find the missing combination
        assert len(result) >= 1

    def test_saves_missing_csv(self, sample_enriched_df, sample_output_df, tmp_csv_dir):
        """Test that missing coverage is saved to CSV."""
        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"
        missing_path = tmp_csv_dir / "missing.csv"

        sample_enriched_df.to_csv(enriched_path, index=False)
        sample_output_df.to_csv(output_path, index=False)

        find_missing_coverage(enriched_path, output_path, missing_path)

        assert missing_path.exists()

        # Verify file content
        saved_df = pd.read_csv(missing_path)
        assert "reason" in saved_df.columns
        assert all(saved_df["reason"] == "отсутствует")

    def test_result_columns(self, sample_enriched_df, sample_output_df, tmp_csv_dir):
        """Test that result has correct columns."""
        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"
        missing_path = tmp_csv_dir / "missing.csv"

        sample_enriched_df.to_csv(enriched_path, index=False)
        sample_output_df.to_csv(output_path, index=False)

        result = find_missing_coverage(enriched_path, output_path, missing_path)

        expected_cols = ["group0", "group1", "group2", "marka", "model", "reason"]
        for col in expected_cols:
            assert col in result.columns


class TestGenerateCoverageReport:
    """Test coverage report generation."""

    def test_coverage_report_calculation(self, sample_enriched_df, sample_output_df, tmp_csv_dir):
        """Test coverage percentage calculation."""
        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        sample_enriched_df.to_csv(enriched_path, index=False)
        sample_output_df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert "total_combinations" in report
        assert "covered_combinations" in report
        assert "missing_combinations" in report
        assert "coverage_percentage" in report

        # Check that values are reasonable
        assert report["total_combinations"] == 3
        assert report["covered_combinations"] == 1
        assert report["missing_combinations"] == 2
        assert report["coverage_percentage"] > 0

    def test_full_coverage_report(self, tmp_csv_dir):
        """Test report with 100% coverage."""
        df = pd.DataFrame(
            [
                {"group0": "test", "group1": "a", "group2": "1"},
                {"group0": "test", "group1": "b", "group2": "2"},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        df.to_csv(enriched_path, index=False)
        df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert report["coverage_percentage"] == 100.0
        assert report["missing_combinations"] == 0

    def test_zero_coverage_report(self, tmp_csv_dir):
        """Test report with 0% coverage."""
        enriched_df = pd.DataFrame(
            [
                {"group0": "a", "group1": "a", "group2": "a"},
            ]
        )
        output_df = pd.DataFrame(
            [
                {"group0": "b", "group1": "b", "group2": "b"},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        enriched_df.to_csv(enriched_path, index=False)
        output_df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert report["coverage_percentage"] == 0.0

    def test_empty_catalogs(self, tmp_csv_dir):
        """Test report with empty catalogs."""
        enriched_df = pd.DataFrame(columns=["group0", "group1", "group2"])
        output_df = pd.DataFrame(columns=["group0", "group1", "group2"])

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        enriched_df.to_csv(enriched_path, index=False)
        output_df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert report["coverage_percentage"] == 0

    def test_duplicate_handling(self, tmp_csv_dir):
        """Test that duplicates are handled correctly."""
        # Enriched has duplicates
        enriched_df = pd.DataFrame(
            [
                {"group0": "test", "group1": "a", "group2": "1"},
                {"group0": "test", "group1": "a", "group2": "1"},  # duplicate
            ]
        )
        # Output has duplicates too
        output_df = pd.DataFrame(
            [
                {"group0": "test", "group1": "a", "group2": "1"},
                {"group0": "test", "group1": "a", "group2": "1"},  # duplicate
                {"group0": "test", "group1": "b", "group2": "2"},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        enriched_df.to_csv(enriched_path, index=False)
        output_df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        # Should count unique combinations only
        assert report["total_combinations"] == 2
        assert report["covered_combinations"] == 1
        assert report["missing_combinations"] == 1


class TestAnalyzerEdgeCases:
    """Test edge cases in analyzer."""

    def test_special_characters_in_groups(self, tmp_csv_dir):
        """Test handling of special characters in group values."""
        df = pd.DataFrame(
            [
                {"group0": "тест / тест", "group1": "a&b", "group2": "1+2"},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        df.to_csv(enriched_path, index=False)
        df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert report["coverage_percentage"] == 100.0

    def test_very_long_group_values(self, tmp_csv_dir):
        """Test handling of very long group names."""
        long_name = "a" * 1000
        df = pd.DataFrame(
            [
                {"group0": long_name, "group1": "test", "group2": "test"},
            ]
        )

        enriched_path = tmp_csv_dir / "enriched.csv"
        output_path = tmp_csv_dir / "output.csv"

        df.to_csv(enriched_path, index=False)
        df.to_csv(output_path, index=False)

        report = generate_coverage_report(enriched_path, output_path)

        assert report["coverage_percentage"] == 100.0
