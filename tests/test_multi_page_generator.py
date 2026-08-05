"""Tests for the multi-page site generator."""

from __future__ import annotations

import json

import pytest

from bloggereasy.multi_page_generator import MultiPageGenerator
from bloggereasy.theme.models import NavLink, PageStructure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def default_gen() -> MultiPageGenerator:
    return MultiPageGenerator()


@pytest.fixture
def custom_gen() -> MultiPageGenerator:
    return MultiPageGenerator(
        site_name="ACME Corp",
        tagline="Building the future",
        primary_color="#ff6600",
        secondary_color="#0099cc",
        background_color="#fafafa",
        text_color="#333333",
        body_font="Georgia, serif",
        heading_font="Arial, sans-serif",
        layout="two-column",
        contact_email="hello@acme.example.com",
        contact_phone="+1-555-1234",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestMultiPageGeneratorInit:
    def test_default_values(self, default_gen: MultiPageGenerator) -> None:
        assert default_gen.site_name == "My Site"
        assert default_gen.tagline == ""
        assert default_gen.primary_color == "#1a73e8"
        assert default_gen.layout == "single-column"

    def test_custom_values(self, custom_gen: MultiPageGenerator) -> None:
        assert custom_gen.site_name == "ACME Corp"
        assert custom_gen.tagline == "Building the future"
        assert custom_gen.primary_color == "#ff6600"
        assert custom_gen.secondary_color == "#0099cc"
        assert custom_gen.layout == "two-column"
        assert custom_gen.contact_email == "hello@acme.example.com"
        assert custom_gen.contact_phone == "+1-555-1234"


class TestNavigation:
    def test_nav_has_three_links(self, default_gen: MultiPageGenerator) -> None:
        nav = default_gen.generate_navigation()
        assert len(nav) == 3

    def test_nav_link_labels_and_hrefs(self, default_gen: MultiPageGenerator) -> None:
        nav = default_gen.generate_navigation()
        expected = [
            ("Home", "/"),
            ("About", "/about"),
            ("Contact", "/contact"),
        ]
        for link, (label, href) in zip(nav, expected):
            assert link.label == label
            assert link.href == href

    def test_nav_links_are_navlink_instances(self, default_gen: MultiPageGenerator) -> None:
        nav = default_gen.generate_navigation()
        for link in nav:
            assert isinstance(link, NavLink)


class TestHomePage:
    def test_home_title_includes_site_name(self, default_gen: MultiPageGenerator) -> None:
        home = default_gen.generate_home()
        assert "My Site" in home.title
        assert home.title.endswith(" - Home")

    def test_home_has_headings(self, default_gen: MultiPageGenerator) -> None:
        home = default_gen.generate_home()
        assert len(home.headings) >= 3

    def test_home_has_sample_paragraphs(self, default_gen: MultiPageGenerator) -> None:
        home = default_gen.generate_home()
        assert len(home.sample_paragraphs) >= 3


class TestAboutPage:
    def test_about_title(self, custom_gen: MultiPageGenerator) -> None:
        about = custom_gen.generate_about()
        assert "ACME Corp" in about.title
        assert about.title.endswith(" - About")

    def test_about_description(self, custom_gen: MultiPageGenerator) -> None:
        about = custom_gen.generate_about()
        assert "ACME Corp" in about.description


class TestContactPage:
    def test_contact_has_email_when_provided(self, custom_gen: MultiPageGenerator) -> None:
        contact = custom_gen.generate_contact()
        combined = " ".join(contact.sample_paragraphs)
        assert "hello@acme.example.com" in combined

    def test_contact_has_phone_when_provided(self, custom_gen: MultiPageGenerator) -> None:
        contact = custom_gen.generate_contact()
        combined = " ".join(contact.sample_paragraphs)
        assert "+1-555-1234" in combined

    def test_contact_without_details(self, default_gen: MultiPageGenerator) -> None:
        contact = default_gen.generate_contact()
        combined = " ".join(contact.sample_paragraphs)
        assert "Email:" not in combined
        assert "Phone:" not in combined


class TestGenerateAll:
    def test_generate_all_returns_three_pages(self, default_gen: MultiPageGenerator) -> None:
        pages = default_gen.generate_all()
        assert len(pages) == 3
        assert set(pages.keys()) == {"home", "about", "contact"}

    def test_generate_all_pages_are_page_structures(self, default_gen: MultiPageGenerator) -> None:
        pages = default_gen.generate_all()
        for page in pages.values():
            assert isinstance(page, PageStructure)

    def test_all_pages_share_navigation(self, default_gen: MultiPageGenerator) -> None:
        pages = default_gen.generate_all()
        nav_ids = []
        for page in pages.values():
            nav_repr = [(l.label, l.href) for l in page.nav_links]
            nav_ids.append(nav_repr)
        # All pages should have identical navigation
        assert len(set(tuple(x) for x in nav_ids)) == 1

    def test_all_pages_share_colors(self, custom_gen: MultiPageGenerator) -> None:
        pages = custom_gen.generate_all()
        for page in pages.values():
            assert page.colors.primary == "#ff6600"
            assert page.colors.background == "#fafafa"


class TestExport:
    def test_export_json_is_valid(self, default_gen: MultiPageGenerator) -> None:
        json_str = default_gen.export_json()
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_export_json_contains_site_name(self, custom_gen: MultiPageGenerator) -> None:
        json_str = custom_gen.export_json()
        data = json.loads(json_str)
        assert data["site_name"] == "ACME Corp"

    def test_export_json_contains_navigation(self, default_gen: MultiPageGenerator) -> None:
        json_str = default_gen.export_json()
        data = json.loads(json_str)
        assert len(data["navigation"]) == 3

    def test_export_json_contains_all_pages(self, default_gen: MultiPageGenerator) -> None:
        json_str = default_gen.export_json()
        data = json.loads(json_str)
        assert set(data["pages"].keys()) == {"home", "about", "contact"}

    def test_to_dict_matches_export_json(self, default_gen: MultiPageGenerator) -> None:
        d = default_gen.to_dict()
        j = json.loads(default_gen.export_json())
        assert d == j


class TestHelpers:
    def test_page_count(self, default_gen: MultiPageGenerator) -> None:
        assert default_gen.page_count() == 3

    def test_page_names(self, default_gen: MultiPageGenerator) -> None:
        names = default_gen.page_names()
        assert names == ["home", "about", "contact"]
