from __future__ import annotations

from pathlib import Path

from bloggereasy.theme import generate_preview_html


SAMPLE_HTML = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>"


def test_generate_preview_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "preview.html"
    result = generate_preview_html(SAMPLE_HTML, out, title="Test Blog")
    assert result == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "BloggerEasy Preview" in content
    assert '<iframe' in content
    assert "viewport-btn" in content
    assert "Hello World" in content


def test_preview_has_viewport_buttons(tmp_path: Path) -> None:
    out = tmp_path / "preview.html"
    generate_preview_html(SAMPLE_HTML, out)
    content = out.read_text(encoding="utf-8")
    assert "Desktop" in content
    assert "Tablet" in content
    assert "Mobile" in content
    assert "setViewport" in content


def test_preview_with_custom_template_name(tmp_path: Path) -> None:
    out = tmp_path / "preview.html"
    generate_preview_html(SAMPLE_HTML, out, template_name="dark_dev")
    content = out.read_text(encoding="utf-8")
    assert "dark_dev" in content


def test_preview_respects_title(tmp_path: Path) -> None:
    out = tmp_path / "preview.html"
    generate_preview_html(SAMPLE_HTML, out, title="My Custom Blog")
    content = out.read_text(encoding="utf-8")
    assert "My Custom Blog" in content
