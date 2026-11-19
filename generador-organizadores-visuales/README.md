# 🧠 Generador de Organizadores Visuales

Aplicación web (Python + Streamlit) que toma tu información (texto, Word, PDF o enlace web), la **organiza en
título, subtítulos, ideas primarias, ideas secundarias y conectores lógicos**, y genera **16 organizadores visuales**,
con **imágenes referenciales de la web** (opcional) y la opción de **mejorar el trabajo con IA**.

## Organizadores incluidos

| | | | |
|---|---|---|---|
| Mapa conceptual | Mapa mental | Mapa de ideas o telaraña | Cuadro sinóptico |
| Organigrama | Cuadro comparativo | Diagrama de Venn | Cuadro T |
| Línea de tiempo | Diagrama de flujo | Causa-efecto (espina de pescado) | Infografía |
| Mapa semántico | Rueda de atributos | Cadena de secuencias | Esquema de llaves |

## Funciones

- **Entrada:** escribir/pegar texto, subir `.docx`, `.pdf`, `.txt`, `.md`, o pegar un enlace web.
- **Organización automática (sin IA):** detecta títulos y subtítulos (encabezados de Word, `#`/`##`, numeración),
  extrae ideas principales y secundarias, conectores lógicos (causa, consecuencia, contraste, adición, secuencia…),
  palabras clave, cifras y fechas.
- **Organización y mejora con IA:** Google Gemini, Groq (ambos con clave gratuita), OpenAI o Anthropic Claude.
  La IA reescribe ideas breves, elige conectores precisos y completa los datos de cada organizador
  (fechas, pasos, causas, criterios de comparación, conjuntos de Venn, columnas del cuadro T, atributos).
- **Edición manual:** cada subtítulo, conector e idea se puede corregir antes de generar.
- **Imágenes referenciales:** búsqueda en Wikimedia Commons y Openverse (licencias libres, con créditos
  automáticos en el organizador) o subir tus propias imágenes.
- **5 temas de color:** Vivo, Pastel, Académico, Naturaleza, Oscuro.
- **Exportación:** PNG (alta resolución), PDF, SVG (editable en Inkscape/Illustrator/PowerPoint), HTML,
  ZIP con los 16 organizadores, esquema en texto y proyecto `.json` para seguir editando después.

## Ejecutar en tu computadora

```bash
pip install -r requirements.txt
streamlit run app.py
```

> En Windows, para exportar PNG/PDF instala también GTK/Cairo (https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer).
> Si no lo tienes, el SVG y el HTML funcionan igual.

## Publicar gratis en Streamlit Community Cloud

1. Entra a https://share.streamlit.io con tu cuenta de GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Repositorio: `jeanfrancoibarrak25/generador-organizadores-visuales`, rama `main`, archivo principal `app.py`.
4. (Opcional) En **Advanced settings → Secrets** pega tu clave de IA para no escribirla cada vez:
   ```toml
   GEMINI_API_KEY = "tu-clave"
   ```
5. **Deploy**. El archivo `packages.txt` instala Cairo y las fuentes para exportar PNG/PDF.

## Claves de IA gratuitas

- Google Gemini: https://aistudio.google.com/apikey
- Groq: https://console.groq.com/keys

## Estructura del proyecto

```
app.py                     Interfaz Streamlit
organizador/
  extractor.py             Lectura de texto, Word, PDF y páginas web
  estructura.py            Análisis: título, subtítulos, ideas, conectores, datos
  ia.py                    Estructuración y mejora con IA (Gemini, Groq, OpenAI, Claude)
  imagenes.py              Búsqueda de imágenes (Wikimedia Commons, Openverse)
  svgkit.py                Utilidades de dibujo SVG y temas de color
  render.py                Los 16 organizadores visuales
  exportar.py              PNG, PDF, SVG, HTML y ZIP
ejemplos/fotosintesis.txt  Texto de ejemplo
```
