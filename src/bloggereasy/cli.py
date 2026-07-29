from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from bloggereasy import __version__
from bloggereasy.config import OUT_DIR, SAMPLES_DIR, TEMPLATES_DIR
from bloggereasy.integrations.sdk import (
    generate_from_html,
    generate_from_html_string,
    generate_from_image,
    generate_from_url,
)
from bloggereasy.parse.fetch import fetch_html_url
from bloggereasy.parse.html_page import parse_html_file
from bloggereasy.theme.builder import build_blogger_xml, sanitize_filename
from bloggereasy.theme.presets import (
    PRESETS,
    PRESET_TAGS,
    registry,
    tokens_diff,
    tokens_for_preset,
    tokens_to_css,
    tokens_to_json,
)
from bloggereasy.theme.validate import (
    format_validation_text,
    format_validation_markdown,
    validate_theme_file,
)

app = typer.Typer(
    help="BloggerEasy — generate usable Blogger XML themes from HTML, URL, or images.",
    no_args_is_help=True,
)
gen_app = typer.Typer(help="Generate themes")
parse_app = typer.Typer(help="Parse inputs")
templates_app = typer.Typer(help="Built-in templates")
app.add_typer(gen_app, name="gen")
app.add_typer(parse_app, name="parse")
app.add_typer(templates_app, name="templates")
console = Console()


@app.command("version")
def version_cmd() -> None:
    console.print(f"BloggerEasy {__version__}")
    console.print(f"Templates: {', '.join(PRESETS)}")


@app.command("samples")
def samples_cmd() -> None:
    """List HTML fixtures under data/samples/html with sizes (fixture inventory)."""
    html_dir = SAMPLES_DIR / "html"
    files = sorted(html_dir.glob("*.html")) if html_dir.is_dir() else []
    table = Table(title=f"HTML samples ({len(files)})")
    table.add_column("File")
    table.add_column("Bytes", justify="right")
    table.add_column("Title (heuristic)")
    for path in files:
        title = path.stem.replace("_", " ")
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:800]
            if "<title>" in head and "</title>" in head:
                title = head.split("<title>", 1)[1].split("</title>", 1)[0].strip()[:48]
        except OSError:
            pass
        table.add_row(path.name, str(path.stat().st_size), title)
    console.print(table)
    console.print(f"[dim]dir[/dim] {html_dir}")


@app.command("stats")
def stats_cmd() -> None:
    """Quick inventory: templates, samples, last demo outputs."""
    html_n = (
        len(list((SAMPLES_DIR / "html").glob("*.html"))) if (SAMPLES_DIR / "html").is_dir() else 0
    )
    demo_n = len(list((OUT_DIR / "demo").glob("*.xml"))) if (OUT_DIR / "demo").is_dir() else 0
    console.print_json(
        data={
            "version": __version__,
            "templates": list(PRESETS.keys()),
            "html_samples": html_n,
            "demo_xml_outputs": demo_n,
            "samples_dir": str(SAMPLES_DIR / "html"),
            "out_dir": str(OUT_DIR),
        }
    )


@app.command("validate-samples")
def validate_samples_cmd() -> None:
    """Generate + validate every HTML fixture (CI-friendly fixture gate)."""
    html_dir = SAMPLES_DIR / "html"
    samples = sorted(html_dir.glob("*.html")) if html_dir.is_dir() else []
    if not samples:
        console.print("[red]No HTML samples[/red]")
        raise typer.Exit(1)
    root = OUT_DIR / "validate_samples"
    root.mkdir(parents=True, exist_ok=True)
    ok_n = 0
    table = Table(title="Validate samples")
    table.add_column("Sample")
    table.add_column("OK")
    table.add_column("Errors")
    for path in samples:
        out = root / f"{path.stem}.xml"
        result = generate_from_html(path, out, template="simple")
        ok = bool(result.get("validation", {}).get("ok"))
        errs = result.get("validation", {}).get("errors") or []
        if ok:
            ok_n += 1
        table.add_row(path.name, "yes" if ok else "no", str(len(errs)))
    console.print(table)
    console.print(f"[green]{ok_n}/{len(samples)} ok[/green] → {root}")
    if ok_n < len(samples):
        raise typer.Exit(1)


@app.command("demo")
def demo_cmd(
    out_dir: Path = typer.Option(None, "--out-dir", "-o"),
) -> None:
    """Generate themes for all bundled HTML samples (runnable smoke demo)."""
    root = out_dir or (OUT_DIR / "demo")
    root.mkdir(parents=True, exist_ok=True)
    samples = (
        sorted((SAMPLES_DIR / "html").glob("*.html")) if (SAMPLES_DIR / "html").exists() else []
    )
    if not samples:
        console.print("[red]No samples under data/samples/html[/red]")
        raise typer.Exit(1)
    table = Table(title="Demo generations")
    table.add_column("Sample")
    table.add_column("Output")
    table.add_column("OK")
    template_for = {
        "portfolio.html": "portfolio",
        "news_portal.html": "news",
        "dark_dev.html": "dark",
    }
    for path in samples:
        out = root / f"{path.stem}.xml"
        tmpl = template_for.get(path.name, "simple")
        result = generate_from_html(path, out, template=tmpl)
        ok = "yes" if result["validation"]["ok"] else "no"
        table.add_row(path.name, str(out), ok)
    console.print(table)
    console.print(f"[green]Demo complete[/green] → {root}")
    console.print("Import any XML: Blogger → Theme → Backup/Restore → Upload")


@templates_app.command("list")
def templates_list(
    tag: str | None = typer.Option(
        None,
        "--tag",
        "-t",
        help="Filter templates by tag/category (e.g. light, dark, blog, portfolio, creative).",
    ),
    layout: str | None = typer.Option(
        None,
        "--layout",
        "-l",
        help="Filter by layout: single-column, two-column, three-column, auto.",
    ),
    dark: bool | None = typer.Option(
        None,
        "--dark/--light",
        help="Filter by dark/light mode.",
    ),
    audience: str | None = typer.Option(
        None,
        "--audience",
        "-a",
        help="Filter by target audience (e.g. developers, publishers, creatives).",
    ),
    search: str | None = typer.Option(
        None,
        "--search",
        "-s",
        help="Fuzzy search across preset names, tags, and notes.",
    ),
) -> None:
    """List built-in templates with optional tag, layout, dark, audience, and search filters."""
    names = registry.list_names()

    # Apply search first (returns scored results)
    if search:
        scored = registry.search(search)
        if not scored:
            console.print(f"[yellow]No templates match '{search}'[/yellow]")
            return
        names = [name for name, _ in scored]
        suffix = f" (search: {search})"
    elif tag or layout or dark is not None or audience:
        names = registry.filter_by_tags(
            include=[tag] if tag else None,
            mode="any",
        )
        if layout:
            names = [n for n in names if n in registry.filter_by_layout(layout)]
        if dark is not None:
            names = [n for n in names if n in registry.filter_by_dark(dark)]
        if audience:
            names = [n for n in names if n in registry.filter_by_audience(audience)]
        parts = []
        if tag:
            parts.append(f"tag: {tag}")
        if layout:
            parts.append(f"layout: {layout}")
        if dark is not None:
            parts.append(f"mode: {'dark' if dark else 'light'}")
        if audience:
            parts.append(f"audience: {audience}")
        suffix = f" ({', '.join(parts)})"
    else:
        suffix = ""

    table = Table(title=f"Templates ({len(names)}){suffix}")
    table.add_column("Name")
    table.add_column("Layout")
    table.add_column("Mode")
    table.add_column("Tags")
    table.add_column("Audience")
    table.add_column("Notes")

    for name in names:
        meta = registry.get(name) or {}
        tags = registry.tags_for(name)
        layout_val = meta.get("layout_hint", "single-column")
        mode_val = "🌙 dark" if meta.get("dark") else "☀ light"
        audience_val = meta.get("audience", "general")
        notes = meta.get("notes", "")[:60]

        table.add_row(
            name,
            layout_val,
            mode_val,
            ", ".join(tags[:4]),
            audience_val,
            notes,
        )

    if not names:
        console.print("[yellow]No templates match the given filters[/yellow]")
        return

    console.print(table)

    if TEMPLATES_DIR.exists():
        custom = sorted(TEMPLATES_DIR.glob("*.xml"))
        if custom:
            console.print(f"\n[dim]Custom templates ({len(custom)}): {', '.join(p.stem for p in custom)}[/dim]")


@gen_app.callback(invoke_without_command=True)
def gen_shortcut(
    ctx: typer.Context,
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Generate from the bundled sample for a template, for example magazine.",
    ),
    out: Path | None = typer.Option(None, "--out", "-o"),
    widgets: str = typer.Option(
        "default", "--widgets", help="Sidebar widgets: default, minimal, full."
    ),
    dark: bool = typer.Option(False, "--dark", help="Force dark skin colors."),
) -> None:
    """Generate an XML theme from a bundled sample when no gen subcommand is used."""
    if ctx.invoked_subcommand is not None:
        return
    if template is None and out is None and widgets == "default" and not dark:
        console.print(ctx.get_help())
        raise typer.Exit()

    template_name = template or "simple"
    _validate_widgets(widgets)
    input_path = _sample_for_template(template_name)
    out_path = out or (OUT_DIR / f"{sanitize_filename(template_name)}.xml")
    result = generate_from_html(
        input_path, out_path, template=template_name, widgets=widgets, dark=dark
    )
    console.print(
        f"[green]Wrote[/green] {result['output']} ({result['bytes']} bytes) from {input_path.name}"
    )
    console.print_json(
        data={
            "template": template_name,
            "sample": str(input_path),
            "title": result["structure"]["title"],
            "layout": result["structure"]["layout"],
            "validation": result["validation"],
            "import_hint": result["import_hint"],
        }
    )


@parse_app.command("html")
def parse_html(
    input: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
) -> None:
    console.print_json(data=parse_html_file(input))


@gen_app.command("html")
def gen_html(
    input: Path | None = typer.Option(None, "--input", "-i", exists=True, dir_okay=False),
    url: str | None = typer.Option(
        None, "--url", help="Fetch a public HTML page and generate from it."
    ),
    timeout: float = typer.Option(15.0, "--timeout", min=1.0, help="URL fetch timeout in seconds."),
    out: Path | None = typer.Option(None, "--out", "-o"),
    template: str = typer.Option("simple", "--template", "-t"),
    widgets: str = typer.Option(
        "default", "--widgets", help="Sidebar widgets: default, minimal, full."
    ),
    dark: bool = typer.Option(False, "--dark", help="Force dark skin colors."),
) -> None:
    _validate_widgets(widgets)
    if (input is None) == (url is None):
        console.print("[red]Provide exactly one of --input or --url[/red]")
        raise typer.Exit(1)

    if url is not None:
        out_path = out or (OUT_DIR / "from_url.xml")
        try:
            html = fetch_html_url(url, timeout=timeout)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
        result = generate_from_html_string(
            html, out_path, template=template, widgets=widgets, dark=dark
        )
        result["url"] = url
    else:
        assert input is not None
        out_path = out or (OUT_DIR / f"{sanitize_filename(input.stem)}.xml")
        result = generate_from_html(input, out_path, template=template, widgets=widgets, dark=dark)
    console.print(f"[green]Wrote[/green] {result['output']} ({result['bytes']} bytes)")
    console.print_json(
        data={
            "title": result["structure"]["title"],
            "layout": result["structure"]["layout"],
            "validation": result["validation"],
            "import_hint": result["import_hint"],
        }
    )


@gen_app.command("url")
def gen_url(
    url: str = typer.Option(..., "--url", "-u"),
    out: Path | None = typer.Option(None, "--out", "-o"),
    template: str = typer.Option("simple", "--template", "-t"),
    widgets: str = typer.Option(
        "default", "--widgets", help="Sidebar widgets: default, minimal, full."
    ),
    dark: bool = typer.Option(False, "--dark", help="Force dark skin colors."),
) -> None:
    out_path = out or (OUT_DIR / "from_url.xml")
    _validate_widgets(widgets)
    try:
        result = generate_from_url(
            url,
            out_path,
            template=template,
            cache_dir=OUT_DIR,
            widgets=widgets,
            dark=dark,
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Wrote[/green] {result['output']}")
    console.print_json(
        data={"title": result["structure"]["title"], "validation": result["validation"]}
    )


@gen_app.command("image")
def gen_image(
    input: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
    out: Path | None = typer.Option(None, "--out", "-o"),
    title: str = typer.Option("My Blog", "--title"),
    template: str = typer.Option("from-image", "--template", "-t"),
    widgets: str = typer.Option(
        "default", "--widgets", help="Sidebar widgets: default, minimal, full."
    ),
    dark: bool = typer.Option(False, "--dark", help="Force dark skin colors."),
) -> None:
    out_path = out or (OUT_DIR / f"{sanitize_filename(input.stem)}-image.xml")
    _validate_widgets(widgets)
    result = generate_from_image(
        input, out_path, title=title, template=template, widgets=widgets, dark=dark
    )
    console.print(f"[green]Wrote[/green] {result['output']} ({result['bytes']} bytes)")
    console.print_json(
        data={
            "title": result["structure"]["title"],
            "colors": result["structure"]["colors"],
            "validation": result["validation"],
        }
    )


@gen_app.command("preview-css")
def preview_css(
    input: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
) -> None:
    xml = build_blogger_xml(parse_html_file(input))
    start = xml.find("<![CDATA[")
    end = xml.find("]]>", start)
    if start >= 0 and end > start:
        console.print(xml[start + 9 : end].strip())
    else:
        console.print("[yellow]No skin CDATA found[/yellow]")


def _validate_widgets(widgets: str) -> None:
    if widgets not in {"default", "minimal", "full"}:
        console.print("[red]--widgets must be one of: default, minimal, full[/red]")
        raise typer.Exit(1)


def _sample_for_template(template: str) -> Path:
    sample_map = {
        "dark": "dark_dev.html",
        "docs": "docs_blog.html",
        "food_recipe": "food_recipe.html",
        "from-image": "portfolio.html",
        "magazine": "magazine.html",
        "magazine_news": "magazine_news.html",
        "landing": "landing_saas.html",
        "news": "news_portal.html",
        "personal": "minimal_blog.html",
        "portfolio": "portfolio.html",
        "portfolio_photo": "portfolio_photo.html",
        "simple": "minimal_blog.html",
    }
    if template not in PRESETS:
        console.print(
            f"[red]Unknown template '{template}'. Run `bloggereasy templates list`.[/red]"
        )
        raise typer.Exit(1)
    path = SAMPLES_DIR / "html" / sample_map.get(template, "minimal_blog.html")
    if not path.is_file():
        console.print(f"[red]Bundled sample not found for template '{template}': {path}[/red]")
        raise typer.Exit(1)
    return path


@gen_app.command("preview-html")
def preview_html_cmd(
    input: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
    out: Path | None = typer.Option(None, "--out", "-o"),
    template: str = typer.Option("simple", "--template", "-t"),
) -> None:
    """Write a static HTML mock of the theme structure (open in any browser)."""
    from bloggereasy.config import OUT_DIR
    from bloggereasy.theme.presets import apply_preset
    from bloggereasy.theme.preview import write_preview_html

    structure = apply_preset(parse_html_file(input), template)
    path = out or (OUT_DIR / f"{input.stem}-preview.html")
    write_preview_html(structure, path)
    console.print(f"[green]Preview[/green] {path}")


@gen_app.command("multi")
def gen_multi(
    input: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False),
    out_dir: Path | None = typer.Option(None, "--out-dir", "-o"),
    template: str = typer.Option("simple", "--template", "-t"),
) -> None:
    """Generate coordinated multi-page theme set (home + about + contact)."""
    from bloggereasy.config import OUT_DIR
    from bloggereasy.export.writer import write_theme, write_preview_html
    from bloggereasy.theme.builder import build_blogger_xml
    from bloggereasy.theme.presets import apply_preset
    from bloggereasy.parse.html_page import parse_html_file
    from bloggereasy.theme.validate import validate_theme_file

    base = out_dir or (OUT_DIR / "multi" / sanitize_filename(input.stem or "site"))
    base.mkdir(parents=True, exist_ok=True)
    structure = apply_preset(parse_html_file(input), template)

    pages = {
        "home": {"title": structure.get("title", "Home"), "description": structure.get("description", "Welcome")},
        "about": {"title": "About", "description": "About this blog"},
        "contact": {"title": "Contact", "description": "Get in touch"},
    }

    results = {}
    for slug, overrides in pages.items():
        page_structure = {**structure, **overrides}
        xml = build_blogger_xml(page_structure, template_name=template)
        xml_path = base / f"{slug}.xml"
        write_theme(xml, xml_path)
        html_path = write_preview_html(xml, xml_path, title=overrides["title"])
        validation = validate_theme_file(xml_path)
        results[slug] = {"xml": str(xml_path), "preview": str(html_path), "valid": validation["valid"]}

    console.print(f"[green]Multi-page set[/green] → {base}")
    for slug, info in results.items():
        status = "✅" if info["valid"] else "❌"
        console.print(f"  {status} {slug}: {info['xml']}")
    console.print_json(data={"pages": results})


@app.command("product")
def product_cmd(
    source_ref: str = typer.Argument(
        ..., help="Local HTML/image path or URL, depending on --source."
    ),
    source: str = typer.Option("html", "--source", "-s", help="Input mode: html | url | image."),
    out_dir: Path | None = typer.Option(None, "--out-dir", "-o", help="Bundle output directory."),
    template: str = typer.Option("simple", "--template", "-t"),
    title: str = typer.Option("My Blog", "--title", help="Title used for image mode."),
) -> None:
    """One command: input → importable theme + guide + preview + evidence bundle."""
    from bloggereasy.integrations.bundle import generate_bundle

    target = out_dir or (OUT_DIR / "product" / sanitize_filename(Path(source_ref).stem or "theme"))
    try:
        manifest = generate_bundle(
            source_ref,
            target,
            source=source,
            template=template,
            title=title,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]Bundle ready[/green] → {target}")
    table = Table(title="Product bundle")
    table.add_column("File")
    table.add_column("Path")
    for name, path in manifest["files"].items():
        table.add_row(name, str(path))
    console.print(table)
    console.print_json(
        data={
            "title": manifest["title"],
            "template": manifest["template"],
            "validation": manifest["validation"],
            "import_hint": manifest["import_hint"],
        }
    )
    if not manifest["validation"]["ok"]:
        raise typer.Exit(1)


@app.command("validate")
def validate_cmd(
    file: Path | None = typer.Option(None, "--file", "-f", exists=True, dir_okay=False),
    directory: Path | None = typer.Option(None, "--dir", "-d", exists=True, file_okay=False),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Require parseable Blogger XML and reject sections without widgets.",
    ),
) -> None:
    """Validate one theme XML or batch-validate a directory of themes."""
    if directory is not None:
        from bloggereasy.theme.batch import validate_theme_dir

        report = validate_theme_dir(directory, strict=strict)
        console.print_json(data=report)
        if report["fail"]:
            raise typer.Exit(1)
        return
    if file is None:
        console.print("[red]Provide --file or --dir[/red]")
        raise typer.Exit(1)
    result = validate_theme_file(file, strict=strict)
    console.print_json(data=result)
    if not result["ok"]:
        raise typer.Exit(1)


@app.command("gui")
def gui_cmd() -> None:
    """Launch Qt desktop app: URL / image → Blogger XML (pip install -e '.[gui]')."""
    from bloggereasy.gui.app import main as gui_main

    raise SystemExit(gui_main())


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port", min=1, max=65535),
) -> None:
    """Run FastAPI server (requires: pip install -e '.[api]')."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print('[red]Install API extra:[/red] pip install -e ".[api]"')
        raise typer.Exit(1) from exc
    console.print(f"Serving http://{host}:{port}/health")
    uvicorn.run("bloggereasy.api.app:app", host=host, port=port, log_level="info")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query for templates."),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results."),
) -> None:
    """Fuzzy search templates by name, tag, notes, or audience."""
    results = registry.search(query, limit=limit)
    if not results:
        console.print(f"[yellow]No templates match '{query}'[/yellow]")
        return
    table = Table(title=f"Search: '{query}' ({len(results)} results)")
    table.add_column("Name")
    table.add_column("Score", justify="right")
    table.add_column("Tags")
    table.add_column("Notes")
    for name, score in results:
        tags = ", ".join(registry.tags_for(name)[:3])
        notes = (registry.get(name) or {}).get("notes", "")[:60]
        score_str = f"{score:.2f}"
        score_style = (
            f"[green]{score_str}[/green]"
            if score > 0.7
            else f"[yellow]{score_str}[/yellow]"
            if score > 0.4
            else score_str
        )
        table.add_row(name, score_style, tags, notes)
    console.print(table)


@templates_app.command("tags")
def templates_tags() -> None:
    """List all available tags and tag groups."""
    summary = registry.summary()
    console.print(f"[bold]Tags ({summary['tag_count']}):[/bold] {', '.join(summary['all_tags'])}")
    console.print()
    for group, tags in summary["tag_groups"].items():
        console.print(f"[bold]{group}:[/bold] {', '.join(tags)}")


@templates_app.command("summary")
def templates_summary() -> None:
    """Print a JSON summary of all presets with counts and tag groups."""
    console.print_json(data=registry.summary())


@app.command("tokens")
def tokens_cmd(
    template: str = typer.Option(
        "simple", "--template", "-t", help="Template preset to extract tokens from."
    ),
    out: Path | None = typer.Option(None, "--out", "-o", help="Write JSON file instead of printing."),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json (structured dict), css (:root block), flat (flat token list).",
    ),
) -> None:
    """Export design tokens (CSS custom properties) from a template preset."""
    if template not in PRESETS:
        console.print(
            f"[red]Unknown template '{template}'. Run `bloggereasy templates list`.[/red]"
        )
        raise typer.Exit(1)

    if fmt == "css":
        output = tokens_to_css(template)
    elif fmt == "flat":
        data = tokens_for_preset(template)
        output = json.dumps(data["tokens"], indent=2)
    else:
        output = tokens_to_json(template)

    if out is not None:
        out.write_text(output, encoding="utf-8")
        console.print(f"[green]Tokens written[/green] → {out}")
        if fmt == "css":
            console.print("[dim]Paste the :root block into a stylesheet or Custom CSS field.[/dim]")
    else:
        if fmt == "css":
            console.print(output)
        else:
            console.print_json(data=json.loads(output) if fmt == "json" else json.loads(output))


@app.command("tokens-diff")
def tokens_diff_cmd(
    left: str = typer.Option(..., "--left", "-a", help="First template name."),
    right: str = typer.Option(..., "--right", "-b", help="Second template name."),
    out: Path | None = typer.Option(None, "--out", "-o", help="Write JSON diff to file."),
) -> None:
    """Show design token differences between two template presets."""
    for name in (left, right):
        if name not in PRESETS:
            console.print(
                f"[red]Unknown template '{name}'. Run `bloggereasy templates list`.[/red]"
            )
            raise typer.Exit(1)

    diff = tokens_diff(left, right)
    output = json.dumps(diff, indent=2)

    if out is not None:
        out.write_text(output, encoding="utf-8")
        console.print(f"[green]Diff written[/green] → {out}")
    else:
        summary = diff["summary"]
        console.print(f"[bold]Token diff: {left} → {right}[/bold]")
        console.print(
            f"Total: {summary['total']} | "
            f"[green]+{summary['added']} added[/green] | "
            f"[red]-{summary['removed']} removed[/red] | "
            f"[yellow]~{summary['changed']} changed[/yellow] | "
            f"{summary['unchanged']} unchanged"
        )
        if diff["changed"]:
            console.print("\n[bold]Changed tokens:[/bold]")
            for key, change in sorted(diff["changed"].items()):
                console.print(f"  {key}: {change['from']} → {change['to']}")
        if diff["added"]:
            console.print(f"\n[bold]Added ({len(diff['added'])}):[/bold]")
            for key in sorted(diff["added"]):
                console.print(f"  + {key}: {diff['added'][key]}")
        if diff["removed"]:
            console.print(f"\n[bold]Removed ({len(diff['removed'])}):[/bold]")
            for key in sorted(diff["removed"]):
                console.print(f"  - {key}: {diff['removed'][key]}")


@templates_app.command("info")
def templates_info(
    name: str = typer.Argument(..., help="Template preset name."),
) -> None:
    """Show detailed metadata and tokens for a single template preset."""
    if name not in PRESETS:
        console.print(f"[red]Unknown template '{name}'.[/red]")
        raise typer.Exit(1)

    meta = registry.get(name) or {}
    tags = registry.tags_for(name)
    data = tokens_for_preset(name)

    console.print(f"\n[bold]Template: {name}[/bold]")
    console.print(f"  Layout:   {meta.get('layout_hint', 'single-column')}")
    console.print(f"  Mode:     {'dark' if meta.get('dark') else 'light'}")
    console.print(f"  Dense:    {meta.get('dense', False)}")
    console.print(f"  Audience: {meta.get('audience', 'general')}")
    console.print(f"  Tags:     {', '.join(tags)}")
    console.print(f"  Notes:    {meta.get('notes', '')}")
    console.print(f"  Features: {json.dumps(data['features'])}")
    console.print(f"\n[bold]Design Tokens ({len(data['tokens'])}):[/bold]")
    for key, value in sorted(data["tokens"].items()):
        console.print(f"  {key}: {value}")


if __name__ == "__main__":
    app()
