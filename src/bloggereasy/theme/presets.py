from __future__ import annotations

import difflib
import json
from typing import Any

from bloggereasy.theme.models import PageStructure, structure_dict

# ---------------------------------------------------------------------------
# Preset definitions with rich metadata (tags, notes, audience, complexity)
# ---------------------------------------------------------------------------
PRESETS: dict[str, dict] = {
    "simple": {
        "layout_hint": "auto",
        "dark": False,
        "notes": "Clean universal starting point for any blog",
        "audience": "general",
        "complexity": "low",
    },
    "magazine": {
        "layout_hint": "three-column",
        "dark": False,
        "dense": True,
        "notes": "Three-column news/magazine layout with left rail",
        "audience": "publishers",
        "complexity": "high",
    },
    "dark": {
        "layout_hint": "two-column",
        "dark": True,
        "notes": "Dark mode developer / devops look",
        "audience": "developers",
        "complexity": "medium",
    },
    "from-image": {
        "layout_hint": "two-column",
        "dark": False,
        "notes": "Derive palette from a design image",
        "audience": "designers",
        "complexity": "medium",
    },
    "portfolio": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": False,
        "accent": "#c4a574",
        "notes": "Warm portfolio / showcase accent",
        "audience": "creatives",
        "complexity": "medium",
    },
    "news": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": True,
        "accent": "#b91c1c",
        "notes": "Dense news portal with red accent",
        "audience": "publishers",
        "complexity": "medium",
    },
    "personal": {
        "layout_hint": "single-column",
        "dark": False,
        "dense": False,
        "accent": "#7c3aed",
        "notes": "Personal blog with purple accent",
        "audience": "individuals",
        "complexity": "low",
    },
    "docs": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": True,
        "accent": "#0d9488",
        "notes": "Documentation-style with teal accent",
        "audience": "developers",
        "complexity": "medium",
    },
    "landing": {
        "layout_hint": "single-column",
        "dark": False,
        "dense": False,
        "accent": "#0ea5e9",
        "landing": True,
        "notes": "SaaS / product landing page layout",
        "audience": "marketers",
        "complexity": "high",
    },
    "portfolio_photo": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": False,
        "accent": "#c4a574",
        "notes": "Photography portfolio warm accent",
        "audience": "photographers",
        "complexity": "medium",
    },
    "food_recipe": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": False,
        "accent": "#d97742",
        "notes": "Food blog with orange accent",
        "audience": "creatives",
        "complexity": "low",
    },
    "magazine_news": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": True,
        "accent": "#b91c1c",
        "notes": "News magazine with bold red accent",
        "audience": "publishers",
        "complexity": "medium",
    },
    "corporate_blue": {
        "layout_hint": "two-column",
        "dark": False,
        "dense": False,
        "accent": "#0055aa",
        "notes": "Corporate blue professional style",
        "audience": "business",
        "complexity": "low",
    },
}

# ---------------------------------------------------------------------------
# Categorised tag taxonomy (flat dict for fast lookup, plus curated sets)
# ---------------------------------------------------------------------------
PRESET_TAGS: dict[str, list[str]] = {
    "simple": ["light", "blog", "minimal", "general"],
    "magazine": ["light", "blog", "dense", "magazine", "multi-column"],
    "dark": ["dark", "blog", "dev", "developer"],
    "from-image": ["light", "blog", "creative", "dynamic"],
    "portfolio": ["light", "portfolio", "creative", "showcase"],
    "news": ["light", "blog", "dense", "news", "publisher"],
    "personal": ["light", "blog", "personal", "minimal"],
    "docs": ["light", "docs", "dense", "developer"],
    "landing": ["light", "landing", "marketing", "saas", "single-column"],
    "portfolio_photo": ["light", "portfolio", "creative", "photography"],
    "food_recipe": ["light", "blog", "creative", "food", "lifestyle"],
    "magazine_news": ["light", "blog", "dense", "news", "magazine", "publisher"],
    "corporate_blue": ["light", "blog", "corporate", "professional", "business"],
}

# Curated tag groups for discovery UX
TAG_GROUPS: dict[str, list[str]] = {
    "mode": ["light", "dark"],
    "type": ["blog", "portfolio", "docs", "landing", "news", "magazine"],
    "density": ["minimal", "dense"],
    "audience": [
        "general",
        "developer",
        "creative",
        "publisher",
        "marketing",
        "business",
        "photographer",
    ],
    "layout": ["single-column", "multi-column"],
}

# Inverted index: tag → list of preset names (built lazily)
_tag_index: dict[str, list[str]] | None = None


def _build_tag_index() -> dict[str, list[str]]:
    """Build an inverted index mapping every tag to the preset names that carry it."""
    index: dict[str, list[str]] = {}
    for name, tags in PRESET_TAGS.items():
        for tag in tags:
            index.setdefault(tag, []).append(name)
    return index


def get_tag_index() -> dict[str, list[str]]:
    global _tag_index
    if _tag_index is None:
        _tag_index = _build_tag_index()
    return _tag_index


# ---------------------------------------------------------------------------
# TemplateRegistry: rich query interface over presets
# ---------------------------------------------------------------------------
class TemplateRegistry:
    """Central registry for template presets with tagging, search, and discovery."""

    def __init__(self) -> None:
        self._presets = PRESETS
        self._tags = PRESET_TAGS
        self._tag_index = get_tag_index()

    # ---- basic accessors ---------------------------------------------------

    def list_names(self) -> list[str]:
        return sorted(self._presets.keys())

    def get(self, name: str) -> dict | None:
        return self._presets.get(name)

    def tags_for(self, name: str) -> list[str]:
        return self._tags.get(name, [])

    # ---- filtering ---------------------------------------------------------

    def filter_by_tag(self, tag: str) -> list[str]:
        """Return preset names that carry *exactly* the given tag."""
        tag_lower = tag.lower()
        return sorted(self._tag_index.get(tag_lower, []))

    def filter_by_tags(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        mode: str = "any",
    ) -> list[str]:
        """
        Filter presets by tag inclusion/exclusion.

        *mode*
            ``any`` – preset matches when it has **at least one** included tag.
            ``all`` – preset matches when it has **every** included tag.
        """
        include = [t.lower() for t in (include or [])]
        exclude = [t.lower() for t in (exclude or [])]

        results: list[str] = []
        for name in sorted(self._presets.keys()):
            tags = {t.lower() for t in self._tags.get(name, [])}
            if include:
                if mode == "all":
                    if not all(t in tags for t in include):
                        continue
                else:  # any
                    if not any(t in tags for t in include):
                        continue
            if exclude and any(t in tags for t in exclude):
                continue
            results.append(name)
        return results

    def filter_by_layout(self, layout: str) -> list[str]:
        """Return presets whose layout_hint matches."""
        return sorted(
            name
            for name, preset in self._presets.items()
            if (preset.get("layout_hint") or "") == layout
        )

    def filter_by_dark(self, dark: bool) -> list[str]:
        return sorted(
            name for name, preset in self._presets.items() if preset.get("dark") == dark
        )

    def filter_by_audience(self, audience: str) -> list[str]:
        audience_lower = audience.lower()
        return sorted(
            name
            for name, preset in self._presets.items()
            if (preset.get("audience") or "").lower() == audience_lower
        )

    # ---- search ------------------------------------------------------------

    def search(self, query: str, *, cutoff: float = 0.3, limit: int = 10) -> list[tuple[str, float]]:
        """
        Fuzzy search across preset names, tags, notes, and audience.

        Returns a list of ``(name, score)`` sorted by descending score.
        """
        query_lower = query.lower()
        candidates: list[tuple[str, float]] = []

        for name, preset in self._presets.items():
            score = 0.0

            # Name match (exact → substring → fuzzy)
            if name == query_lower:
                score += 1.0
            elif query_lower in name:
                score += 0.8
            else:
                name_ratio = difflib.SequenceMatcher(None, query_lower, name).ratio()
                score += name_ratio * 0.5

            # Tag match
            tags = [t.lower() for t in self._tags.get(name, [])]
            if query_lower in tags:
                score += 0.7
            for tag in tags:
                if query_lower in tag or tag in query_lower:
                    score += 0.3
                    break

            # Notes / audience substring match
            notes = (preset.get("notes") or "").lower()
            audience = (preset.get("audience") or "").lower()
            if query_lower in notes:
                score += 0.4
            if query_lower in audience:
                score += 0.35

            if score >= cutoff:
                candidates.append((name, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]

    # ---- summary -----------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a structured summary suitable for serialisation."""
        all_tags = sorted({t for tags in self._tags.values() for t in tags})
        return {
            "preset_count": len(self._presets),
            "presets": sorted(self._presets.keys()),
            "tag_count": len(all_tags),
            "all_tags": all_tags,
            "tag_groups": {
                group: tags for group, tags in TAG_GROUPS.items()
            },
            "dark_presets": self.filter_by_dark(True),
            "light_presets": self.filter_by_dark(False),
        }


registry = TemplateRegistry()


# ---------------------------------------------------------------------------
# Preset application (unchanged logic, kept for compatibility)
# ---------------------------------------------------------------------------
def apply_preset(structure: PageStructure | dict, template: str) -> dict:
    preset = PRESETS.get(template, PRESETS["simple"])
    out = structure_dict(structure)
    if preset.get("layout_hint") in {"two-column", "three-column"}:
        out["layout"] = preset["layout_hint"]
        feats = dict(out.get("features") or {})
        feats["sidebar"] = True
        if preset.get("layout_hint") == "three-column":
            feats["magazine_left_rail"] = True
        out["features"] = feats
    if preset.get("dark"):
        out = apply_dark_variant(out)
    if preset.get("accent") and not preset.get("dark"):
        colors = dict(out.get("colors") or {})
        colors["primary"] = preset["accent"]
        out["colors"] = colors
    if preset.get("dense"):
        feats = dict(out.get("features") or {})
        feats["dense"] = True
        out["features"] = feats
    if preset.get("landing"):
        feats = dict(out.get("features") or {})
        feats["landing"] = True
        feats["sidebar"] = False
        out["features"] = feats
        out["layout"] = "single-column"
    out["template"] = template
    return out


def apply_dark_variant(structure: dict) -> dict:
    out = dict(structure)
    colors = dict(out.get("colors") or {})
    colors.update(
        {
            "background": "#0f172a",
            "text": "#e2e8f0",
            "primary": colors.get("primary") or "#38bdf8",
            "secondary": colors.get("secondary") or "#818cf8",
            "surface": "#111827",
            "muted": "#1e293b",
            "border": "#334155",
            "footer": "#020617",
            "footer_text": "#cbd5e1",
        }
    )
    out["colors"] = colors
    features = dict(out.get("features") or {})
    features["dark"] = True
    out["features"] = features
    return out


# ---------------------------------------------------------------------------
# Design token extraction with multi-format output
# ---------------------------------------------------------------------------
def tokens_for_preset(template: str) -> dict:
    """
    Extract comprehensive design tokens (CSS custom properties) from a template preset.

    Returns a structured dict with token blocks (colors, typography, layout, spacing,
    interactive) plus metadata (tags, features, audience).
    """
    if template not in PRESETS:
        available = sorted(PRESETS.keys())
        raise ValueError(
            f"Unknown template '{template}'. Available: {', '.join(available)}"
        )

    preset = PRESETS[template]
    layout = preset.get("layout_hint", "single-column")
    dark = preset.get("dark", False)
    dense = preset.get("dense", False)
    accent = preset.get("accent")

    # Colors
    color_tokens: dict[str, str] = {}
    color_tokens["--color-primary"] = accent or ("#38bdf8" if dark else "#1a73e8")
    color_tokens["--color-secondary"] = "#818cf8" if dark else "#34a853"

    if dark:
        color_tokens["--color-background"] = "#0f172a"
        color_tokens["--color-text"] = "#e2e8f0"
        color_tokens["--color-surface"] = "#111827"
        color_tokens["--color-muted"] = "#1e293b"
        color_tokens["--color-border"] = "#334155"
        color_tokens["--color-footer"] = "#020617"
        color_tokens["--color-footer-text"] = "#cbd5e1"
    else:
        color_tokens["--color-background"] = "#ffffff"
        color_tokens["--color-text"] = "#222222"
        color_tokens["--color-surface"] = "#ffffff"
        color_tokens["--color-muted"] = "#f8fafc"
        color_tokens["--color-border"] = "#e5e7eb"
        color_tokens["--color-footer"] = "#0f172a"
        color_tokens["--color-footer-text"] = "#e2e8f0"

    # Typography
    typography_tokens: dict[str, str] = {
        "--font-body": "system-ui, sans-serif",
        "--font-heading": "system-ui, sans-serif",
        "--font-size-base": "16px",
        "--font-size-h1": "2.4rem",
        "--font-size-small": "0.82rem",
        "--line-height": "1.6",
    }

    # Layout
    layout_tokens: dict[str, str] = {
        "--layout-columns": (
            "220px 1fr 260px"
            if layout == "three-column"
            else "1fr 300px"
            if layout == "two-column"
            else "1fr"
        ),
        "--layout-max-width": "1100px",
        "--layout-sidebar": str(layout in {"two-column", "three-column"}).lower(),
        "--layout-magazine-rail": str(layout == "three-column").lower(),
    }

    # Spacing
    if dense:
        spacing_tokens: dict[str, str] = {
            "--spacing-post-pad": "0.6rem 0.85rem",
            "--spacing-content-pad": "0.5rem",
            "--spacing-gap": "1rem",
            "--spacing-section-gap": "0.6rem",
        }
    else:
        spacing_tokens = {
            "--spacing-post-pad": "1rem 1.25rem",
            "--spacing-content-pad": "1rem",
            "--spacing-gap": "1.5rem",
            "--spacing-section-gap": "1rem",
        }

    spacing_tokens["--spacing-radius"] = "8px"
    spacing_tokens["--spacing-header-pad"] = "1.5rem 1rem"
    spacing_tokens["--spacing-footer-pad"] = "1rem"

    # Interactive (buttons, links)
    interactive_tokens: dict[str, str] = {
        "--button-background": color_tokens["--color-primary"],
        "--button-color": "#ffffff",
        "--button-padding": "0.55rem 0.9rem",
        "--button-radius": "6px",
        "--link-color": color_tokens["--color-primary"],
    }

    all_tokens: dict[str, str] = {}
    all_tokens.update(color_tokens)
    all_tokens.update(typography_tokens)
    all_tokens.update(layout_tokens)
    all_tokens.update(spacing_tokens)
    all_tokens.update(interactive_tokens)

    return {
        "template": template,
        "tags": PRESET_TAGS.get(template, []),
        "audience": preset.get("audience", "general"),
        "dark": dark,
        "dense": dense,
        "layout": layout,
        "features": {
            "sidebar": layout in {"two-column", "three-column"},
            "magazine_left_rail": layout == "three-column",
            "dark": dark,
            "dense": dense,
            "landing": preset.get("landing", False),
        },
        "tokens": all_tokens,
        "token_groups": {
            "colors": color_tokens,
            "typography": typography_tokens,
            "layout": layout_tokens,
            "spacing": spacing_tokens,
            "interactive": interactive_tokens,
        },
    }


def _flatten_tokens(token_dict: dict[str, str], indent: str = "  ") -> str:
    """Render token dict as CSS :root block."""
    lines = [":root {"]
    for key, value in token_dict.items():
        lines.append(f"{indent}{key}: {value};")
    lines.append("}")
    return "\n".join(lines)


def tokens_to_css(template: str, *, minify: bool = False) -> str:
    """
    Export preset tokens as a CSS :root custom-property block.

    Set *minify* to ``True`` for a single-line output.
    """
    data = tokens_for_preset(template)
    tokens = data["tokens"]
    if minify:
        inner = "; ".join(f"{k}: {v}" for k, v in tokens.items())
        return f":root {{ {inner}; }}"
    return _flatten_tokens(tokens)


def tokens_to_json(template: str, *, indent: int = 2) -> str:
    """Export preset tokens as pretty-printed JSON."""
    return json.dumps(tokens_for_preset(template), indent=indent)


def tokens_diff(left: str, right: str) -> dict:
    """
    Compare design tokens between two presets.

    Returns a structured diff with ``added``, ``removed``, ``changed``, ``unchanged``.
    """
    a = tokens_for_preset(left)["tokens"]
    b = tokens_for_preset(right)["tokens"]
    all_keys = sorted(set(a.keys()) | set(b.keys()))

    added: dict[str, str] = {}
    removed: dict[str, str] = {}
    changed: dict[str, dict[str, str]] = {}
    unchanged: dict[str, str] = {}

    for key in all_keys:
        va = a.get(key)
        vb = b.get(key)
        if va is None and vb is not None:
            added[key] = vb
        elif vb is None and va is not None:
            removed[key] = va
        elif va != vb:
            changed[key] = {"from": va, "to": vb}
        else:
            unchanged[key] = va

    return {
        "left": left,
        "right": right,
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "summary": {
            "total": len(all_keys),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": len(unchanged),
        },
    }


def all_tokens_summary() -> dict:
    """Return a summary of token counts across all presets."""
    result: dict[str, dict] = {}
    for name in sorted(PRESETS.keys()):
        data = tokens_for_preset(name)
        result[name] = {
            "token_count": len(data["tokens"]),
            "color_count": len(data["token_groups"]["colors"]),
            "features": data["features"],
            "tags": data["tags"],
        }
    return result
