from __future__ import annotations

from pathlib import Path


def write_theme(xml: str, out_path: Path, *, structure: dict | None = None, preview: bool = False) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")

    if preview:
        from bloggereasy.theme.preview import emit_preview_sidecar
        sidecar = emit_preview_sidecar(out_path, structure=structure)
        if sidecar:
            import logging
            logging.getLogger(__name__).info("preview sidecar written: %s", sidecar)

    return out_path
