"""Exportación de los organizadores: SVG, PNG, PDF, HTML y ZIP con todos."""
from __future__ import annotations

import io
import re
import zipfile
from html import escape


def a_png(svg: str, escala: float = 2.0) -> bytes:
    import cairosvg

    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), scale=escala)


def a_pdf(svg: str) -> bytes:
    import cairosvg

    return cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))


def a_html(svg: str, titulo: str) -> str:
    return (f"<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'><title>{escape(titulo)}</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{margin:0;padding:24px;background:#f3f4f6;font-family:sans-serif}"
            "svg{max-width:100%;height:auto;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.12);border-radius:12px}</style>"
            f"</head><body>{svg}</body></html>")


def nombre_archivo(texto: str) -> str:
    t = re.sub(r"[^\w\-]+", "_", texto.strip().lower(), flags=re.UNICODE).strip("_")
    return t[:60] or "organizador"


def zip_todos(svgs: dict[str, str], con_png: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for tipo, svg in svgs.items():
            base = nombre_archivo(tipo)
            z.writestr(f"svg/{base}.svg", svg)
            if con_png:
                try:
                    z.writestr(f"png/{base}.png", a_png(svg, 1.6))
                except Exception:  # noqa: BLE001 - si falla PNG, se mantiene el SVG
                    pass
    return buf.getvalue()
