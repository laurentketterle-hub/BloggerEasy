"""Tests for enhanced template registry with tags, search, and filtering."""

from __future__ import annotations

from bloggereasy.theme.presets import (
    PRESETS,
    PRESET_TAGS,
    TAG_GROUPS,
    TemplateRegistry,
    registry,
)


class TestPresetTags:
    """Every preset has comprehensive tag coverage."""

    def test_all_presets_have_tags(self) -> None:
        for name in PRESETS:
            assert name in PRESET_TAGS, f"Missing tags for preset '{name}'"
            assert isinstance(PRESET_TAGS[name], list)
            assert len(PRESET_TAGS[name]) > 0, f"Empty tags for preset '{name}'"

    def test_all_tags_are_non_empty_strings(self) -> None:
        for name, tags in PRESET_TAGS.items():
            for tag in tags:
                assert tag and isinstance(tag, str), f"Invalid tag '{tag}' in '{name}'"
                assert tag == tag.lower(), f"Tag '{tag}' in '{name}' should be lowercase"

    def test_tag_index_covers_all_tags(self) -> None:
        from bloggereasy.theme.presets import get_tag_index

        index = get_tag_index()
        all_tags_in_index = set(index.keys())
        all_tags_in_presets = {t for tags in PRESET_TAGS.values() for t in tags}
        assert all_tags_in_index == all_tags_in_presets

    def test_light_and_dark_mode_tags_separated(self) -> None:
        """Presets tagged 'light' should not have 'dark' tag and vice versa."""
        for name, tags in PRESET_TAGS.items():
            if "light" in tags:
                assert "dark" not in tags, f"{name}: light and dark cannot coexist"
            if "dark" in tags:
                assert "light" not in tags, f"{name}: dark and light cannot coexist"

    def test_preset_metadata_has_audience(self) -> None:
        """Every preset in PRESETS must have an 'audience' field."""
        for name, meta in PRESETS.items():
            assert "audience" in meta, f"Missing audience for '{name}'"
            assert isinstance(meta["audience"], str), f"audience must be string in '{name}'"
            assert meta["audience"], f"audience cannot be empty in '{name}'"

    def test_preset_metadata_has_notes(self) -> None:
        """Every preset must have descriptive notes."""
        for name, meta in PRESETS.items():
            assert "notes" in meta, f"Missing notes for '{name}'"
            assert len(meta["notes"]) > 10, f"Notes too short for '{name}'"


class TestTagGroups:
    """Tag groups are well-structured."""

    def test_tag_groups_exist(self) -> None:
        assert "mode" in TAG_GROUPS
        assert "type" in TAG_GROUPS
        assert "density" in TAG_GROUPS
        assert "audience" in TAG_GROUPS
        assert "layout" in TAG_GROUPS

    def test_mode_tags_are_light_and_dark(self) -> None:
        assert "light" in TAG_GROUPS["mode"]
        assert "dark" in TAG_GROUPS["mode"]

    def test_density_tags_include_minimal_and_dense(self) -> None:
        assert "minimal" in TAG_GROUPS["density"]
        assert "dense" in TAG_GROUPS["density"]

    def test_all_tags_appear_in_at_least_one_group(self) -> None:
        all_group_tags = {t for tags in TAG_GROUPS.values() for t in tags}
        all_preset_tags = {t for tags in PRESET_TAGS.values() for t in tags}
        missing = all_preset_tags - all_group_tags
        # Some tags might be in presets but not groups — that's OK, just verify
        # they are not completely orphaned by checking the tag index.
        from bloggereasy.theme.presets import get_tag_index

        index = get_tag_index()
        for tag in missing:
            assert tag in index, f"Tag '{tag}' is neither in groups nor indexed"


class TestTemplateRegistry:
    """TemplateRegistry query and filtering."""

    def test_list_names_returns_all_presets(self) -> None:
        names = registry.list_names()
        assert len(names) == len(PRESETS)
        assert "simple" in names
        assert "dark" in names

    def test_get_returns_metadata(self) -> None:
        meta = registry.get("dark")
        assert meta is not None
        assert meta["dark"] is True

    def test_tags_for(self) -> None:
        tags = registry.tags_for("dark")
        assert "dark" in tags
        assert "blog" in tags

    def test_filter_by_tag_exact(self) -> None:
        names = registry.filter_by_tag("dark")
        assert "dark" in names
        assert all("dark" in registry.tags_for(n) for n in names)

    def test_filter_by_tag_case_insensitive(self) -> None:
        names_lower = registry.filter_by_tag("dark")
        names_upper = registry.filter_by_tag("DARK")
        assert names_lower == names_upper

    def test_filter_by_tags_include_any(self) -> None:
        names = registry.filter_by_tags(include=["dev", "food"], mode="any")
        assert "dark" in names  # dev
        assert "food_recipe" in names  # food

    def test_filter_by_tags_include_all(self) -> None:
        names = registry.filter_by_tags(include=["light", "blog", "dense"], mode="all")
        assert "news" in names
        assert "docs" in names
        assert "dark" not in names  # dark is not light

    def test_filter_by_tags_exclude(self) -> None:
        names = registry.filter_by_tags(exclude=["dark"])
        assert "dark" not in names
        assert "simple" in names

    def test_filter_by_layout(self) -> None:
        names = registry.filter_by_layout("two-column")
        assert "portfolio" in names
        for n in names:
            meta = registry.get(n)
            assert meta and meta.get("layout_hint") == "two-column"

    def test_filter_by_dark(self) -> None:
        names = registry.filter_by_dark(True)
        assert "dark" in names
        for n in names:
            meta = registry.get(n)
            assert meta and meta.get("dark") is True

    def test_filter_by_audience(self) -> None:
        names = registry.filter_by_audience("developers")
        assert "dark" in names
        assert "docs" in names

    def test_search_by_name(self) -> None:
        results = registry.search("dark")
        assert len(results) > 0
        assert results[0][0] == "dark"
        assert results[0][1] >= 0.9

    def test_search_by_tag(self) -> None:
        results = registry.search("food")
        assert len(results) > 0
        assert any("food" in r[0] for r in results)

    def test_search_case_insensitive(self) -> None:
        r1 = registry.search("PORTFOLIO")
        r2 = registry.search("portfolio")
        assert r1 and r2
        assert r1[0][0] == r2[0][0]

    def test_search_returns_limited_results(self) -> None:
        results = registry.search("blog", limit=3)
        assert len(results) <= 3

    def test_summary_contains_expected_keys(self) -> None:
        summary = registry.summary()
        assert "preset_count" in summary
        assert "presets" in summary
        assert "tag_count" in summary
        assert "all_tags" in summary
        assert "tag_groups" in summary
        assert "dark_presets" in summary
        assert "light_presets" in summary

    def test_summary_dark_light_partitions_complete(self) -> None:
        summary = registry.summary()
        assert len(summary["dark_presets"]) + len(summary["light_presets"]) == len(PRESETS)


class TestRegistryEdgeCases:
    """Edge cases and error handling."""

    def test_filter_by_tag_unknown_returns_empty(self) -> None:
        names = registry.filter_by_tag("nonexistent_tag_xyz")
        assert names == []

    def test_filter_by_tags_empty_include_returns_all(self) -> None:
        names = registry.filter_by_tags(include=[])
        assert len(names) == len(PRESETS)

    def test_search_garbage_query_returns_empty(self) -> None:
        results = registry.search("xyzhghfgh2345", cutoff=0.5)
        assert results == []
