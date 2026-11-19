"""Utilidades mínimas para dibujar SVG con texto ajustado, temas de color e imágenes."""
from __future__ import annotations

import math
from html import escape

FUENTE = "DejaVu Sans, Verdana, Arial, Helvetica, sans-serif"

TEMAS = {
    "Vivo": {"fondo": "#FFFFFF", "texto": "#1F2937", "titulo": "#1E3A8A", "linea": "#64748B",
             "colores": ["#2563EB", "#16A34A", "#EA580C", "#9333EA", "#DC2626", "#0891B2", "#CA8A04", "#DB2777"]},
    "Pastel": {"fondo": "#FFFDF8", "texto": "#374151", "titulo": "#6D5BD0", "linea": "#9CA3AF",
               "colores": ["#7FA7E0", "#7CC6A4", "#F2A97F", "#B79CE0", "#EE8E9A", "#6FC3D1", "#E5C267", "#E59AC4"]},
    "Académico": {"fondo": "#FFFFFF", "texto": "#111827", "titulo": "#0F2A4A", "linea": "#475569",
                  "colores": ["#1F4E79", "#2E7D32", "#8B5E34", "#5B4B8A", "#9E2A2B", "#256D7B", "#7A6C1D", "#6B7280"]},
    "Naturaleza": {"fondo": "#FBFCF7", "texto": "#1F2A1F", "titulo": "#2F5D3A", "linea": "#6B7F6B",
                   "colores": ["#3F7D4E", "#8A6B3D", "#2C7A7B", "#B7791F", "#6B8E23", "#A0522D", "#4A6FA5", "#7C5E9B"]},
    "Oscuro": {"fondo": "#0F172A", "texto": "#E5E7EB", "titulo": "#38BDF8", "linea": "#94A3B8",
               "colores": ["#60A5FA", "#4ADE80", "#FB923C", "#C084FC", "#F87171", "#22D3EE", "#FACC15", "#F472B6"]},
}


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def mezclar(c1: str, c2: str, t: float) -> str:
    """Mezcla c1 hacia c2 en proporción t (0 = c1, 1 = c2)."""
    a, b = _hex(c1), _hex(c2)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def suave(c: str, T: dict, t: float = 0.82) -> str:
    return mezclar(c, T["fondo"], t)


def color(T: dict, i: int) -> str:
    return T["colores"][i % len(T["colores"])]


def texto_sobre(c: str) -> str:
    r, g, b = _hex(c)
    return "#111827" if (0.299 * r + 0.587 * g + 0.114 * b) > 170 else "#FFFFFF"


def tinta(c: str, T: dict) -> str:
    """Color legible para texto de color sobre el fondo del tema."""
    r, g, b = _hex(c)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fondo_claro = sum(_hex(T["fondo"])) > 380
    if fondo_claro and lum > 140:
        return mezclar(c, "#000000", 0.35)
    return c


def ancho(texto: str, fs: float, negrita: bool = False) -> float:
    total = 0.0
    for ch in texto:
        if ch in "il.,;:'|!íì ":
            total += 0.32
        elif ch in "mwMWÑ%@":
            total += 0.9
        elif ch.isupper():
            total += 0.68
        else:
            total += 0.56
    return total * fs * (1.07 if negrita else 1.0)


def envolver(texto: str, max_w: float, fs: float, negrita: bool = False, max_lineas: int = 8) -> list[str]:
    palabras = str(texto).split()
    if not palabras:
        return [""]
    lineas, actual = [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if ancho(prueba, fs, negrita) <= max_w or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = lineas[-1].rstrip(" ,.;") + "…"
    return lineas


class SVG:
    def __init__(self, T: dict, ancho_: float | None = None, alto: float | None = None):
        self.T = T
        self.w, self.h = ancho_, alto
        self.defs: list[str] = []
        self.capas: dict[int, list[str]] = {0: [], 1: [], 2: []}
        self.bbox = [math.inf, math.inf, -math.inf, -math.inf]
        self._marcadores: set[str] = set()
        self._clip = 0

    # --- registro de límites -------------------------------------------------
    def incluir(self, x: float, y: float, w: float = 0, h: float = 0):
        b = self.bbox
        b[0], b[1] = min(b[0], x), min(b[1], y)
        b[2], b[3] = max(b[2], x + w), max(b[3], y + h)

    def add(self, s: str, capa: int = 1):
        self.capas[capa].append(s)

    # --- primitivas ------------------------------------------------------------
    def rect(self, x, y, w, h, fill="none", stroke="none", rx=8, sw=1.5, capa=1, extra=""):
        self.incluir(x, y, w, h)
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}" {extra}/>', capa)

    def circulo(self, cx, cy, r, fill="none", stroke="none", sw=1.5, capa=1, extra=""):
        self.incluir(cx - r, cy - r, 2 * r, 2 * r)
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>', capa)

    def elipse(self, cx, cy, rx, ry, fill="none", stroke="none", sw=1.5, capa=1, extra=""):
        self.incluir(cx - rx, cy - ry, 2 * rx, 2 * ry)
        self.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>', capa)

    def marcador(self, c: str) -> str:
        mid = "f" + c.lstrip("#")
        if mid not in self._marcadores:
            self._marcadores.add(mid)
            self.defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                             f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
        return mid

    def linea(self, x1, y1, x2, y2, stroke=None, sw=1.8, flecha=False, capa=0, guion=None):
        stroke = stroke or self.T["linea"]
        m = f' marker-end="url(#{self.marcador(stroke)})"' if flecha else ""
        d = f' stroke-dasharray="{guion}"' if guion else ""
        self.incluir(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}{m}/>', capa)

    def camino(self, d, stroke=None, sw=1.8, fill="none", flecha=False, capa=0, guion=None, extra=""):
        stroke = stroke or self.T["linea"]
        m = f' marker-end="url(#{self.marcador(stroke)})"' if flecha else ""
        g = f' stroke-dasharray="{guion}"' if guion else ""
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" '
                 f'stroke-linejoin="round"{g}{m} {extra}/>', capa)

    def texto(self, x, y, lineas, fs=14, fill=None, anchor="middle", negrita=False, lh=1.25, capa=2, cursiva=False):
        """Escribe líneas; (x, y) es la línea base de la primera línea."""
        fill = fill or self.T["texto"]
        if isinstance(lineas, str):
            lineas = [lineas]
        peso = ' font-weight="bold"' if negrita else ""
        est = ' font-style="italic"' if cursiva else ""
        tsp = "".join(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else fs * lh:.1f}">{escape(l)}</tspan>' for i, l in enumerate(lineas))
        w = max(ancho(l, fs, negrita) for l in lineas)
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        self.incluir(x0, y - fs, w, fs * lh * len(lineas))
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FUENTE}" font-size="{fs}" fill="{fill}" '
                 f'text-anchor="{anchor}"{peso}{est}>{tsp}</text>', capa)

    def texto_centrado(self, cx, cy, lineas, fs=14, fill=None, negrita=False, lh=1.25, anchor="middle", cursiva=False):
        """Bloque de texto centrado verticalmente en cy."""
        if isinstance(lineas, str):
            lineas = [lineas]
        alto = fs * lh * (len(lineas) - 1)
        self.texto(cx, cy - alto / 2 + fs * 0.36, lineas, fs, fill, anchor, negrita, lh, cursiva=cursiva)

    def imagen(self, x, y, w, h, href, redondo=False, rx=8, capa=1):
        if not href:
            return
        self._clip += 1
        cid = f"clip{self._clip}"
        if redondo:
            forma = f'<circle cx="{x + w / 2:.1f}" cy="{y + h / 2:.1f}" r="{min(w, h) / 2:.1f}"/>'
        else:
            forma = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"/>'
        self.defs.append(f'<clipPath id="{cid}">{forma}</clipPath>')
        self.incluir(x, y, w, h)
        self.add(f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" href="{href}" xlink:href="{href}" '
                 f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>', capa)

    def llave(self, x, y1, y2, w=26, stroke=None, sw=2.2):
        """Llave '{' con la punta en x y los brazos en x + w."""
        r = min(14, (y2 - y1) / 4)
        ym = (y1 + y2) / 2
        xm = x + w / 2
        d = (f"M{x + w:.1f},{y1:.1f} Q{xm:.1f},{y1:.1f} {xm:.1f},{y1 + r:.1f} L{xm:.1f},{ym - r:.1f} "
             f"Q{xm:.1f},{ym:.1f} {x:.1f},{ym:.1f} Q{xm:.1f},{ym:.1f} {xm:.1f},{ym + r:.1f} "
             f"L{xm:.1f},{y2 - r:.1f} Q{xm:.1f},{y2:.1f} {x + w:.1f},{y2:.1f}")
        self.camino(d, stroke=stroke, sw=sw)
        self.incluir(x, y1, w, y2 - y1)

    def etiqueta_enlace(self, cx, cy, texto, fs=12, color_=None):
        """Palabra de enlace (conector lógico) sobre una línea."""
        if not texto:
            return
        c = color_ or self.T["linea"]
        w = ancho(texto, fs, False) + 14
        self.rect(cx - w / 2, cy - fs * 0.85, w, fs * 1.7, fill=self.T["fondo"], stroke=c, rx=fs * 0.85, sw=1, capa=1)
        self.texto(cx, cy + fs * 0.36, texto, fs, fill=c, cursiva=True)

    # --- salida ----------------------------------------------------------------
    def svg(self, margen: float = 30) -> str:
        if self.w and self.h:
            x0, y0, w, h = 0, 0, self.w, self.h
        else:
            b = self.bbox
            if b[0] == math.inf:
                b = [0, 0, 100, 100]
            x0, y0 = b[0] - margen, b[1] - margen
            w, h = b[2] - b[0] + 2 * margen, b[3] - b[1] + 2 * margen
        cuerpo = "".join(self.capas[0] + self.capas[1] + self.capas[2])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{w:.0f}" height="{h:.0f}" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}">'
                f'<defs>{"".join(self.defs)}</defs>'
                f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{self.T["fondo"]}"/>'
                f'{cuerpo}</svg>')


def medir(texto: str, max_w: float, fs: float, negrita=False, pad_x=14, pad_y=10, lh=1.25, max_lineas=8):
    lineas = envolver(texto, max_w - 2 * pad_x, fs, negrita, max_lineas)
    w = max(ancho(l, fs, negrita) for l in lineas) + 2 * pad_x
    h = fs * lh * len(lineas) + 2 * pad_y - fs * (lh - 1)
    return w, h, lineas


def nodo(s: SVG, cx, cy, texto, max_w=200, fs=14, fill="#fff", stroke="#333", color_txt=None, negrita=False,
         forma="rect", ancho_fijo=None, sw=1.8, img=None, img_h=70, guion=None, cursiva=False):
    """Dibuja un nodo centrado en (cx, cy). Devuelve (x, y, w, h)."""
    w, h, lineas = medir(texto, ancho_fijo or max_w, fs, negrita)
    if ancho_fijo:
        w = ancho_fijo
    ih = img_h + 8 if img else 0
    h_total = h + ih
    x, y = cx - w / 2, cy - h_total / 2
    extra = f'stroke-dasharray="{guion}"' if guion else ""
    if forma == "elipse":
        rx, ry = w / 2 * 1.18, h_total / 2 * 1.3
        s.elipse(cx, cy, rx, ry, fill, stroke, sw, extra=extra)
        x, y, w, h_total = cx - rx, cy - ry, 2 * rx, 2 * ry
    elif forma == "pildora":
        s.rect(x, y, w, h_total, fill, stroke, rx=h / 2, sw=sw, extra=extra)
    else:
        s.rect(x, y, w, h_total, fill, stroke, rx=8, sw=sw, extra=extra)
    if img:
        s.imagen(cx - (w - 16) / 2, cy - h_total / 2 + 8, w - 16, img_h, img)
    s.texto_centrado(cx, cy + ih / 2, lineas, fs, color_txt, negrita, cursiva=cursiva)
    return x, y, w, h_total


def tam_nodo(texto, max_w=200, fs=14, negrita=False, ancho_fijo=None, img=False, img_h=70):
    w, h, _ = medir(texto, ancho_fijo or max_w, fs, negrita)
    if ancho_fijo:
        w = ancho_fijo
    return w, h + (img_h + 8 if img else 0)
