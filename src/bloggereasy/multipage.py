"""Multi-page site generator for BloggerEasy.

Generates a coordinated set of pages (home, about, contact) from a single
configuration, producing Blogger XML themes for each page.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bloggereasy.integrations.sdk import generate_from_html
from bloggereasy.theme.presets import PRESETS, apply_preset


MULTIPAGE_TEMPLATES = {
    "home": "templates/multipage/home.html",
    "about": "templates/multipage/about.html",
    "contact": "templates/multipage/contact.html",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "site_title": "My Blog",
    "site_tagline": "Thoughts and stories",
    "hero_text": "Welcome to our corner of the internet.",
    "year": 2025,
    "contact_email": "hello@example.com",
    "contact_twitter": "@myblog",
    "contact_github": "myblog",
    "features": [
        {"title": "Fast", "description": "Optimized for speed"},
        {"title": "Responsive", "description": "Looks great everywhere"},
        {"title": "Accessible", "description": "Built for everyone"},
    ],
    "team_members": [
        {"name": "Jane Doe", "role": "Founder", "bio": "Building since 2020."},
        {"name": "John Smith", "role": "Engineer", "bio": "Full-stack developer."},
    ],
}


def _render_template(template_path: str, config: dict[str, Any]) -> str:
    """Simple mustache-style template rendering."""
    text = Path(template_path).read_text(encoding="utf-8")
    for key, value in config.items():
        if isinstance(value, str):
            text = text.replace("{{" + key + "}}", value)
    return text


def generate_multipage(
    config: dict[str, Any] | None = None,
    template: str = "simple",
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Generate a multi-page blog site with home, about, and contact pages.

    Args:
        config: Site configuration dict. Merged with DEFAULT_CONFIG.
        template: Theme preset name from PRESETS.
        output_dir: Directory for output XML files.

    Returns:
        Dict with per-page results and validation status.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    out = Path(output_dir) if output_dir else Path("output")
    out.mkdir(parents=True, exist_ok=True)

    if template not in PRESETS:
        template = "simple"

    results: dict[str, Any] = {"template": template, "pages": {}}

    for page_name, tpl_rel in MULTIPAGE_TEMPLATES.items():
        tpl_path = Path(__file__).resolve().parents[2] / tpl_rel
        if not tpl_path.exists():
            results["pages"][page_name] = {"ok": False, "error": f"Template not found: {tpl_path}"}
            continue

        html_content = _render_template(str(tpl_path), cfg)
        out_file = out / f"{page_name}.xml"

        gen_result = generate_from_html(
            html_content if isinstance(html_content, str) else str(html_content),
            out_file,
            template=template,
        )
        results["pages"][page_name] = {
            "ok": gen_result.get("validation", {}).get("ok", False),
            "output": str(out_file),
            "additions": gen_result.get("additions", 0),
        }

    results["all_ok"] = all(p.get("ok") for p in results["pages"].values())
    return results


def list_templates() -> list[str]:
    """List available multipage template names."""
    return sorted(MULTIPAGE_TEMPLATES.keys())
