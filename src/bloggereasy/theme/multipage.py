"""Multi-page static site generator."""
from pathlib import Path
from xml.sax.saxutils import escape as _e
from datetime import datetime
from bloggereasy.theme.models import structure_dict
from bloggereasy.theme.presets import apply_preset

DEFAULT_PAGES = ["home", "about", "contact"]

PAGE_CONTENT = {
    "home": {
        "title": "Home",
        "heading": "Welcome",
        "content": "<p>Welcome to your multi-page site built with <strong>BloggerEasy</strong>.</p><p>Customize this content to introduce your project.</p>"
    },
    "about": {
        "title": "About",
        "heading": "About Us",
        "content": "<p>Learn about our mission and team.</p><p>Replace this placeholder with your own story.</p>"
    },
    "contact": {
        "title": "Contact",
        "heading": "Get in Touch",
        "content": "<p>We would love to hear from you.</p><p><strong>Email:</strong> hello@example.com<br><strong>Phone:</strong> +1 (555) 000-0000</p>"
    },
}
def build_multi_page_site(structure, out_dir, *, template="simple", pages=None, site_name=None, description=None, custom_content=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    structure = apply_preset(structure_dict(structure), template)
    pages = pages or DEFAULT_PAGES
    nm = site_name or structure.get("title", "My Site")
    md = description or structure.get("description", f"{nm} site")
    css = _css(structure)
    nav = _nav(nm, pages)
    ft = _ft(nm)
    built = []
    for slug in pages:
        c = (custom_content or {}).get(slug) or PAGE_CONTENT.get(slug, PAGE_CONTENT["home"])
        html = _page(nm, c.get("title", slug.title()), c.get("heading", ""), c.get("content", "<p>X</p>"), nav, css, ft, md, slug)
        p = out_dir / f"{slug}.html"
        p.write_text(html, encoding="utf-8")
        built.append({"slug": slug, "path": str(p), "title": c.get("title", "")})
    idx = out_dir / "index.html"
    if "home" in pages and not idx.exists():
        idx.write_text(_idx(nm), encoding="utf-8")
        built.append({"slug": "index", "path": str(idx), "title": nm})
    return {"pages": built, "out_dir": str(out_dir), "template": template}
def _idx(site_name):
    return chr(10).join([
        "<!DOCTYPE html>",
        "<html lang=en>",
        "<head>",
        "<meta charset=utf-8>",
        "<meta http-equiv=refresh content=0;url=home.html>",
        f"<title>{_e(site_name)}</title>",
        "</head>",
        f"<body><p>Redirecting to <a href=home.html>home</a>...</p></body>",
        "</html>"
    ])
def _css(s):
    c = s.get("colors") or {}
    f = s.get("fonts") or {}
    def pc(k, d): return _e(str(c.get(k, d)))
    def fc(k, d): return _e(str(f.get(k, d)))
    bf = fc("body", "system-ui, sans-serif")
    hf = fc("heading", bf)
    pr = pc("primary", "#1a73e8")
    sc = pc("secondary", "#34a853")
    bg = pc("background", "#fff")
    tx = pc("text", "#222")
    su = pc("surface", "#fff")
    ft_bg = pc("footer", "#0f172a")
    ft_tx = pc("footer_text", "#e2e8f0")
    return (
        "*{box-sizing:border-box}"
        f"body{{margin:0;font-family:{bf};color:{tx};background:{bg};line-height:1.6}}"
        f"a{{color:{pr};text-decoration:none}}a:hover{{text-decoration:underline}}"
        f".site-header{{background:{pr};color:#fff;padding:1.25rem 1rem}}"
        f".site-header h1{{margin:0;font-family:{hf};font-size:1.8rem}}.site-header h1 a{{color:#fff}}"
        f".site-nav{{background:{sc};padding:.5rem 1rem}}"
        ".site-nav ul{list-style:none;margin:0;padding:0;display:flex;gap:1rem;flex-wrap:wrap}"
        ".site-nav a{color:#fff;padding:.3rem .6rem;border-radius:4px}"
        ".site-nav a.active{background:rgba(255,255,255,.2);font-weight:600}"
        f".main-content{{max-width:960px;margin:0 auto;padding:2rem 1rem;background:{su};min-height:50vh}}"
        f".main-content h2{{font-family:{hf};color:{tx};margin-top:0}}"
        f".site-footer{{margin-top:2rem;padding:1.5rem 1rem;text-align:center;background:{ft_bg};color:{ft_tx};font-size:.9rem}}"
        "@media(max-width:640px){.site-header h1{font-size:1.4rem}.site-nav ul{flex-direction:column;gap:.25rem}.main-content{padding:1rem}}"
    )

def _nav(site_name, pages):
    labels = {"home": "Home", "about": "About", "contact": "Contact"}
    links = []
    for p in pages:
        label = labels.get(p, p.title())
        links.append(f'<li><a href="{_e(p)}.html" class="nav-link" data-page="{_e(p)}">{_e(label)}</a></li>')
    return f"<ul>{''.join(links)}</ul>"

def _ft(site_name):
    y = datetime.now().year
    return f"<p>&copy; {y} {_e(site_name)}. Built with <a href=https://github.com/mergeos-bounties/BloggerEasy>BloggerEasy</a>.</p>"

def _page(site_name, page_title, heading, body, nav_html, css, footer_html, meta_desc, active):
    nav = nav_html.replace(
        "data-page=" + chr(34) + _e(active) + chr(34),
        "class=" + chr(34) + "nav-link active" + chr(34) + " data-page=" + chr(34) + _e(active) + chr(34)
    )
    return chr(10).join([
        "<!DOCTYPE html>",
        "<html lang=en>",
        "<head>",
        "<meta charset=utf-8>",
        "<meta name=viewport content=width=device-width,initial-scale=1>",
        "<meta name=description content=" + chr(39) + _e(meta_desc) + chr(39) + ">",
        "<title>" + _e(page_title) + " | " + _e(site_name) + "</title>",
        "<style>", css, "</style>",
        "</head>",
        "<body>",
        "<header class=site-header><h1><a href=home.html>" + _e(site_name) + "</a></h1></header>",
        "<nav class=site-nav>" + nav + "</nav>",
        "<main class=main-content><h2>" + _e(heading) + "</h2>" + body + "</main>",
        "<footer class=site-footer>" + footer_html + "</footer>",
        "</body>",
        "</html>"
    ])