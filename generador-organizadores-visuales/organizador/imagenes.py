"""Búsqueda de imágenes referenciales en la web (sin clave de API).

Fuentes de imágenes de licencia libre:
  - Wikimedia Commons  (https://commons.wikimedia.org)
  - Openverse          (https://openverse.org)

Cada imagen se descarga, se reduce y se incrusta en el SVG como data-URI,
para que el organizador funcione sin conexión y se pueda exportar a PNG/PDF.
"""
from __future__ import annotations

import base64
import io
import re
from html import unescape

import requests

UA = {"User-Agent": "GeneradorOrganizadoresVisuales/1.0 (https://github.com; uso educativo)"}


def _sin_html(t: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def buscar_wikimedia(consulta: str, n: int = 4, tiempo: int = 15) -> list[dict]:
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{consulta} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": n * 2,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime", "iiurlwidth": 480,
    }
    r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers=UA, timeout=tiempo)
    r.raise_for_status()
    paginas = (r.json().get("query") or {}).get("pages") or {}
    salida = []
    for p in sorted(paginas.values(), key=lambda x: x.get("index", 0)):
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        meta = info.get("extmetadata") or {}
        salida.append({
            "miniatura": info.get("thumburl") or info.get("url"),
            "titulo": p.get("title", "").replace("File:", "").rsplit(".", 1)[0],
            "autor": _sin_html((meta.get("Artist") or {}).get("value", ""))[:60] or "Wikimedia Commons",
            "licencia": (meta.get("LicenseShortName") or {}).get("value", ""),
            "pagina": info.get("descriptionurl", ""),
            "fuente": "Wikimedia Commons",
        })
        if len(salida) >= n:
            break
    return salida


def buscar_openverse(consulta: str, n: int = 4, tiempo: int = 15) -> list[dict]:
    r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=tiempo,
                     params={"q": consulta, "page_size": n, "mature": "false"})
    r.raise_for_status()
    salida = []
    for it in r.json().get("results", [])[:n]:
        salida.append({
            "miniatura": it.get("thumbnail") or it.get("url"),
            "titulo": it.get("title") or consulta,
            "autor": (it.get("creator") or "Openverse")[:60],
            "licencia": ("CC " + it.get("license", "").upper()) if it.get("license") else "",
            "pagina": it.get("foreign_landing_url") or it.get("url", ""),
            "fuente": "Openverse",
        })
    return salida


def buscar(consulta: str, fuentes=("Wikimedia Commons", "Openverse"), n: int = 3) -> list[dict]:
    resultados: list[dict] = []
    errores = []
    for f in fuentes:
        try:
            if f == "Wikimedia Commons":
                resultados += buscar_wikimedia(consulta, n)
            elif f == "Openverse":
                resultados += buscar_openverse(consulta, n)
        except Exception as ex:  # noqa: BLE001
            errores.append(f"{f}: {ex}")
        if len(resultados) >= n:
            break
    if not resultados and errores:
        raise RuntimeError("; ".join(errores))
    return resultados[:n]


def a_data_uri(datos: bytes, max_lado: int = 520, calidad: int = 82) -> str:
    """Reduce la imagen y la devuelve como data-URI JPEG."""
    from PIL import Image

    img = Image.open(io.BytesIO(datos))
    img = img.convert("RGB")
    img.thumbnail((max_lado, max_lado))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=calidad, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def descargar(url: str, tiempo: int = 20) -> str:
    r = requests.get(url, headers=UA, timeout=tiempo)
    r.raise_for_status()
    return a_data_uri(r.content)


def credito(img: dict) -> str:
    partes = [img.get("titulo", "")[:40], img.get("autor", ""), img.get("licencia", ""), img.get("fuente", "")]
    return ", ".join(p for p in partes if p)
