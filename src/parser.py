"""
HTML Parser for Avito Ads.

Extracts advertisements from saved HTML pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Ad:
    """Represents a parsed advertisement."""

    ad_id: str
    title: str
    url: str = ""
    region: str = ""
    price: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for CSV writing."""
        return {
            "ad_id": self.ad_id,
            "title": self.title,
            "url": self.url,
            "region": self.region,
            "price": self.price,
        }


def parse_html_file(file_path: str | Path) -> list[Ad]:
    """
    Parse a single HTML file and extract ads.

    Args:
        file_path: Path to the HTML file.

    Returns:
        List of parsed Ad objects.
    """
    from pathlib import Path  # noqa: PLC0415

    content = Path(file_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "lxml")
    items = soup.find_all(attrs={"data-item-id": True})

    ads: list[Ad] = []
    for item in items:
        ad_id = str(item.get("data-item-id", ""))
        if not ad_id:
            continue

        # Extract title
        title_elem = item.find(attrs={"data-marker": "item-title"})
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract URL
        url = ""
        if title_elem and title_elem.name == "a":
            url = str(title_elem.get("href", ""))
        elif title_elem:
            link_elem = title_elem.find("a")
            if link_elem:
                url = str(link_elem.get("href", ""))

        # Extract location
        location_elem = item.find(attrs={"data-marker": "item-location"})
        region = location_elem.get_text(strip=True) if location_elem else ""

        # Extract price
        price_elem = item.find(attrs={"data-marker": "item-price"})
        price = price_elem.get_text(strip=True) if price_elem else ""

        if title:  # Only add if we have at least a title
            ads.append(Ad(ad_id=ad_id, title=title, url=url, region=region, price=price))

    return ads


def parse_html_files(file_paths: list[str | Path]) -> list[Ad]:
    """
    Parse multiple HTML files and extract ads.

    Args:
        file_paths: List of paths to HTML files.

    Returns:
        List of parsed Ad objects.
    """
    all_ads: list[Ad] = []
    for file_path in file_paths:
        try:
            ads = parse_html_file(file_path)
            all_ads.extend(ads)
        except (OSError, FileNotFoundError):
            # Skip files that don't exist or can't be read
            continue
    return all_ads
