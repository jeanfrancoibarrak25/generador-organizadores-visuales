"""Análisis de la información sin IA (reglas lingüísticas sencillas en español).

Produce una estructura común para todos los organizadores:

{
  "titulo": str,
  "resumen": str,
  "secciones": [
      {"subtitulo": str, "conector": str,
       "ideas_principales": [str], "ideas_secundarias": [str],
       "busqueda_imagen": str}
  ],
  "conectores": [{"conector": str, "tipo": str}],
  "palabras_clave": [str],
  "datos": [{"valor": str, "texto": str}],
  # Datos específicos (se deducen si faltan):
  "eventos": [{"fecha": str, "hecho": str}],
  "pasos": [str],
  "causa_efecto": {"efecto": str, "categorias": [{"nombre": str, "causas": [str]}]},
  "comparacion": {"criterios": [str], "elementos": [{"nombre": str, "valores": [str]}]},
  "venn": {"conjuntos": [{"nombre": str, "elementos": [str]}], "comunes": [str]},
  "cuadro_t": {"izquierda": {"titulo": str, "elementos": [str]},
               "derecha": {"titulo": str, "elementos": [str]}},
  "atributos": [str],
}
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

STOP = set(
    """a al algo algunas algunos ante antes aquel aquella aquellas aquellos aqui así asi aun aunque cada casi como con
    contra cual cuales cualquier cuando de del desde donde dos e el ella ellas ello ellos en entre era eran es esa esas
    ese eso esos esta estaba estan están estar este esto estos fue fueron gran ha han hasta hay la las le les lo los mas
    más me mi mientras muy no nos o otra otras otro otros para pero poco por porque que qué se sea según segun ser si
    sí sido sin sobre son su sus tal también tambien tan tanto te tiene tienen todo todos tras tu un una unas uno unos
    y ya cuyo cuya puede pueden debe deben hace hacen así mismo misma cual mediante dicho dicha dichos dichas cómo
    lugar parte forma tipo tipos manera través traves embargo además ademas entonces luego pues decir etc vez veces
    sino bien gracias solo sólo cuanto cuanta día años año siempre nunca mayor menor mejor gran grandes nuevo nueva primer primera
    the of and to in is for on with as by an be are this that""".split()
)

# Conectores lógicos: (expresión, tipo, etiqueta corta para enlaces)
CONECTORES = [
    ("por lo tanto", "consecuencia"), ("por consiguiente", "consecuencia"), ("en consecuencia", "consecuencia"),
    ("por ende", "consecuencia"), ("de modo que", "consecuencia"), ("así que", "consecuencia"),
    ("debido a", "causa"), ("ya que", "causa"), ("puesto que", "causa"), ("porque", "causa"),
    ("a causa de", "causa"), ("dado que", "causa"), ("gracias a", "causa"),
    ("sin embargo", "contraste"), ("no obstante", "contraste"), ("en cambio", "contraste"),
    ("por el contrario", "contraste"), ("aunque", "contraste"), ("a pesar de", "contraste"), ("pero", "contraste"),
    ("además", "adición"), ("asimismo", "adición"), ("también", "adición"), ("igualmente", "adición"),
    ("de igual manera", "adición"), ("por otra parte", "adición"),
    ("por ejemplo", "ejemplificación"), ("es decir", "explicación"), ("o sea", "explicación"),
    ("en otras palabras", "explicación"), ("como", "ejemplificación"),
    ("primero", "secuencia"), ("en primer lugar", "secuencia"), ("luego", "secuencia"), ("después", "secuencia"),
    ("posteriormente", "secuencia"), ("finalmente", "secuencia"), ("por último", "secuencia"),
    ("en conclusión", "conclusión"), ("en resumen", "conclusión"), ("en síntesis", "conclusión"),
    ("si", "condición"), ("siempre que", "condición"), ("con el fin de", "finalidad"), ("para que", "finalidad"),
]

# Conector por defecto para enlazar niveles según el tipo dominante del texto.
ENLACE_TIPO = {
    "consecuencia": "provoca", "causa": "se debe a", "contraste": "a diferencia de", "adición": "además",
    "ejemplificación": "por ejemplo", "explicación": "es decir", "secuencia": "luego", "conclusión": "concluye",
    "condición": "si", "finalidad": "para",
}

NEGATIVAS = ("desventaja", "riesgo", "problema", "limitación", "limitacion", "contra", "negativ", "debilidad",
             "amenaza", "dificultad", "perjuicio", "daño", "costo", "inconveniente")
POSITIVAS = ("ventaja", "beneficio", "fortaleza", "positiv", "oportunidad", "pro", "favorable", "mejora", "logro")


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def limpiar(texto: str) -> str:
    texto = texto.replace("\r", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\[\d+\]", "", texto)  # referencias tipo [1]
    return texto.strip()


def oraciones(parrafo: str) -> list[str]:
    parrafo = re.sub(r"\s+", " ", parrafo).strip()
    partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡0-9\"“])", parrafo)
    return [p.strip() for p in partes if len(p.strip()) > 2]


def palabras(texto: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", texto.lower()) if w not in STOP]


def acortar(texto: str, max_palabras: int = 16) -> str:
    """Reduce una oración a una idea breve, sin cortar a mitad de palabra."""
    t = re.sub(r"\s*\([^)]*\)", "", texto).strip()
    t = re.sub(r"^(además|asimismo|también|sin embargo|no obstante|por lo tanto|por ejemplo|es decir|"
               r"en primer lugar|primero|luego|después|finalmente|por último|en conclusión|en resumen),?\s+",
               "", t, flags=re.I)
    t = t.rstrip(" .;:")
    pal = t.split()
    if len(pal) > max_palabras:
        # Intenta cortar en una coma o conjunción antes del límite.
        corte = " ".join(pal[:max_palabras])
        m = max(corte.rfind(","), corte.rfind(";"), corte.rfind(" que "), corte.rfind(" y "))
        if m > len(corte) * 0.55:
            corte = corte[:m]
        t = corte.rstrip(" ,;:") + "…"
    if t:
        t = t[0].upper() + t[1:]
    return t


def etiqueta(texto: str, max_palabras: int = 5) -> str:
    """Etiqueta corta para nodos: corta en una frontera natural y termina en palabra con contenido."""
    t = acortar(texto, 60).rstrip("…")
    t = re.sub(r"^(el|la|los|las|un|una|unos|unas|lo)\s+", "", t, flags=re.I)
    pal = t.split()
    if len(pal) > max_palabras:
        # 1) primera cláusula (hasta coma o punto y coma) si cabe
        clausula = re.split(r"[,;:]", t)[0].split()
        if 2 <= len(clausula) <= max_palabras + 2:
            pal = clausula
        else:
            pal = pal[:max_palabras]
    # 2) no terminar en palabras vacías ni en signos
    while len(pal) > 1 and (pal[-1].lower().strip(",;:.") in STOP or pal[-1].lower() in ("se", "le", "lo")):
        pal = pal[:-1]
    t = " ".join(pal).rstrip(",;:. ")
    return (t[0].upper() + t[1:]) if t else t


def detectar_conectores(texto: str) -> list[dict]:
    bajo = " " + texto.lower() + " "
    vistos: dict[str, dict] = {}
    for c, tipo in CONECTORES:
        n = len(re.findall(r"(?<![a-záéíóúñ])" + re.escape(c) + r"(?![a-záéíóúñ])", bajo))
        if c in ("como", "si", "pero") and n < 2:
            continue
        if n:
            vistos[c] = {"conector": c, "tipo": tipo, "veces": n}
    return sorted(vistos.values(), key=lambda d: -d["veces"])


def conector_seccion(texto: str) -> str:
    encontrados = [d for d in detectar_conectores(texto) if d["conector"] not in ("como", "si")]
    if encontrados:
        return ENLACE_TIPO.get(encontrados[0]["tipo"], encontrados[0]["conector"])
    return "incluye"


def _es_titulo_implicito(linea: str, siguiente: str | None) -> bool:
    pal = linea.split()
    if not (1 <= len(pal) <= 12) or len(linea) > 90:
        return False
    if linea.endswith((".", ",", ";")):
        return False
    if re.match(r"^(\d+(\.\d+)*[.)]?|[IVXLC]+[.)])\s+\S", linea):
        return True
    if linea.endswith(":"):
        return True
    if linea.isupper() and len(linea) > 3:
        return True
    return siguiente is not None and len(siguiente) > len(linea) * 1.8


def _bloques(texto: str) -> list[tuple[int, str]]:
    """Devuelve [(nivel, texto)] donde nivel 0 = párrafo, 1-3 = título."""
    lineas = [l.strip() for l in re.split(r"\n+", texto) if l.strip()]
    salida: list[tuple[int, str]] = []
    for i, l in enumerate(lineas):
        m = re.match(r"^(#{1,6})\s+(.*)$", l)
        if m:
            salida.append((min(len(m.group(1)), 3), m.group(2).strip()))
            continue
        sig = lineas[i + 1] if i + 1 < len(lineas) else None
        if l.startswith(("- ", "• ", "* ", "· ")):
            salida.append((0, l[2:].strip()))
        elif _es_titulo_implicito(l, sig):
            limpio = re.sub(r"^(\d+(\.\d+)*[.)]?|[IVXLC]+[.)])\s+", "", l).rstrip(":").strip()
            nivel = 3 if re.match(r"^\d+\.\d+", l) else 2
            salida.append((nivel, limpio[:1].upper() + limpio[1:].lower() if limpio.isupper() else limpio))
        else:
            salida.append((0, l))
    return salida


def _forma_original(texto: str) -> dict[str, str]:
    formas: dict[str, Counter] = {}
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", texto):
        formas.setdefault(w.lower(), Counter())[w] += 1
    return {k: v.most_common(1)[0][0] for k, v in formas.items()}


def _subtitulo_generado(texto: str, df: Counter, n_docs: int, excluir: set[str], formas: dict[str, str]) -> str:
    pal = [w for w in palabras(texto) if w not in excluir] or palabras(texto)
    if not pal:
        return etiqueta(texto, 4)
    local = Counter(pal)
    import math as _m

    def peso(w):
        return local[w] * (1 + _m.log((n_docs + 1) / (df[w] + 0.5))) + (0.3 if formas.get(w, w)[:1].isupper() else 0)

    orden = sorted(local, key=lambda w: (-peso(w), pal.index(w)))
    claves = [formas.get(w, w) for w in orden if len(w) > 3][:2] or [formas.get(orden[0], orden[0])]
    claves = [c if c[:1].isupper() and c.lower() != c else c.lower() for c in claves]
    if len(claves) == 2:
        return f"{claves[0][:1].upper() + claves[0][1:]} y {claves[1]}"
    return claves[0][:1].upper() + claves[0][1:]


def _titulo_de_oracion(o: str) -> str:
    m = re.split(r"\s(?:es|fue|son|fueron|era|eran|consiste|consisten|se define|se refiere|constituye|representa|"
                 r"comprende|se entiende)\s", o, maxsplit=1)
    if len(m) == 2 and 1 <= len(m[0].split()) <= 9:
        return m[0].strip(" ,")
    return etiqueta(o, 6)


CLAVES_BASE = ("titulo", "resumen", "secciones", "conectores", "palabras_clave", "datos", "busqueda_imagen")
CLAVES_ESPECIFICAS = ("eventos", "pasos", "causa_efecto", "comparacion", "venn", "cuadro_t", "atributos")


def analizar(texto: str, max_secciones: int = 6, max_principales: int = 3, max_secundarias: int = 4) -> dict:
    texto = limpiar(texto)
    if not texto:
        raise ValueError("No hay texto para analizar.")
    bloques = _bloques(texto)
    todo = " ".join(t if n == 0 else t.rstrip(".:") + "." for n, t in bloques)
    frec = Counter(palabras(todo))

    # 1) Título
    titulo = None
    for nivel, t in bloques:
        if nivel == 1:
            titulo = t
            break
    if titulo is None:
        titulos2 = [i for i, (n, _) in enumerate(bloques) if n >= 2]
        if titulos2 and titulos2[0] == 0 and (len(titulos2) == 1 or bloques[1][0] >= 2):
            titulo = bloques[0][1]
            bloques = bloques[1:]
        elif titulos2 and titulos2[0] == 0 and len(titulos2) == 1:
            titulo = bloques[0][1]
            bloques = bloques[1:]
    if titulo is None:
        primeras = oraciones(next((t for n, t in bloques if n == 0), todo))
        claves = [w for w, _ in frec.most_common(3)]
        titulo = _titulo_de_oracion(primeras[0]) if primeras else " ".join(claves).capitalize()
    bloques = [(n, t) for n, t in bloques if not (n == 1 and t == titulo)]

    # 2) Agrupar en secciones (por subtítulos o por párrafos)
    grupos: list[dict] = []
    hay_subtitulos = any(n >= 2 for n, _ in bloques)
    if hay_subtitulos:
        nivel_sec = min(n for n, _ in bloques if n >= 2)
        actual = None
        for n, t in bloques:
            if n == nivel_sec or (n == 1):
                actual = {"subtitulo": t, "parrafos": []}
                grupos.append(actual)
            elif n > nivel_sec:
                if actual is None:
                    actual = {"subtitulo": t, "parrafos": []}
                    grupos.append(actual)
                else:
                    actual["parrafos"].append(t.rstrip(":") + ".")
            else:
                if actual is None:
                    actual = {"subtitulo": None, "parrafos": []}
                    grupos.append(actual)
                actual["parrafos"].append(t)
        grupos = [g for g in grupos if g["parrafos"] or g["subtitulo"]]
    else:
        parrafos = [t for _, t in bloques]
        if len(parrafos) == 1:
            ors = oraciones(parrafos[0])
            tam = max(2, -(-len(ors) // max_secciones))
            parrafos = [" ".join(ors[i:i + tam]) for i in range(0, len(ors), tam)]
        for p in parrafos:
            grupos.append({"subtitulo": None, "parrafos": [p]})

    # Si hay demasiados grupos, fusiona los más pequeños en orden.
    while len(grupos) > max_secciones:
        tam = [sum(len(p) for p in g["parrafos"]) for g in grupos]
        i = min(range(len(grupos) - 1), key=lambda k: tam[k] + tam[k + 1])
        a, b = grupos[i], grupos.pop(i + 1)
        a["parrafos"] += ([b["subtitulo"] + "."] if b["subtitulo"] else []) + b["parrafos"]

    # 3) Ideas primarias y secundarias
    secciones = []
    cuerpos = [" ".join(g["parrafos"]) or (g["subtitulo"] or "") for g in grupos]
    df = Counter(w for c in cuerpos for w in set(palabras(c)))
    excluir = set(palabras(titulo))
    formas = _forma_original(todo)
    for g, cuerpo in zip(grupos, cuerpos):
        sub = g["subtitulo"] or _subtitulo_generado(cuerpo, df, len(cuerpos), excluir, formas)
        principales, resto = [], []
        for p in g["parrafos"]:
            ors = oraciones(p)
            if not ors:
                continue
            principales.append(ors[0])
            resto.extend(ors[1:])
        if len(principales) > max_principales:
            resto = principales[max_principales:] + resto
            principales = principales[:max_principales]
        if len(principales) < min(2, max_principales) and resto:
            principales.append(resto.pop(0))

        def puntaje(o: str) -> float:
            ws = palabras(o)
            return sum(min(frec[w], 6) for w in ws) / (len(ws) ** 0.5 + 1)

        sec_orden = sorted(resto, key=puntaje, reverse=True)[:max_secundarias]
        secundarias = [o for o in resto if o in sec_orden]
        secciones.append({
            "subtitulo": etiqueta(sub, 7),
            "conector": conector_seccion(cuerpo),
            "ideas_principales": [acortar(o, 16) for o in principales] or [acortar(cuerpo, 16)],
            "ideas_secundarias": [acortar(o, 13) for o in secundarias],
            "busqueda_imagen": " ".join([w for w, _ in Counter(palabras(sub + " " + sub + " " + cuerpo)).most_common(2)]),
        })

    resumen_fuente = oraciones(next((t for n, t in _bloques(texto) if n == 0), todo))
    estructura = {
        "titulo": acortar(titulo, 10).rstrip("…"),
        "resumen": acortar(" ".join(resumen_fuente[:2]), 32) if resumen_fuente else "",
        "secciones": secciones,
        "conectores": [{"conector": d["conector"], "tipo": d["tipo"]} for d in detectar_conectores(todo)[:10]],
        "palabras_clave": [w for w, _ in frec.most_common(12)],
        "datos": extraer_datos(todo),
        "eventos": extraer_eventos(todo),
        "busqueda_imagen": " ".join(w for w, _ in frec.most_common(2)) or titulo,
    }
    return estructura


def extraer_datos(texto: str, maximo: int = 4) -> list[dict]:
    datos = []
    for o in oraciones(texto):
        m = re.search(r"((?:\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(?:%|°C|°|km²|km|kg|toneladas|millones|mil|años|horas|metros)?)", o)
        if not m:
            continue
        valor = m.group(1).strip()
        if len(re.sub(r"\D", "", valor)) < 2 and "%" not in valor:
            continue
        if re.fullmatch(r"(1[0-9]{3}|20[0-9]{2})", valor):  # años → línea de tiempo
            continue
        datos.append({"valor": valor, "texto": acortar(o, 12)})
        if len(datos) >= maximo:
            break
    return datos


def extraer_eventos(texto: str, maximo: int = 8) -> list[dict]:
    eventos = []
    for o in oraciones(texto):
        m = re.search(r"\b((?:siglo\s+[IVXLC]+)|(?:1[0-9]{3}|20[0-9]{2}))\b", o, flags=re.I)
        if m:
            eventos.append({"fecha": m.group(1), "hecho": acortar(o, 14)})
    def clave(e):
        f = e["fecha"]
        return int(f) if f.isdigit() else 0
    if all(e["fecha"].isdigit() for e in eventos):
        eventos.sort(key=clave)
    return eventos[:maximo]


def _lista(x) -> list:
    if x is None:
        return []
    if isinstance(x, str):
        return [s.strip() for s in x.split("\n") if s.strip()]
    return [str(i).strip() if not isinstance(i, dict) else i for i in x if i]


def normalizar(e: dict) -> dict:
    """Completa claves faltantes y deduce los datos específicos de cada organizador."""
    e = dict(e or {})
    e["titulo"] = str(e.get("titulo") or "Tema central").strip()
    e["resumen"] = str(e.get("resumen") or "").strip()
    secs = []
    for s in e.get("secciones") or []:
        if not isinstance(s, dict):
            continue
        secs.append({
            "subtitulo": str(s.get("subtitulo") or "Aspecto").strip(),
            "conector": str(s.get("conector") or "incluye").strip(),
            "ideas_principales": _lista(s.get("ideas_principales")),
            "ideas_secundarias": _lista(s.get("ideas_secundarias")),
            "busqueda_imagen": str(s.get("busqueda_imagen") or s.get("subtitulo") or "").strip(),
        })
    if not secs:
        secs = [{"subtitulo": "Idea central", "conector": "incluye", "ideas_principales": [e["resumen"] or e["titulo"]],
                 "ideas_secundarias": [], "busqueda_imagen": e["titulo"]}]
    e["secciones"] = secs
    e["conectores"] = [c if isinstance(c, dict) else {"conector": str(c), "tipo": ""} for c in (e.get("conectores") or [])]
    e["palabras_clave"] = _lista(e.get("palabras_clave"))
    e["datos"] = [d for d in (e.get("datos") or []) if isinstance(d, dict) and d.get("valor")]
    e["busqueda_imagen"] = str(e.get("busqueda_imagen") or e["titulo"])

    # Línea de tiempo
    ev = [x for x in (e.get("eventos") or []) if isinstance(x, dict) and x.get("hecho")]
    if len(ev) < 3:
        ev = [{"fecha": f"Etapa {i + 1}", "hecho": s["subtitulo"] + (": " + s["ideas_principales"][0] if s["ideas_principales"] else "")}
              for i, s in enumerate(secs)]
    e["eventos"] = ev

    # Pasos (flujo y cadena de secuencias)
    pasos = _lista(e.get("pasos"))
    if len(pasos) < 3:
        pasos = []
        for s in secs:
            pasos.append(s["subtitulo"] + (": " + etiqueta(s["ideas_principales"][0], 9) if s["ideas_principales"] else ""))
    e["pasos"] = pasos

    # Causa-efecto
    ce = e.get("causa_efecto") or {}
    cats = [c for c in (ce.get("categorias") or []) if isinstance(c, dict) and c.get("nombre")]
    if not cats:
        cats = [{"nombre": s["subtitulo"], "causas": [etiqueta(i, 9) for i in (s["ideas_principales"] + s["ideas_secundarias"])[:3]]}
                for s in secs[:6]]
    e["causa_efecto"] = {"efecto": str(ce.get("efecto") or e["titulo"]), "categorias": cats}

    # Comparación
    comp = e.get("comparacion") or {}
    elems = [x for x in (comp.get("elementos") or []) if isinstance(x, dict) and x.get("nombre")]
    criterios = _lista(comp.get("criterios"))
    if not elems or not criterios:
        criterios = ["Idea principal", "Características", "Detalle o ejemplo"]
        elems = []
        for s in secs[:5]:
            p = s["ideas_principales"]
            sec = s["ideas_secundarias"]
            elems.append({"nombre": s["subtitulo"], "valores": [
                p[0] if p else "—",
                " ".join(p[1:3]) or (sec[0] if sec else "—"),
                (sec[0] if sec and len(p) > 1 else (sec[1] if len(sec) > 1 else "—")),
            ]})
    for x in elems:
        vals = _lista(x.get("valores"))
        x["valores"] = (vals + ["—"] * len(criterios))[:len(criterios)]
    e["comparacion"] = {"criterios": criterios, "elementos": elems}

    # Venn
    venn = e.get("venn") or {}
    conj = [c for c in (venn.get("conjuntos") or []) if isinstance(c, dict) and c.get("nombre")]
    if len(conj) < 2:
        base = secs[:3] if len(secs) >= 3 else (secs + secs)[:2]
        conj = [{"nombre": s["subtitulo"], "elementos": [etiqueta(i, 9) for i in (s["ideas_principales"] + s["ideas_secundarias"])[:3]]}
                for s in base[:3]]
        sets = [set(palabras(" ".join([s["subtitulo"]] + s["ideas_principales"] + s["ideas_secundarias"]))) for s in base[:3]]
        comunes = set.intersection(*sets) if sets else set()
        comunes_l = [w.capitalize() for w in e["palabras_clave"] if w in comunes][:3] or [e["titulo"]]
        venn = {"comunes": comunes_l}
    e["venn"] = {"conjuntos": conj[:3], "comunes": _lista(venn.get("comunes")) or [e["titulo"]]}

    # Cuadro T
    ct = e.get("cuadro_t") or {}
    if not (ct.get("izquierda") and ct.get("derecha")):
        pos = next((s for s in secs if any(k in _sin_tildes(s["subtitulo"].lower()) for k in POSITIVAS)), None)
        neg = next((s for s in secs if any(k in _sin_tildes(s["subtitulo"].lower()) for k in NEGATIVAS)), None)
        if pos and neg and pos is not neg:
            a, b = pos, neg
        elif len(secs) >= 2:
            a, b = secs[0], secs[1]
        else:
            a = b = secs[0]
        def col(s):
            return {"titulo": s["subtitulo"], "elementos": [acortar(i, 14) for i in (s["ideas_principales"] + s["ideas_secundarias"])[:5]]}
        ct = {"izquierda": col(a), "derecha": col(b)}
    for lado in ("izquierda", "derecha"):
        ct[lado] = {"titulo": str(ct[lado].get("titulo", "")), "elementos": _lista(ct[lado].get("elementos"))}
    e["cuadro_t"] = ct

    # Atributos (rueda)
    atr = _lista(e.get("atributos"))
    if len(atr) < 4:
        atr = [s["subtitulo"] for s in secs]
        usadas = " ".join(atr).lower()
        for w in e["palabras_clave"]:
            if len(atr) >= 8:
                break
            if w not in usadas:
                atr.append(w.capitalize())
                usadas += " " + w
    e["atributos"] = atr[:10]
    return e


def a_texto_esquema(e: dict) -> str:
    """Resumen jerárquico en texto plano (para copiar/pegar)."""
    out = [e["titulo"].upper(), ""]
    if e.get("resumen"):
        out += [e["resumen"], ""]
    for i, s in enumerate(e["secciones"], 1):
        out.append(f"{i}. {s['subtitulo']}  [conector: {s['conector']}]")
        for p in s["ideas_principales"]:
            out.append(f"   • {p}")
        for q in s["ideas_secundarias"]:
            out.append(f"      – {q}")
    if e.get("conectores"):
        out += ["", "Conectores lógicos: " + ", ".join(f"{c['conector']} ({c['tipo']})" for c in e["conectores"])]
    return "\n".join(out)
