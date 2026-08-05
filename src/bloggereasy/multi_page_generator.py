"""Multi-page site generator for coordinated home / about / contact theme sets."""

from __future__ import annotations

import json as json_lib
from typing import Any

from bloggereasy.theme.models import (
    ColorPalette,
    FeatureFlags,
    FontSet,
    NavLink,
    PageStructure,
)


class MultiPageGenerator:
    """Generates coordinated multi-page theme sets with home, about, and contact pages.

    Each page is represented as a ``PageStructure`` and includes consistent
    navigation, colors, fonts, and layout.  The generator also supports JSON
    export so the full site blueprint can be serialised and shared.

    Basic usage::

        gen = MultiPageGenerator(site_name="My Site")
        site = gen.generate_all()
        json_str = gen.export_json()
    """

    def __init__(
        self,
        site_name: str = "My Site",
        tagline: str = "",
        primary_color: str = "#1a73e8",
        secondary_color: str = "#34a853",
        background_color: str = "#ffffff",
        text_color: str = "#222222",
        body_font: str = "system-ui, sans-serif",
        heading_font: str | None = None,
        layout: str = "single-column",
        contact_email: str = "",
        contact_phone: str = "",
    ) -> None:
        self.site_name = site_name
        self.tagline = tagline
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.background_color = background_color
        self.text_color = text_color
        self.body_font = body_font
        self.heading_font = heading_font
        self.layout: str = layout
        self.contact_email = contact_email
        self.contact_phone = contact_phone

        # Shared colour palette and font set for all pages
        self._colors = ColorPalette(
            primary=primary_color,
            secondary=secondary_color,
            background=background_color,
            text=text_color,
        )
        self._fonts = FontSet(body=body_font, heading=heading_font)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def generate_navigation(self) -> list[NavLink]:
        """Return a consistent navigation link list for the site."""
        return [
            NavLink(label="Home", href="/"),
            NavLink(label="About", href="/about"),
            NavLink(label="Contact", href="/contact"),
        ]

    # ------------------------------------------------------------------
    # Page generators
    # ------------------------------------------------------------------
    def _base_structure(self, title_suffix: str, description: str) -> dict[str, Any]:
        """Shared foundation every page builds on."""
        return {
            "source": "multi-page-gen",
            "title": f"{self.site_name} - {title_suffix}",
            "description": description,
            "nav_links": self.generate_navigation(),
            "colors": self._colors,
            "fonts": self._fonts,
            "layout": self.layout,
            "features": FeatureFlags(header=True, footer=True, sidebar=False),
        }

    def generate_home(self) -> PageStructure:
        """Generate the Home / landing page structure."""
        data = self._base_structure(
            "Home",
            f"Welcome to {self.site_name}. {self.tagline}".strip(),
        )
        data["headings"] = [
            f"Welcome to {self.site_name}",
            "Latest Updates",
            "Featured Content",
        ]
        data["sample_paragraphs"] = [
            f"Thanks for visiting {self.site_name}. We bring you the latest insights, "
            "stories, and resources to keep you informed and inspired.",
            "Stay tuned for regular updates, fresh content, and community highlights.",
            "Explore our pages to learn more about what we do and how to get in touch.",
        ]
        return PageStructure(**data)

    def generate_about(self) -> PageStructure:
        """Generate the About page structure."""
        data = self._base_structure(
            "About",
            f"Learn more about {self.site_name} and our mission.",
        )
        data["headings"] = [
            "About Us",
            "Our Mission",
            "Our Team",
        ]
        data["sample_paragraphs"] = [
            f"{self.site_name} was founded with a simple goal: to create a space where "
            "ideas, stories, and knowledge can be shared freely.",
            "Our mission is to empower creators, developers, and dreamers with the tools "
            "and inspiration they need to build something great.",
            "We are a small but passionate team committed to quality, openness, and community.",
        ]
        return PageStructure(**data)

    def generate_contact(self) -> PageStructure:
        """Generate the Contact page structure."""
        data = self._base_structure(
            "Contact",
            f"Get in touch with {self.site_name}.",
        )
        data["headings"] = [
            "Contact Us",
            "Send Us a Message",
            "Find Us",
        ]
        contact_lines = [
            f"We'd love to hear from you! Reach out to the {self.site_name} team.",
        ]
        if self.contact_email:
            contact_lines.append(f"Email: {self.contact_email}")
        if self.contact_phone:
            contact_lines.append(f"Phone: {self.contact_phone}")
        contact_lines.append(
            "You can also follow us on social media for the latest news and updates."
        )
        data["sample_paragraphs"] = contact_lines
        return PageStructure(**data)

    def generate_all(self) -> dict[str, PageStructure]:
        """Return a dict mapping page names to their ``PageStructure``."""
        return {
            "home": self.generate_home(),
            "about": self.generate_about(),
            "contact": self.generate_contact(),
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return the full site blueprint as a plain dict suitable for JSON."""
        pages = self.generate_all()
        return {
            "site_name": self.site_name,
            "tagline": self.tagline,
            "layout": self.layout,
            "colors": self._colors.model_dump(exclude_none=True),
            "fonts": self._fonts.model_dump(exclude_none=True),
            "navigation": [nav.model_dump() for nav in self.generate_navigation()],
            "pages": {
                name: page.model_dump(exclude_none=True) for name, page in pages.items()
            },
        }

    def export_json(self, indent: int = 2) -> str:
        """Export the full site blueprint as a JSON string."""
        return json_lib.dumps(self.to_dict(), indent=indent)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def page_count(self) -> int:
        """Return the number of pages this generator produces."""
        return len(self.generate_all())

    def page_names(self) -> list[str]:
        """Return the ordered list of page names."""
        return list(self.generate_all().keys())


__all__ = ["MultiPageGenerator"]
