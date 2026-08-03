"""Golden XML + HTML fixture validation for travel_journal theme."""

from pathlib import Path

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.validate import validate_theme_file


def test_travel_journal_html_fixture_exists() -> None:
    fixture = Path("data/samples/html/travel_journal.html")
    assert fixture.exists(), "travel_journal.html fixture missing"
    html = fixture.read_text(encoding="utf-8")
    assert "Coastal Escape" in html or "travel" in html.lower()
    assert "<style>" in html


def test_travel_journal_golden_xml_exists() -> None:
    golden = Path("data/templates/travel_journal.xml")
    assert golden.exists(), "travel_journal.xml golden missing"
    xml = golden.read_text(encoding="utf-8")
    assert "b:skin" in xml
    assert "Travel Journal" in xml
    assert "BloggerEasy" in xml


def test_travel_journal_generate_valid(tmp_path: Path) -> None:
    src = Path("data/samples/html/travel_journal.html")
    out = tmp_path / "travel_journal.xml"
    result = generate_from_html(src, out, template="travel")
    assert result["validation"]["ok"] is True
    xml = out.read_text(encoding="utf-8")
    assert "b:skin" in xml or "skin" in xml.lower()
    assert "Blog" in xml


def test_travel_journal_golden_validates() -> None:
    golden = Path("data/templates/travel_journal.xml")
    v = validate_theme_file(golden)
    assert v["ok"] is True, f"Golden XML validation failed: {v.get('issues')}"
