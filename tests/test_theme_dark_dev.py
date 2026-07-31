"""Theme pack sample: dark_dev (Fixes #24).

Verifies the dark_dev preset generates valid Blogger XML from the
self-contained HTML fixture, containing a b:skin block and a Blog widget.
"""

from __future__ import annotations

from pathlib import Path

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.presets import PRESETS
from bloggereasy.theme.validate import validate_theme_file

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples" / "html"


def test_dark_dev_preset_registered() -> None:
    assert "dark_dev" in PRESETS
    assert PRESETS["dark_dev"]["accent"] == "#38bdf8"
    assert PRESETS["dark_dev"]["dark"] is True


def test_dark_dev_sample_exists() -> None:
    assert (SAMPLES / "dark_dev.html").is_file()


def test_gen_html_dark_dev_produces_skin_and_blog_widget(tmp_path: Path) -> None:
    src = SAMPLES / "dark_dev.html"
    out = tmp_path / "dark_dev.xml"
    result = generate_from_html(src, out, template="dark_dev")

    assert result["validation"]["ok"], result["validation"]
    assert out.exists()

    xml = out.read_text(encoding="utf-8")
    assert "xmlns:b=" in xml
    assert "b:skin" in xml
    assert "type='Blog'" in xml or 'type="Blog"' in xml
    # dark_dev dark theme colors should be present in the skin
    assert "#0f172a" in xml or "0f172a" in xml  # dark background
    assert "Template: dark_dev" in xml

    v = validate_theme_file(out)
    assert v["ok"] is True
