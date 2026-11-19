"""Generador de Organizadores Visuales — aplicación Streamlit.

Ejecutar localmente:  streamlit run app.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from organizador import exportar, extractor, ia, imagenes
from organizador.estructura import (CLAVES_BASE, CLAVES_ESPECIFICAS, a_texto_esquema, analizar, normalizar)
from organizador.render import ORGANIZADORES, generar
from organizador.svgkit import TEMAS

st.set_page_config(page_title="Generador de Organizadores Visuales", page_icon="🧠", layout="wide")

ss = st.session_state
for k, v in {"base": None, "extras": {}, "ver": 0, "texto_fuente": "", "candidatos": {}, "elegidas": {},
             "propias": {}}.items():
    ss.setdefault(k, v)

CARPETA = Path(__file__).resolve().parent
try:
    EJEMPLO = (CARPETA / "ejemplos" / "fotosintesis.txt").read_text(encoding="utf-8")
except OSError:
    EJEMPLO = ("# La fotosíntesis\n\nLa fotosíntesis es el proceso mediante el cual las plantas transforman la energía "
               "luminosa en energía química. Gracias a este proceso se produce el oxígeno.\n\n## Fase luminosa\n\n"
               "Ocurre en los tilacoides y necesita luz. Por lo tanto, se libera oxígeno.\n\n## Fase oscura\n\n"
               "Ocurre en el estroma. Sin embargo, usa la energía producida en la fase luminosa.")

# Organizadores que usan imágenes por sección (el resto usa solo la del título)
USAN_IMG_SECCION = {"Mapa conceptual", "Infografía"}
USAN_IMG_TITULO = {"Mapa conceptual", "Mapa mental", "Mapa de ideas o telaraña", "Infografía", "Mapa semántico",
                   "Rueda de atributos"}


def _secreto(nombre: str) -> str:
    try:
        return st.secrets.get(nombre, "")
    except Exception:  # noqa: BLE001 - no hay secrets.toml
        return ""


def cargar(d: dict):
    ss.base = {k: d.get(k) for k in CLAVES_BASE if k in d}
    ss.extras = {k: d[k] for k in CLAVES_ESPECIFICAS if d.get(k)}
    ss.ver += 1
    ss.candidatos, ss.elegidas, ss.propias = {}, {}, {}


def sugerir(e: dict) -> list[str]:
    tipos = {c.get("tipo") for c in e.get("conectores", [])}
    sug = ["Mapa conceptual", "Cuadro sinóptico"]
    if any(str(x.get("fecha", "")).isdigit() for x in e["eventos"]):
        sug.insert(0, "Línea de tiempo")
    if "secuencia" in tipos:
        sug += ["Diagrama de flujo", "Cadena de secuencias"]
    if "contraste" in tipos:
        sug += ["Cuadro comparativo", "Diagrama de Venn", "Cuadro T"]
    if tipos & {"causa", "consecuencia"}:
        sug.append("Diagrama de causa-efecto (espina de pescado)")
    if e.get("datos"):
        sug.append("Infografía")
    return list(dict.fromkeys(sug))[:5]


@st.cache_data(show_spinner=False, ttl=3600)
def _descargar(url: str) -> str:
    return imagenes.descargar(url)


@st.cache_data(show_spinner=False, ttl=3600)
def _buscar(consulta: str, fuentes: tuple) -> list[dict]:
    return imagenes.buscar(consulta, fuentes, n=3)


def _tam_svg(svg: str) -> tuple[float, float]:
    m = re.search(r'width="([\d.]+)" height="([\d.]+)"', svg)
    return (float(m.group(1)), float(m.group(2))) if m else (1000, 700)


def mostrar_svg(svg: str, ancho_vista: int = 1150):
    """Muestra el SVG ajustado al ancho disponible (con desplazamiento si es muy alto)."""
    w, h = _tam_svg(svg)
    ancho_px = min(w, ancho_vista)
    alto_px = h * ancho_px / w
    estilo_caja = "max-height:1600px;overflow:auto;" if alto_px > 1600 else ""
    st.html(f"<div style='{estilo_caja}text-align:center;border:1px solid #e5e7eb;border-radius:12px;padding:8px'>"
            f"<div style='display:inline-block;width:100%;max-width:{ancho_px:.0f}px'>"
            + svg.replace("<svg ", "<svg style='width:100%;height:auto' ", 1) + "</div></div>")


# ---------------------------------------------------------------------------
# Barra lateral: configuración
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox("Tema de colores", list(TEMAS))
    secundarias = st.toggle("Mostrar ideas secundarias", value=True)
    st.caption("Nivel de detalle del análisis")
    max_s = st.slider("Máx. subtítulos (secciones)", 3, 8, 5)
    max_p = st.slider("Máx. ideas principales por sección", 1, 4, 2)
    max_q = st.slider("Máx. ideas secundarias por sección", 0, 5, 2)

    st.divider()
    st.header("🤖 Inteligencia Artificial")
    proveedor = st.selectbox("Proveedor", list(ia.PROVEEDORES))
    info = ia.PROVEEDORES[proveedor]
    clave = st.text_input("Clave de API (API key)", value=_secreto(info["secreto"]), type="password",
                          help="Gemini y Groq ofrecen claves gratuitas. La clave no se guarda: solo se usa en esta sesión.")
    modelo = st.text_input("Modelo", value=info["modelo"])
    st.caption("Claves gratis: [Gemini](https://aistudio.google.com/apikey) · [Groq](https://console.groq.com/keys)")
    if st.button("Probar conexión", width="stretch"):
        try:
            ia.probar(proveedor, clave, modelo)
            st.success("Conexión correcta ✅")
        except ia.ErrorIA as ex:
            st.error(str(ex))

# ---------------------------------------------------------------------------
# Paso 1: información
# ---------------------------------------------------------------------------
st.title("🧠 Generador de Organizadores Visuales")
st.write("Organiza cualquier información en **título, subtítulos, ideas primarias, ideas secundarias y conectores "
         "lógicos**, y genera 16 tipos de organizadores visuales, con imágenes referenciales de la web y mejora con IA.")

st.subheader("1. Información")
t1, t2, t3, t4 = st.tabs(["✍️ Escribir o pegar texto", "📄 Subir archivo", "🔗 Enlace web", "💾 Abrir proyecto"])
texto_nuevo = None
with t1:
    if st.button("Cargar texto de ejemplo"):
        ss["txt_entrada"] = EJEMPLO
    txt = st.text_area("Texto", key="txt_entrada", height=220,
                       placeholder="Pega aquí tu información. Puedes marcar títulos con # y subtítulos con ##.")
    if txt.strip():
        texto_nuevo = txt
with t2:
    arch = st.file_uploader("Word (.docx), PDF, TXT o MD", type=["docx", "pdf", "txt", "md"])
    if arch is not None:
        try:
            texto_nuevo = extractor.desde_archivo(arch.name, arch.getvalue())
            st.success(f"Se leyeron {len(texto_nuevo.split())} palabras de «{arch.name}».")
        except Exception as ex:  # noqa: BLE001
            st.error(f"No se pudo leer el archivo: {ex}")
with t3:
    url = st.text_input("Enlace (URL) de una página web")
    if url:
        try:
            texto_nuevo = extractor.desde_url(url)
            st.success(f"Se extrajeron {len(texto_nuevo.split())} palabras de la página.")
            with st.expander("Ver texto extraído"):
                st.text(texto_nuevo[:5000])
        except Exception as ex:  # noqa: BLE001
            st.error(f"No se pudo leer la página: {ex}")
with t4:
    proy = st.file_uploader("Proyecto guardado (.json)", type=["json"], key="proy")
    if proy is not None and st.button("Abrir proyecto"):
        d = json.loads(proy.getvalue().decode("utf-8"))
        ss.texto_fuente = d.get("texto_fuente", "")
        cargar(d.get("estructura", d))
        st.rerun()

instr = st.text_input("Indicaciones para la IA (opcional)",
                      placeholder="Ej.: enfócate en las causas; usa lenguaje para estudiantes de secundaria")
c1, c2 = st.columns(2)
if c1.button("📑 Organizar información (sin IA)", type="primary", width="stretch", disabled=not texto_nuevo):
    try:
        ss.texto_fuente = texto_nuevo
        cargar(analizar(texto_nuevo, max_s, max_p, max_q))
        st.rerun()
    except ValueError as ex:
        st.error(str(ex))
if c2.button("✨ Organizar con IA", width="stretch", disabled=not texto_nuevo):
    with st.spinner("La IA está analizando y estructurando la información…"):
        try:
            ss.texto_fuente = texto_nuevo
            cargar(ia.estructurar(texto_nuevo, proveedor, clave, modelo, max_s, max_p, max_q, instr))
            st.rerun()
        except ia.ErrorIA as ex:
            st.error(str(ex))

if not ss.base:
    st.info("Escribe, sube o enlaza tu información y pulsa **Organizar información**.")
    st.stop()

# ---------------------------------------------------------------------------
# Paso 2: estructura editable
# ---------------------------------------------------------------------------
st.subheader("2. Estructura de la información")
v = ss.ver
base = ss.base
col_a, col_b = st.columns([2, 3])
titulo = col_a.text_input("Título", value=base.get("titulo", ""), key=f"tit{v}")
resumen = col_b.text_input("Resumen", value=base.get("resumen", ""), key=f"res{v}")

secciones = []
for i, s in enumerate(base.get("secciones") or []):
    with st.expander(f"Subtítulo {i + 1}: {s.get('subtitulo', '')}", expanded=False):
        a, b, c = st.columns([3, 2, 1])
        sub = a.text_input("Subtítulo", value=s.get("subtitulo", ""), key=f"sub{v}_{i}")
        con = b.text_input("Conector lógico", value=s.get("conector", ""), key=f"con{v}_{i}",
                           help="Palabra de enlace entre el título y este subtítulo (se muestra en el mapa conceptual).")
        borrar = c.checkbox("Quitar", key=f"del{v}_{i}")
        ip = st.text_area("Ideas principales (una por línea)", value="\n".join(s.get("ideas_principales") or []),
                          key=f"ip{v}_{i}", height=100)
        isec = st.text_area("Ideas secundarias (una por línea)", value="\n".join(s.get("ideas_secundarias") or []),
                            key=f"is{v}_{i}", height=90)
        bus = st.text_input("Búsqueda de imagen", value=s.get("busqueda_imagen", ""), key=f"bus{v}_{i}")
        if not borrar:
            secciones.append({"subtitulo": sub, "conector": con, "ideas_principales": [x for x in ip.split("\n") if x.strip()],
                              "ideas_secundarias": [x for x in isec.split("\n") if x.strip()], "busqueda_imagen": bus})

actual = dict(base, titulo=titulo, resumen=resumen, secciones=secciones)
b1, b2, b3 = st.columns(3)
if b1.button("➕ Agregar subtítulo", width="stretch"):
    actual["secciones"].append({"subtitulo": "Nuevo subtítulo", "conector": "incluye", "ideas_principales": ["Nueva idea"],
                                "ideas_secundarias": [], "busqueda_imagen": ""})
    ss.base = actual
    ss.ver += 1
    st.rerun()
if b2.button("✔️ Aplicar cambios / quitar marcados", width="stretch"):
    ss.base = actual
    ss.ver += 1
    st.rerun()

e = normalizar({**actual, **ss.extras})

if e.get("conectores"):
    st.caption("**Conectores lógicos detectados:** " + " · ".join(f"{c['conector']} ({c['tipo']})" if c.get("tipo") else c["conector"]
                                                                   for c in e["conectores"]))

with st.expander("🔧 Datos específicos (línea de tiempo, pasos, causas, comparación, Venn, cuadro T, atributos)"):
    st.caption("Se calculan automáticamente a partir de los subtítulos e ideas. Puedes editarlos aquí (formato JSON).")
    extras_txt = st.text_area("JSON", value=json.dumps({k: e[k] for k in CLAVES_ESPECIFICAS}, ensure_ascii=False, indent=2),
                              height=300, key=f"ext{v}_{hash(json.dumps(ss.extras, sort_keys=True))}")
    x1, x2 = st.columns(2)
    if x1.button("Aplicar datos específicos"):
        try:
            ss.extras = json.loads(extras_txt)
            ss.base = actual
            ss.ver += 1
            st.rerun()
        except json.JSONDecodeError as ex:
            st.error(f"JSON inválido: {ex}")
    if x2.button("Recalcular automáticamente"):
        ss.extras = {}
        ss.base = actual
        ss.ver += 1
        st.rerun()

# Mejora con IA
with st.container(border=True):
    st.markdown("**✨ Mejorar el trabajo con IA**")
    m1, m2 = st.columns([3, 1])
    instr_m = m1.text_input("¿Qué quieres mejorar?", key="instr_m",
                            placeholder="Ej.: ideas más cortas, mejores conectores, agrega ejemplos, nivel universitario")
    objetivo = m2.selectbox("Optimizar para", ["(todos)"] + list(ORGANIZADORES), key="obj_m")
    if st.button("✨ Mejorar con IA", width="stretch"):
        with st.spinner("La IA está mejorando la organización…"):
            try:
                mejorado = ia.mejorar(e, proveedor, clave, modelo, "" if objetivo == "(todos)" else objetivo, instr_m,
                                      ss.texto_fuente, max_s, max_p, max_q)
                elegidas = ss.elegidas
                cargar(mejorado)
                ss.elegidas = elegidas
                st.rerun()
            except ia.ErrorIA as ex:
                st.error(str(ex))

# ---------------------------------------------------------------------------
# Paso 3: imágenes referenciales
# ---------------------------------------------------------------------------
st.subheader("3. Imágenes referenciales (opcional)")
usar_img = st.toggle("Agregar imágenes referenciales extraídas de la web", value=bool(ss.elegidas))
if usar_img:
    f1, f2 = st.columns([3, 1])
    fuentes = f1.multiselect("Fuentes (imágenes de licencia libre)", ["Wikimedia Commons", "Openverse"],
                             default=["Wikimedia Commons", "Openverse"])
    nodos = [("titulo", e["titulo"], e.get("busqueda_imagen") or e["titulo"])] + [
        (i, s["subtitulo"], s.get("busqueda_imagen") or s["subtitulo"]) for i, s in enumerate(e["secciones"])]
    if f2.button("🔎 Buscar imágenes", width="stretch"):
        with st.spinner("Buscando imágenes…"):
            errores = []
            for clave_n, nombre, consulta in nodos:
                try:
                    ss.candidatos[clave_n] = _buscar(consulta, tuple(fuentes))
                except Exception as ex:  # noqa: BLE001
                    errores.append(f"{nombre}: {ex}")
            if errores:
                st.warning("Algunas búsquedas fallaron: " + " | ".join(errores[:3]))
    st.caption("Elige una imagen para cada elemento (o sube la tuya). El título se usa en mapas mental, conceptual, "
               "semántico, telaraña, rueda e infografía; las de los subtítulos, en el mapa conceptual y la infografía.")
    for clave_n, nombre, consulta in nodos:
        cands = ss.candidatos.get(clave_n, [])
        with st.expander(f"🖼️ {'Título' if clave_n == 'titulo' else 'Subtítulo'}: {nombre}  —  búsqueda: «{consulta}»",
                         expanded=False):
            nueva = st.text_input("Cambiar búsqueda", value=consulta, key=f"q{v}_{clave_n}")
            if st.button("Buscar de nuevo", key=f"qb{v}_{clave_n}"):
                try:
                    ss.candidatos[clave_n] = cands = _buscar(nueva, tuple(fuentes))
                except Exception as ex:  # noqa: BLE001
                    st.warning(str(ex))
            if cands:
                cols = st.columns(len(cands))
                for j, (col, cand) in enumerate(zip(cols, cands)):
                    col.image(cand["miniatura"], width="stretch")
                    col.caption(imagenes.credito(cand))
                opciones = ["Sin imagen"] + [f"Imagen {j + 1}" for j in range(len(cands))]
                previa = ss.elegidas.get(clave_n, {}).get("idx", 0)
                sel = st.radio("Usar", opciones, index=min(previa, len(opciones) - 1), horizontal=True, key=f"r{v}_{clave_n}")
                idx = opciones.index(sel)
                if idx == 0:
                    ss.elegidas.pop(clave_n, None)
                elif ss.elegidas.get(clave_n, {}).get("idx") != idx:
                    try:
                        cand = cands[idx - 1]
                        ss.elegidas[clave_n] = {"idx": idx, "uri": _descargar(cand["miniatura"]),
                                                "credito": imagenes.credito(cand)}
                    except Exception as ex:  # noqa: BLE001
                        st.warning(f"No se pudo descargar la imagen: {ex}")
            propia = st.file_uploader("…o sube tu propia imagen", type=["png", "jpg", "jpeg", "webp"], key=f"up{v}_{clave_n}")
            if propia is not None:
                ss.elegidas[clave_n] = {"idx": 99, "uri": imagenes.a_data_uri(propia.getvalue()), "credito": ""}

imgs = {k: d["uri"] for k, d in ss.elegidas.items()} if usar_img else {}
creditos = [d["credito"] for d in ss.elegidas.values() if d.get("credito")] if usar_img else []

# ---------------------------------------------------------------------------
# Paso 4: organizador visual
# ---------------------------------------------------------------------------
st.subheader("4. Organizador visual")
sug = sugerir(e)
st.caption("Sugeridos para esta información: " + ", ".join(f"**{s}**" for s in sug))
tipo = st.selectbox("Tipo de organizador", list(ORGANIZADORES), index=list(ORGANIZADORES).index(sug[0]))
st.caption(ORGANIZADORES[tipo][1])
opc = {"secundarias": secundarias, "creditos": creditos}
svg = generar(tipo, e, tema, imgs, opc)
mostrar_svg(svg)

nombre = exportar.nombre_archivo(f"{tipo}_{e['titulo']}")
d1, d2, d3, d4 = st.columns(4)
try:
    d1.download_button("⬇️ PNG (alta resolución)", exportar.a_png(svg, 2.0), f"{nombre}.png", "image/png", width="stretch")
    d2.download_button("⬇️ PDF", exportar.a_pdf(svg), f"{nombre}.pdf", "application/pdf", width="stretch")
except Exception as ex:  # noqa: BLE001
    st.warning(f"No se pudo generar PNG/PDF en este servidor ({ex}). Descarga el SVG o el HTML.")
d3.download_button("⬇️ SVG (editable)", svg, f"{nombre}.svg", "image/svg+xml", width="stretch")
d4.download_button("⬇️ HTML", exportar.a_html(svg, e["titulo"]), f"{nombre}.html", "text/html", width="stretch")

st.divider()
z1, z2, z3 = st.columns(3)
if z1.button("📦 Preparar los 16 organizadores (ZIP)", width="stretch"):
    with st.spinner("Generando los 16 organizadores…"):
        todos = {t: generar(t, e, tema, imgs, opc) for t in ORGANIZADORES}
        ss["zip"] = exportar.zip_todos(todos)
if ss.get("zip"):
    z1.download_button("⬇️ Descargar ZIP", ss["zip"], exportar.nombre_archivo(e["titulo"]) + "_organizadores.zip",
                       "application/zip", width="stretch")
z2.download_button("⬇️ Esquema en texto (TXT)", a_texto_esquema(e), exportar.nombre_archivo(e["titulo"]) + "_esquema.txt",
                   width="stretch")
proyecto = {"texto_fuente": ss.texto_fuente, "estructura": {**actual, **ss.extras}}
z3.download_button("💾 Guardar proyecto (JSON)", json.dumps(proyecto, ensure_ascii=False, indent=2),
                   exportar.nombre_archivo(e["titulo"]) + "_proyecto.json", "application/json", width="stretch")

with st.expander("📋 Ver esquema jerárquico"):
    st.text(a_texto_esquema(e))
