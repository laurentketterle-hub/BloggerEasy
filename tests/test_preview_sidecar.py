"""Tests for responsive preview HTML sidecar (BloggerEasy #78)."""
from pathlib import Path

import pytest

from bloggereasy.config import SAMPLES_DIR
from bloggereasy.integrations.sdk import generate_preview_sidecar
from bloggereasy.parse.html_page import parse_html_file
from bloggereasy.theme.presets import apply_preset


@pytest.fixture
def sample_structure():
    """Parse a sample HTML and apply a template."""
    html_dir = SAMPLES_DIR / "html"
    samples = sorted(html_dir.glob("*.html"))
    assert samples, "Need HTML samples"
    return apply_preset(parse_html_file(samples[0]), "corporate_blue")


class TestPreviewSidecar:
    """Responsive preview HTML sidecar tests."""

    def test_generates_valid_html(self, sample_structure, tmp_path):
        """Sidecar output is a valid HTML document."""
        out = tmp_path / "preview.html"
        result = generate_preview_sidecar(sample_structure, out)
        assert out.is_file()
        assert result["bytes"] > 1000
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content

    def test_has_three_breakpoints(self, sample_structure, tmp_path):
        """Sidecar shows mobile, tablet, and desktop breakpoints."""
        out = tmp_path / "preview.html"
        result = generate_preview_sidecar(sample_structure, out)
        assert result["breakpoints"] == 3
        content = out.read_text(encoding="utf-8")
        assert "Mobile" in content
        assert "Tablet" in content
        assert "Desktop" in content

    def test_contains_iframes(self, sample_structure, tmp_path):
        """Sidecar uses iframes for breakpoint simulation."""
        out = tmp_path / "preview.html"
        generate_preview_sidecar(sample_structure, out)
        content = out.read_text(encoding="utf-8")
        assert content.count("<iframe") == 3

    def test_uses_theme_colors(self, sample_structure, tmp_path):
        """Sidecar CSS includes the theme's primary color."""
        out = tmp_path / "preview.html"
        generate_preview_sidecar(sample_structure, out)
        content = out.read_text(encoding="utf-8")
        colors = sample_structure.get("colors") or {}
        primary = colors.get("primary", "#1a73e8")
        assert primary in content

    def test_cli_preview_flag(self):
        """CLI --preview flag works with gen html."""
        import subprocess
        import sys

        html_dir = SAMPLES_DIR / "html"
        samples = sorted(html_dir.glob("*.html"))
        result = subprocess.run(
            [
                sys.executable, "-m", "bloggereasy.cli", "gen", "html",
                "--input", str(samples[0]),
                "--preview",
                "-t", "simple",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "Preview sidecar" in result.stdout

    def test_cli_preview_help(self):
        """CLI help mentions --preview."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "bloggereasy.cli", "gen", "html", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--preview" in result.stdout

    def test_sidebar_reflected_in_preview(self, sample_structure, tmp_path):
        """Sidecar includes sidebar when layout is two-column."""
        out = tmp_path / "preview.html"
        generate_preview_sidecar(sample_structure, out)
        content = out.read_text(encoding="utf-8")
        assert "Sidebar" in content  # Sidebar mention in iframe content
