"""Multi-page site generator: produce coordinated Home, About, and Contact page sets.

Generates a Blogger XML theme plus HTML content for About and Contact static pages,
all sharing the same colour scheme, typography, and navigation.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from bloggereasy.theme.builder import build_blogger_xml, sanitize_filename
from bloggereasy.theme.models import PageStructure, structure_dict


def _about_html(structure: dict) -> str:
    """Generate About page HTML content ready for a Blogger static page."""
    title = escape(str(structure.get("title") or "My Blog"))
    desc = escape(str(structure.get("description") or "About this blog"))
    colors = structure.get("colors") or {}
    primary = escape(str(colors.get("primary") or "#1a73e8"))
    fonts = structure.get("fonts") or {}
    body_font = escape(str(fonts.get("body") or "system-ui, sans-serif"))

    paragraphs = structure.get("sample_paragraphs") or []
    about_parts = []
    for p in paragraphs[:3]:
        about_parts.append(f"<p>{escape(str(p))}</p>")

    if not about_parts:
        about_parts = [
            "<p>Welcome to our blog! We share insights, stories, and resources "
            "on topics that matter to our readers.</p>",
            "<p>Founded with a passion for sharing knowledge, this blog covers "
            "a wide range of subjects from technology to lifestyle.</p>",
            "<p>Thank you for visiting &#8212; we are glad you are here!</p>",
        ]

    about_text = "\n".join(about_parts)

    return (
        f'<h2 style="color:{primary}; font-family:{body_font};">About {title}</h2>\n'
        f"{about_text}\n"
        f'<div style="margin-top:2rem;">\n'
        f'  <h3 style="color:{primary};">Our Story</h3>\n'
        f"  <p>{desc}</p>\n"
        f"</div>"
    )


def _contact_html(structure: dict) -> str:
    """Generate Contact page HTML content ready for a Blogger static page."""
    colors = structure.get("colors") or {}
    primary = escape(str(colors.get("primary") or "#1a73e8"))
    fonts = structure.get("fonts") or {}
    body_font = escape(str(fonts.get("body") or "system-ui, sans-serif"))

    return (
        f'<h2 style="color:{primary}; font-family:{body_font};">Contact Us</h2>\n'
        f"<p>We would love to hear from you! Whether you have a question, "
        f"suggestion, or just want to say hello, feel free to reach out.</p>\n"
        f'<div style="margin-top:1.5rem;">\n'
        f'  <h3 style="color:{primary};">Get in Touch</h3>\n'
        f'  <ul style="list-style:none; padding:0;">\n'
        f'    <li style="margin-bottom:0.75rem;">Email: contact@example.com</li>\n'
        f'    <li style="margin-bottom:0.75rem;">Twitter: @YourHandle</li>\n'
        f'    <li style="margin-bottom:0.75rem;">Instagram: @YourHandle</li>\n'
        f"  </ul>\n"
        f"</div>\n"
        f'<div style="margin-top:2rem; padding:1.25rem; background:#f8fafc; '
        f'border:1px solid #e5e7eb; border-radius:8px;">\n'
        f'  <h3 style="color:{primary};">Send a Message</h3>\n'
        f"  <p>Use the comment section below or reach out via social media "
        f"&#8212; we respond to every message within 48 hours.</p>\n"
        f"</div>"
    )


def build_multi_page_set(
    structure: PageStructure | dict,
    *,
    template_name: str = "simple",
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate a coordinated multi-page Blogger site set (home + about + contact).

    Returns a manifest with paths to generated files.
    """
    from bloggereasy.theme.preview import write_preview_html

    structure = structure_dict(structure)

    # Ensure nav links include Home, About, Contact
    nav = list(structure.get("nav_links") or [])
    existing_labels = {str(n.get("label") or "").strip().lower() for n in nav}
    defaults = [
        ("Home", "#home"),
        ("About", "#about"),
        ("Contact", "#contact"),
    ]
    for label, href in defaults:
        if label.lower() not in existing_labels:
            nav.append({"label": label, "href": href})
    structure["nav_links"] = nav

    title_slug = sanitize_filename(str(structure.get("title") or "my-blog"))
    root = out_dir or Path(f"data/out/multi_page/{title_slug}")
    root.mkdir(parents=True, exist_ok=True)

    # Generate theme XML
    theme_xml = build_blogger_xml(structure, template_name=template_name)
    theme_path = root / "theme.xml"
    theme_path.write_text(theme_xml, encoding="utf-8")

    # Generate page content
    about_html = _about_html(structure)
    about_path = root / "about.html"
    about_path.write_text(about_html, encoding="utf-8")

    contact_html = _contact_html(structure)
    contact_path = root / "contact.html"
    contact_path.write_text(contact_html, encoding="utf-8")

    # Generate preview
    preview_path = write_preview_html(structure, root / "preview.html")

    return {
        "title": structure.get("title"),
        "template": template_name,
        "files": {
            "theme": str(theme_path),
            "about": str(about_path),
            "contact": str(contact_path),
            "preview": str(preview_path),
        },
        "import_hint": (
            "1. Import theme.xml in Blogger -> Theme -> Backup/Restore. "
            "2. Create static pages 'About' and 'Contact' via Blogger dashboard. "
            "3. Paste about.html and contact.html content into those pages (HTML view). "
            "4. Ensure nav links point to the correct page URLs."
        ),
    }
