"""Responsive preview HTML sidecar for BloggerEasy.

Emits a self-contained preview HTML file alongside generated XML for
local browser verification before publishing.
"""
from __future__ import annotations

from pathlib import Path

PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BloggerEasy Preview — {title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f2f5;
    color: #1a1a1a;
  }}
  .toolbar {{
    background: #1a1a2e;
    color: white;
    padding: 0.75rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }}
  .toolbar h1 {{ font-size: 1rem; font-weight: 600; }}
  .toolbar .badge {{
    background: #6C5CE7;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
  }}
  .toolbar select {{
    padding: 0.3rem 0.6rem;
    border-radius: 4px;
    border: 1px solid #444;
    background: #16213e;
    color: white;
    font-size: 0.85rem;
  }}
  .viewport-toolbar {{
    background: white;
    border-bottom: 1px solid #e0e0e0;
    padding: 0.5rem 1.5rem;
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }}
  .viewport-btn {{
    padding: 0.4rem 0.8rem;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.2s;
  }}
  .viewport-btn:hover {{ background: #f0f0f0; }}
  .viewport-btn.active {{ background: #6C5CE7; color: white; border-color: #6C5CE7; }}
  .viewport-btn .icon {{ margin-right: 0.3rem; }}
  .preview-frame {{
    display: flex;
    justify-content: center;
    padding: 1rem;
  }}
  iframe {{
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    background: white;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    transition: width 0.3s ease;
  }}
  .info-bar {{
    background: white;
    border-top: 1px solid #e0e0e0;
    padding: 0.6rem 1.5rem;
    font-size: 0.8rem;
    color: #666;
    display: flex;
    justify-content: space-between;
  }}
</style>
</head>
<body>
<div class="toolbar">
  <h1>BloggerEasy Preview</h1>
  <span class="badge">{template_name}</span>
  <span style="color:#aaa;font-size:0.85rem;">{page_title}</span>
</div>
<div class="viewport-toolbar">
  <button class="viewport-btn active" onclick="setViewport('100%')">
    <span class="icon">🖥️</span>Desktop
  </button>
  <button class="viewport-btn" onclick="setViewport('768px')">
    <span class="icon">📱</span>Tablet
  </button>
  <button class="viewport-btn" onclick="setViewport('375px')">
    <span class="icon">📱</span>Mobile
  </button>
</div>
<div class="preview-frame">
  <iframe id="preview" src="about:blank" width="100%" height="800" sandbox="allow-same-origin"></iframe>
</div>
<div class="info-bar">
  <span>Generated: {generated_at}</span>
  <span>Template: {template_name} | Valid: {valid}</span>
</div>
<script>
  var pageContent = {page_content_json};
  var frame = document.getElementById('preview');
  frame.srcdoc = pageContent;

  function setViewport(width) {{
    frame.style.width = width;
    document.querySelectorAll('.viewport-btn').forEach(function(btn) {{
      btn.classList.remove('active');
    }});
    event.target.classList.add('active');
  }}
</script>
</body>
</html>"""


def generate_preview_html(
    html_content: str,
    output_path: Path | str,
    *,
    title: str = "Blog Preview",
    template_name: str = "simple",
    page_title: str = "",
    generated_at: str = "",
    valid: str = "Yes",
) -> Path:
    """Generate a responsive preview HTML file alongside XML output.

    Creates a self-contained HTML page with an iframe showing the blog
    content at desktop/tablet/mobile viewport widths.

    Args:
        html_content: The blog HTML content to preview.
        output_path: Where to write the preview file.
        title: Page title for the preview toolbar.
        template_name: Theme preset name for the badge.
        page_title: Blog page title for display.
        generated_at: Timestamp string.
        valid: Validation status string.

    Returns:
        Path to the generated preview file.
    """
    import json as _json
    from datetime import datetime, timezone

    if not generated_at:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    page_content_json = _json.dumps(html_content)

    preview = PREVIEW_TEMPLATE.format(
        title=title,
        template_name=template_name,
        page_title=page_title or title,
        generated_at=generated_at,
        valid=valid,
        page_content_json=page_content_json,
    )

    out = Path(output_path)
    out.write_text(preview, encoding="utf-8")
    return out
