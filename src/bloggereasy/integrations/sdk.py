from __future__ import annotations

from pathlib import Path

from bloggereasy.export.writer import write_theme
from bloggereasy.parse.fetch import fetch_html_url, save_html
from bloggereasy.parse.html_page import parse_html_file, parse_html_string
from bloggereasy.theme.builder import build_blogger_xml
from bloggereasy.theme.presets import apply_dark_variant, apply_preset
from bloggereasy.theme.validate import validate_blogger_xml
from bloggereasy.vision.palette import structure_from_image


def generate_multi_page(
    pages: dict[str, Path],
    out_dir: Path,
    *,
    template: str = "simple",
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    """Generate a coordinated multi-page theme set.

    Each page gets its own Blogger XML, sharing colors/fonts from the first page.
    Typical use: home + about + contact.

    Args:
        pages: Dict of page_name -> html_path (e.g. {"home": Path("home.html"), ...}).
        out_dir: Output directory for the generated XML files.
        template: Theme preset name.
        widgets: Sidebar widget mode (default, minimal, full).
        dark: Force dark skin colors.

    Returns:
        Dict with per-page results, shared structure, and validation summary.
    """
    if not pages:
        raise ValueError("At least one page is required")
    page_names = list(pages.keys())

    # Parse all pages
    structures: dict[str, dict] = {}
    for name, path in pages.items():
        structures[name] = parse_html_file(path)

    # Share colors, fonts, and skin from the first page
    first = structures[page_names[0]]
    shared_colors = dict(first.get("colors") or {})
    shared_fonts = dict(first.get("fonts") or {})
    shared_skin = dict(first.get("skin") or {})

    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    all_valid = True

    for name in page_names:
        structure = dict(structures[name])
        # Override with shared theme
        structure["colors"] = dict(shared_colors)
        structure["fonts"] = dict(shared_fonts)
        structure["skin"] = dict(shared_skin)
        out_path = out_dir / f"{name}.xml"

        page_result = _build(
            structure, out_path, template=template, widgets=widgets, dark=dark
        )
        page_result["page"] = name
        results[name] = page_result
        if not page_result["validation"].get("ok"):
            all_valid = False

    return {
        "integration_version": "bloggereasy.sdk.multi.v1",
        "pages": results,
        "shared_colors": shared_colors,
        "shared_fonts": shared_fonts,
        "template": template,
        "all_valid": all_valid,
        "output_dir": str(out_dir),
    }


def _build(
    structure: dict,
    out_path: Path,
    *,
    template: str = "simple",
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    structure = apply_preset(structure, template)
    if dark:
        structure = apply_dark_variant(structure)
    if widgets != "default":
        features = dict(structure.get("features") or {})
        features["widgets"] = widgets
        features["sidebar"] = True
        structure["features"] = features
        if structure.get("layout") == "single-column":
            structure["layout"] = "two-column"
    xml = build_blogger_xml(structure, template_name=template)
    validation = validate_blogger_xml(xml)
    path = write_theme(xml, out_path)
    return {
        "integration_version": "bloggereasy.sdk.v1",
        "structure": structure,
        "output": str(path),
        "bytes": path.stat().st_size,
        "validation": validation,
        "import_hint": "Blogger \u2192 Theme \u2192 Backup/Restore \u2192 Upload XML",
    }


def generate_from_html(
    html_path: Path,
    out_path: Path,
    *,
    template: str = "simple",
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    structure = parse_html_file(html_path)
    result = _build(structure, out_path, template=template, widgets=widgets, dark=dark)
    result["mode"] = "html"
    return result


def generate_from_html_string(
    html: str,
    out_path: Path,
    *,
    template: str = "simple",
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    structure = parse_html_string(html)
    result = _build(structure, out_path, template=template, widgets=widgets, dark=dark)
    result["mode"] = "html_string"
    return result


def generate_from_url(
    url: str,
    out_path: Path,
    *,
    template: str = "simple",
    cache_dir: Path | None = None,
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    html = fetch_html_url(url)
    if cache_dir is not None:
        save_html(html, cache_dir / "fetched.html")
    structure = parse_html_string(html, source=url)
    result = _build(structure, out_path, template=template, widgets=widgets, dark=dark)
    result["mode"] = "url"
    result["url"] = url
    return result


def generate_from_image(
    image_path: Path,
    out_path: Path,
    *,
    title: str = "My Blog",
    template: str = "from-image",
    widgets: str = "default",
    dark: bool = False,
) -> dict:
    structure = structure_from_image(image_path, title=title)
    result = _build(structure, out_path, template=template, widgets=widgets, dark=dark)
    result["mode"] = "image"
    return result
