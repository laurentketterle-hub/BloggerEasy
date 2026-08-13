# BloggerEasy CLI Reference

`bloggereasy` is a Typer CLI that generates usable Blogger XML themes from HTML, a URL, or images.

## Global commands

- `bloggereasy version` — print the version and the list of built-in templates.
- `bloggereasy samples` — list HTML fixtures under `data/samples/html` with sizes and a title heuristic.
- `bloggereasy stats` — quick inventory: templates, samples count, and demo XML outputs (JSON).

## Subcommands

- `bloggereasy gen ...` — generate themes.
- `bloggereasy parse ...` — parse inputs (fetch a URL, parse an HTML page).
- `bloggereasy templates ...` — work with the built-in templates.

## Template tags & validation

- `--tag <name>` filters templates by category tag (see `PRESET_TAGS` in `src/bloggereasy/theme/presets.py`).
- `--strict` enables strict validation mode (see `src/bloggereasy/theme/validate.py`).
- `tokens` exports CSS design tokens as JSON.

## Programmatic SDK

`bloggereasy.integrations.sdk` exposes:
`generate_from_html`, `generate_from_html_string`, `generate_from_image`, `generate_from_url`.
