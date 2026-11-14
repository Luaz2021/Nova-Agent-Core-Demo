"""Tipo ACTIVIDAD: el documento se guia por el ENUNCIADO, leido como lo leeria un alumno (12/11/2026, Claude).

Lee el enunciado en local (docx con su estructura de vinetas y tablas, pdf, txt, md) y saca, SIN IA:

REGLAS globales: formato pedido (presentacion, informe, poster, video...), extension (paginas, palabras,
  diapositivas, minutos), modalidad (individual / grupo), normas (APA...) y si hay rubrica.
REQUISITOS, uno por vineta (empiece como empiece) o por frase con verbo de encargo en un parrafo:
  - obligatorio: lo que hay que hacer ("Elabora...", "Elementos innovadores que...")
  - apartado:    vineta que acaba en ":" ("Descripcion del producto o servicio:")
  - pregunta:    pregunta que hay que contestar
  - ayuda:       preguntas que el enunciado da "de ayuda" / "orientativas": NO bloquean, solo se avisa
  - rubrica:     cada criterio de una tabla de evaluacion
  - entrega:     como entregar (subir, plazo...): se listan, no se cubren
Cada seccion del guion lleva "cubre": ["R2", "R5"]. cobertura() bloquea si falta un requisito que no sea de
ayuda ni de entrega, y avisa de las preguntas de ayuda que no se tocan.
"""

import json
import re
from pathlib import Path

ENUNCIADO, REQUISITOS = "enunciado.txt", "requisitos.json"

VERBOS = (
    "elabora|realiza|describe|explica|genera|indica|analiza|compara|incluye|presenta|redacta|justifica|define|"
    "identifica|diseña|disena|desarrolla|investiga|busca|responde|argumenta|valora|enumera|calcula|crea|haz|"
    "elige|selecciona|propón|propon|plantea|reflexiona|resume|detalla|expón|expon|aporta|adjunta|piensa|"
    "elaborad|realizad|describid|explicad|generad|analizad|presentad|redactad|cread|haced|responded"
)
ENTRADAS = r"(?:(?:para ello|adem[aá]s|tambi[eé]n|a continuaci[oó]n|despu[eé]s|luego|por [uú]ltimo|finalmente|y),?\s+)?"
RE_TAREA = re.compile(rf"^{ENTRADAS}(?:{VERBOS})\b", re.IGNORECASE)
RE_ENTREGA = re.compile(
    r"^(?:sub(?:e|ir|id)|entrega(?:r|d)?\b|env[ií]a|fecha|plazo|formato de entrega|m[eé]todo de entrega)",
    re.IGNORECASE,
)
RE_AYUDA = re.compile(
    r"(?i)sirvan? de ayuda|a modo de (?:gu[ií]a|ayuda|ejemplo)|orientativ|puedes apoyarte|pod[eé]is apoyaros|"
    r"te planteo|os planteo|como gu[ií]a|por ejemplo"
)
FORMATOS = [  # el primero que aparezca manda
    (
        "presentación",
        r"presentaci[oó]n(?! de la actividad)|diapositivas|powerpoint|slides|pitch",
    ),
    ("póster", r"p[oó]ster|infograf[ií]a|cartel"),
    ("vídeo", r"\bv[ií]deo\b|grabaci[oó]n"),
    ("informe", r"informe|memoria|documento escrito|ensayo|trabajo escrito"),
]
RE_EXTENSION = re.compile(
    r"(?:m[aá]ximo|m[ií]nimo|entre|hasta|no m[aá]s de|al menos)?\s*(\d+)(?:\s*(?:-|a|y)\s*(\d+))?\s*"
    r"(p[aá]ginas|folios|palabras|diapositivas|minutos|caracteres)",
    re.IGNORECASE,
)
RE_RUBRICA = re.compile(
    r"(?i)criterio|puntuaci[oó]n|peso|ponderaci[oó]n|r[uú]brica|calificaci[oó]n"
)


# ------------------------------------------------------------------ lectura con estructura


def _lineas_docx(archivo: Path) -> list[tuple[str, str]]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = docx.Document(archivo)
    lineas = []
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            p = Paragraph(el, doc)
            texto = p.text.strip()
            if not texto:
                continue
            estilo = (p.style.name or "").lower()
            if estilo.startswith(("heading", "título", "titulo", "title")):
                lineas.append(("titulo", texto))
            elif el.xpath(".//*[local-name()='numPr']") or re.search(
                r"list|lista|vi[ñn]eta|bullet", estilo
            ):
                lineas.append(("vineta", texto))
            else:
                lineas.append(("parrafo", texto))
        elif el.tag.endswith("}tbl"):
            for fila in Table(el, doc).rows:
                celdas = []
                for c in fila.cells:
                    t = c.text.strip().replace("\n", " / ")
                    if not celdas or t != celdas[-1]:
                        celdas.append(t)
                if any(celdas):
                    lineas.append(("tabla", " | ".join(celdas)))
            lineas.append(("fin_tabla", ""))
    return lineas


def _lineas_texto(archivo: Path) -> list[tuple[str, str]]:
    import conversor  # nova_core/conversor.py

    extractor = (
        conversor.extraer_pdf
        if archivo.suffix.lower() == ".pdf"
        else conversor.extraer_texto_plano
    )
    lineas = []
    for linea in "\n".join(extractor(archivo)).splitlines():
        limpia = linea.strip()
        if not limpia:
            continue
        if m := re.match(r"^(?:[-*•·▪◦]|\d+[.)]|[a-z][.)])\s+(.*)", limpia):
            lineas.append(("vineta", m.group(1)))
        elif limpia.startswith("|"):
            lineas.append(("tabla", limpia.strip("|")))
        else:
            lineas.append(("parrafo", limpia))
    return lineas


def leer(archivo: Path) -> list[tuple[str, str]]:
    return (
        _lineas_docx(archivo)
        if archivo.suffix.lower() == ".docx"
        else _lineas_texto(archivo)
    )


# ------------------------------------------------------------------ reglas y requisitos


def reglas(lineas: list[tuple[str, str]]) -> dict:
    texto = "\n".join(t for _, t in lineas)
    bajo = texto.lower()
    formato = next(
        (nombre for nombre, patron in FORMATOS if re.search(patron, bajo)), "documento"
    )
    extension = [m.group(0).strip() for m in RE_EXTENSION.finditer(texto)]
    modalidad = (
        "grupo"
        if re.search(r"\ben grupo|grupal|por parejas|equipo de \d", bajo)
        else ("individual" if "individual" in bajo else "no indicada")
    )
    normas = [
        n
        for n in ("APA", "Harvard", "Vancouver", "MLA", "IEEE")
        if re.search(rf"\b{n}\b", texto)
    ]
    if re.search(r"bibliograf[ií]a|referencias|fuentes consultadas", bajo):
        normas.append("bibliografía")
    return {
        "formato": formato,
        "extension": extension,
        "modalidad": modalidad,
        "normas": normas,
    }


def _frases(texto: str) -> list[str]:
    return [
        f.strip()
        for f in re.split(r"(?<=[.?!])\s+(?=[¿A-ZÁÉÍÓÚ])", texto)
        if len(f.strip()) > 5
    ]


def extraer(lineas: list[tuple[str, str]]) -> list[dict]:
    reqs: list[dict] = []
    ayuda = False
    en_rubrica = False

    def nuevo(clase: str, texto: str) -> None:
        bajo = texto.lower()
        etiquetas = [
            e
            for e, pista in (
                ("dafo", "dafo"),
                ("visual", r"visual|p[oó]ster|cartel|anuncio|imagen"),
            )
            if re.search(pista, bajo)
        ]
        reqs.append(
            {
                "id": f"R{len(reqs) + 1}",
                "clase": clase,
                "texto": texto,
                "etiquetas": etiquetas,
            }
        )

    for tipo, texto in lineas:
        if tipo == "fin_tabla":
            en_rubrica = False
            continue
        if tipo == "tabla":
            if (
                RE_RUBRICA.search(texto) and not en_rubrica
            ):  # fila de cabecera de una rubrica
                en_rubrica = True
            elif en_rubrica:
                nuevo("rubrica", texto)
            continue
        if tipo == "titulo":
            ayuda = False
            continue
        limpia = texto.lstrip("¿¡ ")
        if RE_AYUDA.search(texto) and not texto.endswith("?"):
            ayuda = True  # lo que sigue son preguntas de ayuda
            continue
        if RE_ENTREGA.match(limpia):
            nuevo("entrega", texto)
            continue
        if texto.endswith("?"):
            nuevo("ayuda" if ayuda else "pregunta", texto)
            continue
        if tipo == "vineta":
            ayuda = False  # una vineta que no es pregunta cierra el bloque de ayuda
            nuevo("apartado" if texto.endswith(":") else "obligatorio", texto)
            continue
        for frase in _frases(
            texto
        ):  # parrafo suelto: solo las frases que encargan algo
            if RE_TAREA.match(frase.lstrip("¿¡ ")):
                nuevo("obligatorio", frase)
    return reqs


# ------------------------------------------------------------------ guardar / usar


def preparar(archivo: Path, carpeta: Path) -> tuple[list[dict], dict]:
    if not archivo.exists():
        raise SystemExit(f"[error] No existe el enunciado: {archivo}")
    lineas = leer(archivo)
    reqs, normas = extraer(lineas), reglas(lineas)
    if not reqs:
        raise SystemExit(
            "[error] No encontre tareas ni preguntas en el enunciado. Revisa el archivo."
        )
    (carpeta / ENUNCIADO).write_text("\n".join(t for _, t in lineas), encoding="utf-8")
    (carpeta / REQUISITOS).write_text(
        json.dumps(
            {"reglas": normas, "requisitos": reqs}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return reqs, normas


def cargar(carpeta: Path) -> tuple[list[dict], dict]:
    ruta = carpeta / REQUISITOS
    if not ruta.exists():
        return [], {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return (
        (datos, {})
        if isinstance(datos, list)
        else (datos["requisitos"], datos.get("reglas", {}))
    )


def texto_guardado(carpeta: Path) -> str:
    ruta = carpeta / ENUNCIADO
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def cobertura(carpeta: Path, guion: dict) -> tuple[list[str], list[str]]:
    """(bloqueos, avisos)."""
    reqs, normas = cargar(carpeta)
    if not reqs:
        return [
            "[ENUNCIADO] No hay requisitos.json: ejecuta redactar.py enunciado --archivo <enunciado> --carpeta <carpeta>"
        ], []
    cubiertos = {r for s in guion.get("secciones", []) for r in s.get("cubre", [])}
    bloqueos, avisos = [], []
    for r in reqs:
        if r["id"] in cubiertos or r["clase"] == "entrega":
            continue
        linea = f"{r['id']} ({r['clase']}): «{r['texto'][:110]}»"
        if r["clase"] == "ayuda":
            avisos.append(
                f"[AYUDA] {linea} no se toca en ninguna sección (no es obligatoria, pero ayuda a la nota)."
            )
        else:
            bloqueos.append(
                f'[FALTA] {linea} no lo responde ninguna sección (añádelo a su "cubre").'
            )
    if normas.get("formato") not in (None, "documento", "informe"):
        avisos.append(
            f"[FORMATO] El enunciado pide {normas['formato'].upper()}, no un documento Word. "
            "Para presentación: exportar --formatos gamma."
        )
    if normas.get("extension"):
        avisos.append(
            f"[EXTENSIÓN] El enunciado marca: {', '.join(normas['extension'])}. Compruébalo antes de entregar."
        )
    return bloqueos, avisos


def plantilla_guion(archivo: Path, reqs: list[dict], normas: dict) -> dict:
    secciones = []
    ayuda = [r for r in reqs if r["clase"] in ("pregunta", "ayuda")]
    if ayuda:
        secciones.append(
            {
                "titulo": "Necesidad, demanda e innovación",
                "cubre": [r["id"] for r in ayuda],
                "puntos": [
                    "Usa estas preguntas como guía; no hace falta contestarlas una a una como un examen:"
                ]
                + [f"{r['id']}: {r['texto']}" for r in ayuda],
            }
        )
    extra = {"dafo": " (usa un bloque :::dafo)", "visual": " (usa un bloque :::cartel)"}
    for r in reqs:
        if r["clase"] in ("obligatorio", "apartado", "rubrica"):
            pista = "".join(extra[e] for e in r["etiquetas"] if e in extra)
            secciones.append(
                {
                    "titulo": r["texto"].rstrip(":")[:60],
                    "cubre": [r["id"]],
                    "puntos": [r["texto"] + pista],
                }
            )
    return {
        "tipo": "actividad",
        "titulo": "...",
        "subtitulo": "...",
        "modulo": "...",
        "autor": "Alexander Martínez",
        "fecha": "...",
        "enunciado": str(archivo),
        "reglas_del_enunciado": normas,
        "contexto": "datos verdaderos que la IA debe usar tal cual",
        "datos": [
            "toda cifra que salga en el documento tiene que estar aqui (o en el contexto)"
        ],
        "secciones": secciones,
    }
