"""Sitemap and SEO generator."""
import xml.etree.ElementTree as ET
from datetime import datetime

def generate_sitemap(pages, site_url, out_path="sitemap.xml"):
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for page in pages:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = site_url + page["path"]
        ET.SubElement(url, "lastmod").text = page.get("date", datetime.now().strftime("%Y-%m-%d"))
        ET.SubElement(url, "changefreq").text = page.get("freq", "weekly")
        ET.SubElement(url, "priority").text = str(page.get("priority", 0.5))
    ET.ElementTree(urlset).write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path

def generate_robots(site_url, out_path="robots.txt"):
    content = f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n"
    with open(out_path, "w") as f: f.write(content)
    return out_path

def generate_meta_tags(page):
    tags = []
    for k,v in page.get("meta", {}).items():
        if k.startswith("og:"): tags.append(f'<meta property="{k}" content="{v}">')
        else: tags.append(f'<meta name="{k}" content="{v}">')
    return "\n".join(tags)
