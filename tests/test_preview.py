from bloggereasy.parse.html_page import parse_html_file
from bloggereasy.theme.presets import apply_preset
from bloggereasy.theme.preview import structure_to_preview_html
from pathlib import Path


def test_preview_html_contains_title() -> None:
    sample = Path("data/samples/html/portfolio.html")
    structure = apply_preset(parse_html_file(sample), "portfolio")
    html = structure_to_preview_html(structure)
    assert "<!DOCTYPE html>" in html
    assert "preview" in html.lower()
    assert structure.get("title") is not None
