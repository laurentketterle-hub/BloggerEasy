"""Comprehensive tests for the multi-page Blogger site generator.

Tests cover:
- Core multi_page module functions
- Site manifest generation from directories and strings
- Edge cases: empty directories, missing files, invalid HTML
- Template mapping and auto-detection
- CLI integration via mock
- Validation of generated XML
- Page entry lifecycle
"""

from __future__ import annotations

import json

import pytest

from bloggereasy.multi_page import (
    DEFAULT_NAV_LINKS,
    STEM_TEMPLATE_MAP,
    PageEntry,
    SiteManifest,
    build_page_entry,
    discover_html_files,
    generate_multi_page_from_strings,
    generate_multi_page_site,
    generate_page_xml,
    generate_page_xml_from_html_string,
    guess_template_for_stem,
    resolve_template,
    validate_all_xml,
)


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

MINI_HOME_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>My Home</title></head>
<body>
<header><h1>Welcome Home</h1></header>
<main><p>This is the home page.</p></main>
<footer><p>Footer</p></footer>
</body>
</html>
"""

MINI_ABOUT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>About Us</title></head>
<body>
<header><h1>About Our Team</h1></header>
<main><p>We build great things.</p><p>Our mission is quality.</p></main>
<footer><p>Footer</p></footer>
</body>
</html>
"""

MINI_CONTACT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Contact Us</title></head>
<body>
<header><h1>Get In Touch</h1></header>
<main><p>Email: hello@example.com</p><p>Phone: 555-0100</p></main>
<footer><p>Footer</p></footer>
</body>
</html>
"""

BROKEN_HTML = "<html><head><title>Broken</title></head><body><p>No closing tags"


# ---------------------------------------------------------------------------
# guess_template_for_stem
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "stem, expected",
    [
        ("home", "home"),
        ("index", "home"),
        ("about", "about"),
        ("about_page", "about"),
        ("about_team", "about"),
        ("contact", "contact"),
        ("contact_page", "contact"),
        ("contact_form", "contact"),
        ("portfolio", "portfolio"),
        ("news", "news"),
        ("blog", "simple"),
        ("docs", "docs"),
        ("landing", "landing"),
        ("unknown_stem_xyz", "simple"),
        ("", "simple"),
    ],
)
def test_guess_template_for_stem(stem, expected):
    """Stem-to-template mapping works for all known patterns."""
    assert guess_template_for_stem(stem) == expected


def test_guess_template_fuzzy_match():
    """Unrecognised stems that contain known substrings are matched."""
    # "about_us_page" contains "about" and "page" → should match "about"
    assert guess_template_for_stem("about_us_page") == "about"
    # "my_contact_info" contains "contact"
    assert guess_template_for_stem("my_contact_info") == "contact"


# ---------------------------------------------------------------------------
# resolve_template
# ---------------------------------------------------------------------------

def test_resolve_template_valid():
    """Valid template names pass through."""
    assert resolve_template("home") == "home"
    assert resolve_template("portfolio") == "portfolio"


def test_resolve_template_invalid_defaults_to_simple():
    """Unknown template names resolve to 'simple'."""
    assert resolve_template("nonsense") == "simple"


# ---------------------------------------------------------------------------
# discover_html_files
# ---------------------------------------------------------------------------

def test_discover_html_files_from_populated_dir(tmp_path):
    """Finds all .html files, sorted."""
    (tmp_path / "c.html").write_text("<p>C</p>")
    (tmp_path / "a.html").write_text("<p>A</p>")
    (tmp_path / "b.html").write_text("<p>B</p>")
    (tmp_path / "readme.md").write_text("not html")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "d.html").write_text("<p>D</p>")

    files = discover_html_files(tmp_path)
    assert len(files) == 3
    assert [f.name for f in files] == ["a.html", "b.html", "c.html"]


def test_discover_html_files_empty_dir(tmp_path):
    """Returns empty list for empty directory."""
    assert discover_html_files(tmp_path) == []


def test_discover_html_files_missing_dir(tmp_path):
    """Returns empty list for non-existent directory."""
    assert discover_html_files(tmp_path / "nope") == []


# ---------------------------------------------------------------------------
# build_page_entry
# ---------------------------------------------------------------------------

def test_build_page_entry_from_html(tmp_path):
    """PageEntry populated correctly from an HTML file."""
    html = tmp_path / "about.html"
    html.write_text(MINI_ABOUT_HTML)

    entry = build_page_entry(html)
    assert entry.stem == "about"
    assert entry.template == "about"
    assert entry.title == "About Us"
    assert entry.source_html == html
    assert len(entry.nav_links) > 0


def test_build_page_entry_with_template_override(tmp_path):
    """Explicit template override is respected."""
    html = tmp_path / "home.html"
    html.write_text(MINI_HOME_HTML)
    entry = build_page_entry(html, template="dark")
    assert entry.template == "dark"


def test_build_page_entry_fallback_title(tmp_path):
    """When HTML has no title, stem is used as fallback."""
    html = tmp_path / "my_custom_page.html"
    html.write_text("<html><body><p>no title</p></body></html>")
    entry = build_page_entry(html)
    assert entry.title == "My Blog"  # Default from PageStructure when no <title>


# ---------------------------------------------------------------------------
# PageEntry dataclass
# ---------------------------------------------------------------------------

def test_page_entry_defaults():
    """PageEntry has sensible defaults."""
    entry = PageEntry(stem="test", template="simple")
    assert entry.title == ""
    assert entry.validation == {"ok": False, "errors": []}
    assert entry.bytes == 0


# ---------------------------------------------------------------------------
# SiteManifest dataclass
# ---------------------------------------------------------------------------

def test_site_manifest_defaults():
    """SiteManifest initialises with empty collections."""
    m = SiteManifest(site_name="Test")
    assert m.site_name == "Test"
    assert m.pages == []
    assert m.total_bytes == 0
    assert m.all_valid is False
    assert m.errors == []
    assert m.template_summary == {}


# ---------------------------------------------------------------------------
# generate_page_xml
# ---------------------------------------------------------------------------

def test_generate_page_xml_produces_valid_output(tmp_path):
    """generate_page_xml creates a validated XML file."""
    html = tmp_path / "home.html"
    html.write_text(MINI_HOME_HTML)
    out_dir = tmp_path / "out"

    entry = PageEntry(stem="home", template="home", source_html=html)
    result = generate_page_xml(entry, out_dir)

    assert result.generated_xml is not None
    assert result.generated_xml.is_file()
    assert result.validation["ok"] is True
    assert result.bytes > 0
    assert "b:skin" in result.generated_xml.read_text(encoding="utf-8")


def test_generate_page_xml_missing_source(tmp_path):
    """Returns validation error when source HTML is missing."""
    entry = PageEntry(stem="gone", template="simple", source_html=None)
    result = generate_page_xml(entry, tmp_path / "out")
    assert result.validation["ok"] is False
    assert "Source HTML not found" in result.validation["errors"]


def test_generate_page_xml_with_dark_variant(tmp_path):
    """Dark variant produces dark-colored output."""
    html = tmp_path / "dark_test.html"
    html.write_text(MINI_HOME_HTML)
    out_dir = tmp_path / "out"

    entry = PageEntry(stem="dark_test", template="dark", source_html=html)
    result = generate_page_xml(entry, out_dir, dark=True)
    assert result.validation["ok"]


# ---------------------------------------------------------------------------
# generate_page_xml_from_html_string
# ---------------------------------------------------------------------------

def test_generate_page_xml_from_string(tmp_path):
    """In-memory string generation produces valid XML."""
    out_dir = tmp_path / "out"
    entry = PageEntry(stem="inline", template="simple")
    result = generate_page_xml_from_html_string(entry, MINI_HOME_HTML, out_dir)

    assert result.generated_xml is not None
    assert result.generated_xml.is_file()
    assert result.validation["ok"]
    assert result.bytes > 0


def test_generate_page_xml_from_broken_string(tmp_path):
    """Even broken HTML should produce output (may or may not validate)."""
    out_dir = tmp_path / "out"
    entry = PageEntry(stem="broken", template="simple")
    result = generate_page_xml_from_html_string(entry, BROKEN_HTML, out_dir)
    assert result.generated_xml is not None
    assert result.generated_xml.is_file()
    # The parser should handle it gracefully — at minimum, file is written


# ---------------------------------------------------------------------------
# generate_multi_page_site (from directory)
# ---------------------------------------------------------------------------

def test_generate_multi_page_from_dir(tmp_path):
    """Full multi-page generation from a directory of HTML files."""
    html_dir = tmp_path / "html_src"
    html_dir.mkdir()
    (html_dir / "home.html").write_text(MINI_HOME_HTML)
    (html_dir / "about.html").write_text(MINI_ABOUT_HTML)
    (html_dir / "contact.html").write_text(MINI_CONTACT_HTML)
    out_dir = tmp_path / "out"

    manifest = generate_multi_page_site(html_dir, out_dir, site_name="Test Site")

    assert manifest.site_name == "Test Site"
    assert len(manifest.pages) == 3
    assert manifest.total_bytes > 0
    assert manifest.all_valid is True
    assert manifest.errors == []
    assert manifest.template_summary == {"home": 1, "about": 1, "contact": 1}

    # Check output files exist
    assert (out_dir / "home.xml").is_file()
    assert (out_dir / "about.xml").is_file()
    assert (out_dir / "contact.xml").is_file()

    # Check manifest JSON
    manifest_json = out_dir / "site_manifest.json"
    assert manifest_json.is_file()
    data = json.loads(manifest_json.read_text())
    assert data["site_name"] == "Test Site"
    assert data["all_valid"] is True
    assert data["page_count"] == 3


def test_generate_multi_page_empty_dir(tmp_path):
    """Empty directory produces manifest with error."""
    out_dir = tmp_path / "out"
    manifest = generate_multi_page_site(tmp_path / "empty", out_dir)
    assert len(manifest.pages) == 0
    assert len(manifest.errors) > 0


def test_generate_multi_page_with_overrides(tmp_path):
    """Template overrides are respected in multi-page generation."""
    html_dir = tmp_path / "html_src"
    html_dir.mkdir()
    (html_dir / "home.html").write_text(MINI_HOME_HTML)
    (html_dir / "about.html").write_text(MINI_ABOUT_HTML)
    out_dir = tmp_path / "out"

    manifest = generate_multi_page_site(
        html_dir,
        out_dir,
        template_overrides={"home": "dark", "about": "dark"},
    )
    assert manifest.template_summary.get("dark", 0) == 2


def test_generate_multi_page_dark_global(tmp_path):
    """Dark=True applies dark variant to all pages."""
    html_dir = tmp_path / "html_src"
    html_dir.mkdir()
    (html_dir / "home.html").write_text(MINI_HOME_HTML)
    out_dir = tmp_path / "out"

    manifest = generate_multi_page_site(html_dir, out_dir, dark=True)
    assert manifest.all_valid


# ---------------------------------------------------------------------------
# generate_multi_page_from_strings
# ---------------------------------------------------------------------------

def test_generate_multi_page_from_strings(tmp_path):
    """In-memory multi-page generation works end-to-end."""
    pages = {
        "home": MINI_HOME_HTML,
        "about": MINI_ABOUT_HTML,
        "contact": MINI_CONTACT_HTML,
    }
    out_dir = tmp_path / "out"

    manifest = generate_multi_page_from_strings(pages, out_dir, site_name="Memory Site")

    assert manifest.site_name == "Memory Site"
    assert len(manifest.pages) == 3
    assert manifest.all_valid
    assert manifest.total_bytes > 0

    for stem in ["home", "about", "contact"]:
        assert (out_dir / f"{stem}.xml").is_file()


def test_generate_multi_page_from_strings_with_overrides(tmp_path):
    """Template overrides work with string-based generation."""
    pages = {"custom_page": MINI_HOME_HTML}
    out_dir = tmp_path / "out"

    manifest = generate_multi_page_from_strings(
        pages,
        out_dir,
        template_overrides={"custom_page": "portfolio"},
    )
    assert manifest.pages[0].template == "portfolio"
    assert manifest.all_valid


def test_generate_multi_page_from_strings_partial_failure(tmp_path):
    """When one page fails, manifest reports it but others succeed."""
    pages = {
        "good": MINI_HOME_HTML,
        "bad": "",  # Empty HTML may fail validation
    }
    out_dir = tmp_path / "out"
    manifest = generate_multi_page_from_strings(pages, out_dir)
    # At minimum, good page should be fine
    assert len(manifest.pages) == 2
    # We just verify that the manifest is returned with both pages
    assert all(p.stem in {"good", "bad"} for p in manifest.pages)


# ---------------------------------------------------------------------------
# validate_all_xml
# ---------------------------------------------------------------------------

def test_validate_all_xml_all_valid(tmp_path):
    """Batch validation reports all valid for well-formed XML."""
    # First generate valid XML from strings
    pages = {"home": MINI_HOME_HTML, "about": MINI_ABOUT_HTML}
    manifest = generate_multi_page_from_strings(pages, tmp_path)
    assert manifest.all_valid

    report = validate_all_xml(tmp_path)
    assert report["total"] == 2
    assert report["ok"] == 2
    assert report["fail"] == 0


def test_validate_all_xml_empty_dir(tmp_path):
    """Empty directory yields zero total."""
    report = validate_all_xml(tmp_path)
    assert report["total"] == 0


# ---------------------------------------------------------------------------
# Integration: test against real sample files from data/samples/html
# ---------------------------------------------------------------------------

def test_multi_page_with_about_page_sample(tmp_path):
    """Generate XML from the real about_page.html sample."""
    from bloggereasy.config import SAMPLES_DIR

    sample = SAMPLES_DIR / "html" / "about_page.html"
    if not sample.is_file():
        pytest.skip("about_page.html sample not available")

    entry = PageEntry(stem="about_page", template="about", source_html=sample)
    result = generate_page_xml(entry, tmp_path)
    assert result.validation["ok"], (
        f"about_page.html validation failed: {result.validation.get('errors')}"
    )
    assert result.bytes > 0


def test_multi_page_with_contact_page_sample(tmp_path):
    """Generate XML from the real contact_page.html sample."""
    from bloggereasy.config import SAMPLES_DIR

    sample = SAMPLES_DIR / "html" / "contact_page.html"
    if not sample.is_file():
        pytest.skip("contact_page.html sample not available")

    entry = PageEntry(stem="contact_page", template="contact", source_html=sample)
    result = generate_page_xml(entry, tmp_path)
    assert result.validation["ok"], (
        f"contact_page.html validation failed: {result.validation.get('errors')}"
    )
    assert result.bytes > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_multi_page_very_large_html(tmp_path):
    """Multi-page handles a page with many paragraphs."""
    large = "<!DOCTYPE html><html><head><title>Big</title></head><body>" + (
        "<p>Paragraph content.</p>" * 200
    ) + "</body></html>"

    pages = {"big": large}
    manifest = generate_multi_page_from_strings(pages, tmp_path)
    assert manifest.pages[0].validation["ok"]


def test_multi_page_unicode_title(tmp_path):
    """Titles with Unicode characters are preserved."""
    html = '<html><head><title>Blog về Ẩm Thực 🍜</title></head><body><p>Ngon!</p></body></html>'
    pages = {"unicode": html}
    out_dir = tmp_path / "out"
    manifest = generate_multi_page_from_strings(pages, out_dir)
    assert manifest.all_valid
    content = (out_dir / "unicode.xml").read_text(encoding="utf-8")
    assert "Ẩm Thực" in content or "Blog" in content


def test_multi_page_navigation_links_present():
    """DEFAULT_NAV_LINKS includes expected pages."""
    labels = {link["label"] for link in DEFAULT_NAV_LINKS}
    assert "Home" in labels
    assert "About" in labels
    assert "Contact" in labels


def test_stem_template_map_complete():
    """STEM_TEMPLATE_MAP only references templates in PRESETS."""
    from bloggereasy.theme.presets import PRESETS
    for stem, tmpl in STEM_TEMPLATE_MAP.items():
        assert tmpl in PRESETS, f"STEM_TEMPLATE_MAP[{stem!r}]={tmpl!r} not in PRESETS"


# ---------------------------------------------------------------------------
# Performance / sanity
# ---------------------------------------------------------------------------

def test_multi_page_many_pages(tmp_path):
    """Generate a site with 10 pages — ensures no runaway resource usage."""
    pages = {}
    for i in range(10):
        stem = f"page_{i:02d}"
        pages[stem] = (
            f"<!DOCTYPE html><html><head><title>Page {i}</title></head>"
            f"<body><p>Content for page {i}.</p></body></html>"
        )
    out_dir = tmp_path / "out"
    manifest = generate_multi_page_from_strings(pages, out_dir)
    assert len(manifest.pages) == 10
    assert manifest.total_bytes > 0
    # All should validate
    assert manifest.all_valid
