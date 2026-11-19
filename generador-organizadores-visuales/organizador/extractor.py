"""Lectura de la información de entrada: texto, Word (.docx), PDF, TXT/MD o enlace web.

Todas las funciones devuelven texto "marcado" donde los títulos van precedidos
por '#', '##' o '###' (como Markdown), para que el analizador pueda reconocer
títulos y subtítulos.
"""
from __future__ import annotations

import io
import re

import requests

UA = {"User-Agent": "GeneradorOrganizadoresVisuales/1.0 (uso educativo)"}


def desde_docx(datos: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(datos))
    lineas: list[str] = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        estilo = (p.style.name or "").lower() if p.style is not None else ""
        nivel = 0
        m = re.search(r"(heading|título|titulo|encabezado)\s*(\d)", estilo)
        if m:
            nivel = min(int(m.group(2)) + 1, 3)
        elif estilo in ("title", "título", "titulo", "puesto"):
            nivel = 1
        if nivel:
            lineas.append("#" * nivel + " " + t)
        else:
            lineas.append(t)
    for tabla in doc.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
            if celdas:
                lineas.append(" | ".join(dict.fromkeys(celdas)))
    return "\n\n".join(lineas)


def desde_pdf(datos: bytes) -> str:
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(datos))
    paginas = [(pg.extract_text() or "") for pg in lector.pages]
    texto = "\n".join(paginas)
    # Une líneas cortadas a mitad de oración, conserva saltos de párrafo.
    texto = re.sub(r"-\n(\w)", r"\1", texto)
    texto = re.sub(r"(?<![.:;!?\n])\n(?!\n)", " ", texto)
    return texto


def desde_url(url: str, tiempo: int = 20) -> str:
    from bs4 import BeautifulSoup

    r = requests.get(url, headers=UA, timeout=tiempo)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    sopa = BeautifulSoup(r.text, "html.parser")
    for basura in sopa(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        basura.decompose()
    raiz = sopa.find("article") or sopa.find("main") or sopa.body or sopa
    lineas: list[str] = []
    titulo = sopa.find("h1")
    if titulo is None and sopa.title:
        lineas.append("# " + sopa.title.get_text(strip=True))
    for el in raiz.find_all(["h1", "h2", "h3", "p", "li"]):
        t = el.get_text(" ", strip=True)
        if not t or len(t) < 3:
            continue
        if el.name == "h1":
            lineas.append("# " + t)
        elif el.name == "h2":
            lineas.append("## " + t)
        elif el.name == "h3":
            lineas.append("### " + t)
        elif el.name == "li":
            if len(t) > 15:
                lineas.append("- " + t)
        else:
            if len(t) > 40:
                lineas.append(t)
    return "\n\n".join(lineas)


def desde_archivo(nombre: str, datos: bytes) -> str:
    ext = nombre.lower().rsplit(".", 1)[-1]
    if ext == "docx":
        return desde_docx(datos)
    if ext == "pdf":
        return desde_pdf(datos)
    for cod in ("utf-8", "latin-1"):
        try:
            return datos.decode(cod)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="ignore")
