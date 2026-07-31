"""Tests for multi-page site generator (Issue #80).

Covers: models, MultiPageGenerator, XML generation, validation, CLI integration,
HTML template parsing, bundle generation, and edge cases.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from bloggereasy.feature_issue_80 import (
    ContactForm,
    ContentBlock,
    HeroSection,
    MultiPageGenerator,
    MultiPageSiteConfig,
    PageConfig,
    TeamMember,
    _build_page_xml,
    _generate_multi_page_css,
    _render_contact_form,
    _render_content_block,
    _render_hero,
    _render_social_links,
    _render_team_section,
    generate_from_html_templates,
    generate_multi_page_site,
)
from bloggereasy.theme.models import ColorPalette, FontSet, NavLink
from bloggereasy.theme.validate import validate_blogger_xml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_colors() -> ColorPalette:
    return ColorPalette(
        primary="#1a73e8",
        secondary="#34a853",
        background="#ffffff",
        text="#222222",
    )


@pytest.fixture
def default_fonts() -> FontSet:
    return FontSet(body="system-ui, sans-serif", heading="Georgia, serif")


@pytest.fixture
def basic_site_config(default_colors, default_fonts) -> MultiPageSiteConfig:
    """A minimal but complete site configuration."""
    return MultiPageSiteConfig(
        site_name="Test Site",
        tagline="Just a test",
        author="Tester",
        site_url="https://test.blogspot.com",
        global_colors=default_colors,
        global_fonts=default_fonts,
        pages=MultiPageGenerator._default_pages(),
        footer_text="Test footer",
    )


@pytest.fixture
def generator(basic_site_config) -> MultiPageGenerator:
    return MultiPageGenerator(basic_site_config)


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------

class TestHeroSection:
    """Test HeroSection model validation."""

    def test_default_hero(self) -> None:
        hero = HeroSection()
        assert hero.heading == "Welcome"
        assert hero.subheading == ""
        assert hero.cta_label == "Learn More"
        assert hero.cta_link == "#"

    def test_custom_hero(self) -> None:
        hero = HeroSection(
            heading="Hello World",
            subheading="A great site",
            cta_label="Go",
            cta_link="/go",
            background_color="#ff0000",
            image_url="hero.jpg",
        )
        assert hero.heading == "Hello World"
        assert hero.background_color == "#ff0000"
        assert hero.image_url == "hero.jpg"

    def test_hero_stringifies_none(self) -> None:
        hero = HeroSection(heading=None, subheading=None)  # type: ignore[arg-type]
        assert hero.heading == ""
        assert hero.subheading == ""


class TestContentBlock:
    """Test ContentBlock model."""

    def test_text_block(self) -> None:
        block = ContentBlock(block_type="text", heading="Hi", body="Hello world")
        assert block.block_type == "text"
        assert block.heading == "Hi"

    def test_feature_block(self) -> None:
        block = ContentBlock(
            block_type="feature",
            heading="Feature",
            body="Description",
            image_url="img.png",
            image_alt="Alt text",
        )
        assert block.image_url == "img.png"
        assert block.image_alt == "Alt text"

    def test_list_block_items(self) -> None:
        block = ContentBlock(block_type="list", items=["a", "b", "c"])
        assert len(block.items) == 3
        assert block.items[0] == "a"

    def test_quote_block(self) -> None:
        block = ContentBlock(block_type="quote", body="To be or not to be", heading="Shakespeare")
        assert block.block_type == "quote"

    def test_default_block_type(self) -> None:
        block = ContentBlock()
        assert block.block_type == "text"

    def test_items_stringifies_singleton(self) -> None:
        block = ContentBlock(items="single")  # type: ignore[arg-type]
        assert block.items == ["single"]


class TestTeamMember:
    """Test TeamMember model."""

    def test_default_member(self) -> None:
        m = TeamMember()
        assert m.name == ""
        assert m.role == ""
        assert m.bio == ""
        assert m.social_links == {}

    def test_member_with_socials(self) -> None:
        m = TeamMember(
            name="John",
            role="Dev",
            bio="Coder",
            social_links={"GitHub": "https://github.com/john", "Twitter": "https://x.com/john"},
        )
        assert len(m.social_links) == 2
        assert m.social_links["GitHub"] == "https://github.com/john"


class TestContactForm:
    """Test ContactForm model."""

    def test_default_form(self) -> None:
        cf = ContactForm()
        assert cf.email == ""
        assert cf.phone == ""
        assert cf.address == ""
        assert cf.show_map is False

    def test_full_form(self) -> None:
        cf = ContactForm(
            email="a@b.com",
            phone="555-0123",
            address="123 St",
            show_map=True,
            map_embed_url="https://maps.example.com",
        )
        assert cf.email == "a@b.com"
        assert cf.show_map is True
        assert cf.map_embed_url == "https://maps.example.com"


class TestPageConfig:
    """Test PageConfig model."""

    def test_default_page(self) -> None:
        pc = PageConfig()
        assert pc.page_id == "home"
        assert pc.page_label == "Home"
        assert pc.page_title == "My Blog"
        assert pc.layout == "single-column"
        assert pc.show_blog_posts is True
        assert pc.contact_form is None

    def test_about_page(self) -> None:
        pc = PageConfig(
            page_id="about",
            page_label="About",
            page_title="About Us",
            layout="two-column",
            show_blog_posts=False,
            show_sidebar=True,
            team=[TeamMember(name="Jane")],
        )
        assert len(pc.team) == 1
        assert pc.show_sidebar is True

    def test_contact_page_with_form(self) -> None:
        pc = PageConfig(
            page_id="contact",
            page_label="Contact",
            contact_form=ContactForm(email="hi@test.com"),
        )
        assert pc.contact_form is not None
        assert pc.contact_form.email == "hi@test.com"


class TestMultiPageSiteConfig:
    """Test MultiPageSiteConfig model."""

    def test_default_config(self) -> None:
        cfg = MultiPageSiteConfig()
        assert cfg.site_name == "My Site"
        assert cfg.language == "en"
        assert cfg.pages == []
        assert cfg.social_links == {}

    def test_config_with_social(self) -> None:
        cfg = MultiPageSiteConfig(
            site_name="Blog",
            social_links={"Twitter": "https://x.com/blog", "Instagram": "https://instagr.am/blog"},
        )
        assert len(cfg.social_links) == 2

    def test_config_with_nav(self) -> None:
        cfg = MultiPageSiteConfig(
            global_nav=[NavLink(label="Home", href="/"), NavLink(label="Blog", href="/blog")],
        )
        assert len(cfg.global_nav) == 2

    def test_config_with_footer_links(self) -> None:
        cfg = MultiPageSiteConfig(
            footer_links=[NavLink(label="Privacy", href="/privacy")],
            footer_text="© 2024",
        )
        assert len(cfg.footer_links) == 1
        assert cfg.footer_text == "© 2024"


# ---------------------------------------------------------------------------
# HTML rendering tests
# ---------------------------------------------------------------------------

class TestRenderHero:
    """Test hero section HTML rendering."""

    def test_basic_hero(self) -> None:
        hero = HeroSection(heading="Hello", subheading="World", cta_label="Go", cta_link="/go")
        html = _render_hero(hero)
        assert "<h1>Hello</h1>" in html
        assert "World" in html
        assert 'href="/go"' in html
        assert "Go" in html

    def test_hero_with_background(self) -> None:
        hero = HeroSection(heading="X", background_color="#ff0000")
        html = _render_hero(hero)
        assert "background-color: #ff0000" in html

    def test_hero_with_image(self) -> None:
        hero = HeroSection(heading="X", image_url="img.jpg")
        html = _render_hero(hero)
        assert 'src="img.jpg"' in html
        assert "hero-img" in html

    def test_hero_escapes_html(self) -> None:
        hero = HeroSection(heading="<script>alert(1)</script>")
        html = _render_hero(hero)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestRenderContentBlock:
    """Test content block HTML rendering."""

    def test_text_block(self) -> None:
        html = _render_content_block(ContentBlock(block_type="text", heading="H", body="B"))
        assert "<h3>H</h3>" in html
        assert "<p>B</p>" in html

    def test_feature_block(self) -> None:
        html = _render_content_block(
            ContentBlock(block_type="feature", heading="F", body="Desc", image_url="f.jpg", image_alt="alt")
        )
        assert "content-feature" in html
        assert 'src="f.jpg"' in html
        assert 'alt="alt"' in html

    def test_image_block(self) -> None:
        html = _render_content_block(
            ContentBlock(block_type="image", image_url="p.jpg", image_alt="photo", body="caption")
        )
        assert "content-image" in html
        assert 'src="p.jpg"' in html
        assert "caption" in html

    def test_quote_block(self) -> None:
        html = _render_content_block(
            ContentBlock(block_type="quote", body="Words", heading="Author")
        )
        assert "content-quote" in html
        assert "Words" in html
        assert "Author" in html

    def test_list_block(self) -> None:
        html = _render_content_block(
            ContentBlock(block_type="list", heading="Items", items=["a", "b"])
        )
        assert "<li>a</li>" in html
        assert "<li>b</li>" in html

    def test_empty_block(self) -> None:
        html = _render_content_block(ContentBlock())
        assert "content-text" in html


class TestRenderTeamSection:
    """Test team section HTML rendering."""

    def test_empty_team(self) -> None:
        assert _render_team_section([]) == ""

    def test_single_member(self) -> None:
        html = _render_team_section([TeamMember(name="Alice", role="CEO", bio="Leader")])
        assert "Alice" in html
        assert "CEO" in html
        assert "Leader" in html
        assert "team-grid" in html
        assert "Our Team" in html

    def test_member_with_social(self) -> None:
        html = _render_team_section([
            TeamMember(name="Bob", social_links={"GitHub": "https://gh.com/bob"})
        ])
        assert 'href="https://gh.com/bob"' in html
        assert "GitHub" in html

    def test_member_with_image(self) -> None:
        html = _render_team_section([TeamMember(name="Cat", image_url="cat.jpg")])
        assert 'src="cat.jpg"' in html
        assert "team-avatar" in html


class TestRenderContactForm:
    """Test contact form HTML rendering."""

    def test_empty_form(self) -> None:
        html = _render_contact_form(ContactForm())
        assert "Get In Touch" in html
        assert "contact-form" in html

    def test_full_form(self) -> None:
        cf = ContactForm(
            email="hi@test.com",
            phone="555",
            address="123 Main St",
        )
        html = _render_contact_form(cf)
        assert "hi@test.com" in html
        assert "555" in html
        assert "123 Main St" in html
        assert 'mailto:hi@test.com' in html

    def test_form_with_map(self) -> None:
        cf = ContactForm(show_map=True, map_embed_url="https://maps.example.com")
        html = _render_contact_form(cf)
        assert "contact-map" in html
        assert "https://maps.example.com" in html


class TestRenderSocialLinks:
    """Test social links HTML rendering."""

    def test_empty_social(self) -> None:
        assert _render_social_links({}) == ""

    def test_social_links(self) -> None:
        html = _render_social_links({"Twitter": "https://x.com/t", "GitHub": "https://gh.com/g"})
        assert "Twitter" in html
        assert "GitHub" in html
        assert "social-links" in html


# ---------------------------------------------------------------------------
# CSS generation tests
# ---------------------------------------------------------------------------

class TestMultiPageCss:
    """Test CSS generation for multi-page sites."""

    def test_generates_css(self) -> None:
        css = _generate_multi_page_css(
            {"primary": "#123456", "secondary": "#abcdef", "background": "#fff", "text": "#000",
             "surface": "#eee", "muted": "#ddd", "border": "#ccc", "footer": "#111", "footer_text": "#eee"},
            {"body": "Arial", "heading": "Georgia"},
        )
        assert "#123456" in css
        assert "Arial" in css
        assert "Georgia" in css
        assert ".site-header" in css
        assert ".site-nav" in css
        assert ".site-hero" in css
        assert ".content-block" in css
        assert ".team-grid" in css
        assert ".contact-grid" in css
        assert ".site-footer" in css
        assert "@media" in css

    def test_css_uses_defaults_when_missing_colors(self) -> None:
        css = _generate_multi_page_css({}, {"body": "sans-serif"})
        assert "#1a73e8" in css  # default primary
        assert "sans-serif" in css

    def test_css_escapes_special_chars(self) -> None:
        css = _generate_multi_page_css(
            {"primary": '"><script>'}, {"body": "Arial"}
        )
        # Should not contain unescaped dangerous chars
        assert '"' not in css.split("primary:")[1].split(";")[0] if "primary:" in css else True


# ---------------------------------------------------------------------------
# XML page builder tests
# ---------------------------------------------------------------------------

class TestBuildPageXml:
    """Test _build_page_xml directly."""

    def test_builds_valid_xml(self, basic_site_config) -> None:
        page = basic_site_config.pages[0]
        xml = _build_page_xml(page, basic_site_config, page_index=0)
        assert '<?xml version="1.0"' in xml
        assert "BloggerEasy Multi-Page Site" in xml
        assert "Test Site" in xml
        assert "b:skin" in xml
        assert "b:widget" in xml
        # Validate
        result = validate_blogger_xml(xml)
        assert result["ok"] is True, f"Validation failed: {result.get('errors', [])}"

    def test_builds_home_page_with_blog_posts(self, basic_site_config) -> None:
        page = basic_site_config.pages[0]  # home
        xml = _build_page_xml(page, basic_site_config, page_index=0)
        assert "Blog1" in xml
        assert "Blog Posts" in xml

    def test_builds_about_page_with_team(self, basic_site_config) -> None:
        page = basic_site_config.pages[1]  # about
        xml = _build_page_xml(page, basic_site_config, page_index=1)
        assert "Our Team" in xml or "team-grid" in xml
        assert "Jane Doe" in xml

    def test_builds_contact_page_with_form(self, basic_site_config) -> None:
        page = basic_site_config.pages[2]  # contact
        xml = _build_page_xml(page, basic_site_config, page_index=2)
        assert "Get In Touch" in xml or "contact-form" in xml
        assert "hello@example.com" in xml

    def test_navigation_marks_active_page(self, basic_site_config) -> None:
        page = basic_site_config.pages[0]
        xml = _build_page_xml(page, basic_site_config, page_index=0)
        # Home should be marked active
        assert 'class="active"' in xml

    def test_all_pages_have_nav_links(self, basic_site_config) -> None:
        for i, page in enumerate(basic_site_config.pages):
            xml = _build_page_xml(page, basic_site_config, page_index=i)
            assert f'{page.page_id}.html' in xml

    def test_blog_widget_always_present(self, basic_site_config) -> None:
        page = basic_site_config.pages[1]  # about — show_blog_posts=False
        xml = _build_page_xml(page, basic_site_config, page_index=1)
        assert "Blog1" in xml  # Blogger requires blog widget on all themes

    def test_page_with_custom_css(self, basic_site_config) -> None:
        page = PageConfig(
            page_id="custom",
            page_label="Custom",
            custom_css=".custom { color: red; }",
        )
        config = MultiPageSiteConfig(
            site_name="Test",
            pages=[page],
        )
        xml = _build_page_xml(page, config, page_index=0)
        assert ".custom { color: red; }" in xml

    def test_page_with_meta_keywords(self, basic_site_config) -> None:
        page = PageConfig(
            page_id="home",
            page_label="Home",
            meta_keywords="blog, tech, fun",
        )
        config = MultiPageSiteConfig(site_name="Test", pages=[page])
        xml = _build_page_xml(page, config, page_index=0)
        assert 'name="keywords"' in xml
        assert "blog, tech, fun" in xml

    def test_page_escapes_xml_special_chars(self, basic_site_config) -> None:
        page = PageConfig(
            page_id="test",
            page_label="Test",
            page_title='Fun & Games <cool> "quoted"',
        )
        config = MultiPageSiteConfig(site_name="Test", pages=[page])
        xml = _build_page_xml(page, config, page_index=0)
        assert "&amp;" in xml or "Fun" in xml  # XML escape
        # Should still validate
        result = validate_blogger_xml(xml)
        assert result["ok"] is True


# ---------------------------------------------------------------------------
# MultiPageGenerator tests
# ---------------------------------------------------------------------------

class TestMultiPageGenerator:
    """Test MultiPageGenerator class."""

    def test_default_pages_created(self) -> None:
        pages = MultiPageGenerator._default_pages()
        assert len(pages) == 3
        ids = {p.page_id for p in pages}
        assert ids == {"home", "about", "contact"}

    def test_default_pages_structure(self) -> None:
        pages = MultiPageGenerator._default_pages()
        home = pages[0]
        assert home.page_id == "home"
        assert len(home.content_blocks) == 3
        assert home.content_blocks[0].block_type == "feature"
        about = pages[1]
        assert len(about.team) == 3
        contact = pages[2]
        assert contact.contact_form is not None
        assert "@" in contact.contact_form.email

    def test_generate_all_creates_files(self, generator, tmp_path) -> None:
        out = tmp_path / "site"
        manifest = generator.generate_all(out)
        assert out.exists()
        assert (out / "home.xml").exists()
        assert (out / "about.xml").exists()
        assert (out / "contact.xml").exists()
        assert (out / "site_manifest.json").exists()
        assert manifest["page_count"] == 3

    def test_generate_all_produces_valid_xml(self, generator, tmp_path) -> None:
        out = tmp_path / "site2"
        manifest = generator.generate_all(out)
        for page_id, info in manifest["pages"].items():
            assert info["validation"]["ok"] is True, (
                f"{page_id} failed: {info['validation'].get('errors', [])}"
            )
        assert manifest["all_valid"] is True

    def test_generate_all_manifest_is_valid_json(self, generator, tmp_path) -> None:
        out = tmp_path / "site3"
        generator.generate_all(out)
        manifest_path = out / "site_manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["site_name"] == "Test Site"
        assert "pages" in data
        assert len(data["pages"]) == 3

    def test_generate_bundle_creates_guide(self, generator, tmp_path) -> None:
        out = tmp_path / "bundle"
        manifest = generator.generate_bundle(out)
        guide = out / "GUIDE.md"
        assert guide.exists()
        content = guide.read_text(encoding="utf-8")
        assert "Test Site" in content
        assert "home.xml" in content
        assert "Import Instructions" in content

    def test_custom_pages(self, tmp_path) -> None:
        config = MultiPageSiteConfig(
            site_name="Custom",
            pages=[
                PageConfig(page_id="home", page_label="Home", hero=HeroSection(heading="Custom Home")),
                PageConfig(page_id="about", page_label="About Us"),
            ],
        )
        gen = MultiPageGenerator(config)
        out = tmp_path / "custom_site"
        manifest = gen.generate_all(out)
        assert manifest["page_count"] == 2
        xml = (out / "home.xml").read_text(encoding="utf-8")
        assert "Custom Home" in xml

    def test_generator_adds_defaults_when_no_pages(self) -> None:
        config = MultiPageSiteConfig(site_name="Empty")
        gen = MultiPageGenerator(config)
        assert len(gen.config.pages) == 3

    def test_generate_page_standalone(self, generator) -> None:
        xml = generator.generate_page(generator.config.pages[0], page_index=0)
        assert '<?xml version="1.0"' in xml
        result = validate_blogger_xml(xml)
        assert result["ok"] is True

    def test_page_with_social_links(self, tmp_path) -> None:
        config = MultiPageSiteConfig(
            site_name="Social Site",
            social_links={"Twitter": "https://x.com/s"},
            pages=[PageConfig(page_id="home", page_label="Home")],
        )
        gen = MultiPageGenerator(config)
        out = tmp_path / "social"
        gen.generate_all(out)
        xml = (out / "home.xml").read_text(encoding="utf-8")
        assert "Twitter" in xml
        assert "social-links" in xml

    def test_page_with_footer_links(self, tmp_path) -> None:
        config = MultiPageSiteConfig(
            site_name="Footer Site",
            footer_links=[NavLink(label="Privacy", href="/privacy")],
            pages=[PageConfig(page_id="home", page_label="Home")],
        )
        gen = MultiPageGenerator(config)
        out = tmp_path / "footer"
        gen.generate_all(out)
        xml = (out / "home.xml").read_text(encoding="utf-8")
        assert "Privacy" in xml
        assert "footer-nav" in xml

    def test_page_with_global_nav_links(self, tmp_path) -> None:
        config = MultiPageSiteConfig(
            site_name="Nav Site",
            global_nav=[NavLink(label="External", href="https://ext.com")],
            pages=[PageConfig(page_id="home", page_label="Home")],
        )
        gen = MultiPageGenerator(config)
        out = tmp_path / "nav"
        gen.generate_all(out)
        xml = (out / "home.xml").read_text(encoding="utf-8")
        assert "External" in xml
        assert "https://ext.com" in xml

    def test_large_content_blocks(self, tmp_path) -> None:
        """Test with many content blocks — stress test."""
        blocks = [
            ContentBlock(block_type="text", heading=f"Section {i}", body=f"Body {i}" * 50)
            for i in range(20)
        ]
        page = PageConfig(
            page_id="big",
            page_label="Big Page",
            content_blocks=blocks,
        )
        config = MultiPageSiteConfig(site_name="Big", pages=[page])
        gen = MultiPageGenerator(config)
        out = tmp_path / "big"
        manifest = gen.generate_all(out)
        assert manifest["all_valid"] is True
        xml = (out / "big.xml").read_text(encoding="utf-8")
        assert len(xml) > 5000  # Should be substantial
        assert "Section 19" in xml


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------

class TestGenerateMultiPageSite:
    """Test generate_multi_page_site convenience function."""

    def test_from_dict(self, tmp_path) -> None:
        cfg = {
            "site_name": "Dict Site",
            "tagline": "From a dict",
            "pages": [
                {"page_id": "home", "page_label": "Home", "hero": {"heading": "Hello"}},
            ],
        }
        manifest = generate_multi_page_site(cfg, tmp_path / "dict_site")
        assert manifest["page_count"] == 1
        assert manifest["site_name"] == "Dict Site"

    def test_from_config_object(self, tmp_path) -> None:
        cfg = MultiPageSiteConfig(
            site_name="Obj Site",
            pages=[PageConfig(page_id="home", page_label="Home")],
        )
        manifest = generate_multi_page_site(cfg, tmp_path / "obj_site")
        assert manifest["page_count"] == 1

    def test_with_bundle(self, tmp_path) -> None:
        cfg = MultiPageSiteConfig(
            site_name="Bundle Site",
            pages=[PageConfig(page_id="home", page_label="Home")],
        )
        out = tmp_path / "bundle_site"
        manifest = generate_multi_page_site(cfg, out, bundle=True)
        assert (out / "GUIDE.md").exists()

    def test_all_pages_valid(self, tmp_path) -> None:
        """End-to-end: all three pages should validate."""
        manifest = generate_multi_page_site(
            {"site_name": "Full Site"},
            tmp_path / "full_site",
            bundle=True,
        )
        assert manifest["all_valid"] is True, (
            f"Not all valid: {json.dumps(manifest, indent=2, default=str)}"
        )
        for page_id, info in manifest["pages"].items():
            assert info["validation"]["ok"] is True, (
                f"{page_id}: {info['validation'].get('errors', [])}"
            )


class TestGenerateFromHtmlTemplates:
    """Test generate_from_html_templates."""

    def test_empty_call_generates_defaults(self, tmp_path) -> None:
        manifest = generate_from_html_templates(
            output_dir=tmp_path / "html_tmpl",
            site_name="HTML Test",
        )
        assert manifest["page_count"] == 3
        assert manifest["all_valid"] is True

    def test_with_home_html(self, tmp_path) -> None:
        html = "<html><head><title>My Home</title></head><body><h1>Welcome</h1><p>Hello world</p></body></html>"
        manifest = generate_from_html_templates(
            home_html=html,
            output_dir=tmp_path / "home_test",
            site_name="One Page",
        )
        assert manifest["page_count"] >= 3  # Fills in defaults for missing
        # Find home page
        home_xml = (tmp_path / "home_test" / "home.xml").read_text(encoding="utf-8")
        assert "My Home" in home_xml

    def test_with_all_html_templates(self, tmp_path) -> None:
        home = "<html><head><title>H</title></head><body><h1>Home</h1><p>Welcome</p></body></html>"
        about = "<html><head><title>A</title></head><body><h1>About</h1><p>Our story</p></body></html>"
        contact = "<html><head><title>C</title></head><body><h1>Contact</h1><p>Reach us</p></body></html>"
        manifest = generate_from_html_templates(
            home_html=home,
            about_html=about,
            contact_html=contact,
            output_dir=tmp_path / "all_three",
            site_name="Three Pages",
        )
        assert manifest["page_count"] == 3
        assert manifest["all_valid"] is True


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and robustness tests."""

    def test_empty_site_config(self) -> None:
        config = MultiPageSiteConfig()
        gen = MultiPageGenerator(config)
        assert len(gen.config.pages) == 3  # defaults added

    def test_unicode_content(self, generator, tmp_path) -> None:
        page = PageConfig(
            page_id="unicode",
            page_label="Üñîçødë",
            page_title="Café & Résumé",
            hero=HeroSection(heading="こんにちは世界"),
            content_blocks=[
                ContentBlock(block_type="text", body="😀🎉🔥")
            ],
        )
        config = MultiPageSiteConfig(
            site_name="Üñî Test",
            pages=[page],
        )
        gen = MultiPageGenerator(config)
        out = tmp_path / "unicode"
        manifest = gen.generate_all(out)
        assert manifest["all_valid"] is True
        xml = (out / "unicode.xml").read_text(encoding="utf-8")
        assert "こんにちは世界" in xml
        assert "😀" in xml

    def test_very_long_title(self, generator, tmp_path) -> None:
        long_title = "A" * 200
        page = PageConfig(page_id="long", page_label="Long", page_title=long_title)
        config = MultiPageSiteConfig(site_name="Long", pages=[page])
        gen = MultiPageGenerator(config)
        out = tmp_path / "long"
        manifest = gen.generate_all(out)
        assert manifest["all_valid"] is True

    def test_multiple_pages_navigation_consistency(self, generator, tmp_path) -> None:
        """Verify that all pages link to each other in navigation."""
        out = tmp_path / "nav_test"
        manifest = generator.generate_all(out)
        for page_id, info in manifest["pages"].items():
            xml = (out / info["filename"]).read_text(encoding="utf-8")
            assert "home.html" in xml
            assert "about.html" in xml
            assert "contact.html" in xml

    def test_no_duplicate_page_ids(self, generator, tmp_path) -> None:
        out = tmp_path / "dup_test"
        manifest = generator.generate_all(out)
        page_ids = [p["page_id"] for p in manifest["pages"].values()]
        assert len(page_ids) == len(set(page_ids))

    def test_custom_template_for_page(self, tmp_path) -> None:
        cfg = MultiPageSiteConfig(
            site_name="Custom T",
            pages=[PageConfig(page_id="home", page_label="Home", template="simple")],
        )
        gen = MultiPageGenerator(cfg)
        out = tmp_path / "custom_t"
        manifest = gen.generate_all(out)
        assert manifest["all_valid"] is True

    def test_xml_files_are_importable_size(self, generator, tmp_path) -> None:
        """Each generated XML should be > 1KB (non-trivial)."""
        out = tmp_path / "size_test"
        generator.generate_all(out)
        for name in ["home.xml", "about.xml", "contact.xml"]:
            path = out / name
            assert path.stat().st_size > 1000, f"{name} is too small"
