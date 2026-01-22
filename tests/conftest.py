"""
Shared fixtures for tests.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_html():
    """Sample HTML content with ad listings."""
    return """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="123456789">
        <a data-marker="item-title" href="/item/123">Test Ad Title</a>
        <span data-marker="item-location">Test Location</span>
        <p data-marker="item-price">10 000₽</p>
    </div>
    <div data-item-id="987654321">
        <a data-marker="item-title" href="/item/456">Another Ad</a>
        <span data-marker="item-location">Another Location</span>
        <p data-marker="item-price">20 000₽</p>
    </div>
</body>
</html>"""


@pytest.fixture
def sample_html_file(tmp_path, sample_html):
    """Create a temporary HTML file with sample content."""
    html_file = tmp_path / "test.html"
    html_file.write_text(sample_html, encoding="utf-8")
    return html_file


@pytest.fixture
def sample_ads_df():
    """Sample DataFrame with parsed ads."""
    return pd.DataFrame(
        [
            {
                "ad_id": "123456789",
                "title": "Запчасти в бортовой редуктор хода jcb",
                "url": "https://avito.ru/item/123",
                "region": "Москва",
                "price": "10 000₽",
            },
            {
                "ad_id": "987654321",
                "title": "Редуктор jcb js160",
                "url": "https://avito.ru/item/456",
                "region": "СПб",
                "price": "20 000₽",
            },
        ]
    )


@pytest.fixture
def sample_enriched_df():
    """Sample DataFrame with enriched ads."""
    return pd.DataFrame(
        [
            {
                "ad_id": "123456789",
                "title": "Запчасти в бортовой редуктор хода jcb",
                "url": "https://avito.ru/item/123",
                "region": "Москва",
                "price": "10 000₽",
                "marka": "jcb",
                "model": "JS 220",
                "group0": "гидравлический компонент",
                "group1": "редуктор",
                "group2": "редуктор хода",
                "group3": "",
                "group4": "",
            },
            {
                "ad_id": "987654321",
                "title": "Редуктор jcb js160",
                "url": "https://avito.ru/item/456",
                "region": "СПб",
                "price": "20 000₽",
                "marka": "jcb",
                "model": "JS 160",
                "group0": "гидравлический компонент",
                "group1": "редуктор",
                "group2": "!",
                "group3": "",
                "group4": "",
            },
        ]
    )


@pytest.fixture
def sample_output_df():
    """Sample DataFrame with target catalog."""
    return pd.DataFrame(
        [
            {
                "title": "Test Item 1",
                "marka": "jcb",
                "model": "JS 220",
                "catalog_number": "123-456",
                "group0": "гидравлический компонент",
                "group1": "редуктор",
                "group2": "редуктор хода",
                "group3": "",
                "group4": "",
            },
            {
                "title": "Test Item 2",
                "marka": "cat",
                "model": "312",
                "catalog_number": "188-0895",
                "group0": "ходовая часть",
                "group1": "натяжитель",
                "group2": "натяжитель в сборе",
                "group3": "",
                "group4": "",
            },
            {
                "title": "Test Item 3",
                "marka": "hyundai",
                "model": "R210",
                "catalog_number": "31N5-43000",
                "group0": "ходовая часть",
                "group1": "каток опорный",
                "group2": "!",
                "group3": "",
                "group4": "",
            },
        ]
    )


@pytest.fixture
def api_success_response():
    """Sample successful API response."""
    return {
        "processed_data": [
            {
                "title": "Запчасти в бортовой редуктор хода jcb",
                "raw_item": "Запчасти в бортовой редуктор хода jcb",
                "day": "2026-01-22",
                "marka": "jcb",
                "model": "JS 220",
                "catalog_number": "",
                "group0": "гидравлический компонент",
                "group1": "редуктор",
                "group2": "редуктор хода",
                "group3": "",
                "group4": "",
                "clear_item": "запчасти в бортовой редуктор хода jcb",
            }
        ]
    }


@pytest.fixture
def tmp_csv_dir(tmp_path):
    """Create temporary directory for CSV files."""
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    return csv_dir
