"""
Tests for HTML parser module.

Following SRP: focused testing of parsing logic only.
"""

from __future__ import annotations

from src.parser import Ad, parse_html_file, parse_html_files


class TestAd:
    """Test Ad dataclass."""

    def test_ad_to_dict(self):
        """Test Ad conversion to dictionary."""
        ad = Ad(
            ad_id="123",
            title="Test Ad",
            url="https://test.com/ad/123",
            region="Москва",
            price="10 000₽",
        )
        result = ad.to_dict()

        assert result == {
            "ad_id": "123",
            "title": "Test Ad",
            "url": "https://test.com/ad/123",
            "region": "Москва",
            "price": "10 000₽",
        }


class TestParseHtmlFile:
    """Test single HTML file parsing."""

    def test_parse_valid_html(self, sample_html_file):
        """Test parsing valid HTML with ads."""
        ads = parse_html_file(sample_html_file)

        assert len(ads) == 2
        assert ads[0].ad_id == "123456789"
        assert ads[0].title == "Test Ad Title"
        assert ads[0].url == "/item/123"
        assert ads[0].region == "Test Location"
        assert ads[0].price == "10 000₽"

    def test_parse_html_missing_optional_fields(self, tmp_path):
        """Test parsing HTML with missing optional fields."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="111">
        <a data-marker="item-title" href="/item/111">Minimal Ad</a>
    </div>
</body>
</html>"""
        html_file = tmp_path / "minimal.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)

        assert len(ads) == 1
        assert ads[0].ad_id == "111"
        assert ads[0].title == "Minimal Ad"
        assert ads[0].url == "/item/111"
        assert ads[0].region == ""
        assert ads[0].price == ""

    def test_parse_html_no_items(self, tmp_path):
        """Test parsing HTML without ad items."""
        html = """<!DOCTYPE html>
<html>
<body>
    <p>No ads here</p>
</body>
</html>"""
        html_file = tmp_path / "empty.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)
        assert ads == []

    def test_parse_html_nested_link(self, tmp_path):
        """Test parsing when title element contains nested link."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="222">
        <div data-marker="item-title">
            <a href="/item/222">Nested Link Title</a>
        </div>
    </div>
</body>
</html>"""
        html_file = tmp_path / "nested.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)

        assert len(ads) == 1
        assert ads[0].title == "Nested Link Title"
        assert ads[0].url == "/item/222"

    def test_parse_html_without_id_skipped(self, tmp_path):
        """Test that items without data-item-id are skipped."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div>
        <a data-marker="item-title" href="/item/no-id">No ID Ad</a>
    </div>
</body>
</html>"""
        html_file = tmp_path / "no-id.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)
        assert ads == []

    def test_parse_html_with_empty_id_skipped(self, tmp_path):
        """Test that items with empty data-item-id are skipped (line 56)."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="">
        <a data-marker="item-title" href="/item/empty">Empty ID Ad</a>
    </div>
</body>
</html>"""
        html_file = tmp_path / "empty-id.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)
        assert ads == []

    def test_parse_html_without_title_skipped(self, tmp_path):
        """Test that items without title are skipped."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="333">
        <span data-marker="item-location">Location without title</span>
    </div>
</body>
</html>"""
        html_file = tmp_path / "no-title.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)
        assert ads == []


class TestParseHtmlFiles:
    """Test parsing multiple HTML files."""

    def test_parse_multiple_files(self, tmp_path, sample_html):
        """Test parsing multiple HTML files."""
        file1 = tmp_path / "file1.html"
        file2 = tmp_path / "file2.html"
        file1.write_text(sample_html)
        file2.write_text(sample_html)

        ads = parse_html_files([file1, file2])

        assert len(ads) == 4  # 2 from each file

    def test_parse_empty_list(self):
        """Test parsing empty file list."""
        ads = parse_html_files([])
        assert ads == []

    def test_parse_mixed_valid_invalid(self, tmp_path, sample_html):
        """Test parsing mix of valid and invalid files."""
        valid_file = tmp_path / "valid.html"
        valid_file.write_text(sample_html)

        ads = parse_html_files([valid_file, tmp_path / "nonexistent.html"])

        assert len(ads) == 2  # Only from valid file


class TestParserEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_unicode_characters(self, tmp_path):
        """Test parsing HTML with unicode characters."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="777">
        <a data-marker="item-title" href="/item/777">Запчасти редуктор 液压</a>
        <span data-marker="item-location">Москва́</span>
    </div>
</body>
</html>"""
        html_file = tmp_path / "unicode.html"
        html_file.write_text(html, encoding="utf-8")

        ads = parse_html_file(html_file)

        assert len(ads) == 1
        assert "Запчасти редуктор" in ads[0].title

    def test_parse_large_price_value(self, tmp_path):
        """Test parsing large price values."""
        html = """<!DOCTYPE html>
<html>
<body>
    <div data-item-id="999">
        <a data-marker="item-title" href="/item/999">Expensive Item</a>
        <p data-marker="item-price">1 500 000₽</p>
    </div>
</body>
</html>"""
        html_file = tmp_path / "price.html"
        html_file.write_text(html)

        ads = parse_html_file(html_file)

        assert len(ads) == 1
        assert ads[0].price == "1 500 000₽"
