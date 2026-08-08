from __future__ import annotations

from pathlib import Path

from bloggereasy.multipage import generate_multipage, list_templates
from bloggereasy.theme.presets import PRESETS


def test_list_templates() -> None:
    templates = list_templates()
    assert "home" in templates
    assert "about" in templates
    assert "contact" in templates
    assert len(templates) == 3


def test_generate_multipage_creates_all_pages(tmp_path: Path) -> None:
    result = generate_multipage(output_dir=tmp_path)
    assert result["all_ok"], f"Not all pages passed: {result}"
    assert (tmp_path / "home.xml").exists()
    assert (tmp_path / "about.xml").exists()
    assert (tmp_path / "contact.xml").exists()


def test_generate_multipage_with_custom_config(tmp_path: Path) -> None:
    config = {
        "site_title": "Test Blog",
        "site_tagline": "Testing",
        "hero_text": "Hello Test",
    }
    result = generate_multipage(config=config, output_dir=tmp_path, template="simple")
    assert result["all_ok"]
    for page in result["pages"].values():
        assert page["ok"]


def test_generate_multipage_rejects_bad_template(tmp_path: Path) -> None:
    result = generate_multipage(template="nonexistent", output_dir=tmp_path)
    assert result["template"] == "simple"  # falls back


def test_multipage_supports_all_presets(tmp_path: Path) -> None:
    for preset_name in ["simple", "dark", "magazine", "personal", "docs"]:
        result = generate_multipage(template=preset_name, output_dir=tmp_path / preset_name)
        assert result["all_ok"], f"{preset_name} failed: {result}"
