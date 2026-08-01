"""Tests for the multi-page site generator."""

from __future__ import annotations

from pathlib import Path

from bloggereasy.multi_page import MultiPageSite, generate_multi_page_site


# ---------------------------------------------------------------------------
# 1 – Default generation writes all three pages
# ---------------------------------------------------------------------------

def test_generates_default_pages(tmp_path: Path) -> None:
    result = generate_multi_page_site(tmp_path / "dist")
    assert result["site_name"] == "My Site"
    assert set(result["pages"]) == {"index.html", "about.html", "contact.html"}
    assert result["total_bytes"] > 0

    for name in result["pages"]:
        path = Path(result["output_dir"]) / name
        assert path.exists(), f"Missing {name}"


# ---------------------------------------------------------------------------
# 2 – Pages contain expected HTML structure
# ---------------------------------------------------------------------------

def test_pages_contain_expected_markup(tmp_path: Path) -> None:
    out = tmp_path / "out"
    generate_multi_page_site(out)

    index_html = (out / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in index_html
    assert "My Site" in index_html
    assert '<a href="about.html">About</a>' in index_html
    assert 'class="active"' in index_html  # Home (index) is active
    assert "<footer" in index_html

    about_html = (out / "about.html").read_text(encoding="utf-8")
    assert "About Us" in about_html
    assert '<a href="index.html">Home</a>' in about_html

    contact_html = (out / "contact.html").read_text(encoding="utf-8")
    assert "Contact Us" in contact_html
    assert "contact-form" in contact_html


# ---------------------------------------------------------------------------
# 3 – Custom site name and tagline propagate
# ---------------------------------------------------------------------------

def test_custom_site_name_and_tagline(tmp_path: Path) -> None:
    result = generate_multi_page_site(
        tmp_path / "mysite",
        site_name="Acme Corp",
        tagline="Building tomorrow",
    )
    assert result["site_name"] == "Acme Corp"

    index_html = (tmp_path / "mysite" / "index.html").read_text(encoding="utf-8")
    assert "Acme Corp" in index_html
    assert "Building tomorrow" in index_html
    assert '<div class="site-tagline"' in index_html


# ---------------------------------------------------------------------------
# 4 – Colour options are reflected in the CSS
# ---------------------------------------------------------------------------

def test_custom_colors_applied(tmp_path: Path) -> None:
    generate_multi_page_site(
        tmp_path / "colored",
        primary_color="#ff0000",
        background_color="#fafafa",
        text_color="#111111",
        font_family="Georgia, serif",
    )
    css = (tmp_path / "colored" / "index.html").read_text(encoding="utf-8")
    assert "#ff0000" in css
    assert "#fafafa" in css
    assert "#111111" in css
    assert "Georgia, serif" in css


# ---------------------------------------------------------------------------
# 5 – --no-contact-form removes the form
# ---------------------------------------------------------------------------

def test_no_contact_form_suppresses_form(tmp_path: Path) -> None:
    generate_multi_page_site(tmp_path / "nc", show_contact_form=False)
    contact_html = (tmp_path / "nc" / "contact.html").read_text(encoding="utf-8")
    # The <form> or form container markup should not appear in the page body —
    # but the CSS class .contact-form may still be in the stylesheet.
    # Check that we do NOT have an actual form element.
    assert "<form" not in contact_html
    assert 'id="cf-name"' not in contact_html
    assert 'id="cf-email"' not in contact_html
    assert "Contact Us" in contact_html  # page still exists


# ---------------------------------------------------------------------------
# 6 – Programmatic MultiPageSite class works directly
# ---------------------------------------------------------------------------

def test_multi_page_site_class_direct(tmp_path: Path) -> None:
    site = MultiPageSite(
        site_name="Solo",
        tagline="One man show",
        pages=[
            {"title": "Home", "slug": "index", "content": "<p>root</p>"},
            {"title": "About", "slug": "about", "content": "<p>bio</p>"},
            {"title": "Contact", "slug": "contact", "content": "<p>reach out</p>"},
        ],
    )
    result = site.generate(tmp_path / "solo")
    assert len(result["pages"]) == 3
    for p in result["pages"]:
        path = tmp_path / "solo" / p
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "Solo" in text
        assert "One man show" in text


# ---------------------------------------------------------------------------
# 7 – Custom pages can be provided (different count / layout)
# ---------------------------------------------------------------------------

def test_custom_pages_list(tmp_path: Path) -> None:
    result = generate_multi_page_site(
        tmp_path / "two",
        site_name="Minimal",
        pages=[
            {"title": "Home", "slug": "index", "content": "<p>Welcome</p>"},
            {"title": "Contact", "slug": "contact", "content": "{contact_form}"},
        ],
    )
    assert set(result["pages"]) == {"index.html", "contact.html"}
    assert result["total_bytes"] > 0


# ---------------------------------------------------------------------------
# 8 – Output directory is created if missing
# ---------------------------------------------------------------------------

def test_creates_output_directory(tmp_path: Path) -> None:
    out = tmp_path / "deeply" / "nested" / "dir"
    assert not out.exists()
    generate_multi_page_site(out)
    assert out.is_dir()
    assert (out / "index.html").exists()
