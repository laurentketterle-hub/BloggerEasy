from __future__ import annotations

from pathlib import Path

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.presets import PRESETS

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples" / "html"


def test_dark_dev_preset_registered() -> None:
    assert "dark_dev" in PRESETS, "dark_dev missing from PRESETS"


def test_dark_dev_generates_valid_xml(tmp_path: Path) -> None:
    out = tmp_path / "dark_dev.xml"
    result = generate_from_html(SAMPLES / "dark_dev.html", out, template="dark_dev")
    assert result["validation"]["ok"], "dark_dev failed validation"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "b:skin" in text
    assert "Template: dark_dev" in text


def test_dark_dev_is_dark_mode() -> None:
    preset = PRESETS["dark_dev"]
    assert preset["dark"] is True
    assert preset["accent"] == "#58a6ff"
