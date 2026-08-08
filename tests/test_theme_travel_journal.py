from __future__ import annotations

from pathlib import Path

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.presets import PRESETS

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples" / "html"


def test_travel_journal_preset_registered() -> None:
    assert "travel_journal" in PRESETS, "travel_journal missing from PRESETS"


def test_travel_journal_generates_valid_xml(tmp_path: Path) -> None:
    out = tmp_path / "travel_journal.xml"
    result = generate_from_html(SAMPLES / "travel_journal.html", out, template="travel_journal")
    assert result["validation"]["ok"], "travel_journal failed validation"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "b:skin" in text
    assert "Template: travel_journal" in text


def test_travel_journal_has_correct_accent() -> None:
    preset = PRESETS["travel_journal"]
    assert preset["accent"] == "#d97742"
    assert preset["layout_hint"] == "two-column"
    assert preset["dark"] is False
