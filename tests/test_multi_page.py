"""Tests for multi-page site generator."""
from pathlib import Path
import tempfile
from bloggereasy.theme.multi_page import build_multi_page_set, _about_html, _contact_html
from bloggereasy.theme.models import PageStructure


def test_about_html_default():
    structure = {"title": "Test Blog", "description": "A test blog"}
    html = _about_html(structure)
    assert "About Test Blog" in html
    assert "A test blog" in html
    assert "<h2" in html


def test_about_html_with_paragraphs():
    structure = {
        "title": "Dev Blog",
        "sample_paragraphs": ["We build great software.", "Open source FTW."]
    }
    html = _about_html(structure)
    assert "We build great software." in html
    assert "Open source FTW." in html


def test_contact_html():
    structure = {"title": "My Blog"}
    html = _contact_html(structure)
    assert "Contact Us" in html
    assert "contact@example.com" in html


def test_build_multi_page_set_default():
    structure = PageStructure(
        title="Multi Page Test",
        description="Testing coordinated pages",
        sample_paragraphs=["First paragraph", "Second paragraph"],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "output"
        result = build_multi_page_set(structure, out_dir=out)
        assert result["title"] == "Multi Page Test"
        assert "theme" in result["files"]
        assert "about" in result["files"]
        assert "contact" in result["files"]
        assert "preview" in result["files"]
        # Verify files exist and have content
        theme_path = Path(result["files"]["theme"])
        assert theme_path.exists()
        theme_content = theme_path.read_text(encoding="utf-8")
        assert "Multi Page Test" in theme_content
        assert "<?xml" in theme_content
        about_path = Path(result["files"]["about"])
        assert about_path.exists()
        about_content = about_path.read_text(encoding="utf-8")
        assert "About Multi Page Test" in about_content
        contact_path = Path(result["files"]["contact"])
        assert contact_path.exists()
        contact_content = contact_path.read_text(encoding="utf-8")
        assert "Contact Us" in contact_content
        preview_path = Path(result["files"]["preview"])
        assert preview_path.exists()
        assert "import_hint" in result


def test_build_multi_page_set_adds_nav_links():
    structure = PageStructure(title="Nav Test")
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "output"
        result = build_multi_page_set(structure, out_dir=out)
        theme_path = Path(result["files"]["theme"])
        content = theme_path.read_text(encoding="utf-8")
        assert "Home" in content
        assert "About" in content
        assert "Contact" in content


def test_build_multi_page_set_preserves_existing_nav():
    structure = PageStructure(
        title="Custom Nav",
        nav_links=[
            {"label": "Blog", "href": "/blog"},
            {"label": "Portfolio", "href": "/portfolio"},
        ],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "output"
        result = build_multi_page_set(structure, out_dir=out)
        theme_path = Path(result["files"]["theme"])
        content = theme_path.read_text(encoding="utf-8")
        assert "Blog" in content
        assert "Portfolio" in content
