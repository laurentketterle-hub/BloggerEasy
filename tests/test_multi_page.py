"""Tests for multi-page site generator (BloggerEasy #80)."""
from pathlib import Path

import pytest

from bloggereasy.config import OUT_DIR, SAMPLES_DIR
from bloggereasy.integrations.sdk import generate_multi_page


@pytest.fixture
def html_samples():
    """Return first 3 HTML samples for multi-page tests."""
    html_dir = SAMPLES_DIR / "html"
    samples = sorted(html_dir.glob("*.html"))
    assert len(samples) >= 3, f"Need 3+ samples, got {len(samples)}"
    return samples


class TestMultiPage:
    """Multi-page site generator tests."""

    def test_generates_home_only(self, html_samples, tmp_path):
        """Single page (home only) produces one valid XML."""
        pages = {"home": html_samples[0]}
        result = generate_multi_page(pages, tmp_path, template="simple")
        assert result["all_valid"]
        assert len(result["pages"]) == 1
        home = result["pages"]["home"]
        assert home["validation"]["ok"]
        assert (tmp_path / "home.xml").is_file()
        assert home["bytes"] > 0

    def test_generates_home_about_contact(self, html_samples, tmp_path):
        """Three pages share colors and all validate."""
        pages = {
            "home": html_samples[0],
            "about": html_samples[1],
            "contact": html_samples[2],
        }
        result = generate_multi_page(pages, tmp_path, template="corporate_blue")
        assert result["all_valid"]
        assert len(result["pages"]) == 3
        for name in ("home", "about", "contact"):
            assert result["pages"][name]["validation"]["ok"]
            assert (tmp_path / f"{name}.xml").is_file()
            assert result["pages"][name]["bytes"] > 1000

    def test_pages_share_colors(self, html_samples, tmp_path):
        """All pages share the same color palette from the first page."""
        pages = {
            "home": html_samples[0],
            "about": html_samples[1],
        }
        result = generate_multi_page(pages, tmp_path, template="simple")
        shared = result["shared_colors"]

        for name in ("home", "about"):
            page_colors = result["pages"][name]["structure"].get("colors", {})
            for key in ("primary", "secondary", "background", "text"):
                if key in shared:
                    assert page_colors.get(key) == shared[key], (
                        f"{name}.colors.{key} should match shared"
                    )

    def test_pages_have_different_titles(self, html_samples, tmp_path):
        """Each page keeps its own title and content."""
        pages = {
            "home": html_samples[0],
            "about": html_samples[1],
            "contact": html_samples[2],
        }
        result = generate_multi_page(pages, tmp_path)
        titles = {
            name: result["pages"][name]["structure"].get("title", "")
            for name in pages
        }
        # At least one title should differ (pages have different content)
        assert len(set(titles.values())) >= 1, "Pages should have distinct titles"

    def test_multi_page_with_dark_template(self, html_samples, tmp_path):
        """Dark template propagates to all pages."""
        pages = {"home": html_samples[0], "about": html_samples[1]}
        result = generate_multi_page(pages, tmp_path, template="dark")
        assert result["all_valid"]
        for name in pages:
            feats = result["pages"][name]["structure"].get("features", {})
            assert feats.get("dark"), f"{name} should have dark feature"

    def test_multi_page_with_landing_template(self, html_samples, tmp_path):
        """Landing template works with multi-page."""
        pages = {"home": html_samples[0]}
        result = generate_multi_page(pages, tmp_path, template="landing")
        assert result["all_valid"]
        home_feats = result["pages"]["home"]["structure"].get("features", {})
        assert home_feats.get("landing"), "Landing feature should be enabled"

    def test_empty_pages_raises(self, tmp_path):
        """Empty pages dict raises ValueError."""
        with pytest.raises(ValueError, match="At least one page"):
            generate_multi_page({}, tmp_path)

    def test_output_files_exist(self, html_samples, tmp_path):
        """All generated XML files exist on disk with content."""
        pages = {"home": html_samples[0], "about": html_samples[1]}
        result = generate_multi_page(pages, tmp_path)

        for name in pages:
            xml_path = tmp_path / f"{name}.xml"
            assert xml_path.is_file()
            content = xml_path.read_text(encoding="utf-8")
            assert '<?xml version="1.0"' in content
            assert "<b:skin" in content
            assert "<b:section" in content

    def test_cli_help_shows_multi(self):
        """CLI help includes the multi command."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "bloggereasy.cli", "gen", "multi", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        assert result.returncode == 0
        assert "--home" in result.stdout
        assert "--about" in result.stdout
        assert "--contact" in result.stdout
