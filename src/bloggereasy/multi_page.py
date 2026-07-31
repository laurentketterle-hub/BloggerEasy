"""Multi-page Blogger site generator.

Build a complete multi-page Blogger theme bundle from a directory of HTML files.
Each HTML file maps to a page template (home, about, contact, etc.) and the
generator produces a validated XML theme for each page, plus a site manifest
with cross-page navigation links.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bloggereasy.config import OUT_DIR, SAMPLES_DIR
from bloggereasy.integrations.sdk import generate_from_html, generate_from_html_string
from bloggereasy.parse.html_page import parse_html_file, parse_html_string
from bloggereasy.theme.builder import build_blogger_xml
from bloggereasy.theme.presets import PRESETS, apply_preset
from bloggereasy.theme.validate import validate_blogger_xml

#: Mapping from filename stem to template name.  Recognised stems get the
#: matching preset; unrecognised ones fall back to ``"simple"``.
STEM_TEMPLATE_MAP: dict[str, str] = {
    "home": "home",
    "index": "home",
    "about": "about",
    "about_page": "about",
    "about_team": "about",
    "contact": "contact",
    "contact_page": "contact",
    "contact_form": "contact",
    "contact_card": "contact",
    "portfolio": "portfolio",
    "news": "news",
    "blog": "simple",
    "docs": "docs",
    "landing": "landing",
    "dark": "dark",
}

#: Multi-page site navigation structure — each page links to others.
DEFAULT_NAV_LINKS: list[dict[str, str]] = [
    {"label": "Home", "href": "/"},
    {"label": "About", "href": "/about"},
    {"label": "Contact", "href": "/contact"},
    {"label": "Blog", "href": "/blog"},
]


@dataclass
class PageEntry:
    """A single page in a multi-page site."""

    stem: str
    template: str
    title: str = ""
    description: str = ""
    source_html: Path | None = None
    generated_xml: Path | None = None
    validation: dict[str, Any] = field(default_factory=lambda: {"ok": False, "errors": []})
    bytes: int = 0
    nav_links: list[dict[str, str]] = field(default_factory=list)


@dataclass
class SiteManifest:
    """Manifest for a generated multi-page Blogger site."""

    site_name: str
    pages: list[PageEntry] = field(default_factory=list)
    total_bytes: int = 0
    all_valid: bool = False
    output_dir: Path | None = None
    errors: list[str] = field(default_factory=list)
    template_summary: dict[str, int] = field(default_factory=dict)


def guess_template_for_stem(stem: str) -> str:
    """Map a filename stem to the best-matching template preset.

    Parameters
    ----------
    stem : str
        Lowercase filename stem (no extension).

    Returns
    -------
    str
        Template name from :data:`PRESETS`, defaulting to ``"simple"``.
    """
    stem_lower = stem.lower().replace("-", "_").replace(" ", "_")
    # Empty stem → simple
    if not stem_lower:
        return "simple"
    # Direct lookup
    if stem_lower in STEM_TEMPLATE_MAP:
        return STEM_TEMPLATE_MAP[stem_lower]
    # Fuzzy match: check if any known stem is a substring
    for known, tmpl in STEM_TEMPLATE_MAP.items():
        if known in stem_lower or stem_lower in known:
            return tmpl
    return "simple"


def resolve_template(template_name: str) -> str:
    """Return a valid template name, defaulting to simple if unknown."""
    return template_name if template_name in PRESETS else "simple"


def discover_html_files(directory: Path, *, pattern: str = "*.html") -> list[Path]:
    """Find all HTML files in *directory*, sorted by name.

    Parameters
    ----------
    directory : Path
        Directory to scan.
    pattern : str
        Glob pattern (default ``"*.html"``).

    Returns
    -------
    list[Path]
        Sorted list of matching files.
    """
    if not directory.is_dir():
        return []
    return sorted(directory.glob(pattern))


def build_page_entry(
    html_path: Path,
    *,
    template: str | None = None,
    nav_links: list[dict[str, str]] | None = None,
) -> PageEntry:
    """Parse an HTML file and prepare a :class:`PageEntry`.

    Parameters
    ----------
    html_path : Path
        Path to an HTML file.
    template : str | None
        Override template.  Guessed from stem if *None*.
    nav_links : list[dict] | None
        Navigation links for cross-page linking.

    Returns
    -------
    PageEntry
    """
    stem = html_path.stem
    tmpl = resolve_template(template or guess_template_for_stem(stem))
    
    structure = parse_html_file(html_path)
    title = str(structure.get("title") or stem.replace("_", " ").title())
    description = str(structure.get("description") or f"{title} page")

    return PageEntry(
        stem=stem,
        template=tmpl,
        title=title,
        description=description,
        source_html=html_path,
        nav_links=list(nav_links or DEFAULT_NAV_LINKS),
    )


def generate_page_xml(
    entry: PageEntry,
    output_dir: Path,
    *,
    widgets: str = "default",
    dark: bool = False,
) -> PageEntry:
    """Generate validated Blogger XML for a single page entry.

    The generated XML is written to *output_dir* / ``{stem}.xml`` and the
    :class:`PageEntry` is updated in-place with the result.

    Parameters
    ----------
    entry : PageEntry
        Page to generate.
    output_dir : Path
        Directory for output XML files.
    widgets : str
        Widget preset (``"default"``, ``"minimal"``, ``"full"``).
    dark : bool
        Force dark theme.

    Returns
    -------
    PageEntry
        The same entry, mutated with generation results.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{entry.stem}.xml"

    if entry.source_html is None or not entry.source_html.is_file():
        entry.validation = {"ok": False, "errors": ["Source HTML not found"]}
        return entry

    result = generate_from_html(
        entry.source_html,
        out_path,
        template=entry.template,
        widgets=widgets,
        dark=dark,
    )

    entry.generated_xml = out_path
    entry.validation = result.get("validation", {"ok": False, "errors": ["unknown"]})
    entry.bytes = result.get("bytes", 0)
    entry.title = result.get("structure", {}).get("title") or entry.title
    return entry


def generate_page_xml_from_html_string(
    entry: PageEntry,
    html: str,
    output_dir: Path,
    *,
    widgets: str = "default",
    dark: bool = False,
) -> PageEntry:
    """Like :func:`generate_page_xml` but works with an HTML string."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{entry.stem}.xml"

    result = generate_from_html_string(
        html,
        out_path,
        template=entry.template,
        widgets=widgets,
        dark=dark,
    )
    entry.generated_xml = out_path
    entry.validation = result.get("validation", {"ok": False, "errors": ["unknown"]})
    entry.bytes = result.get("bytes", 0)
    entry.title = result.get("structure", {}).get("title") or entry.title
    return entry


def generate_multi_page_site(
    html_dir: Path,
    output_dir: Path | None = None,
    *,
    site_name: str = "My Multi-Page Blog",
    template_overrides: dict[str, str] | None = None,
    widgets: str = "default",
    dark: bool = False,
) -> SiteManifest:
    """Generate a full multi-page Blogger site from a directory of HTML files.

    This is the top-level entry point for multi-page site generation.  Every
    HTML file in *html_dir* is parsed, mapped to a template, and converted to
    a validated Blogger XML theme.  The returned :class:`SiteManifest` carries
    a summary of every page plus aggregate statistics.

    Parameters
    ----------
    html_dir : Path
        Directory containing HTML source files.
    output_dir : Path | None
        Output directory for generated XML.  Defaults to
        ``OUT_DIR / "multi_page"``.
    site_name : str
        Human-readable site name for the manifest.
    template_overrides : dict[str, str] | None
        Mapping ``{stem: template_name}`` to override auto-detection.
    widgets : str
        Widget pack (``"default"``, ``"minimal"``, ``"full"``).
    dark : bool
        Apply dark variant to all pages.

    Returns
    -------
    SiteManifest
    """
    overrides = template_overrides or {}
    out = output_dir or (OUT_DIR / "multi_page")
    out.mkdir(parents=True, exist_ok=True)

    html_files = discover_html_files(html_dir)
    if not html_files:
        return SiteManifest(
            site_name=site_name,
            errors=["No HTML files found in directory"],
            output_dir=out,
        )

    manifest = SiteManifest(site_name=site_name, output_dir=out)
    nav_links = _build_nav_from_files(html_files)

    for html_path in html_files:
        stem = html_path.stem
        tmpl = overrides.get(stem) or guess_template_for_stem(stem)
        page = build_page_entry(html_path, template=tmpl, nav_links=nav_links)
        page = generate_page_xml(page, out, widgets=widgets, dark=dark)
        manifest.pages.append(page)

    _summarize_manifest(manifest)
    _write_manifest_json(manifest, out)
    return manifest


def generate_multi_page_from_strings(
    html_pages: dict[str, str],
    output_dir: Path | None = None,
    *,
    site_name: str = "My Multi-Page Blog",
    template_overrides: dict[str, str] | None = None,
    widgets: str = "default",
    dark: bool = False,
) -> SiteManifest:
    """Generate a multi-page site from in-memory HTML strings.

    This is useful for testing and programmatic generation where HTML content
    is constructed at runtime rather than read from disk.

    Parameters
    ----------
    html_pages : dict[str, str]
        Mapping ``{stem: html_content}``.
    output_dir : Path | None
        Output directory.
    site_name : str
        Site name.
    template_overrides : dict[str, str] | None
        Per-page template overrides.
    widgets : str
        Widget pack.
    dark : bool
        Dark mode.

    Returns
    -------
    SiteManifest
    """
    overrides = template_overrides or {}
    out = output_dir or (OUT_DIR / "multi_page")
    out.mkdir(parents=True, exist_ok=True)

    manifest = SiteManifest(site_name=site_name, output_dir=out)
    stems = list(html_pages.keys())
    nav_links = _build_nav_from_stems(stems)

    for stem, html in html_pages.items():
        tmpl = overrides.get(stem) or guess_template_for_stem(stem)
        page = PageEntry(
            stem=stem,
            template=resolve_template(tmpl),
            title=stem.replace("_", " ").title(),
            nav_links=nav_links,
        )
        page = generate_page_xml_from_html_string(page, html, out, widgets=widgets, dark=dark)
        manifest.pages.append(page)

    _summarize_manifest(manifest)
    _write_manifest_json(manifest, out)
    return manifest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_nav_from_files(files: list[Path]) -> list[dict[str, str]]:
    """Construct navigation links from a list of HTML file paths."""
    nav: list[dict[str, str]] = []
    seen: set[str] = set()
    label_map = {
        "home": "Home", "index": "Home",
        "about": "About", "about_page": "About", "about_team": "About Team",
        "contact": "Contact", "contact_page": "Contact", "contact_form": "Contact",
        "blog": "Blog", "news": "News", "portfolio": "Portfolio",
        "docs": "Docs", "landing": "Landing",
    }
    for f in files:
        stem = f.stem
        if stem in seen:
            continue
        seen.add(stem)
        label = label_map.get(stem, stem.replace("_", " ").title())
        nav.append({"label": label, "href": f"/{stem}"})
    return nav or DEFAULT_NAV_LINKS


def _build_nav_from_stems(stems: list[str]) -> list[dict[str, str]]:
    """Construct nav links from stem strings."""
    nav: list[dict[str, str]] = []
    label_map = {
        "home": "Home", "index": "Home",
        "about": "About", "contact": "Contact",
        "blog": "Blog", "news": "News", "portfolio": "Portfolio",
        "docs": "Docs", "landing": "Landing",
    }
    for stem in stems:
        label = label_map.get(stem, stem.replace("_", " ").title())
        nav.append({"label": label, "href": f"/{stem}"})
    return nav


def _summarize_manifest(manifest: SiteManifest) -> None:
    """Compute aggregate stats for a manifest."""
    manifest.total_bytes = sum(p.bytes for p in manifest.pages)
    manifest.all_valid = all(p.validation.get("ok") for p in manifest.pages)
    manifest.errors = [
        f"{p.stem}: {err}"
        for p in manifest.pages
        for err in (p.validation.get("errors") or [])
        if not p.validation.get("ok")
    ]
    manifest.template_summary = {}
    for p in manifest.pages:
        manifest.template_summary[p.template] = (
            manifest.template_summary.get(p.template, 0) + 1
        )


def _write_manifest_json(manifest: SiteManifest, output_dir: Path) -> None:
    """Persist the manifest as JSON in the output directory."""
    data: dict[str, Any] = {
        "site_name": manifest.site_name,
        "all_valid": manifest.all_valid,
        "total_bytes": manifest.total_bytes,
        "page_count": len(manifest.pages),
        "template_summary": manifest.template_summary,
        "errors": manifest.errors,
        "pages": [
            {
                "stem": p.stem,
                "template": p.template,
                "title": p.title,
                "valid": p.validation.get("ok", False),
                "bytes": p.bytes,
                "xml": str(p.generated_xml) if p.generated_xml else None,
            }
            for p in manifest.pages
        ],
    }
    manifest_path = output_dir / "site_manifest.json"
    manifest_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def validate_all_xml(output_dir: Path) -> dict[str, Any]:
    """Batch-validate every ``.xml`` file in *output_dir*.

    Returns a report with per-file status.
    """
    xml_files = sorted(output_dir.glob("*.xml")) if output_dir.is_dir() else []
    report: dict[str, Any] = {"total": len(xml_files), "ok": 0, "fail": 0, "files": {}}
    for xml_path in xml_files:
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        validation = validate_blogger_xml(content)
        report["files"][xml_path.stem] = validation
        if validation.get("ok"):
            report["ok"] += 1
        else:
            report["fail"] += 1
    return report
