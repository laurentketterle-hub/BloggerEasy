"""Tests for multi-page site generator (bounty #80)."""
import sys
sys.path.insert(0, "src")

from bloggereasy.theme.multipage import build_multi_page_site


def test_generates_all_pages(tmp_path):
    structure = {"title": "Test", "colors": {"primary": "#ff6600"}}
    result = build_multi_page_site(structure, tmp_path / "site", template="simple")
    pages = {p["slug"]: p for p in result["pages"]}
    assert "home" in pages
    assert "about" in pages
    assert "contact" in pages
    assert "index" in pages
    for p in result["pages"]:
        assert (tmp_path / "site" / (p["slug"] + ".html")).exists() or p["slug"] == "index"


def test_home_page_has_title_and_nav(tmp_path):
    structure = {"title": "MyCo", "colors": {"primary": "#333"}}
    result = build_multi_page_site(structure, tmp_path / "site", template="simple")
    home_path = tmp_path / "site" / "home.html"
    content = home_path.read_text()
    assert "MyCo" in content
    assert "Welcome" in content
    assert 'href="home.html"' in content
    assert 'href="about.html"' in content
    assert 'href="contact.html"' in content


def test_index_redirects_to_home(tmp_path):
    structure = {"title": "X"}
    result = build_multi_page_site(structure, tmp_path / "site")
    idx = tmp_path / "site" / "index.html"
    content = idx.read_text()
    assert "home.html" in content
    assert "Redirecting" in content


def test_custom_content(tmp_path):
    structure = {"title": "Custom"}
    custom = {
        "home": {"title": "My Home", "heading": "Welcome!", "content": "<p>Hello</p>"},
    }
    result = build_multi_page_site(structure, tmp_path / "site", custom_content=custom)
    home = tmp_path / "site" / "home.html"
    content = home.read_text()
    assert "My Home" in content
    assert "Welcome!" in content
    assert "<p>Hello</p>" in content


def test_site_name_override(tmp_path):
    structure = {"title": "Original"}
    result = build_multi_page_site(structure, tmp_path / "site", site_name="Overridden")
    home = tmp_path / "site" / "home.html"
    content = home.read_text()
    assert "Overridden" in content
    assert "Original" not in content


def test_template_changes_colors(tmp_path):
    structure = {"title": "T"}
    result = build_multi_page_site(structure, tmp_path / "site", template="dark")
    home = tmp_path / "site" / "home.html"
    content = home.read_text()
    # Dark template should have dark background colors
    assert "#0f172a" in content or "#111827" in content
