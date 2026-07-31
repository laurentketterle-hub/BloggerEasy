"""Tests for the new multi-page templates (home, about, contact).

Covers:
- Template presence in PRESETS
- Template application via apply_preset
- Valid XML generation for each template
- Edge cases: unknown template fallback, dark variant
- CLI integration: _sample_for_template, templates list
"""

from __future__ import annotations

import pytest

from bloggereasy.theme.presets import PRESETS, apply_dark_variant, apply_preset
from bloggereasy.theme.models import PageStructure


# ---------------------------------------------------------------------------
# Template presence
# ---------------------------------------------------------------------------

EXPECTED_MULTI_PAGE_TEMPLATES = {"home", "about", "contact"}


def test_new_templates_exist_in_presets():
    """Each multi-page template is defined in PRESETS."""
    for template in EXPECTED_MULTI_PAGE_TEMPLATES:
        assert template in PRESETS, (
            f"Template '{template}' not found in PRESETS; "
            f"available: {sorted(PRESETS)}"
        )


def test_home_preset_single_column():
    """Home template uses single-column layout."""
    preset = PRESETS["home"]
    assert preset["layout_hint"] == "single-column"
    assert preset["dark"] is False
    assert preset.get("accent") == "#4cc9f0"


def test_about_preset_two_column():
    """About template uses two-column layout with pink accent."""
    preset = PRESETS["about"]
    assert preset["layout_hint"] == "two-column"
    assert preset.get("accent") == "#f72585"


def test_contact_preset_dense():
    """Contact template is dense (compact layout)."""
    preset = PRESETS["contact"]
    assert preset.get("dense") is True
    assert preset.get("accent") == "#4cc9f0"


# ---------------------------------------------------------------------------
# apply_preset behaviour
# ---------------------------------------------------------------------------

def _minimal_structure() -> dict:
    return PageStructure(title="Test Page").model_dump(exclude_none=True)


def test_apply_home_preset_sets_layout():
    """Applying home preset yields single-column layout."""
    result = apply_preset(_minimal_structure(), "home")
    assert result["template"] == "home"
    assert result["layout"] == "single-column"


def test_apply_about_preset_sets_sidebar():
    """About template (two-column) activates sidebar."""
    result = apply_preset(_minimal_structure(), "about")
    assert result.get("features", {}).get("sidebar") is True


def test_apply_contact_preset_sets_dense():
    """Contact template sets dense feature flag."""
    result = apply_preset(_minimal_structure(), "contact")
    assert result.get("features", {}).get("dense") is True


def test_apply_preset_applies_accent_color():
    """Applying a preset with accent updates the primary color."""
    result = apply_preset(_minimal_structure(), "about")
    assert result["colors"]["primary"] == "#f72585"


def test_apply_preset_falls_back_to_simple():
    """Unknown template falls back to 'simple'."""
    result = apply_preset(_minimal_structure(), "nonexistent")
    assert result["template"] == "nonexistent"
    # simple preset is 'auto', which doesn't force sidebar
    assert result.get("features", {}).get("sidebar", False) is False


def test_apply_home_then_dark():
    """Home + dark variant combines correctly."""
    result = apply_preset(_minimal_structure(), "home")
    result = apply_dark_variant(result)
    assert result["features"]["dark"] is True
    assert result["colors"]["background"] == "#0f172a"


# ---------------------------------------------------------------------------
# CLI integration tests (_sample_for_template)
# ---------------------------------------------------------------------------

def test_sample_for_template_home():
    """_sample_for_template resolves 'home' to an existing sample file."""
    from bloggereasy.cli import _sample_for_template
    path = _sample_for_template("home")
    assert path.name == "minimal_blog.html"
    # The file must exist inside the repo
    assert path.is_file(), f"Sample not found: {path}"


def test_sample_for_template_about():
    """_sample_for_template resolves 'about' to about_page.html."""
    from bloggereasy.cli import _sample_for_template
    path = _sample_for_template("about")
    assert path.name == "about_page.html"
    assert path.is_file(), f"Sample not found: {path}"


def test_sample_for_template_contact():
    """_sample_for_template resolves 'contact' to contact_page.html."""
    from bloggereasy.cli import _sample_for_template
    path = _sample_for_template("contact")
    assert path.name == "contact_page.html"
    assert path.is_file(), f"Sample not found: {path}"


def test_sample_for_template_unknown_raises():
    """Unknown template triggers typer.Exit with a helpful message."""
    from bloggereasy.cli import _sample_for_template
    import typer
    with pytest.raises(typer.Exit):
        _sample_for_template("no_such_template_zzz")


# ---------------------------------------------------------------------------
# Generate valid XML for each multi-page template (in-memory)
# ---------------------------------------------------------------------------

SIMPLE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Test Site</title></head>
<body>
  <header><h1>Welcome</h1><nav><a href="/">Home</a></nav></header>
  <main><article><h2>Hello World</h2><p>This is a test page.</p></article></main>
  <footer><p>&copy; 2025 Test</p></footer>
</body>
</html>
"""


def test_generate_valid_xml_home_template(tmp_path):
    """Generate valid Blogger XML with the 'home' template."""
    from bloggereasy.integrations.sdk import generate_from_html_string

    out = tmp_path / "home_test.xml"
    result = generate_from_html_string(SIMPLE_HTML, out, template="home")
    assert result["validation"]["ok"], (
        f"Validation failed: {result['validation'].get('errors')}"
    )
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "b:skin" in content
    assert "b:section" in content


def test_generate_valid_xml_about_template(tmp_path):
    """Generate valid Blogger XML with the 'about' template."""
    from bloggereasy.integrations.sdk import generate_from_html_string

    out = tmp_path / "about_test.xml"
    result = generate_from_html_string(SIMPLE_HTML, out, template="about")
    assert result["validation"]["ok"], (
        f"Validation failed: {result['validation'].get('errors')}"
    )
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "b:skin" in content
    assert "Blog" in content


def test_generate_valid_xml_contact_template(tmp_path):
    """Generate valid Blogger XML with the 'contact' template."""
    from bloggereasy.integrations.sdk import generate_from_html_string

    out = tmp_path / "contact_test.xml"
    result = generate_from_html_string(SIMPLE_HTML, out, template="contact")
    assert result["validation"]["ok"], (
        f"Validation failed: {result['validation'].get('errors')}"
    )
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "b:skin" in content


def test_all_new_templates_generate_valid_xml(tmp_path):
    """Parametric: home, about, contact all produce valid XML."""
    from bloggereasy.integrations.sdk import generate_from_html_string

    for tmpl in ["home", "about", "contact"]:
        out = tmp_path / f"{tmpl}_test.xml"
        result = generate_from_html_string(SIMPLE_HTML, out, template=tmpl)
        assert result["validation"]["ok"], (
            f"Template '{tmpl}' failed: {result['validation'].get('errors')}"
        )
        content = out.read_text(encoding="utf-8")
        assert "b:skin" in content, f"No b:skin in {tmpl} output"
        assert "b:section" in content, f"No b:section in {tmpl} output"


# ---------------------------------------------------------------------------
# Template count consistency
# ---------------------------------------------------------------------------

def test_all_templates_at_least_fifteen():
    """We expect at least 15 templates (counting the new ones)."""
    assert len(PRESETS) >= 15, (
        f"Expected >=15 templates, got {len(PRESETS)}: {sorted(PRESETS)}"
    )
