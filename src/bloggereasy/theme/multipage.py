"""Coordinated multi-page theme set generator for BloggerEasy.

Produces home, about, and contact pages from a shared style configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bloggereasy.theme.builder import build_blogger_xml
from bloggereasy.theme.presets import PRESETS


@dataclass
class SiteConfig:
    """Configuration for a multi-page site."""
    site_name: str = "My Site"
    tagline: str = "Built with BloggerEasy"
    primary: str = "#1a73e8"
    secondary: str = "#34a853"
    background: str = "#ffffff"
    text: str = "#222222"
    surface: str = "#ffffff"
    muted: str = "#f8fafc"
    border: str = "#e5e7eb"
    footer: str = "#0f172a"
    footer_text: str = "#e2e8f0"
    body_font: str = "system-ui, sans-serif"
    heading_font: str = "Georgia, serif"
    radius: str = "8px"
    gap: str = "1.5rem"
    card_padding: str = "1rem 1.25rem"
    section_padding: str = "1rem"
    accent: str = ""
    layout: str = "two-column"

    about_text: str = (
        "We are a team passionate about creating beautiful, functional websites. "
        "Our mission is to make web publishing accessible to everyone."
    )
    contact_email: str = "hello@example.com"
    contact_address: str = "123 Design Street, Web City"
    nav_links: list[dict] = field(default_factory=lambda: [
        {"label": "Home", "href": "/"},
        {"label": "About", "href": "/p/about.html"},
        {"label": "Contact", "href": "/p/contact.html"},
    ])

    @classmethod
    def from_preset(cls, preset_name: str, **overrides) -> "SiteConfig":
        """Create a SiteConfig from a BloggerEasy preset."""
        preset = PRESETS.get(preset_name, PRESETS["simple"])
        cfg = cls()
        if preset.get("accent"):
            cfg.primary = preset["accent"]
            cfg.secondary = preset["accent"]
        if preset.get("dark"):
            cfg.background = "#0f172a"
            cfg.text = "#e2e8f0"
            cfg.surface = "#1e293b"
            cfg.muted = "#334155"
            cfg.border = "#475569"
            cfg.footer = "#020617"
            cfg.footer_text = "#94a3b8"
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


def _base_structure(cfg: SiteConfig, page_title: str, has_sidebar: bool = True) -> dict:
    return {
        "title": page_title,
        "description": cfg.tagline,
        "colors": {
            "primary": cfg.primary,
            "secondary": cfg.secondary,
            "background": cfg.background,
            "text": cfg.text,
            "surface": cfg.surface,
            "muted": cfg.muted,
            "border": cfg.border,
            "footer": cfg.footer,
            "footer_text": cfg.footer_text,
        },
        "fonts": {
            "body": cfg.body_font,
            "heading": cfg.heading_font,
        },
        "layout": cfg.layout,
        "features": {
            "sidebar": has_sidebar,
            "widgets": "default",
        },
        "skin": {
            "spacing": {
                "radius": cfg.radius,
                "gap": cfg.gap,
                "card_padding": cfg.card_padding,
                "section_padding": cfg.section_padding,
            },
        },
        "nav_links": cfg.nav_links,
    }


def generate_multipage(cfg: SiteConfig) -> dict[str, str]:
    """Generate coordinated home, about, and contact Blogger XML themes.

    Returns a dict mapping page type to XML string.
    """
    pages = {}

    # Home page
    home_structure = _base_structure(cfg, cfg.site_name, has_sidebar=True)
    home_structure["sample_paragraphs"] = [
        "Welcome to our site! Browse our latest articles and updates below.",
        "Each post is crafted with care and attention to detail.",
        "Stay tuned for more content coming soon.",
    ]
    pages["home"] = build_blogger_xml(home_structure, template_name="simple")

    # About page
    about_structure = _base_structure(cfg, "About " + cfg.site_name, has_sidebar=False)
    about_structure["sample_paragraphs"] = [
        cfg.about_text,
        "Founded with a vision to simplify web publishing, we have grown from a small project into a full-featured platform trusted by creators worldwide.",
        "Our values: simplicity, accessibility, and craftsmanship.",
    ]
    pages["about"] = build_blogger_xml(about_structure, template_name="simple")

    # Contact page
    contact_structure = _base_structure(cfg, "Contact " + cfg.site_name, has_sidebar=False)
    contact_structure["sample_paragraphs"] = [
        "Get in touch with us! We would love to hear from you.",
        "Email: " + cfg.contact_email,
        "Address: " + cfg.contact_address,
    ]
    pages["contact"] = build_blogger_xml(contact_structure, template_name="simple")

    return pages


def write_multipage(cfg: SiteConfig, out_dir: Path) -> dict[str, Path]:
    """Generate and write coordinated theme files to disk.

    Returns a dict mapping page type to output path.
    """
    pages = generate_multipage(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for page_type, xml in pages.items():
        out_path = out_dir / (page_type + ".xml")
        out_path.write_text(xml, encoding="utf-8")
        paths[page_type] = out_path
    return paths


MULTIPAGE_PRESETS: dict[str, dict[str, Any]] = {
    "corporate": {
        "primary": "#0055aa",
        "secondary": "#003b73",
        "body_font": "Segoe UI, Arial, sans-serif",
        "heading_font": "Segoe UI, Arial, sans-serif",
        "tagline": "Professional Web Solutions",
    },
    "creative": {
        "primary": "#7c3aed",
        "secondary": "#a78bfa",
        "background": "#faf5ff",
        "body_font": "Georgia, serif",
        "heading_font": "Georgia, serif",
        "tagline": "Creative Studio",
    },
    "magazine": {
        "primary": "#b91c1c",
        "secondary": "#dc2626",
        "layout": "three-column",
        "tagline": "Daily News and Insights",
    },
    "minimal": {
        "primary": "#1c1917",
        "secondary": "#57534e",
        "background": "#fafaf9",
        "body_font": "system-ui, sans-serif",
        "heading_font": "system-ui, sans-serif",
        "tagline": "Clean and Simple",
    },
    "tech": {
        "primary": "#0ea5e9",
        "secondary": "#0284c7",
        "background": "#f8fafc",
        "body_font": "system-ui, sans-serif",
        "heading_font": "monospace",
        "tagline": "Technology Blog",
    },
}
