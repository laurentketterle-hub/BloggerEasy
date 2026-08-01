"""Multi-page site generator — produces a static HTML site with home, about, and contact pages.

Provides:
  - MultiPageSite: core class with .generate() that writes index.html, about.html, contact.html
  - Standalone helper: generate_multi_page_site() for programmatic use (returns a result dict).

All pages share a consistent header (with an active-state nav) and footer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class _SitePage(BaseModel):
    """Configuration for a single page in the multi-page site."""
    title: str = "Page"
    slug: str = ""
    description: str = ""
    content: str = ""
    template: str = "default"


class _SiteInfo(BaseModel):
    """Top-level site configuration."""
    site_name: str = "My Site"
    tagline: str = ""
    author: str = ""
    email: str = ""
    year: int = 2026
    primary_color: str = "#1a73e8"
    background_color: str = "#ffffff"
    text_color: str = "#222222"
    font_family: str = "system-ui, sans-serif"
    show_contact_form: bool = True
    pages: list[_SitePage] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Default pages
# ---------------------------------------------------------------------------

DEFAULT_PAGES: list[dict[str, Any]] = [
    {
        "title": "Home",
        "slug": "index",
        "description": "Welcome to our website",
        "content": (
            "<h2>Welcome</h2>\n"
            "<p>This is the home page of <strong>My Site</strong>.</p>\n"
            "<p>Explore our content, learn about us, or get in touch.</p>"
        ),
        "template": "home",
    },
    {
        "title": "About",
        "slug": "about",
        "description": "Learn more about us",
        "content": (
            "<h2>About Us</h2>\n"
            "<p>We are a passionate team dedicated to building great things.</p>\n"
            "<p>Our mission is to create value through technology and design.</p>"
        ),
        "template": "about",
    },
    {
        "title": "Contact",
        "slug": "contact",
        "description": "Get in touch",
        "content": (
            "<h2>Contact Us</h2>\n"
            "<p>We'd love to hear from you. Reach out via email or the form below.</p>\n"
            "{contact_form}"
        ),
        "template": "contact",
    },
]


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS_TEMPLATE = """\
/* -*- MultiPageSite theme -*- */
*,
*::before,
*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: {font_family};
  color: {text_color};
  background: {background_color};
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

a {{ color: {primary_color}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ---------- header ---------- */
.site-header {{
  background: {primary_color};
  color: #fff;
  padding: 1rem 1.5rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}}
.site-header .site-name {{
  font-size: 1.4rem;
  font-weight: 700;
}}
.site-header .site-tagline {{
  font-size: 0.85rem;
  opacity: 0.85;
  margin-top: 0.15rem;
}}
.site-nav a {{
  color: #fff;
  margin-left: 1.2rem;
  font-size: 0.95rem;
}}
.site-nav a.active {{
  font-weight: 700;
  text-decoration: underline;
}}

/* ---------- main ---------- */
.site-main {{
  flex: 1;
  max-width: 800px;
  width: 100%;
  margin: 2rem auto;
  padding: 0 1.5rem;
}}
.site-main h2 {{
  color: {primary_color};
  margin-bottom: 1rem;
}}
.site-main p {{
  margin-bottom: 0.8rem;
}}

/* ---------- contact form ---------- */
.contact-form {{
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 480px;
}}
.contact-form label {{
  font-weight: 600;
  font-size: 0.9rem;
}}
.contact-form input,
.contact-form textarea {{
  padding: 0.6rem 0.8rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.95rem;
}}
.contact-form textarea {{
  min-height: 120px;
  resize: vertical;
}}
.contact-form button {{
  background: {primary_color};
  color: #fff;
  border: none;
  padding: 0.7rem 1.4rem;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  align-self: flex-start;
}}
.contact-form button:hover {{
  opacity: 0.9;
}}

/* ---------- footer ---------- */
.site-footer {{
  background: #0f172a;
  color: #e2e8f0;
  text-align: center;
  padding: 1.2rem 1.5rem;
  font-size: 0.85rem;
}}
.site-footer a {{
  color: #93c5fd;
}}
"""


# ---------------------------------------------------------------------------
# Page HTML skeleton
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{description}">
<title>{title} — {site_name}</title>
<style>
{css}
</style>
</head>
<body>

<header class="site-header">
  <div>
    <div class="site-name">{site_name}</div>
    {tagline_html}
  </div>
  <nav class="site-nav">
    {nav_links}
  </nav>
</header>

<main class="site-main">
{body_html}
</main>

<footer class="site-footer">
  <p>&copy; {year} {site_name}. Built with <a href="https://github.com/mergeos-bounties/BloggerEasy">BloggerEasy</a>.</p>
</footer>

</body>
</html>
"""


def _nav_html(pages: list[dict[str, Any]], active_slug: str) -> str:
    """Build navigation links with active class on the current page."""
    links: list[str] = []
    for p in pages:
        slug = p.get("slug", "")
        href = f"{slug}.html"
        label = p.get("title", slug.title())
        cls = ' class="active"' if slug == active_slug else ""
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    return "\n    ".join(links)


def _contact_form_html() -> str:
    return """\
<div class="contact-form">
  <div>
    <label for="cf-name">Name</label>
    <input type="text" id="cf-name" placeholder="Your name" />
  </div>
  <div>
    <label for="cf-email">Email</label>
    <input type="email" id="cf-email" placeholder="you@example.com" />
  </div>
  <div>
    <label for="cf-message">Message</label>
    <textarea id="cf-message" placeholder="Your message..."></textarea>
  </div>
  <button type="button">Send</button>
</div>"""


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class MultiPageSite:
    """Generate a consistent multi-page static HTML site (home, about, contact).

    Usage::

        site = MultiPageSite(
            site_name="Acme Corp",
            tagline="Building the future",
            pages=[...],   # optional override
        )
        result = site.generate(Path("dist/"))
        # dist/index.html, dist/about.html, dist/contact.html
    """

    def __init__(
        self,
        *,
        site_name: str = "My Site",
        tagline: str = "",
        author: str = "",
        email: str = "",
        year: int = 2026,
        primary_color: str = "#1a73e8",
        background_color: str = "#ffffff",
        text_color: str = "#222222",
        font_family: str = "system-ui, sans-serif",
        show_contact_form: bool = True,
        pages: list[dict[str, Any]] | None = None,
    ) -> None:
        self._info = _SiteInfo(
            site_name=site_name,
            tagline=tagline,
            author=author,
            email=email,
            year=year,
            primary_color=primary_color,
            background_color=background_color,
            text_color=text_color,
            font_family=font_family,
            show_contact_form=show_contact_form,
            pages=[_SitePage(**p) for p in (pages or DEFAULT_PAGES)],
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """Write all pages to *output_dir* and return a result dict."""
        output_dir.mkdir(parents=True, exist_ok=True)

        css = _CSS_TEMPLATE.format(
            primary_color=self._info.primary_color,
            background_color=self._info.background_color,
            text_color=self._info.text_color,
            font_family=self._info.font_family,
        )

        pages_data = [p.model_dump() for p in self._info.pages]
        written: list[str] = []
        total_bytes = 0

        for page in pages_data:
            slug = page["slug"]
            body = page.get("content", "")
            if slug == "contact" and self._info.show_contact_form:
                body = body.replace("{contact_form}", _contact_form_html())

            tagline_html = (
                f'<div class="site-tagline">{self._info.tagline}</div>'
                if self._info.tagline
                else ""
            )

            html = _PAGE_TEMPLATE.format(
                title=page.get("title", slug.title()),
                site_name=self._info.site_name,
                description=page.get("description", ""),
                css=css,
                tagline_html=tagline_html,
                nav_links=_nav_html(pages_data, slug),
                body_html=f"<h2>{page.get('title', slug.title())}</h2>\n{body}",
                year=self._info.year,
            )

            out_path = output_dir / f"{slug}.html"
            out_path.write_text(html, encoding="utf-8")
            written.append(out_path.name)
            total_bytes += out_path.stat().st_size

        return {
            "site_name": self._info.site_name,
            "pages": written,
            "output_dir": str(output_dir),
            "total_bytes": total_bytes,
        }


# ---------------------------------------------------------------------------
# Standalone helper
# ---------------------------------------------------------------------------

def generate_multi_page_site(
    output_dir: str | Path,
    *,
    site_name: str = "My Site",
    tagline: str = "",
    author: str = "",
    email: str = "",
    year: int = 2026,
    primary_color: str = "#1a73e8",
    background_color: str = "#ffffff",
    text_color: str = "#222222",
    font_family: str = "system-ui, sans-serif",
    show_contact_form: bool = True,
    pages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Programmatic entry-point: create a multi-page site in one call.

    Returns a dict with ``pages``, ``output_dir``, and ``total_bytes``.
    """
    site = MultiPageSite(
        site_name=site_name,
        tagline=tagline,
        author=author,
        email=email,
        year=year,
        primary_color=primary_color,
        background_color=background_color,
        text_color=text_color,
        font_family=font_family,
        show_contact_form=show_contact_form,
        pages=pages,
    )
    return site.generate(Path(output_dir))
