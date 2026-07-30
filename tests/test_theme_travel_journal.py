"""Theme pack sample: travel_journal (Fixes #28).

Verifies the travel_journal preset generates valid Blogger XML from the
self-contained HTML fixture, containing a b:skin block and a Blog widget.
"""

from __future__ import annotations

from pathlib import Path

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.presets import PRESETS
from bloggereasy.theme.validate import validate_theme_file

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples" / "html"


def test_travel_journal_preset_registered() -> None:
    assert "travel_journal" in PRESETS
    assert PRESETS["travel_journal"]["accent"] == "#0ea5e9"


def test_travel_journal_sample_exists() -> None:
    assert (SAMPLES / "travel_journal.html").is_file()


def test_gen_html_travel_journal_produces_skin_and_blog_widget(tmp_path: Path) -> None:
    src = SAMPLES / "travel_journal.html"
    out = tmp_path / "travel_journal.xml"
    result = generate_from_html(src, out, template="travel_journal")

    assert result["validation"]["ok"], result["validation"]
    assert out.exists()

    xml = out.read_text(encoding="utf-8")
    assert "xmlns:b=" in xml
    assert "b:skin" in xml
    assert "type='Blog'" in xml or 'type="Blog"' in xml
    # travel_journal accent should be pushed into the skin
    assert "0ea5e9" in xml
    assert "Template: travel_journal" in xml

    v = validate_theme_file(out)
    assert v["ok"] is True


def test_travel_journal_structure_has_hero(tmp_path: Path) -> None:
    """The travel journal HTML has a hero section that should be preserved."""
    src = SAMPLES / "travel_journal.html"
    out = tmp_path / "travel_journal_hero.xml"
    result = generate_from_html(src, out, template="travel_journal")

    assert result["structure"]["layout"] == "single-column"
    assert result["structure"]["title"] == "Coastal Escape — Travel Story"
