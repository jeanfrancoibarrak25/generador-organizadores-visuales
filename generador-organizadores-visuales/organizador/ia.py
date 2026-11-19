"""Mejora y estructuración de la información con Inteligencia Artificial.

Proveedores admitidos (se usa la API REST directamente, sin SDK):
  - Google Gemini (tiene nivel gratuito)   → https://aistudio.google.com/apikey
  - Groq (tiene nivel gratuito)            → https://console.groq.com/keys
  - OpenAI                                 → https://platform.openai.com/api-keys
  - Anthropic Claude                       → https://console.anthropic.com/
"""
from __future__ import annotations

import json
import re

import requests

PROVEEDORES = {
    "Google Gemini": {"modelo": "gemini-2.5-flash", "secreto": "GEMINI_API_KEY"},
    "Groq (Llama)": {"modelo": "llama-3.3-70b-versatile", "secreto": "GROQ_API_KEY"},
    "OpenAI": {"modelo": "gpt-4o-mini", "secreto": "OPENAI_API_KEY"},
    "Anthropic Claude": {"modelo": "claude-sonnet-5-5", "secreto": "ANTHROPIC_API_KEY"},
}

ESQUEMA = """{
  "titulo": "título breve del tema (máx. 8 palabras)",
  "resumen": "1-2 oraciones que sinteticen el tema",
  "secciones": [
    {
      "subtitulo": "subtítulo o subtema (máx. 6 palabras)",
      "conector": "conector lógico o palabra de enlace que une el título con esta sección (p. ej.: se divide en, incluye, porque, por lo tanto, además, se caracteriza por, provoca, a diferencia de)",
      "ideas_principales": ["idea primaria breve (máx. 16 palabras)", "..."],
      "ideas_secundarias": ["idea secundaria, detalle o ejemplo (máx. 14 palabras)", "..."],
      "busqueda_imagen": "2-4 palabras EN INGLÉS para buscar una foto de referencia de esta sección"
    }
  ],
  "conectores": [{"conector": "por lo tanto", "tipo": "consecuencia"}],
  "palabras_clave": ["8 a 12 palabras clave"],
  "datos": [{"valor": "50 %", "texto": "qué representa la cifra"}],
  "busqueda_imagen": "2-4 palabras EN INGLÉS para buscar una foto del tema central",
  "eventos": [{"fecha": "año o etapa", "hecho": "hecho breve"}],
  "pasos": ["paso 1 en orden", "¿pregunta de decisión? (solo si aplica)", "paso 3"],
  "causa_efecto": {"efecto": "problema o efecto", "categorias": [{"nombre": "categoría", "causas": ["causa breve"]}]},
  "comparacion": {"criterios": ["criterio 1", "criterio 2"], "elementos": [{"nombre": "elemento A", "valores": ["valor para criterio 1", "valor para criterio 2"]}]},
  "venn": {"conjuntos": [{"nombre": "A", "elementos": ["exclusivo de A"]}, {"nombre": "B", "elementos": ["exclusivo de B"]}], "comunes": ["en común"]},
  "cuadro_t": {"izquierda": {"titulo": "p. ej. Ventajas", "elementos": ["..."]}, "derecha": {"titulo": "p. ej. Desventajas", "elementos": ["..."]}},
  "atributos": ["6 a 8 atributos o características del tema central (1-4 palabras cada uno)"]
}"""

REGLAS = """Reglas:
- Responde SOLO con un objeto JSON válido (sin Markdown ni comentarios), en español.
- Usa únicamente la información proporcionada; no inventes datos, cifras ni fechas. Si un campo no aplica, déjalo como lista vacía.
- Organiza la información de forma jerárquica: título → subtítulos → ideas principales → ideas secundarias.
- Las ideas deben ser frases breves, claras y parafraseadas (no copies párrafos completos).
- Elige conectores lógicos coherentes con la relación real entre las ideas (causa, consecuencia, adición, contraste, ejemplo, secuencia).
- Entre {min_s} y {max_s} secciones; de 1 a {max_p} ideas principales y de 0 a {max_q} secundarias por sección.
- "eventos" solo si hay fechas o etapas cronológicas; "pasos" en el orden lógico del proceso.
- En "comparacion" todos los elementos deben tener un valor por cada criterio.
"""


class ErrorIA(Exception):
    pass


def _llamar(proveedor: str, clave: str, modelo: str, sistema: str, usuario: str, tiempo: int = 120) -> str:
    if not clave:
        raise ErrorIA("Falta la clave de API (API key) del proveedor de IA.")
    try:
        if proveedor == "Google Gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            r = requests.post(url, params={"key": clave}, timeout=tiempo, json={
                "systemInstruction": {"parts": [{"text": sistema}]},
                "contents": [{"role": "user", "parts": [{"text": usuario}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
            })
            r.raise_for_status()
            partes = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in partes)
        if proveedor in ("OpenAI", "Groq (Llama)"):
            base = "https://api.openai.com/v1" if proveedor == "OpenAI" else "https://api.groq.com/openai/v1"
            r = requests.post(f"{base}/chat/completions", timeout=tiempo,
                              headers={"Authorization": f"Bearer {clave}"},
                              json={"model": modelo, "temperature": 0.4,
                                    "response_format": {"type": "json_object"},
                                    "messages": [{"role": "system", "content": sistema},
                                                 {"role": "user", "content": usuario}]})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        if proveedor == "Anthropic Claude":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=tiempo,
                              headers={"x-api-key": clave, "anthropic-version": "2023-06-01"},
                              json={"model": modelo, "max_tokens": 8000, "system": sistema,
                                    "messages": [{"role": "user", "content": usuario}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    except requests.HTTPError as ex:
        detalle = ""
        try:
            detalle = ex.response.json()
            detalle = json.dumps(detalle, ensure_ascii=False)[:400]
        except Exception:  # noqa: BLE001
            detalle = (ex.response.text or "")[:400]
        raise ErrorIA(f"El proveedor respondió con error {ex.response.status_code}: {detalle}") from ex
    except requests.RequestException as ex:
        raise ErrorIA(f"No se pudo conectar con el proveedor de IA: {ex}") from ex
    except (KeyError, IndexError) as ex:
        raise ErrorIA("La respuesta de la IA no tiene el formato esperado.") from ex
    raise ErrorIA(f"Proveedor desconocido: {proveedor}")


def _json(texto: str) -> dict:
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        a, b = texto.find("{"), texto.rfind("}")
        if a >= 0 and b > a:
            try:
                return json.loads(texto[a:b + 1])
            except json.JSONDecodeError:
                pass
    raise ErrorIA("La IA no devolvió un JSON válido. Intenta de nuevo o cambia de modelo.")


def _sistema(max_s, max_p, max_q) -> str:
    return ("Eres un experto en pedagogía y en organizadores visuales (mapas conceptuales, mentales, cuadros "
            "sinópticos, líneas de tiempo, diagramas de flujo, Ishikawa, etc.). Analizas textos académicos y los "
            "estructuras en título, subtítulos, ideas primarias, ideas secundarias y conectores lógicos.\n\n"
            f"Devuelve un JSON con este esquema:\n{ESQUEMA}\n\n"
            + REGLAS.format(min_s=min(3, max_s), max_s=max_s, max_p=max_p, max_q=max_q))


def estructurar(texto: str, proveedor: str, clave: str, modelo: str, max_secciones=6, max_principales=3,
                max_secundarias=4, instrucciones: str = "") -> dict:
    texto = texto.strip()
    if len(texto) > 60000:
        texto = texto[:60000]
    usuario = "Organiza la siguiente información:\n\n<<<\n" + texto + "\n>>>"
    if instrucciones:
        usuario += "\n\nIndicaciones adicionales del usuario: " + instrucciones
    return _json(_llamar(proveedor, clave, modelo, _sistema(max_secciones, max_principales, max_secundarias), usuario))


def mejorar(estructura: dict, proveedor: str, clave: str, modelo: str, organizador: str = "", instrucciones: str = "",
            texto_fuente: str = "", max_secciones=6, max_principales=3, max_secundarias=4) -> dict:
    usuario = ("Mejora este organizador visual: redacta ideas más claras y breves, corrige ortografía, jerarquiza "
               "mejor (título, subtítulos, ideas primarias y secundarias), elige conectores lógicos precisos y "
               "completa los campos específicos coherentes con la información.\n")
    if organizador:
        usuario += f"El usuario lo va a presentar como: {organizador}. Optimiza especialmente los campos que ese organizador usa.\n"
    if instrucciones:
        usuario += f"Indicaciones del usuario: {instrucciones}\n"
    usuario += "\nEstructura actual (JSON):\n" + json.dumps(estructura, ensure_ascii=False)
    if texto_fuente:
        usuario += "\n\nTexto original de referencia:\n<<<\n" + texto_fuente[:30000] + "\n>>>"
    return _json(_llamar(proveedor, clave, modelo, _sistema(max_secciones, max_principales, max_secundarias), usuario))


def probar(proveedor: str, clave: str, modelo: str) -> str:
    r = _llamar(proveedor, clave, modelo, "Responde solo con JSON.", 'Devuelve {"ok": true}')
    return r[:200]
