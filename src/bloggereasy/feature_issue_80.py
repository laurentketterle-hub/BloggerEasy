"""
Multi-Page Site Generator (Issue #80)

Generates a complete multi-page Blogger site: home, about, and contact pages
— each an importable Blogger XML theme with shared styling and inter-page
navigation. Accepts HTML templates, site config, or structured input via the
SDK. Produces a ready-to-upload site bundle.

Usage:
    from bloggereasy.feature_issue_80 import MultiPageGenerator, MultiPageSiteConfig

    config = MultiPageSiteConfig(
        site_name="My Blog Site",
        tagline="Welcome to my corner of the web",
        ...
    )
    gen = MultiPageGenerator(config)
    results = gen.generate_all(output_dir)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from xml.sax.saxutils import escape as xml_escape

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bloggereasy.theme.builder import build_blogger_xml, sanitize_filename
from bloggereasy.theme.models import (
    ColorPalette,
    FontSet,
    NavLink,
    PageStructure,
    structure_dict,
)
from bloggereasy.theme.presets import PRESETS, apply_dark_variant, apply_preset
from bloggereasy.theme.validate import validate_blogger_xml


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class HeroSection(BaseModel):
    """Hero / banner section for a page."""
    model_config = ConfigDict(extra="allow")
    heading: str = "Welcome"
    subheading: str = ""
    cta_label: str = "Learn More"
    cta_link: str = "#"
    background_color: str | None = None
    image_url: str | None = None

    @field_validator("heading", "subheading", "cta_label", "cta_link", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        return str(value or "").strip()


class ContentBlock(BaseModel):
    """A generic content block (text, image, feature card, etc.)."""
    model_config = ConfigDict(extra="allow")
    block_type: Literal["text", "feature", "image", "quote", "list"] = "text"
    heading: str = ""
    body: str = ""
    image_url: str | None = None
    image_alt: str = ""
    items: list[str] = Field(default_factory=list)
    href: str | None = None

    @field_validator("heading", "body", "image_alt", "href", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("items", mode="before")
    @classmethod
    def _string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class TeamMember(BaseModel):
    """Team member for about page."""
    model_config = ConfigDict(extra="allow")
    name: str = ""
    role: str = ""
    bio: str = ""
    image_url: str | None = None
    social_links: dict[str, str] = Field(default_factory=dict)

    @field_validator("name", "role", "bio", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        return str(value or "").strip()


class ContactForm(BaseModel):
    """Contact form configuration."""
    model_config = ConfigDict(extra="allow")
    email: str = ""
    phone: str = ""
    address: str = ""
    form_action: str = "#"
    show_map: bool = False
    map_embed_url: str | None = None

    @field_validator("email", "phone", "address", "form_action", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        return str(value or "").strip()


class PageConfig(BaseModel):
    """Configuration for a single page in the multi-page site."""
    model_config = ConfigDict(extra="allow")

    page_id: str = "home"
    page_label: str = "Home"
    page_title: str = "My Blog"
    page_description: str = ""
    template: str = "home"
    layout: Literal["single-column", "two-column", "three-column"] = "single-column"

    hero: HeroSection = Field(default_factory=HeroSection)
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    team: list[TeamMember] = Field(default_factory=list)
    contact_form: ContactForm | None = None

    show_blog_posts: bool = True
    show_sidebar: bool = False

    custom_css: str = ""
    meta_keywords: str = ""

    @field_validator("page_id", "page_label", "page_title", "page_description",
                     "meta_keywords", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        return str(value or "").strip()


class MultiPageSiteConfig(BaseModel):
    """Top-level configuration for a multi-page Blogger site."""
    model_config = ConfigDict(extra="allow")

    site_name: str = "My Site"
    tagline: str = ""
    author: str = ""
    site_url: str = "https://example.blogspot.com"
    language: str = "en"
    favicon_url: str | None = None

    global_colors: ColorPalette = Field(default_factory=ColorPalette)
    global_fonts: FontSet = Field(default_factory=FontSet)
    global_nav: list[NavLink] = Field(default_factory=list)

    pages: list[PageConfig] = Field(default_factory=list)

    footer_text: str = ""
    footer_links: list[NavLink] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)

    analytics_id: str = ""
    custom_meta_tags: str = ""

    @field_validator("site_name", "tagline", "author", "site_url", "language",
                     "footer_text", "analytics_id", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> str:
        return str(value or "").strip()


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

def _render_hero(hero: HeroSection) -> str:
    """Render a hero section as HTML."""
    bg_style = ""
    if hero.background_color:
        bg_style = f" background-color: {xml_escape(hero.background_color)};"
    img_html = ""
    if hero.image_url:
        img_html = (
            f'<div class="hero-img">'
            f'<img src="{xml_escape(hero.image_url)}" alt="{xml_escape(hero.heading)}" />'
            f'</div>'
        )
    return f"""<div class="site-hero" style="padding: 3rem 1.5rem; text-align: center;{bg_style}">
  {img_html}
  <h1>{xml_escape(hero.heading)}</h1>
  <p class="hero-sub">{xml_escape(hero.subheading)}</p>
  <a class="hero-cta button" href="{xml_escape(hero.cta_link)}">{xml_escape(hero.cta_label)}</a>
</div>"""


def _render_content_block(block: ContentBlock) -> str:
    """Render a single content block as HTML."""
    if block.block_type == "text":
        heading_html = (
            f"<h3>{xml_escape(block.heading)}</h3>" if block.heading else ""
        )
        return f"""<section class="content-block content-text">
  {heading_html}
  <p>{xml_escape(block.body)}</p>
</section>"""
    elif block.block_type == "feature":
        img_html = ""
        if block.image_url:
            img_html = (
                f'<div class="feature-img">'
                f'<img src="{xml_escape(block.image_url)}" alt="{xml_escape(block.image_alt)}" />'
                f'</div>'
            )
        return f"""<article class="content-block content-feature landing-card">
  {img_html}
  <h3>{xml_escape(block.heading)}</h3>
  <p>{xml_escape(block.body)}</p>
</article>"""
    elif block.block_type == "image":
        return f"""<div class="content-block content-image">
  <img src="{xml_escape(block.image_url or '#')}" alt="{xml_escape(block.image_alt)}" />
  {f'<p class="image-caption">{xml_escape(block.body)}</p>' if block.body else ''}
</div>"""
    elif block.block_type == "quote":
        return f"""<blockquote class="content-block content-quote">
  <p>{xml_escape(block.body)}</p>
  {f'<cite>— {xml_escape(block.heading)}</cite>' if block.heading else ''}
</blockquote>"""
    elif block.block_type == "list":
        items_html = "\n".join(
            f"  <li>{xml_escape(item)}</li>" for item in block.items
        )
        return f"""<section class="content-block content-list">
  <h3>{xml_escape(block.heading)}</h3>
  <ul>
{items_html}
  </ul>
  {f'<p>{xml_escape(block.body)}</p>' if block.body else ''}
</section>"""
    return ""


def _render_team_section(members: list[TeamMember]) -> str:
    """Render a team/grid section for about page."""
    if not members:
        return ""
    cards = []
    for m in members:
        img_html = ""
        if m.image_url:
            img_html = (
                f'<div class="team-avatar">'
                f'<img src="{xml_escape(m.image_url)}" alt="{xml_escape(m.name)}" />'
                f'</div>'
            )
        social_html = ""
        if m.social_links:
            links = "\n".join(
                f'<a href="{xml_escape(url)}" target="_blank" rel="noopener">'
                f'{xml_escape(platform)}</a>'
                for platform, url in m.social_links.items()
            )
            social_html = f'<div class="team-social">{links}</div>'
        cards.append(f"""<div class="team-card landing-card">
  {img_html}
  <h4>{xml_escape(m.name)}</h4>
  <p class="team-role">{xml_escape(m.role)}</p>
  <p class="team-bio">{xml_escape(m.bio)}</p>
  {social_html}
</div>""")
    return f"""<section class="team-section">
  <h2 class="section-heading">Our Team</h2>
  <div class="team-grid">{''.join(cards)}</div>
</section>"""


def _render_contact_form(form: ContactForm) -> str:
    """Render a contact form section."""
    info_lines = []
    if form.email:
        info_lines.append(
            f'<div class="contact-info-item"><strong>Email:</strong> '
            f'<a href="mailto:{xml_escape(form.email)}">{xml_escape(form.email)}</a></div>'
        )
    if form.phone:
        info_lines.append(
            f'<div class="contact-info-item"><strong>Phone:</strong> '
            f'{xml_escape(form.phone)}</div>'
        )
    if form.address:
        info_lines.append(
            f'<div class="contact-info-item"><strong>Address:</strong> '
            f'{xml_escape(form.address)}</div>'
        )
    info_html = "\n".join(info_lines)

    map_html = ""
    if form.show_map and form.map_embed_url:
        map_html = f"""<div class="contact-map">
  <iframe src="{xml_escape(form.map_embed_url)}" width="100%" height="300"
          style="border:0;" allowfullscreen="" loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"></iframe>
</div>"""

    return f"""<section class="contact-section">
  <h2 class="section-heading">Get In Touch</h2>
  <div class="contact-grid">
    <div class="contact-info">
      {info_html}
    </div>
    <form class="contact-form" action="{xml_escape(form.form_action)}" method="post">
      <div class="form-group">
        <label for="contact-name">Name</label>
        <input type="text" id="contact-name" name="name" required />
      </div>
      <div class="form-group">
        <label for="contact-email">Email</label>
        <input type="email" id="contact-email" name="email" required />
      </div>
      <div class="form-group">
        <label for="contact-subject">Subject</label>
        <input type="text" id="contact-subject" name="subject" />
      </div>
      <div class="form-group">
        <label for="contact-message">Message</label>
        <textarea id="contact-message" name="message" rows="5" required></textarea>
      </div>
      <button type="submit" class="button">Send Message</button>
    </form>
  </div>
  {map_html}
</section>"""


def _render_social_links(social_links: dict[str, str]) -> str:
    """Render social media icon links."""
    if not social_links:
        return ""
    links = "\n".join(
        f'<a href="{xml_escape(url)}" target="_blank" rel="noopener" '
        f'class="social-link social-{xml_escape(platform.lower())}">'
        f'{xml_escape(platform)}</a>'
        for platform, url in social_links.items()
    )
    return f'<div class="social-links">{links}</div>'


# ---------------------------------------------------------------------------
# CSS generation
# ---------------------------------------------------------------------------

def _generate_multi_page_css(
    colors: dict[str, str],
    fonts: dict[str, str],
    layout: str = "single-column",
) -> str:
    """Generate CSS for multi-page site pages."""
    primary = xml_escape(colors.get("primary", "#1a73e8"))
    secondary = xml_escape(colors.get("secondary", "#34a853"))
    background = xml_escape(colors.get("background", "#ffffff"))
    text = xml_escape(colors.get("text", "#222222"))
    surface = xml_escape(colors.get("surface", "#ffffff"))
    muted = xml_escape(colors.get("muted", "#f8fafc"))
    border = xml_escape(colors.get("border", "#e5e7eb"))
    footer_bg = xml_escape(colors.get("footer", "#0f172a"))
    footer_text = xml_escape(colors.get("footer_text", "#e2e8f0"))
    body_font = xml_escape(fonts.get("body") or "system-ui, sans-serif")
    heading_font = xml_escape(fonts.get("heading") or body_font)

    return f"""
/* ── BloggerEasy Multi-Page Site ── */
body {{
  margin: 0;
  font-family: {body_font};
  color: {text};
  background: {background};
  line-height: 1.6;
  overflow-wrap: anywhere;
}}
a {{ color: {primary}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
img, iframe, video {{ max-width: 100%; height: auto; }}

/* ── Header & Navigation ── */
.site-header {{
  background: {primary};
  color: #fff;
  padding: 1.5rem 1rem;
}}
.site-header h1, .site-header a {{ color: #fff; text-decoration: none; font-family: {heading_font}; }}
.site-header .site-tagline {{ opacity: 0.85; margin: 0.25rem 0 0; font-size: 0.95rem; }}

.site-nav {{
  background: {secondary};
  padding: 0.5rem 1rem;
}}
.site-nav ul {{
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}}
.site-nav a {{
  color: #fff;
  text-decoration: none;
  font-weight: 500;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: background 0.2s;
}}
.site-nav a:hover {{ background: rgba(255,255,255,0.15); text-decoration: none; }}
.site-nav a.active {{ background: rgba(255,255,255,0.25); }}

/* ── Page Layout ── */
.site-container {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}}
.site-page-title {{
  font-family: {heading_font};
  font-size: 2rem;
  margin: 0 0 1.5rem;
  color: {text};
  border-bottom: 2px solid {primary};
  padding-bottom: 0.5rem;
}}

/* ── Hero Section ── */
.site-hero {{
  background: {muted};
  border: 1px solid {border};
  border-radius: 10px;
  margin-bottom: 2rem;
}}
.site-hero h1 {{
  margin: 0 0 0.75rem;
  font-family: {heading_font};
  font-size: 2.5rem;
  color: {text};
}}
.site-hero .hero-sub {{
  max-width: 680px;
  margin: 0 auto 1.5rem;
  font-size: 1.1rem;
  color: {text};
  opacity: 0.8;
}}
.hero-cta {{
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: {primary};
  color: #fff;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  font-size: 1.05rem;
}}
.hero-cta:hover {{ opacity: 0.9; text-decoration: none; }}
.hero-img {{ margin-bottom: 1rem; }}
.hero-img img {{ max-height: 300px; }}

/* ── Content Blocks ── */
.content-block {{
  padding: 1.5rem;
  background: {surface};
  border: 1px solid {border};
  border-radius: 8px;
  margin-bottom: 1.25rem;
}}
.content-block h3 {{
  font-family: {heading_font};
  margin-top: 0;
  color: {text};
}}

/* Features grid */
.features-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin: 1.5rem 0;
}}
.content-feature h3 {{ font-family: {heading_font}; margin-top: 0.5rem; }}
.feature-img img {{ border-radius: 6px; }}

/* Quote */
.content-quote {{
  border-left: 4px solid {primary};
  background: {muted};
  font-style: italic;
  padding: 1.25rem 1.5rem;
}}
.content-quote cite {{
  display: block;
  margin-top: 0.5rem;
  font-style: normal;
  color: {text};
  opacity: 0.7;
}}

/* Content image */
.content-image img {{ border-radius: 6px; }}
.image-caption {{ font-size: 0.9rem; color: {text}; opacity: 0.7; margin-top: 0.5rem; }}

/* Content list */
.content-list ul {{ padding-left: 1.2rem; }}
.content-list li {{ margin-bottom: 0.4rem; }}

/* Section heading */
.section-heading {{
  font-family: {heading_font};
  font-size: 1.5rem;
  margin: 2rem 0 1rem;
  color: {text};
}}

/* ── Team Grid ── */
.team-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.5rem;
  margin: 1rem 0;
}}
.team-card {{
  text-align: center;
  padding: 1.5rem 1rem;
}}
.team-avatar {{
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  margin: 0 auto 0.75rem;
  background: {muted};
}}
.team-avatar img {{ width: 100%; height: 100%; object-fit: cover; }}
.team-card h4 {{ font-family: {heading_font}; margin: 0 0 0.25rem; }}
.team-role {{
  color: {primary};
  font-weight: 600;
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
}}
.team-bio {{ font-size: 0.9rem; opacity: 0.85; }}
.team-social {{ margin-top: 0.5rem; }}
.team-social a {{
  display: inline-block;
  margin: 0 0.25rem;
  padding: 0.2rem 0.5rem;
  background: {primary};
  color: #fff;
  border-radius: 4px;
  font-size: 0.8rem;
  text-decoration: none;
}}

/* ── Contact Form ── */
.contact-grid {{
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1.5rem;
  margin: 1rem 0;
}}
.contact-info {{
  padding: 1.25rem;
  background: {muted};
  border: 1px solid {border};
  border-radius: 8px;
}}
.contact-info-item {{
  margin-bottom: 0.75rem;
}}
.contact-form {{
  padding: 1.5rem;
  background: {surface};
  border: 1px solid {border};
  border-radius: 8px;
}}
.form-group {{
  margin-bottom: 1rem;
}}
.form-group label {{
  display: block;
  font-weight: 600;
  margin-bottom: 0.3rem;
  color: {text};
}}
.form-group input,
.form-group textarea {{
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid {border};
  border-radius: 6px;
  font-family: {body_font};
  font-size: 0.95rem;
  box-sizing: border-box;
}}
.form-group input:focus,
.form-group textarea:focus {{
  outline: none;
  border-color: {primary};
  box-shadow: 0 0 0 2px {primary}33;
}}
.contact-form .button {{
  background: {primary};
  color: #fff;
  border: none;
  padding: 0.7rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
}}
.contact-form .button:hover {{ opacity: 0.9; }}
.contact-map {{ margin-top: 1.5rem; border-radius: 8px; overflow: hidden; }}

/* ── Blog Posts Placeholder ── */
.blog-posts-section {{
  margin: 1.5rem 0;
}}
.blog-posts-section h2 {{
  font-family: {heading_font};
  margin-bottom: 1rem;
}}

/* ── Footer ── */
.site-footer {{
  margin-top: 3rem;
  padding: 2rem 1rem;
  background: {footer_bg};
  color: {footer_text};
  text-align: center;
}}
.site-footer a {{ color: {primary}; opacity: 0.9; }}
.site-footer a:hover {{ opacity: 1; }}
.footer-nav {{
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}}
.footer-nav a {{ color: {footer_text}; text-decoration: none; }}
.footer-copy {{ font-size: 0.9rem; opacity: 0.8; }}
.social-links {{
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}}
.social-link {{
  display: inline-block;
  padding: 0.3rem 0.8rem;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  color: {footer_text};
  font-size: 0.85rem;
  text-decoration: none;
  transition: background 0.2s;
}}
.social-link:hover {{ background: rgba(255,255,255,0.2); text-decoration: none; }}

/* ── Responsive ── */
@media (max-width: 800px) {{
  .site-hero {{ padding: 2rem 1rem; }}
  .site-hero h1 {{ font-size: 1.9rem; }}
  .contact-grid {{ grid-template-columns: 1fr; }}
  .features-grid {{ grid-template-columns: 1fr; }}
  .team-grid {{ grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }}
  .site-nav ul {{ gap: 0.45rem; }}
  .site-nav a {{ padding: 0.2rem 0.4rem; }}
}}
@media (max-width: 480px) {{
  .site-container {{ padding: 1rem 0.5rem; }}
  .site-nav ul {{ flex-direction: column; gap: 0.2rem; }}
  .site-page-title {{ font-size: 1.5rem; }}
  .site-hero h1 {{ font-size: 1.6rem; }}
  .footer-nav {{ flex-direction: column; gap: 0.5rem; }}
}}
"""


# ---------------------------------------------------------------------------
# Core XML page builder
# ---------------------------------------------------------------------------

def _build_page_xml(
    page: PageConfig,
    site_config: MultiPageSiteConfig,
    *,
    is_active: bool = False,
    page_index: int = 0,
) -> str:
    """Build a complete Blogger XML theme for a single page.

    Returns a Blogger-compatible XML string with header, nav, content,
    optional blog posts widget, and footer.
    """
    colors = site_config.global_colors.model_dump()
    fonts = site_config.global_fonts.model_dump()
    site_name = xml_escape(site_config.site_name)
    page_title = xml_escape(page.page_title or page.page_label)
    tagline = xml_escape(site_config.tagline)
    description = xml_escape(page.page_description or tagline)

    # Build navigation HTML with active page marking
    nav_items_html = ""
    for i, p in enumerate(site_config.pages):
        active_class = ' class="active"' if i == page_index else ""
        nav_items_html += (
            f'<li><a href="{xml_escape(p.page_id)}.html"{active_class}>'
            f'{xml_escape(p.page_label)}</a></li>\n'
        )
    nav_extra = ""
    for item in site_config.global_nav[:6]:
        href = xml_escape(item.href or "#")
        label = xml_escape(item.label or "Link")
        nav_extra += f'<li><a href="{href}">{label}</a></li>\n'
    nav_html = nav_items_html + nav_extra

    # Generate multi-page CSS
    css = _generate_multi_page_css(colors, fonts, page.layout)
    if page.custom_css:
        css += "\n/* Custom CSS */\n" + page.custom_css

    # Hero section
    hero_html = _render_hero(page.hero)

    # Content blocks
    content_html = ""
    feature_blocks = [b for b in page.content_blocks if b.block_type == "feature"]
    other_blocks = [b for b in page.content_blocks if b.block_type != "feature"]

    if feature_blocks:
        feature_cards = "\n".join(_render_content_block(b) for b in feature_blocks)
        content_html += f'<div class="features-grid">{feature_cards}</div>\n'

    for block in other_blocks:
        content_html += _render_content_block(block) + "\n"

    # Team section (for about page)
    team_html = ""
    if page.team:
        team_html = _render_team_section(page.team)

    # Contact form
    contact_html = ""
    if page.contact_form:
        contact_html = _render_contact_form(page.contact_form)

    # Blog posts section (always required by Blogger, visibility controlled)
    blog_section = """<div class="blog-posts-section">
  <b:section class="main" id="main" name="Main" showaddelement="yes">
    <b:widget id="Blog1" locked="true" title="Blog Posts" type="Blog" version="1">
      <b:includable id="main">
        <b:loop values="data:posts" var="post">
          <article class="post">
            <h3><a expr:href="data:post.url"><data:post.title/></a></h3>
            <div class="post-body"><data:post.body/></div>
          </article>
        </b:loop>
      </b:includable>
    </b:widget>
  </b:section>
</div>"""

    # Social links
    social_html = _render_social_links(site_config.social_links)

    # Footer links
    footer_nav_html = ""
    if site_config.footer_links:
        flinks = "\n".join(
            f'<a href="{xml_escape(link.href or "#")}">{xml_escape(link.label)}</a>'
            for link in site_config.footer_links
        )
        footer_nav_html = f'<div class="footer-nav">{flinks}</div>'

    footer_text = xml_escape(
        site_config.footer_text or f"&copy; {datetime.now(timezone.utc).year} {site_name}"
    )

    # Optional meta keywords
    keywords_meta = ""
    if page.meta_keywords:
        keywords_meta = (
            f'\n  <meta content="{xml_escape(page.meta_keywords)}" name="keywords"/>'
        )

    # Build the full XML document
    xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html>
<html b:css='false' b:defaultwidgetversion='2' b:layoutsVersion='3' b:responsive='true'
  b:templateVersion='1.0.0' expr:class='data:blog.languageDirection'
  xmlns='http://www.w3.org/1999/xhtml'
  xmlns:b='http://www.google.com/2005/gml/b'
  xmlns:data='http://www.google.com/2005/gml/data'
  xmlns:expr='http://www.google.com/2005/gml/expr'>
<head>
  <meta charset='utf-8'/>
  <meta content='width=device-width, initial-scale=1' name='viewport'/>
  <meta content='{description}' name='description'/>{keywords_meta}
  <meta expr:content='data:blog.pageTitle' property='og:title'/>
  <meta expr:content='data:blog.metaDescription' property='og:description'/>
  <meta content='website' property='og:type'/>
  <title>{page_title} — {site_name}</title>
  <b:include data='blog' name='all-head-content'/>
  <b:skin version='1.0.0'><![CDATA[
/*-----------------------------------------------
BloggerEasy Multi-Page Site
Site: {site_name}
Page: {page.page_label}
Template: {page.template}
Generated: {datetime.now(timezone.utc).isoformat()}
-----------------------------------------------*/
{css}
]]></b:skin>
</head>
<body>
  <div class="site-header-outer">
    <header class="site-header">
      <b:section class="header" id="header" maxwidgets="1" name="Header" showaddelement="no">
        <b:widget id="Header1" locked="true" title="{site_name}" type="Header" version="1">
          <b:widget-settings>
            <b:widget-setting name="displayUrl"/>
            <b:widget-setting name="displayHeight">0</b:widget-setting>
            <b:widget-setting name="sectionWidth">-1</b:widget-setting>
            <b:widget-setting name="useImage">false</b:widget-setting>
            <b:widget-setting name="shrinkToFit">false</b:widget-setting>
            <b:widget-setting name="imagePlacement">BEHIND</b:widget-setting>
            <b:widget-setting name="displayWidth">-1</b:widget-setting>
          </b:widget-settings>
          <b:includable id="main">
            <div id="header-inner">
              <h1><b:include name="title"/></h1>
              {f'<p class="site-tagline">{tagline}</p>' if tagline else ''}
            </div>
          </b:includable>
        </b:widget>
      </b:section>
    </header>
    <nav class="site-nav">
      <ul>
        {nav_html}
      </ul>
    </nav>
  </div>

  <div class="site-container">
    {hero_html}

    {content_html}

    {team_html}

    {contact_html}

    {blog_section}
  </div>

  <footer class="site-footer">
    {social_html}
    {footer_nav_html}
    <div class="footer-copy">
      <b:section class="footer" id="footer" name="Footer" showaddelement="yes">
        <b:widget id="TextFooter1" locked="false" title="Footer" type="Text" version="1">
          <b:widget-settings>
            <b:widget-setting name="content">{footer_text} · Built with BloggerEasy</b:widget-setting>
          </b:widget-settings>
          <b:includable id="main"><div class="widget-content"><data:content/></div></b:includable>
        </b:widget>
      </b:section>
    </div>
  </footer>
</body>
</html>"""
    return xml


# ---------------------------------------------------------------------------
# Multi-Page Generator
# ---------------------------------------------------------------------------

class MultiPageGenerator:
    """Generate a complete multi-page Blogger site.

    Usage::

        config = MultiPageSiteConfig(site_name="My Site", ...)
        gen = MultiPageGenerator(config)
        result = gen.generate_all(Path("./output"))
        # result["pages"]["home"]["path"] -> path to home.xml
    """

    def __init__(self, config: MultiPageSiteConfig):
        self.config = config
        # Ensure we have at least default pages
        if not self.config.pages:
            self.config.pages = self._default_pages()

    @staticmethod
    def _default_pages() -> list[PageConfig]:
        """Build sensible default home/about/contact pages."""
        return [
            PageConfig(
                page_id="home",
                page_label="Home",
                page_title="Welcome",
                page_description="Welcome to our site",
                template="home",
                layout="single-column",
                hero=HeroSection(
                    heading="Welcome to Our Site",
                    subheading="Your go-to destination for great content.",
                    cta_label="Explore",
                    cta_link="#",
                ),
                content_blocks=[
                    ContentBlock(
                        block_type="feature",
                        heading="Quality Content",
                        body="We deliver the best articles and resources.",
                    ),
                    ContentBlock(
                        block_type="feature",
                        heading="Regular Updates",
                        body="Fresh content published every week.",
                    ),
                    ContentBlock(
                        block_type="feature",
                        heading="Community Driven",
                        body="Join our growing community of readers.",
                    ),
                ],
                show_blog_posts=True,
            ),
            PageConfig(
                page_id="about",
                page_label="About",
                page_title="About Us",
                page_description="Learn about our story and team",
                template="about",
                layout="two-column",
                hero=HeroSection(
                    heading="About Us",
                    subheading="Get to know our story, mission, and team.",
                    cta_label="Meet the Team",
                    cta_link="#team",
                ),
                content_blocks=[
                    ContentBlock(
                        block_type="text",
                        heading="Our Story",
                        body="We started with a simple idea: make great content accessible to everyone. Since our launch, we have grown into a vibrant community of creators and readers.",
                    ),
                    ContentBlock(
                        block_type="quote",
                        body="The best way to predict the future is to create it.",
                        heading="Peter Drucker",
                    ),
                    ContentBlock(
                        block_type="list",
                        heading="Our Values",
                        items=[
                            "Integrity in everything we do",
                            "Innovation through collaboration",
                            "Inclusivity for all voices",
                            "Impact that matters",
                        ],
                    ),
                ],
                team=[
                    TeamMember(
                        name="Jane Doe",
                        role="Founder & Editor",
                        bio="Jane has been blogging since 2010 and is passionate about quality content.",
                        social_links={"Twitter": "#", "LinkedIn": "#"},
                    ),
                    TeamMember(
                        name="John Smith",
                        role="Tech Lead",
                        bio="John builds the tools that power our platform.",
                        social_links={"GitHub": "#", "Twitter": "#"},
                    ),
                    TeamMember(
                        name="Alex Rivera",
                        role="Content Strategist",
                        bio="Alex ensures every piece of content meets our high standards.",
                        social_links={"LinkedIn": "#"},
                    ),
                ],
                show_blog_posts=False,
                show_sidebar=True,
            ),
            PageConfig(
                page_id="contact",
                page_label="Contact",
                page_title="Contact Us",
                page_description="Get in touch with our team",
                template="contact",
                layout="two-column",
                hero=HeroSection(
                    heading="Contact Us",
                    subheading="We would love to hear from you. Reach out anytime!",
                    cta_label="Send a Message",
                    cta_link="#contact-form",
                ),
                content_blocks=[
                    ContentBlock(
                        block_type="text",
                        heading="How to Reach Us",
                        body="Fill out the form below or use our contact information. We typically respond within 24 hours.",
                    ),
                ],
                contact_form=ContactForm(
                    email="hello@example.com",
                    phone="+1 (555) 123-4567",
                    address="123 Blog Street, Web City, WC 90210",
                    form_action="#",
                ),
                show_blog_posts=False,
                show_sidebar=False,
            ),
        ]

    def generate_page(
        self,
        page: PageConfig,
        *,
        page_index: int = 0,
    ) -> str:
        """Generate XML for a single page."""
        return _build_page_xml(
            page,
            self.config,
            is_active=True,
            page_index=page_index,
        )

    def generate_all(self, output_dir: Path) -> dict:
        """Generate all pages and write them to ``output_dir``.

        Returns a manifest dict with per-page paths, validation results,
        and overall site metadata.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, dict] = {}
        all_ok = True
        total_bytes = 0

        for i, page in enumerate(self.config.pages):
            xml = self.generate_page(page, page_index=i)
            validation = validate_blogger_xml(xml)
            filename = sanitize_filename(page.page_id) + ".xml"
            filepath = output_dir / filename
            filepath.write_text(xml, encoding="utf-8")
            file_size = filepath.stat().st_size
            total_bytes += file_size

            results[page.page_id] = {
                "page_id": page.page_id,
                "page_label": page.page_label,
                "page_title": page.page_title,
                "template": page.template,
                "path": str(filepath),
                "filename": filename,
                "bytes": file_size,
                "validation": validation,
            }
            if not validation.get("ok"):
                all_ok = False

        # Write site manifest
        manifest = {
            "generator": "bloggereasy.feature_issue_80.v1",
            "site_name": self.config.site_name,
            "tagline": self.config.tagline,
            "author": self.config.author,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "page_count": len(self.config.pages),
            "all_valid": all_ok,
            "total_bytes": total_bytes,
            "pages": results,
            "import_hint": (
                "Upload each .xml file in Blogger → Theme → Backup/Restore → Upload. "
                "Each page is a self-contained Blogger theme with inter-page navigation."
            ),
        }
        manifest_path = output_dir / "site_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return manifest

    def generate_bundle(self, output_dir: Path) -> dict:
        """Generate all pages plus a GUIDE.md in a self-contained bundle.

        Produces the same output as ``generate_all`` and additionally writes
        a human-readable GUIDE.md with import instructions.
        """
        manifest = self.generate_all(output_dir)

        # Generate guide
        guide = f"""# {self.config.site_name} — Multi-Page Site Bundle

Generated by BloggerEasy Multi-Page Site Generator (Issue #80).

## Pages

| Page | Template | File |
|------|----------|------|
"""
        for page_id, info in manifest["pages"].items():
            guide += f"| {info['page_label']} | {info['template']} | {info['filename']} |\n"

        guide += f"""
## Validation Status: {'✅ All pages pass' if manifest['all_valid'] else '⚠️ Some pages need review'}

## Import Instructions

1. Open [Blogger](https://www.blogger.com/) → your blog → **Theme**.
2. Click **⋮** → **Backup** to save your current theme.
3. For each page, click **⋮** → **Restore** and upload the corresponding `.xml` file.
4. After uploading all pages, navigate between them using the built-in navigation bar.
5. Adjust colors and layout under **Theme → Customize** as needed.

## Files

"""
        for page_id, info in manifest["pages"].items():
            guide += f"- `{info['filename']}` — {info['page_label']} page ({info['bytes']} bytes)\n"

        guide += f"- `site_manifest.json` — Machine-readable manifest\n"
        guide += f"- `GUIDE.md` — This guide\n"

        guide_path = output_dir / "GUIDE.md"
        guide_path.write_text(guide, encoding="utf-8")

        return manifest


# ---------------------------------------------------------------------------
# Convenience: generate from site config dict
# ---------------------------------------------------------------------------

def generate_multi_page_site(
    site_config: dict[str, Any] | MultiPageSiteConfig,
    output_dir: str | Path,
    *,
    bundle: bool = False,
) -> dict:
    """Convenience function: generate a multi-page site from a dict or config object.

    Args:
        site_config: MultiPageSiteConfig instance or dict to parse.
        output_dir: Where to write generated files.
        bundle: Also generate GUIDE.md if True.

    Returns:
        Manifest dict with per-page details.
    """
    if isinstance(site_config, dict):
        config = MultiPageSiteConfig.model_validate(site_config)
    else:
        config = site_config

    gen = MultiPageGenerator(config)
    if bundle:
        return gen.generate_bundle(Path(output_dir))
    return gen.generate_all(Path(output_dir))


# ---------------------------------------------------------------------------
# Quick-start: generate from HTML templates
# ---------------------------------------------------------------------------

def generate_from_html_templates(
    home_html: str | None = None,
    about_html: str | None = None,
    contact_html: str | None = None,
    output_dir: str | Path = "multi_page_out",
    *,
    site_name: str = "My Multi-Page Blog",
    tagline: str = "",
) -> dict:
    """Generate a multi-page site from raw HTML strings for each page.

    Each HTML string is parsed through the existing HTML parser to extract
    colors, fonts, headings, and paragraphs. The extracted structure is then
    used to build a complete Blogger XML page with navigation.
    """
    from bloggereasy.parse.html_page import parse_html_string

    pages: list[PageConfig] = []

    templates = [
        ("home", "Home", home_html),
        ("about", "About", about_html),
        ("contact", "Contact", contact_html),
    ]

    for page_id, label, html in templates:
        if html is None:
            continue
        parsed = parse_html_string(html, source=f"{page_id}-template")
        title = parsed.get("title", label)
        desc = parsed.get("description", "")
        headings = parsed.get("headings", [])
        paragraphs = parsed.get("sample_paragraphs", [])
        colors = parsed.get("colors", {})

        # Build content blocks from parsed data
        blocks: list[ContentBlock] = []
        hero_heading = headings[0] if headings else title
        hero_sub = paragraphs[0] if paragraphs else desc

        page_config = PageConfig(
            page_id=page_id,
            page_label=label,
            page_title=title,
            page_description=desc,
            template=page_id,
            layout=parsed.get("layout", "single-column"),
            hero=HeroSection(
                heading=hero_heading,
                subheading=hero_sub,
                cta_label="Learn More" if page_id == "home" else (
                    "Meet the Team" if page_id == "about" else "Get In Touch"
                ),
                cta_link="#" if page_id != "about" else "#team",
            ),
            content_blocks=blocks,
            show_blog_posts=(page_id == "home"),
            show_sidebar=False,
        )

        # Add feature blocks from remaining paragraphs
        for i, h in enumerate(headings[1:5]):
            body = paragraphs[i + 1] if i + 1 < len(paragraphs) else ""
            blocks.append(ContentBlock(
                block_type="feature",
                heading=h,
                body=body,
            ))

        # Add text blocks if no features
        if not blocks and paragraphs:
            for p in paragraphs[:3]:
                blocks.append(ContentBlock(
                    block_type="text",
                    body=p,
                ))

        if page_id == "about":
            if not page_config.team:
                page_config.team = MultiPageGenerator._default_pages()[1].team
        if page_id == "contact":
            if not page_config.contact_form:
                page_config.contact_form = MultiPageGenerator._default_pages()[2].contact_form

        pages.append(page_config)

    # Ensure all three pages exist
    existing_ids = {p.page_id for p in pages}
    defaults = MultiPageGenerator._default_pages()
    for dp in defaults:
        if dp.page_id not in existing_ids:
            pages.append(dp)

    config = MultiPageSiteConfig(
        site_name=site_name,
        tagline=tagline,
        pages=pages,
        global_colors=(
            ColorPalette(**pages[0].hero.model_dump())
            if pages else ColorPalette()
        ),
    )

    return generate_multi_page_site(config, output_dir, bundle=True)
