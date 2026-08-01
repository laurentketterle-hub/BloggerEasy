from __future__ import annotations

from pathlib import Path

from bloggereasy.export.writer import write_theme
from bloggereasy.parse.fetch import fetch_html_url, save_html
from bloggereasy.parse.html_page import parse_html_file, parse_html_string
from bloggereasy.theme.builder import build_blogger_xml
from bloggereasy.theme.presets import apply_dark_variant, apply_preset
from bloggereasy.theme.preview import write_preview_html
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


def generate_preview_sidecar(structure: dict, out_path: Path) -> dict:
    """Generate a responsive preview HTML sidecar with device-frame breakpoint simulation.

    Shows the theme at three breakpoints (mobile 375px, tablet 768px, desktop 1100px)
    in a single HTML page with iframes — useful for local browser validation.
    """
    from html import escape

    title = escape(str(structure.get("title") or "My Blog"))
    colors = structure.get("colors") or {}
    primary = escape(str(colors.get("primary") or "#1a73e8"))
    secondary = escape(str(colors.get("secondary") or "#34a853"))
    fonts = structure.get("fonts") or {}
    body_font = escape(str(fonts.get("body") or "system-ui, sans-serif"))
    heading_font = escape(str(fonts.get("heading") or "Georgia, serif"))
    layout = str(structure.get("layout") or "single-column")
    features = structure.get("features") or {}
    sidebar = bool(features.get("sidebar")) or layout in {"two-column", "three-column"}
    template_name = escape(str(structure.get("template") or "simple"))
    desc = escape(str(structure.get("description") or "Preview generated by BloggerEasy"))
    nav = structure.get("nav_links") or [
        {"label": "Home"}, {"label": "About"}, {"label": "Contact"}
    ]
    nav_html = "".join(
        f'<a href="#">{escape(str(n.get("label") or "Link"))}</a>' for n in nav[:8]
    )
    paras = structure.get("sample_paragraphs") or [
        "This is a responsive preview of your Blogger theme.",
        "Each frame shows the theme at a different viewport width.",
    ]
    body_html = "".join(f"<p>{escape(str(p))}</p>" for p in paras[:3])

    sidebar_col = "1fr 220px" if sidebar else "1fr"
    sidebar_html = ""
    if sidebar:
        sidebar_html = (
            '<aside class="pv-sidebar"><h4>Sidebar</h4>'
            '<p>Widgets &amp; labels appear here.</p></aside>'
        )

    iframe_inner = escape(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:{body_font};color:#222;line-height:1.5}}
.pv-header{{background:{primary};color:#fff;padding:1rem}} .pv-header h2{{margin:0;font-family:{heading_font};font-size:1.1rem}}
.pv-nav{{display:flex;gap:0.5rem;flex-wrap:wrap;padding:0.4rem 1rem;background:{secondary}}}
.pv-nav a{{color:#fff;text-decoration:none;font-weight:600;font-size:0.8rem}}
.pv-wrap{{padding:0.75rem;display:grid;grid-template-columns:{sidebar_col};gap:0.75rem}}
.pv-content h3{{font-family:{heading_font};margin-top:0;font-size:0.95rem}}
.pv-content p{{font-size:0.82rem;margin:0.3rem 0}}
.pv-sidebar{{background:#f8f9fa;border:1px solid #e0e0e0;border-radius:6px;padding:0.6rem;font-size:0.8rem}}
.pv-sidebar h4{{margin:0 0 0.3rem;font-size:0.85rem}}
.pv-footer{{text-align:center;padding:0.5rem;font-size:0.72rem;color:#999}}
@media(max-width:600px){{.pv-wrap{{grid-template-columns:1fr}}.pv-nav{{flex-direction:column;gap:0.2rem}}.pv-header h2{{font-size:0.9rem}}}}
@media(min-width:800px){{.pv-header{{padding:1.5rem 2rem}}.pv-header h2{{font-size:1.6rem}}.pv-wrap{{padding:1.25rem}}}}
</style></head><body>
<div class="pv-header"><h2>{title}</h2></div>
<nav class="pv-nav">{nav_html}</nav>
<div class="pv-wrap"><div class="pv-content"><h3>Welcome</h3>{body_html}</div>{sidebar_html}</div>
<div class="pv-footer">{desc}</div>
</body></html>""", quote=True)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"/><title>{title} · Responsive Preview</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:{body_font};color:#333;background:#f0f2f5}}
.tb{{background:#1a1a2e;color:#fff;padding:0.75rem 1.25rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;font-size:0.9rem;position:sticky;top:0;z-index:10}}
.tb h1{{font-size:1.1rem;margin:0;font-weight:600}}
.badge{{display:inline-block;padding:0.15rem 0.5rem;border-radius:4px;font-size:0.7rem;font-weight:600}}
.badge-t{{background:{secondary};color:#fff}} .badge-p{{background:{primary};color:#fff}}
.bps{{display:flex;flex-wrap:wrap;gap:1.5rem;padding:2rem 1rem;justify-content:center}}
.bp-card{{background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;min-width:260px}}
.bp-label{{padding:0.5rem 0.75rem;font-size:0.78rem;font-weight:700;color:#555;background:#fafafa;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center}}
.bp-label .sz{{color:#999;font-weight:400}}
.frame{{margin:0 auto;overflow:hidden;border:2px solid #e0e0e0;border-radius:4px;transition:border-color 0.2s}}
.frame:hover{{border-color:{primary}}}
.frame iframe{{border:none;width:100%;display:block}}
.leg{{max-width:960px;margin:0 auto;padding:1rem 1.5rem 2rem;font-size:0.85rem;color:#666;text-align:center}}
.leg code{{background:#eee;padding:0.15rem 0.35rem;border-radius:3px}}
@media(max-width:768px){{.bps{{padding:1rem 0.5rem;gap:1rem}}.bp-card{{min-width:240px}}}}
</style></head><body>
<div class="tb"><h1>{title}</h1><span class="badge badge-t">template:{template_name}</span><span class="badge badge-p">primary:{primary}</span></div>
<div class="bps">
<div class="bp-card"><div class="bp-label">📱 Mobile <span class="sz">375×667</span></div><div class="frame" style="width:375px;height:450px"><iframe srcdoc="{iframe_inner}" width="375" height="450" scrolling="yes" title="Mobile 375px"></iframe></div></div>
<div class="bp-card"><div class="bp-label">📋 Tablet <span class="sz">768×900</span></div><div class="frame" style="width:580px;height:500px"><iframe srcdoc="{iframe_inner}" width="580" height="500" scrolling="yes" title="Tablet 768px"></iframe></div></div>
<div class="bp-card"><div class="bp-label">🖥️ Desktop <span class="sz">1100×700</span></div><div class="frame" style="width:680px;height:480px"><iframe srcdoc="{iframe_inner}" width="680" height="480" scrolling="yes" title="Desktop 1100px"></iframe></div></div>
</div>
<div class="leg">Responsive preview sidecar · Layout:<code>{layout}</code> · Sidebar:<code>{"yes" if sidebar else "no"}</code> · <code>bloggereasy gen ... --preview</code></div>
</body></html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {"output": str(out_path), "bytes": out_path.stat().st_size, "breakpoints": 3}
