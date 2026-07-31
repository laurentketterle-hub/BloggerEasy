# Multi-Page Blogger Site Generator

BloggerEasy supports generating **multi-page Blogger sites** from a directory of HTML files. Every HTML file becomes a validated Blogger XML theme with appropriate template presets and cross-page navigation.

## Quick Start

```powershell
# Generate a multi-page site from a directory of HTML files
python -c "
from bloggereasy.multi_page import generate_multi_page_site
from bloggereasy.config import SAMPLES_DIR

manifest = generate_multi_page_site(
    SAMPLES_DIR / 'html',
    site_name='My Awesome Blog',
)
print(f'{len(manifest.pages)} pages generated')
print(f'All valid: {manifest.all_valid}')
print(f'Total size: {manifest.total_bytes} bytes')
"
```

## How It Works

1. **Discover**: Scan a directory for `.html` files.
2. **Map**: Each file stem is mapped to a matching template preset:
   - `home.html` / `index.html` → `home` template
   - `about.html` / `about_page.html` / `about_team.html` → `about` template
   - `contact.html` / `contact_page.html` → `contact` template
   - `portfolio.html` → `portfolio` template
   - `news.html` → `news` template
   - Everything else → `simple` template
3. **Generate**: Each HTML file is parsed, coloured, and converted to a Blogger XML theme.
4. **Validate**: Every generated XML is validated for Blogger compatibility.
5. **Manifest**: A `site_manifest.json` is written with per-page stats.

## Template Presets for Multi-Page Sites

| Template | Layout | Accent Color | Best For |
|----------|--------|-------------|----------|
| `home` | Single column | `#4cc9f0` (cyan) | Landing / home page |
| `about` | Two column | `#f72585` (pink) | About / team page |
| `contact` | Two column (dense) | `#4cc9f0` (cyan) | Contact / form page |

## Programmatic API

### Generate from directory

```python
from bloggereasy.multi_page import generate_multi_page_site
from pathlib import Path

manifest = generate_multi_page_site(
    Path("my_html_pages/"),
    output_dir=Path("output/"),
    site_name="My Blog",
    dark=False,
    widgets="default",
)
```

### Generate from in-memory strings

```python
from bloggereasy.multi_page import generate_multi_page_from_strings

pages = {
    "home": "<html>...</html>",
    "about": "<html>...</html>",
    "contact": "<html>...</html>",
}
manifest = generate_multi_page_from_strings(pages, site_name="My Site")
```

### Validate generated XML

```python
from bloggereasy.multi_page import validate_all_xml

report = validate_all_xml(Path("output/"))
print(f"{report['ok']}/{report['total']} valid")
```

## Site Manifest Structure

```json
{
    "site_name": "My Blog",
    "all_valid": true,
    "total_bytes": 45210,
    "page_count": 3,
    "template_summary": {"home": 1, "about": 1, "contact": 1},
    "errors": [],
    "pages": [
        {
            "stem": "home",
            "template": "home",
            "title": "Welcome",
            "valid": true,
            "bytes": 15200,
            "xml": "output/home.xml"
        }
    ]
}
```

## Import Into Blogger

Each generated `.xml` file is a standalone Blogger theme. Import them via:

1. Blogger → Theme → Backup/Restore
2. Upload the `.xml` file
3. Save

For detailed import instructions, see [IMPORT_BLOGGER.md](IMPORT_BLOGGER.md).

## Testing

```powershell
pytest tests/test_multi_page.py -v --tb=short
pytest tests/test_new_templates.py -v --tb=short
```

## Related Documentation

- [README](../README.md) — Main project overview
- [Import Guide](IMPORT_BLOGGER.md) — Blogger import instructions
- [Theme Pack Guide](THEME_PACK.md) — Theme pack creation
