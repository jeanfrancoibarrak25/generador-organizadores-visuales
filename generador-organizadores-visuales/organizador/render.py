"""Renderizadores de los 16 organizadores visuales (salida SVG)."""
from __future__ import annotations

import math

from .estructura import etiqueta
from .svgkit import (SVG, TEMAS, ancho, color, envolver, medir, nodo, suave, tam_nodo, texto_sobre, tinta)

# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------


def _ideas(s: dict, secundarias: bool) -> list[tuple[str, bool]]:
    out = [(i, False) for i in s["ideas_principales"]]
    if secundarias:
        out += [(i, True) for i in s["ideas_secundarias"]]
    return out


def _titulo_superior(s: SVG, e: dict, cx: float, y: float, fs: int = 26) -> float:
    """Título del organizador centrado arriba. Devuelve la y inferior."""
    lineas = envolver(e["titulo"], 900, fs, True)
    s.texto(cx, y + fs, lineas, fs, s.T["titulo"], negrita=True)
    return y + fs * 1.25 * len(lineas) + 10


def _pie_creditos(s: SVG, creditos: list[str], x: float, y: float, max_w: float = 1000):
    if not creditos:
        return
    txt = "Imágenes: " + " · ".join(creditos)
    s.texto(x, y, envolver(txt, max_w, 9.5, max_lineas=4), 9.5, s.T["linea"], anchor="start")


# ---------------------------------------------------------------------------
# 1. Mapa conceptual
# ---------------------------------------------------------------------------


def mapa_conceptual(e, T, imgs, opc):
    s = SVG(T)
    secs = e["secciones"]
    n = len(secs)
    CW = 250
    total_w = n * CW
    cx = total_w / 2
    ti = imgs.get("titulo")
    tw, th = tam_nodo(e["titulo"], 380, 22, True, img=bool(ti), img_h=110)
    y_tit = th / 2
    nodo(s, cx, y_tit, e["titulo"], 380, 22, T["titulo"], T["titulo"], "#FFFFFF", True, img=ti, img_h=110)
    y_bus = th + 55
    s.linea(cx, th, cx, y_bus)
    s.etiqueta_enlace(cx, th + 27, "comprende", 13)
    xs = [CW / 2 + i * CW for i in range(n)]
    if n > 1:
        s.linea(xs[0], y_bus, xs[-1], y_bus)
    y_sec = y_bus + 40
    for i, sec in enumerate(secs):
        c = color(T, i)
        x = xs[i]
        img = imgs.get(i)
        w, h = tam_nodo(sec["subtitulo"], 210, 15, True, img=bool(img))
        s.linea(x, y_bus, x, y_sec, flecha=True)
        nodo(s, x, y_sec + h / 2, sec["subtitulo"], 210, 15, suave(c, T), c, None, True, img=img)
        y = y_sec + h
        for k, (idea, es_sec) in enumerate(_ideas(sec, opc.get("secundarias", True))):
            fs = 12 if es_sec else 13
            iw, ih = tam_nodo(idea, 215, fs)
            gap = 52
            s.linea(x, y, x, y + gap, stroke=c, flecha=True)
            if k == 0:
                s.etiqueta_enlace(x, y + gap / 2, sec["conector"], 11.5, tinta(c, T))
            elif es_sec and not _ideas(sec, True)[k - 1][1]:
                s.etiqueta_enlace(x, y + gap / 2, "por ejemplo", 11.5, tinta(c, T))
            else:
                s.etiqueta_enlace(x, y + gap / 2, "y", 11.5, tinta(c, T))
            nodo(s, x, y + gap + ih / 2, idea, 215, fs, T["fondo"], c, None, False, guion="5,4" if es_sec else None,
                 cursiva=es_sec)
            y += gap + ih
    _pie_creditos(s, opc.get("creditos"), 0, s.bbox[3] + 30, total_w)
    return s.svg()


# ---------------------------------------------------------------------------
# 2. Mapa mental (radial con ramas curvas)
# ---------------------------------------------------------------------------


def mapa_mental(e, T, imgs, opc):
    s = SVG(T)
    secs = e["secciones"]
    n = len(secs)
    ti = imgs.get("titulo")
    x0, y0, w0, h0 = nodo(s, 0, 0, e["titulo"], 260, 22, T["titulo"], T["titulo"], "#FFFFFF", True, forma="elipse",
                          img=ti, img_h=90)
    R1 = max(260, 80 + n * 38)
    R2 = R1 + 150
    for i, sec in enumerate(secs):
        c = color(T, i)
        a = 2 * math.pi * i / n - math.pi / 2 + (math.pi / n if n % 2 == 0 else 0)
        px, py = R1 * math.cos(a), R1 * math.sin(a) * 0.78
        sx, sy = (w0 / 2) * math.cos(a) * 0.85, (h0 / 2) * math.sin(a) * 0.85
        ctrl = (R1 * 0.45 * math.cos(a - 0.35), R1 * 0.45 * math.sin(a - 0.35) * 0.78)
        s.camino(f"M{sx:.1f},{sy:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {px:.1f},{py:.1f}", stroke=c, sw=9)
        nodo(s, px, py, sec["subtitulo"], 200, 15, c, c, texto_sobre(c), True, forma="pildora")
        ideas = _ideas(sec, opc.get("secundarias", False))
        if not ideas:
            continue
        derecha = math.cos(a) >= -0.01
        alturas = [medir(t, 230, 12 if es else 13)[1] for t, es in ideas]
        total = sum(alturas) + 12 * (len(ideas) - 1)
        bx = px + (R2 - R1) * (1 if derecha else -1) * 0.95
        by = py + (R2 - R1) * math.sin(a) * 0.55 - total / 2
        for (t, es), hh in zip(ideas, alturas):
            fs = 12 if es else 13
            _, _, lineas = medir(t, 230, fs)
            ty = by + hh / 2
            ancho_txt = max(ancho(l, fs) for l in lineas)
            borde_x = px + (100 if derecha else -100) * 0.9
            s.camino(f"M{borde_x:.1f},{py:.1f} C{(borde_x + bx) / 2:.1f},{py:.1f} {(borde_x + bx) / 2:.1f},{ty + hh / 2 - 4:.1f} "
                     f"{bx:.1f},{ty + hh / 2 - 4:.1f}", stroke=c, sw=2.5 if not es else 1.6)
            fin = bx + (ancho_txt + 6 if derecha else -ancho_txt - 6)
            s.linea(bx, ty + hh / 2 - 4, fin, ty + hh / 2 - 4, stroke=c, sw=2.5 if not es else 1.6)
            s.texto_centrado(bx + (4 if derecha else -4), ty - 4, lineas, fs, None, False,
                             anchor="start" if derecha else "end", cursiva=es)
            by += hh + 12
    _pie_creditos(s, opc.get("creditos"), s.bbox[0], s.bbox[3] + 30, s.bbox[2] - s.bbox[0])
    return s.svg()


# ---------------------------------------------------------------------------
# 3. Mapa de ideas o telaraña
# ---------------------------------------------------------------------------


def _circulo_texto(s, cx, cy, r, texto, fs, fill, stroke, color_txt=None, negrita=False, sw=2):
    s.circulo(cx, cy, r, fill, stroke, sw)
    lineas = envolver(texto, r * 1.55, fs, negrita, max_lineas=max(2, int(r * 1.5 / (fs * 1.25))))
    s.texto_centrado(cx, cy, lineas, fs, color_txt, negrita)


def mapa_telarana(e, T, imgs, opc):
    s = SVG(T)
    secs = e["secciones"]
    n = len(secs)
    R1, R2 = 290, 480
    puntos = []
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 2
        puntos.append((R1 * math.cos(a), R1 * math.sin(a), a))
    # Hilos de la telaraña
    for frac in (1.0, 1.55):
        pts = " ".join(f"{p[0] * frac:.1f},{p[1] * frac:.1f}" for p in puntos)
        if n >= 3:
            s.add(f'<polygon points="{pts}" fill="none" stroke="{T["linea"]}" stroke-width="1" stroke-dasharray="4,5" opacity="0.55"/>', 0)
    for i, (px, py, a) in enumerate(puntos):
        c = color(T, i)
        s.linea(0, 0, px, py, stroke=c, sw=2.5)
        ideas = [t for t, _ in _ideas(secs[i], opc.get("secundarias", False))][:4]
        m = len(ideas)
        for k, idea in enumerate(ideas):
            da = (k - (m - 1) / 2) * min(0.42, (2 * math.pi / n) * 0.8 / max(m, 1))
            ix, iy = R2 * math.cos(a + da), R2 * math.sin(a + da)
            s.linea(px, py, ix, iy, stroke=c, sw=1.5)
            _circulo_texto(s, ix, iy, 62, etiqueta(idea, 9), 11.5, suave(c, T, 0.88), c)
        _circulo_texto(s, px, py, 78, secs[i]["subtitulo"], 14, suave(c, T, 0.7), c, None, True, 3)
    ti = imgs.get("titulo")
    s.circulo(0, 0, 105, T["titulo"], T["titulo"])
    if ti:
        s.imagen(-45, -95, 90, 70, ti, redondo=True)
        lineas = envolver(e["titulo"], 170, 16, True, 3)
        s.texto_centrado(0, 25, lineas, 16, "#FFFFFF", True)
    else:
        _circulo_texto(s, 0, 0, 105, e["titulo"], 19, T["titulo"], T["titulo"], "#FFFFFF", True)
    _pie_creditos(s, opc.get("creditos"), s.bbox[0], s.bbox[3] + 30, s.bbox[2] - s.bbox[0])
    return s.svg()


# ---------------------------------------------------------------------------
# 4 y 5. Cuadro sinóptico y esquema de llaves
# ---------------------------------------------------------------------------


def _arbol_llaves(e, T, imgs, opc, estilo):
    s = SVG(T)
    secs = e["secciones"]
    CW_T, CW_S, CW_I = 230, 230, 360
    LL = 30
    x_t, x_s = 0, 230 + LL + 14
    x_i = x_s + CW_S + LL + 14
    gap_item, gap_bloque = 8, 22
    bloques = []
    for i, sec in enumerate(secs):
        items = []
        for t, es in _ideas(sec, opc.get("secundarias", True) if estilo == "sinoptico" else True):
            fs = 12.5 if es else 13.5
            texto = ("– " if es and estilo == "llaves" else "") + t
            w, h, lin = medir(texto, CW_I, fs, pad_x=10 if estilo == "sinoptico" else 2, pad_y=7 if estilo == "sinoptico" else 3)
            items.append((texto, es, fs, h, lin))
        alto_items = sum(it[3] for it in items) + gap_item * max(len(items) - 1, 0)
        _, hs, _ = medir(sec["subtitulo"], CW_S, 15, True)
        bloques.append((sec, items, max(alto_items, hs)))
    total = sum(b[2] for b in bloques) + gap_bloque * (len(bloques) - 1)
    # Título
    _, ht, lt = medir(e["titulo"], CW_T, 21, True)
    if estilo == "sinoptico":
        s.rect(x_t, total / 2 - ht / 2, CW_T, ht, T["titulo"], T["titulo"], rx=10)
        s.texto_centrado(x_t + CW_T / 2, total / 2, lt, 21, "#FFFFFF", True)
    else:
        s.texto_centrado(x_t + CW_T / 2, total / 2, lt, 22, T["titulo"], True)
    s.llave(x_t + CW_T + 8, 0, total, LL, T["titulo"], 2.6)
    y = 0
    for i, (sec, items, alto) in enumerate(bloques):
        c = color(T, i)
        cy = y + alto / 2
        _, hs, ls = medir(sec["subtitulo"], CW_S, 15, True)
        if estilo == "sinoptico":
            s.rect(x_s, cy - hs / 2, CW_S, hs, suave(c, T), c, rx=8, sw=2)
            s.texto_centrado(x_s + CW_S / 2, cy, ls, 15, None, True)
        else:
            s.texto_centrado(x_s + 4, cy, ls, 16, tinta(c, T), True, anchor="start")
        if items:
            s.llave(x_s + CW_S + 8, y + (alto - (sum(it[3] for it in items) + gap_item * (len(items) - 1))) / 2,
                    y + (alto + (sum(it[3] for it in items) + gap_item * (len(items) - 1))) / 2, LL, c, 2.2)
            yy = y + (alto - (sum(it[3] for it in items) + gap_item * (len(items) - 1))) / 2
            for texto, es, fs, h, lin in items:
                if estilo == "sinoptico":
                    s.rect(x_i, yy, CW_I, h, T["fondo"] if es else suave(c, T, 0.93), c, rx=6, sw=1.2,
                           extra='stroke-dasharray="4,3"' if es else "")
                    s.texto_centrado(x_i + 10, yy + h / 2, lin, fs, None, False, anchor="start", cursiva=es)
                else:
                    if not es:
                        s.circulo(x_i + 2, yy + h / 2 - (len(lin) - 1) * fs * 0.62, 3.2, c, c)
                    s.texto_centrado(x_i + (12 if not es else 26), yy + h / 2, lin, fs, None, False, anchor="start", cursiva=es)
                yy += h + gap_item
        y += alto + gap_bloque
    _pie_creditos(s, opc.get("creditos"), 0, total + 40, x_i + CW_I)
    return s.svg()


def cuadro_sinoptico(e, T, imgs, opc):
    return _arbol_llaves(e, T, imgs, opc, "sinoptico")


def esquema_llaves(e, T, imgs, opc):
    return _arbol_llaves(e, T, imgs, opc, "llaves")


# ---------------------------------------------------------------------------
# 6. Organigrama
# ---------------------------------------------------------------------------


def organigrama(e, T, imgs, opc):
    s = SVG(T)
    secs = e["secciones"]
    n = len(secs)
    CW = 240
    xs = [CW / 2 + i * CW for i in range(n)]
    cx = n * CW / 2
    tw, th = tam_nodo(e["titulo"], 340, 20, True)
    nodo(s, cx, th / 2, e["titulo"], 340, 20, T["titulo"], T["titulo"], "#FFFFFF", True)
    y_bus = th + 35
    s.linea(cx, th, cx, y_bus, sw=2.2)
    if n > 1:
        s.linea(xs[0], y_bus, xs[-1], y_bus, sw=2.2)
    y_sec = y_bus + 30
    for i, sec in enumerate(secs):
        c = color(T, i)
        x = xs[i]
        w, h = tam_nodo(sec["subtitulo"], 200, 14.5, True, ancho_fijo=210)
        s.linea(x, y_bus, x, y_sec, sw=2.2)
        nodo(s, x, y_sec + h / 2, sec["subtitulo"], 200, 14.5, c, c, texto_sobre(c), True, ancho_fijo=210)
        y = y_sec + h + 20
        x_tronco = x - 210 / 2 + 14
        ideas = _ideas(sec, opc.get("secundarias", False))
        y_ultimo = None
        for t, es in ideas:
            fs = 12 if es else 12.5
            iw, ih = tam_nodo(t, 180, fs, ancho_fijo=180)
            bx = x_tronco + 18 + 90
            nodo(s, bx, y + ih / 2, t, 180, fs, suave(c, T, 0.9), c, None, False, ancho_fijo=180, sw=1.3,
                 guion="4,3" if es else None, cursiva=es)
            s.linea(x_tronco, y + ih / 2, x_tronco + 18, y + ih / 2, stroke=c, sw=1.6)
            y_ultimo = y + ih / 2
            y += ih + 12
        if y_ultimo is not None:
            s.linea(x_tronco, y_sec + h, x_tronco, y_ultimo, stroke=c, sw=1.6)
    return s.svg()


# ---------------------------------------------------------------------------
# 7. Cuadro comparativo
# ---------------------------------------------------------------------------


def cuadro_comparativo(e, T, imgs, opc):
    s = SVG(T)
    comp = e["comparacion"]
    crit, elems = comp["criterios"], comp["elementos"]
    W0, WC = 210, 250
    total_w = W0 + WC * len(elems)
    y = _titulo_superior(s, e, total_w / 2, 0)
    # Encabezado
    hh = max(medir(el["nombre"], WC, 15, True)[1] for el in elems) if elems else 40
    s.rect(0, y, W0, hh, T["titulo"], T["titulo"], rx=0)
    s.texto_centrado(W0 / 2, y + hh / 2, "Criterios", 15, "#FFFFFF", True)
    for j, el in enumerate(elems):
        c = color(T, j)
        _, _, lin = medir(el["nombre"], WC, 15, True)
        s.rect(W0 + j * WC, y, WC, hh, c, T["fondo"], rx=0, sw=2)
        s.texto_centrado(W0 + j * WC + WC / 2, y + hh / 2, lin, 15, texto_sobre(c), True)
    y += hh
    for r, cr in enumerate(crit):
        celdas = [medir(cr, W0, 14, True, pad_y=12)] + [medir(el["valores"][r], WC, 13, pad_y=12, max_lineas=10) for el in elems]
        alto = max(c_[1] for c_ in celdas)
        fondo = suave(T["titulo"], T, 0.9)
        s.rect(0, y, W0, alto, fondo, T["linea"], rx=0, sw=0.8)
        s.texto_centrado(W0 / 2, y + alto / 2, celdas[0][2], 14, None, True)
        for j, el in enumerate(elems):
            c = color(T, j)
            s.rect(W0 + j * WC, y, WC, alto, suave(c, T, 0.93 if r % 2 else 0.97), T["linea"], rx=0, sw=0.8)
            s.texto_centrado(W0 + j * WC + 14, y + alto / 2, celdas[j + 1][2], 13, None, anchor="start")
        y += alto
    return s.svg()


# ---------------------------------------------------------------------------
# 8. Diagrama de Venn
# ---------------------------------------------------------------------------


def _lista_en(s, cx, cy, items, max_w, fs, c=None, negrita=False):
    bloques = [envolver("• " + t, max_w, fs, negrita, 3) for t in items]
    alto = sum(len(b) for b in bloques) * fs * 1.25 + (len(bloques) - 1) * 6
    y = cy - alto / 2 + fs
    for b in bloques:
        s.texto(cx, y, b, fs, c, "middle", negrita)
        y += len(b) * fs * 1.25 + 6


def diagrama_venn(e, T, imgs, opc):
    s = SVG(T)
    v = e["venn"]
    conj = v["conjuntos"]
    _titulo_superior(s, e, 0, -380)
    if len(conj) >= 3:
        r = 230
        centros = [(-145, -60), (145, -60), (0, 175)]
        for i, (x, y) in enumerate(centros):
            c = color(T, i)
            s.circulo(x, y, r, c, c, 2.5, extra='fill-opacity="0.22"')
        externos = [(-235, -120), (235, -120), (0, 300)]
        nombres = [(-270, -300), (270, -300), (0, 432)]
        for i in range(3):
            c = color(T, i)
            s.texto(nombres[i][0], nombres[i][1], envolver(conj[i]["nombre"], 260, 17, True, 2), 17, tinta(c, T), negrita=True)
            _lista_en(s, externos[i][0], externos[i][1], conj[i]["elementos"][:4], 150, 12.5)
        _lista_en(s, 0, 30, v["comunes"][:3], 120, 12.5, T["titulo"], True)
    else:
        r = 250
        centros = [(-160, 0), (160, 0)]
        for i, (x, y) in enumerate(centros):
            c = color(T, i)
            s.circulo(x, y, r, c, c, 2.5, extra='fill-opacity="0.22"')
            s.texto(x + (-60 if i == 0 else 60), -r - 18, envolver(conj[i]["nombre"], 300, 18, True, 2), 18, tinta(c, T), negrita=True)
            _lista_en(s, x + (-95 if i == 0 else 95), 0, conj[i]["elementos"][:5], 190, 13)
        _lista_en(s, 0, 0, v["comunes"][:4], 120, 13, T["titulo"], True)
    s.texto(0, s.bbox[3] + 28, "Zona central: elementos en común", 12, T["linea"], cursiva=True)
    return s.svg()


# ---------------------------------------------------------------------------
# 9. Cuadro T
# ---------------------------------------------------------------------------


def cuadro_t(e, T, imgs, opc):
    s = SVG(T)
    ct = e["cuadro_t"]
    W = 1000
    y = _titulo_superior(s, e, W / 2, 0) + 10
    c1, c2 = color(T, 0), color(T, 1)
    s.rect(0, y, W, 58, T["titulo"], T["titulo"], rx=6)
    for k, (lado, c) in enumerate((("izquierda", c1), ("derecha", c2))):
        s.texto_centrado(W / 4 + k * W / 2, y + 29, envolver(ct[lado]["titulo"], W / 2 - 40, 19, True, 2), 19, "#FFFFFF", True)
    y0 = y + 58
    alturas = []
    for k, (lado, c) in enumerate((("izquierda", c1), ("derecha", c2))):
        yy = y0 + 28
        x = 30 + k * W / 2
        for t in ct[lado]["elementos"]:
            lin = envolver(t, W / 2 - 90, 14.5)
            s.circulo(x + 8, yy + 7, 6, c, c)
            s.texto(x + 24, yy + 12, lin, 14.5, None, "start")
            yy += len(lin) * 14.5 * 1.25 + 16
        alturas.append(yy)
    yfin = max(alturas) + 10
    s.rect(W / 2 - 4, y0, 8, yfin - y0, T["titulo"], T["titulo"], rx=2)
    s.linea(0, yfin, W, yfin, stroke=suave(T["linea"], T, 0.5), sw=1)
    return s.svg()


# ---------------------------------------------------------------------------
# 10. Línea de tiempo
# ---------------------------------------------------------------------------


def linea_tiempo(e, T, imgs, opc):
    s = SVG(T)
    ev = e["eventos"]
    n = len(ev)
    paso = 240
    W = paso * n + 60
    _titulo_superior(s, e, W / 2, -330)
    s.linea(0, 0, W, 0, stroke=T["titulo"], sw=6, flecha=True)
    for i, evento in enumerate(ev):
        c = color(T, i)
        x = 60 + i * paso + paso / 2 - 30
        arriba = i % 2 == 0
        w, h, lin = medir(evento["hecho"], 215, 13, max_lineas=7)
        _, hf, lf = medir(evento["fecha"], 215, 15, True)
        alto = h + hf
        y_card = -60 - alto if arriba else 60
        s.linea(x, 0, x, y_card + (alto if arriba else 0), stroke=c, sw=2, guion="4,3")
        s.rect(x - 110, y_card, 220, alto, suave(c, T, 0.9), c, rx=10, sw=2)
        s.rect(x - 110, y_card, 220, hf, c, c, rx=10)
        s.texto_centrado(x, y_card + hf / 2, lf, 15, texto_sobre(c), True)
        s.texto_centrado(x, y_card + hf + h / 2, lin, 13)
        s.circulo(x, 0, 13, c, T["fondo"], 4)
    return s.svg()


# ---------------------------------------------------------------------------
# 11. Diagrama de flujo
# ---------------------------------------------------------------------------


def _es_decision(t: str) -> bool:
    tl = t.strip().lower()
    return tl.startswith("¿") or tl.endswith("?") or tl.startswith("si ") or " decide" in tl or "verificar" in tl


def diagrama_flujo(e, T, imgs, opc):
    s = SVG(T)
    pasos = e["pasos"]
    y = _titulo_superior(s, e, 0, -40) + 20
    cT = T["titulo"]
    _, _, _, h = nodo(s, 0, y + 25, "Inicio", 140, 16, cT, cT, "#FFFFFF", True, forma="pildora", ancho_fijo=160)
    y += h
    centros = []
    for i, p in enumerate(pasos):
        c = color(T, i)
        s.linea(0, y, 0, y + 42, flecha=True, sw=2)
        y += 42
        if _es_decision(p):
            lin = envolver(p, 210, 13.5, max_lineas=4)
            hd = max(130, len(lin) * 17 + 70)
            wd = 330
            s.add(f'<polygon points="0,{y:.1f} {wd / 2:.1f},{y + hd / 2:.1f} 0,{y + hd:.1f} {-wd / 2:.1f},{y + hd / 2:.1f}" '
                  f'fill="{suave(c, T, 0.85)}" stroke="{c}" stroke-width="2"/>', 1)
            s.incluir(-wd / 2, y, wd, hd)
            s.texto_centrado(0, y + hd / 2, lin, 13.5)
            if centros:
                py, ph = centros[-1]
                s.camino(f"M{wd / 2:.1f},{y + hd / 2:.1f} L{wd / 2 + 70:.1f},{y + hd / 2:.1f} L{wd / 2 + 70:.1f},{py:.1f} L215,{py:.1f}",
                         stroke=T["colores"][4 % len(T["colores"])], sw=2, flecha=True)
                s.texto(wd / 2 + 18, y + hd / 2 - 8, "No", 13, T["colores"][4 % len(T["colores"])], "start", True)
                s.incluir(wd / 2 + 80, py, 1, 1)
            s.texto(14, y + hd + 18, "Sí", 13, T["colores"][1], "start", True)
            centros.append((y + hd / 2, hd))
            y += hd
        else:
            w, h = tam_nodo(p, 400, 14, ancho_fijo=420)
            nodo(s, 0, y + h / 2, p, 400, 14, suave(c, T, 0.85), c, None, False, ancho_fijo=420, sw=2)
            s.circulo(-210, y, 14, c, T["fondo"], 2)
            s.texto_centrado(-210, y, str(i + 1), 12, texto_sobre(c), True)
            centros.append((y + h / 2, h))
            y += h
    s.linea(0, y, 0, y + 42, flecha=True, sw=2)
    nodo(s, 0, y + 42 + 25, "Fin", 140, 16, cT, cT, "#FFFFFF", True, forma="pildora", ancho_fijo=160)
    return s.svg()


# ---------------------------------------------------------------------------
# 12. Diagrama de causa-efecto (espina de pescado / Ishikawa)
# ---------------------------------------------------------------------------


def espina_pescado(e, T, imgs, opc):
    s = SVG(T)
    ce = e["causa_efecto"]
    cats = ce["categorias"]
    arriba = cats[0::2]
    abajo = cats[1::2]
    cols = max(len(arriba), len(abajo), 1)
    ESP = 330
    L = 270  # largo de cada espina
    x_cab = cols * ESP + 80
    _titulo_superior(s, e, x_cab / 2, -L - 140)
    # Cabeza (efecto)
    w, h, lin = medir(ce["efecto"], 230, 17, True)
    s.add(f'<path d="M{x_cab:.1f},{-h / 2 - 30:.1f} L{x_cab + w + 30:.1f},{-h / 2 - 30:.1f} Q{x_cab + w + 90:.1f},0 '
          f'{x_cab + w + 30:.1f},{h / 2 + 30:.1f} L{x_cab:.1f},{h / 2 + 30:.1f} Z" fill="{T["titulo"]}"/>', 1)
    s.incluir(x_cab, -h / 2 - 30, w + 90, h + 60)
    s.texto_centrado(x_cab + (w + 50) / 2, 0, lin, 17, "#FFFFFF", True)
    s.texto(x_cab + (w + 50) / 2, h / 2 + 52, "EFECTO", 12, T["linea"], negrita=True)
    # Espina central y cola
    s.linea(0, 0, x_cab, 0, stroke=T["titulo"], sw=6)
    s.add(f'<path d="M0,0 L-60,-55 L-40,0 L-60,55 Z" fill="{T["titulo"]}"/>', 1)
    s.incluir(-60, -55, 60, 110)
    for fila, grupo in ((-1, arriba), (1, abajo)):
        for j, cat in enumerate(grupo):
            idx = cats.index(cat)
            c = color(T, idx)
            xb = (j + 1) * ESP + (40 if fila == 1 else 0)
            xt, yt = xb - 150, fila * L
            s.linea(xb, 0, xt, yt, stroke=c, sw=3.5)
            w, h, lin = medir(cat["nombre"], 210, 15, True)
            ybox = yt - h - 4 if fila == -1 else yt + 4
            s.rect(xt - w / 2, ybox, w, h, c, c, rx=8)
            s.texto_centrado(xt, ybox + h / 2, lin, 15, texto_sobre(c), True)
            causas = cat["causas"][:4]
            for k, causa in enumerate(causas):
                t = (k + 1) / (len(causas) + 1)
                px, py = xb + (xt - xb) * t, yt * t
                s.linea(px - 120, py, px, py, stroke=c, sw=1.6)
                s.circulo(px, py, 3.5, c, c)
                lin = envolver(causa, 160, 12, max_lineas=2)
                s.texto(px - 124, py - 5 - (len(lin) - 1) * 15, lin, 12, None, "end")
    s.texto(0, L + 80, "CAUSAS", 12, T["linea"], "start", True)
    return s.svg()


# ---------------------------------------------------------------------------
# 13. Infografía
# ---------------------------------------------------------------------------


def infografia(e, T, imgs, opc):
    s = SVG(T)
    W = 1100
    cT = T["titulo"]
    ti = imgs.get("titulo")
    ancho_txt = W - 80 - (300 if ti else 0)
    lt = envolver(e["titulo"].upper(), ancho_txt, 36, True, 3)
    lr = envolver(e.get("resumen") or "", ancho_txt, 16, max_lineas=5) if e.get("resumen") else []
    alto_cab = max(60 + len(lt) * 45 + len(lr) * 21 + 30, 240 if ti else 0)
    s.rect(0, 0, W, alto_cab, cT, cT, rx=18)
    s.texto(40, 70, lt, 36, "#FFFFFF", "start", True)
    if lr:
        s.texto(40, 70 + len(lt) * 45 + 10, lr, 16, "#FFFFFF", "start")
    if ti:
        s.imagen(W - 300, 25, 270, alto_cab - 50, ti, rx=14)
    y = alto_cab + 30
    # Datos destacados
    datos = e.get("datos") or []
    if datos:
        n = min(len(datos), 4)
        wcol = W / n
        for i, d in enumerate(datos[:n]):
            c = color(T, i)
            cx = wcol * i + wcol / 2
            s.circulo(cx, y + 62, 58, suave(c, T, 0.8), c, 4)
            fsv = 26 if len(d["valor"]) <= 6 else 18
            s.texto_centrado(cx, y + 62, envolver(d["valor"], 100, fsv, True, 2), fsv, tinta(c, T), True)
            s.texto(cx, y + 145, envolver(d["texto"], wcol - 30, 12.5, max_lineas=3), 12.5)
        y += 210
    # Tarjetas por sección (2 columnas)
    secs = e["secciones"]
    CWc = (W - 30) / 2
    for fila in range(0, len(secs), 2):
        par = secs[fila:fila + 2]
        alturas = []
        dibujos = []
        for k, sec in enumerate(par):
            i = fila + k
            img = imgs.get(i)
            ancho_lista = CWc - 40 - (170 if img else 0)
            lineas_ideas = [envolver(t, ancho_lista - 45, 13.5 if not es else 12.5, max_lineas=4) for t, es in _ideas(sec, opc.get("secundarias", True))]
            alto_lista = sum(len(l) * (13.5 * 1.3) + 10 for l in lineas_ideas)
            lh = envolver(sec["subtitulo"], CWc - 90, 18, True, 2)
            alto = 20 + len(lh) * 23 + 16 + max(alto_lista, 130 if img else 0) + 20
            alturas.append(alto)
            dibujos.append((i, sec, img, lineas_ideas, lh, ancho_lista))
        alto_fila = max(alturas)
        for k, (i, sec, img, lineas_ideas, lh, ancho_lista) in enumerate(dibujos):
            c = color(T, i)
            x = k * (CWc + 30)
            s.rect(x, y, CWc, alto_fila, suave(c, T, 0.92), c, rx=16, sw=2)
            s.circulo(x + 34, y + 36, 20, c, c)
            s.texto_centrado(x + 34, y + 36, str(i + 1), 18, texto_sobre(c), True)
            s.texto(x + 66, y + 42 - (len(lh) - 1) * 11, lh, 18, tinta(c, T), "start", True)
            yy = y + 20 + len(lh) * 23 + 20
            xl = x + 22
            if img:
                s.imagen(x + 20, yy, 155, 125, img, rx=10)
                xl = x + 190
            for (t, es), lin in zip(_ideas(sec, opc.get("secundarias", True)), lineas_ideas):
                fs = 13.5 if not es else 12.5
                s.circulo(xl + 5, yy + 9, 4, c if not es else T["fondo"], c, 1.5)
                s.texto(xl + 18, yy + 13, lin, fs, None, "start", cursiva=es)
                yy += len(lin) * fs * 1.3 + 10
        y += alto_fila + 24
    # Conectores y palabras clave
    chips = [("Conectores", [c["conector"] for c in e.get("conectores", [])][:8]),
             ("Palabras clave", e.get("palabras_clave", [])[:10])]
    for etiqueta_, lista in chips:
        if not lista:
            continue
        s.texto(0, y + 18, etiqueta_ + ":", 14, cT, "start", True)
        x = ancho(etiqueta_ + ":", 14, True) + 14
        for i, p in enumerate(lista):
            w = ancho(p, 13) + 22
            if x + w > W:
                y += 34
                x = ancho(etiqueta_ + ":", 14, True) + 14
            c = color(T, i)
            s.rect(x, y, w, 26, suave(c, T, 0.8), c, rx=13, sw=1)
            s.texto(x + w / 2, y + 17.5, p, 13)
            x += w + 8
        y += 42
    _pie_creditos(s, opc.get("creditos"), 0, y + 14, W)
    return s.svg()


# ---------------------------------------------------------------------------
# 14. Mapa semántico
# ---------------------------------------------------------------------------


def mapa_semantico(e, T, imgs, opc):
    s = SVG(T)
    secs = e["secciones"]
    n = len(secs)
    BW = 270
    RX, RY = 470 + max(0, n - 6) * 40, 300 + max(0, n - 6) * 30
    cajas = []
    for i, sec in enumerate(secs):
        a = 2 * math.pi * i / n - math.pi / 2
        cx, cy = RX * math.cos(a), RY * math.sin(a)
        c = color(T, i)
        lh = envolver(sec["subtitulo"], BW - 24, 15, True, 2)
        items = [envolver("• " + t, BW - 26, 12.5, max_lineas=3) for t, _ in _ideas(sec, opc.get("secundarias", False))]
        alto_items = sum(len(l) * 15.6 + 6 for l in items)
        hh = len(lh) * 19 + 16
        alto = hh + alto_items + 16
        cajas.append((cx, cy, c, lh, items, hh, alto))
        s.linea(0, 0, cx, cy, stroke=c, sw=2.5)
    for cx, cy, c, lh, items, hh, alto in cajas:
        x, y = cx - BW / 2, cy - alto / 2
        s.rect(x, y, BW, alto, suave(c, T, 0.93), c, rx=12, sw=2)
        s.rect(x, y, BW, hh, c, c, rx=12)
        s.texto_centrado(cx, y + hh / 2, lh, 15, texto_sobre(c), True)
        yy = y + hh + 10 + 12.5
        for l in items:
            s.texto(x + 12, yy, l, 12.5, None, "start")
            yy += len(l) * 15.6 + 6
    ti = imgs.get("titulo")
    nodo(s, 0, 0, e["titulo"], 250, 21, T["titulo"], T["titulo"], "#FFFFFF", True, forma="elipse", img=ti, img_h=80)
    _pie_creditos(s, opc.get("creditos"), s.bbox[0], s.bbox[3] + 30, s.bbox[2] - s.bbox[0])
    return s.svg()


# ---------------------------------------------------------------------------
# 15. Rueda de atributos
# ---------------------------------------------------------------------------


def rueda_atributos(e, T, imgs, opc):
    s = SVG(T)
    atr = e["atributos"]
    n = len(atr)
    R = 300 + max(0, n - 8) * 22
    s.circulo(0, 0, R, "none", suave(T["linea"], T, 0.5), 10)
    for i, a_ in enumerate(atr):
        c = color(T, i)
        a = 2 * math.pi * i / n - math.pi / 2
        x, y = R * math.cos(a), R * math.sin(a)
        s.linea(0, 0, x, y, stroke=c, sw=4)
    for i, a_ in enumerate(atr):
        c = color(T, i)
        a = 2 * math.pi * i / n - math.pi / 2
        x, y = R * math.cos(a), R * math.sin(a)
        _circulo_texto(s, x, y, 78, a_, 13, suave(c, T, 0.8), c, None, True, 3)
    ti = imgs.get("titulo")
    s.circulo(0, 0, 120, T["titulo"], suave(T["titulo"], T, 0.6), 8)
    if ti:
        s.imagen(-50, -100, 100, 75, ti, redondo=True)
        s.texto_centrado(0, 30, envolver(e["titulo"], 190, 17, True, 3), 17, "#FFFFFF", True)
    else:
        s.texto_centrado(0, 0, envolver(e["titulo"], 200, 20, True, 4), 20, "#FFFFFF", True)
    _pie_creditos(s, opc.get("creditos"), s.bbox[0], s.bbox[3] + 30, s.bbox[2] - s.bbox[0])
    return s.svg()


# ---------------------------------------------------------------------------
# 16. Cadena de secuencias
# ---------------------------------------------------------------------------


def cadena_secuencias(e, T, imgs, opc):
    s = SVG(T)
    pasos = e["pasos"]
    POR_FILA = 3
    BW, GX, GY = 270, 90, 80
    W = POR_FILA * BW + (POR_FILA - 1) * GX
    y = _titulo_superior(s, e, W / 2, 0) + 20
    filas = [pasos[i:i + POR_FILA] for i in range(0, len(pasos), POR_FILA)]
    idx = 0
    prev = None
    for f, fila in enumerate(filas):
        medidas = [medir(p, BW - 30, 14, max_lineas=7) for p in fila]
        alto = max(m[1] for m in medidas) + 40
        for k, (p, m) in enumerate(zip(fila, medidas)):
            col = k if f % 2 == 0 else POR_FILA - 1 - k
            x = col * (BW + GX)
            c = color(T, idx)
            s.rect(x, y, BW, alto, suave(c, T, 0.88), c, rx=16, sw=2.5)
            s.circulo(x + 26, y + 4, 22, c, T["fondo"], 3)
            s.texto_centrado(x + 26, y + 4, str(idx + 1), 17, texto_sobre(c), True)
            s.texto_centrado(x + BW / 2, y + alto / 2 + 8, m[2], 14)
            if prev is not None:
                px, py, pf = prev
                if pf == f:
                    if f % 2 == 0:
                        s.linea(px + BW + 6, y + alto / 2, x - 8, y + alto / 2, stroke=T["titulo"], sw=4, flecha=True)
                    else:
                        s.linea(px - 6, y + alto / 2, x + BW + 8, y + alto / 2, stroke=T["titulo"], sw=4, flecha=True)
                else:
                    s.linea(x + BW / 2, py, x + BW / 2, y - 10, stroke=T["titulo"], sw=4, flecha=True)
            prev = (x, y + alto, f)
            idx += 1
        y += alto + GY
    return s.svg()


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

ORGANIZADORES = {
    "Mapa conceptual": (mapa_conceptual, "Jerarquía de conceptos unidos por palabras de enlace (conectores)."),
    "Mapa mental": (mapa_mental, "Idea central con ramas curvas e ideas asociadas alrededor."),
    "Mapa de ideas o telaraña": (mapa_telarana, "Tema en el centro y subtemas conectados como una telaraña."),
    "Cuadro sinóptico": (cuadro_sinoptico, "Síntesis jerárquica de izquierda a derecha con llaves y recuadros."),
    "Organigrama": (organigrama, "Estructura jerárquica en niveles descendentes."),
    "Cuadro comparativo": (cuadro_comparativo, "Tabla que contrasta elementos según criterios."),
    "Diagrama de Venn": (diagrama_venn, "Conjuntos que se superponen para mostrar diferencias y semejanzas."),
    "Cuadro T": (cuadro_t, "Dos columnas para contrastar (p. ej., ventajas y desventajas)."),
    "Línea de tiempo": (linea_tiempo, "Hechos ordenados cronológicamente."),
    "Diagrama de flujo": (diagrama_flujo, "Pasos de un proceso con inicio, acciones, decisiones y fin."),
    "Diagrama de causa-efecto (espina de pescado)": (espina_pescado, "Causas agrupadas por categorías que producen un efecto."),
    "Infografía": (infografia, "Presentación visual con datos, tarjetas e imágenes."),
    "Mapa semántico": (mapa_semantico, "Concepto central y categorías con sus características."),
    "Rueda de atributos": (rueda_atributos, "Tema en el centro y sus atributos alrededor."),
    "Cadena de secuencias": (cadena_secuencias, "Eventos o pasos encadenados en orden."),
    "Esquema de llaves": (esquema_llaves, "Clasificación de ideas mediante llaves sucesivas."),
}


def generar(tipo: str, estructura: dict, tema: str = "Vivo", imagenes: dict | None = None, opciones: dict | None = None) -> str:
    fn = ORGANIZADORES[tipo][0]
    T = TEMAS.get(tema, TEMAS["Vivo"])
    return fn(estructura, T, imagenes or {}, opciones or {})
