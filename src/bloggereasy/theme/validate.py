from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
B_NS = "http://www.google.com/2005/gml/b"
_EXTERNAL_ASSET_RE = re.compile(
    r"<(?P<tag>img|script)\b[^>]*\bsrc\s*=\s*(?P<quote>['\"\"])(?P<url>https?://[^'\"\"]+)(?P=quote)",
    flags=re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Severity levels for validation issues
# ---------------------------------------------------------------------------
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------
def _has_namespace(xml: str, namespace: str) -> bool:
    pattern = rf"xmlns(?::[a-zA-Z0-9_-]+)?\s*=\s*(['\"\"])\b{re.escape(namespace)}\b\1"
    return re.search(pattern, xml, flags=re.IGNORECASE) is not None


def _external_asset_warnings(xml: str) -> list[str]:
    return [
        f"external {match.group('tag').lower()} asset URL: {match.group('url').strip()}"
        for match in _EXTERNAL_ASSET_RE.finditer(xml)
    ]


# ---------------------------------------------------------------------------
# Structured issue type
# ---------------------------------------------------------------------------
def _make_issue(
    message: str,
    severity: str = SEVERITY_ERROR,
    category: str | None = None,
) -> dict[str, str]:
    issue: dict[str, str] = {"message": message, "severity": severity}
    if category:
        issue["category"] = category
    return issue


# ---------------------------------------------------------------------------
# Strict XML schema checks (parsing + required elements)
# ---------------------------------------------------------------------------
def _strict_schema_errors(xml: str) -> list[dict]:
    """Parse the XML and check for required Blogger elements."""
    issues: list[dict] = []
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)

    try:
        root = etree.fromstring(xml.encode("utf-8"), parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        issues.append(
            _make_issue(
                f"strict XML parse failed: {exc}",
                SEVERITY_ERROR,
                "schema",
            )
        )
        return issues

    if root.tag != f"{{{XHTML_NS}}}html":
        issues.append(
            _make_issue(
                "strict root must be XHTML <html>",
                SEVERITY_ERROR,
                "schema",
            )
        )

    skin_nodes = list(root.iter(f"{{{B_NS}}}skin"))
    if not skin_nodes:
        issues.append(
            _make_issue(
                "strict schema requires a <b:skin> element",
                SEVERITY_ERROR,
                "schema",
            )
        )

    sections = list(root.iter(f"{{{B_NS}}}section"))
    if not sections:
        issues.append(
            _make_issue(
                "strict schema requires a <b:section> element",
                SEVERITY_ERROR,
                "schema",
            )
        )

    blog_widgets = [
        node
        for node in root.iter(f"{{{B_NS}}}widget")
        if (node.get("type") or "").strip().lower() == "blog"
    ]
    if not blog_widgets:
        issues.append(
            _make_issue(
                "strict schema requires a Blog widget",
                SEVERITY_ERROR,
                "schema",
            )
        )

    for section in sections:
        if section.find(f".//{{{B_NS}}}widget") is None:
            section_id = section.get("id") or "<unnamed>"
            issues.append(
                _make_issue(
                    f"empty <b:section> is not allowed: {section_id}",
                    SEVERITY_ERROR,
                    "schema",
                )
            )

    # Additional schema checks
    head = root.find(f"{{{XHTML_NS}}}head")
    if head is None:
        issues.append(
            _make_issue("strict: missing <head> element", SEVERITY_ERROR, "structure")
        )
    else:
        title = head.find(f"{{{XHTML_NS}}}title")
        if title is None:
            issues.append(
                _make_issue(
                    "strict: missing <title> element in <head>",
                    SEVERITY_WARNING,
                    "structure",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Content quality checks
# ---------------------------------------------------------------------------
def _content_quality_checks(xml: str) -> list[dict]:
    """Checks for content quality: CDATA, includable blocks, viewport, etc."""
    issues: list[dict] = []

    # CDATA presence
    if "CDATA" not in xml:
        issues.append(
            _make_issue(
                "strict: missing CDATA skin block (CSS not properly wrapped)",
                SEVERITY_ERROR,
                "content",
            )
        )

    # Includable blocks (required for proper widget templates)
    if "<b:includable" not in xml:
        issues.append(
            _make_issue(
                "strict: missing <b:includable> blocks (widget templates incomplete)",
                SEVERITY_ERROR,
                "content",
            )
        )

    # Charset
    if "charset" not in xml.lower():
        issues.append(
            _make_issue(
                "strict: missing charset declaration",
                SEVERITY_ERROR,
                "content",
            )
        )

    # Viewport meta for responsive
    if "viewport" not in xml.lower():
        issues.append(
            _make_issue(
                "strict: no viewport meta tag (responsive breakpoints may fail)",
                SEVERITY_WARNING,
                "content",
            )
        )

    # Open Graph tags for social sharing
    if not re.search(r"<meta\b[^>]*\bog:title\b", xml, flags=re.IGNORECASE):
        issues.append(
            _make_issue(
                "strict: missing og:title meta tag (social sharing preview degraded)",
                SEVERITY_WARNING,
                "content",
            )
        )

    if not re.search(r"<meta\b[^>]*\bog:description\b", xml, flags=re.IGNORECASE):
        issues.append(
            _make_issue(
                "strict: missing og:description meta tag",
                SEVERITY_INFO,
                "content",
            )
        )

    # Section count
    section_count = len(re.findall(r"<b:section\b", xml))
    if section_count < 3:
        issues.append(
            _make_issue(
                f"strict: only {section_count} <b:section> block(s) (layout may be sparse)",
                SEVERITY_WARNING,
                "content",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Size and complexity checks
# ---------------------------------------------------------------------------
def _size_checks(xml: str) -> list[dict]:
    """Checks related to theme size and complexity."""
    issues: list[dict] = []
    xml_bytes = len(xml.encode("utf-8"))

    if xml_bytes < 2000:
        issues.append(
            _make_issue(
                f"strict: theme XML is {xml_bytes} bytes (below 2000 byte floor, likely incomplete)",
                SEVERITY_ERROR,
                "size",
            )
        )
    elif xml_bytes < 4000:
        issues.append(
            _make_issue(
                f"theme XML is {xml_bytes} bytes (on the small side, consider adding content)",
                SEVERITY_WARNING,
                "size",
            )
        )

    if xml_bytes > 100_000:
        issues.append(
            _make_issue(
                f"theme XML is {xml_bytes:,} bytes (very large, may impact import time)",
                SEVERITY_INFO,
                "size",
            )
        )

    # Widget count
    widget_count = len(re.findall(r"<b:widget\b", xml))
    if widget_count < 2:
        issues.append(
            _make_issue(
                f"only {widget_count} widget(s) defined (bare minimum)",
                SEVERITY_WARNING,
                "size",
            )
        )

    # CSS inline content size
    cdata_match = re.search(r"<!\[CDATA\[(.*?)\]\]>", xml, re.DOTALL)
    if cdata_match:
        css_len = len(cdata_match.group(1).strip())
        if css_len < 500:
            issues.append(
                _make_issue(
                    f"skin CSS is only {css_len} chars (limited styling)",
                    SEVERITY_WARNING,
                    "size",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------
def validate_blogger_xml(
    xml: str,
    *,
    strict: bool = False,
    level: str = "standard",
) -> dict[str, Any]:
    """
    Validate a Blogger theme XML document.

    Parameters
    ----------
    xml : str
        The XML document to validate.
    strict : bool
        Enable strict mode with additional schema, content, and size checks.
    level : str
        Validation depth: ``"basic"``, ``"standard"``, or ``"strict"``.
        ``"strict"`` implies *strict* = True plus the most exhaustive checks.

    Returns
    -------
    dict
        A report with keys: ``ok``, ``errors``, ``warnings``, ``infos``,
        ``issues`` (structured), ``bytes``, ``strict``, ``level``,
        ``summary`` (counts by severity).
    """
    structured_issues: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    stripped = xml.strip()
    if not stripped.startswith("<?xml"):
        warnings.append("missing XML declaration")
        structured_issues.append(
            _make_issue("missing XML declaration", SEVERITY_WARNING, "basic")
        )

    if "<html" not in stripped.lower():
        errors.append("missing <html> root element")
        structured_issues.append(
            _make_issue("missing <html> root element", SEVERITY_ERROR, "basic")
        )
        return _build_report(errors, warnings, infos, structured_issues, xml, strict, level)

    # ---- Basic checks ----
    if not _has_namespace(xml, XHTML_NS):
        errors.append("missing XHTML namespace on <html>")
        structured_issues.append(
            _make_issue("missing XHTML namespace on <html>", SEVERITY_ERROR, "basic")
        )

    if not _has_namespace(xml, B_NS):
        errors.append("missing b namespace on <html>")
        structured_issues.append(
            _make_issue("missing b namespace on <html>", SEVERITY_ERROR, "basic")
        )

    if "b:skin" not in xml:
        errors.append("missing <b:skin> theme stylesheet block")
        structured_issues.append(
            _make_issue("missing <b:skin> theme stylesheet block", SEVERITY_ERROR, "basic")
        )

    if "<b:section" not in xml:
        errors.append("missing required <b:section> layout block")
        structured_issues.append(
            _make_issue("missing required <b:section> layout block", SEVERITY_ERROR, "basic")
        )

    if not re.search(r"type\s*=\s*(['\"\"])Blog\1", xml, flags=re.IGNORECASE):
        errors.append("missing Blog widget")
        structured_issues.append(
            _make_issue("missing Blog widget", SEVERITY_ERROR, "basic")
        )

    if not re.search(r"title\s*=\s*(['\"\"]).*Header.*\1", xml, flags=re.IGNORECASE | re.DOTALL):
        warnings.append("no Header widget title found")
        structured_issues.append(
            _make_issue("no Header widget title found", SEVERITY_WARNING, "basic")
        )

    # ---- Standard checks ----
    if level in ("standard", "strict"):
        if len(xml) < 800:
            warnings.append("theme XML is unusually small")
            structured_issues.append(
                _make_issue("theme XML is unusually small", SEVERITY_WARNING, "standard")
            )

        external_issues = _external_asset_warnings(xml)
        warnings.extend(external_issues)
        for issue in external_issues:
            structured_issues.append(_make_issue(issue, SEVERITY_WARNING, "standard"))

    # ---- Strict checks ----
    if strict or level == "strict":
        # Schema checks
        schema_issues = _strict_schema_errors(xml)
        for issue in schema_issues:
            msg = issue["message"]
            sev = issue["severity"]
            structured_issues.append(issue)
            if sev == SEVERITY_ERROR:
                errors.append(msg)
            elif sev == SEVERITY_WARNING:
                warnings.append(msg)
            else:
                infos.append(msg)

        # Content quality checks
        content_issues = _content_quality_checks(xml)
        for issue in content_issues:
            msg = issue["message"]
            sev = issue["severity"]
            structured_issues.append(issue)
            if sev == SEVERITY_ERROR:
                errors.append(msg)
            elif sev == SEVERITY_WARNING:
                warnings.append(msg)
            else:
                infos.append(msg)

        # Size/complexity checks
        size_issues = _size_checks(xml)
        for issue in size_issues:
            msg = issue["message"]
            sev = issue["severity"]
            structured_issues.append(issue)
            if sev == SEVERITY_ERROR:
                errors.append(msg)
            elif sev == SEVERITY_WARNING:
                warnings.append(msg)
            else:
                infos.append(msg)

    return _build_report(errors, warnings, infos, structured_issues, xml, strict, level)


def _build_report(
    errors: list[str],
    warnings: list[str],
    infos: list[str],
    structured: list[dict],
    xml: str,
    strict: bool,
    level: str,
) -> dict[str, Any]:
    """Assemble the final validation report dict."""
    xml_bytes = len(xml.encode("utf-8"))

    # Line count
    line_count = len(xml.splitlines())

    # Character count (excluding whitespace)
    char_count = len(re.sub(r"\s+", "", xml))

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "issues": structured,
        "bytes": xml_bytes,
        "lines": line_count,
        "chars_no_ws": char_count,
        "strict": strict,
        "level": level,
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "infos": len(infos),
            "total_issues": len(errors) + len(warnings) + len(infos),
            "categories": sorted(
                {i.get("category", "basic") for i in structured if i.get("category")}
            ),
        },
    }


# ---------------------------------------------------------------------------
# File-based validation
# ---------------------------------------------------------------------------
def validate_theme_file(path: Path, *, strict: bool = False, level: str = "standard") -> dict:
    xml = path.read_text(encoding="utf-8", errors="replace")
    result = validate_blogger_xml(xml, strict=strict, level=level)
    result["path"] = str(path)
    return result


# ---------------------------------------------------------------------------
# Validation report formatters
# ---------------------------------------------------------------------------
def format_validation_text(result: dict) -> str:
    """Format a validation result as human-readable text."""
    lines: list[str] = []
    status = "PASS" if result["ok"] else "FAIL"
    lines.append(f"Validation: {status}")
    lines.append(f"  Bytes: {result['bytes']:,}")
    lines.append(f"  Lines: {result['lines']}")
    lines.append(f"  Strict: {result.get('strict', False)}")
    lines.append(f"  Level:  {result.get('level', 'standard')}")
    lines.append(f"  Summary: {result.get('summary', {})}")
    lines.append("")

    if result.get("errors"):
        lines.append("Errors:")
        for err in result["errors"]:
            lines.append(f"  ✗ {err}")
        lines.append("")

    if result.get("warnings"):
        lines.append("Warnings:")
        for warn in result["warnings"]:
            lines.append(f"  ⚠ {warn}")
        lines.append("")

    if result.get("infos"):
        lines.append("Info:")
        for info in result["infos"]:
            lines.append(f"  ℹ {info}")

    return "\n".join(lines)


def format_validation_markdown(result: dict) -> str:
    """Format a validation result as a Markdown table."""
    md: list[str] = []
    status = "✅ PASS" if result["ok"] else "❌ FAIL"
    md.append(f"## Validation Report — {status}\n")
    md.append(f"| Metric | Value |")
    md.append(f"|--------|-------|")
    md.append(f"| Bytes | {result['bytes']:,} |")
    md.append(f"| Lines | {result['lines']} |")
    md.append(f"| Strict | {result.get('strict', False)} |")
    md.append(f"| Level | {result.get('level', 'standard')} |")
    summary = result.get("summary", {})
    md.append(f"| Errors | {summary.get('errors', 0)} |")
    md.append(f"| Warnings | {summary.get('warnings', 0)} |")
    md.append(f"| Info | {summary.get('infos', 0)} |")

    if result.get("errors"):
        md.append("\n### Errors\n")
        for err in result["errors"]:
            md.append(f"- ❌ {err}")

    if result.get("warnings"):
        md.append("\n### Warnings\n")
        for warn in result["warnings"]:
            md.append(f"- ⚠️ {warn}")

    if result.get("infos"):
        md.append("\n### Info\n")
        for info in result["infos"]:
            md.append(f"- ℹ️ {info}")

    return "\n".join(md)
