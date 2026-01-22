"""
Avito Ads Parser - Package initialization.

This package provides tools for:
- Parsing HTML files from Avito marketplace
- Enriching ads via API
- Analyzing coverage against a target catalog
"""

from .analyzer import find_missing_coverage, generate_coverage_report
from .parser import Ad, parse_html_file, parse_html_files

__all__ = [
    "Ad",
    "find_missing_coverage",
    "generate_coverage_report",
    "parse_html_file",
    "parse_html_files",
]
