"""Documentos de REDACCION (proyecto, academico, tesis, informe, software): borrador por secciones.

borrador.md es el documento de trabajo. Cada seccion lleva una marca:
    <!-- nova:seccion id=3 estado=borrador -->     Qwen la puede rehacer
    <!-- nova:seccion id=3 estado=bloqueada -->    Alexander la dio por buena: nadie la toca
Alexander puede corregir el .md a mano; las secciones que edita se respetan si las bloquea.
"""

import re
from pathlib import Path

from docx.shared import Cm

from . import estilos, word
from .base import MARCA_PENDIENTE, limpiar_salida_qwen, qwen

RE_MARCA = re.compile(r"<!-- nova:seccion id=(\d+) estado=(\w+) -->")
REGLAS_COMUNES = (
    "Escribes en español formal y claro, con todas sus tildes y eñes, como una persona y no como un folleto. "
    "PROHIBIDO inventar cifras, fechas, nombres, empresas, leyes, articulos o datos tecnicos que no esten en los puntos o "
    "en el contexto. Si hace falta un dato que no tienes, escribe [PENDIENTE: que falta]. "
    "Nada de frases grandilocuentes ni de relleno ('en el mundo actual', 'cabe destacar', 'es imperativo', 'sinergia'). "
    "No escribas el titulo de la seccion, ni saludos, ni comentarios sobre lo que vas a hacer. "
    "Usa parrafos; listas solo si enumeras cosas; tablas Markdown solo si comparas datos que te han dado."
)


def secciones_del_guion(guion: dict, ficha: dict) -> list[dict]:
    secciones = guion.get("secciones") or [
        {"titulo": s["titulo"], "puntos": [s.get("guia", "")]}
        for s in ficha["secciones"]
    ]
    return [{"id": n, **s} for n, s in enumerate(secciones, start=1)]


def _prompt(
    guion: dict, ficha: dict, sec: dict, nota: str = "", texto_previo: str = ""
) -> tuple[str, str]:
    sistema = f"{ficha.get('rol', 'Eres redactor profesional.')} {REGLAS_COMUNES} Tono: {guion.get('tono') or ficha.get('tono', 'formal')}."
    puntos = (
        "\n".join(f"- {p}" for p in sec.get("puntos", []) if p)
        or "- Desarrolla la seccion segun su titulo."
    )
    contexto = guion.get("contexto", "")
    prompt = (
        f"Documento: {guion.get('titulo', '')}\n"
        + (
            f"Contexto general (datos verdaderos, usalos tal cual):\n{contexto}\n\n"
            if contexto
            else ""
        )
        + f"Seccion a redactar: {sec['titulo']}\nPuntos que debe cubrir:\n{puntos}\n\n"
        f"Extension: unas {sec.get('palabras') or ficha.get('palabras_por_seccion', 250)} palabras como maximo."
    )
    if texto_previo:
        prompt += f"\n\nVersion anterior de la seccion:\n{texto_previo}"
    if nota:
        prompt += f"\n\nCorreccion pedida por Alexander (obligatoria): {nota}"
    return prompt, sistema


def redactar_seccion(
    guion: dict, ficha: dict, sec: dict, nota: str = "", texto_previo: str = ""
) -> str:
    if sec.get("literal"):
        return sec["literal"].strip()
    prompt, sistema = _prompt(guion, ficha, sec, nota, texto_previo)
    palabras = sec.get("palabras") or ficha.get("palabras_por_seccion", 250)
    texto = qwen(prompt, sistema, max_tokens=int(palabras * 2.6) + 200)
    return limpiar_salida_qwen(
        texto, sec["titulo"], permitir_codigo=ficha.get("codigo", False)
    )


# ------------------------------------------------------------- archivo .md


def leer(ruta: Path) -> list[dict]:
    texto = ruta.read_text(encoding="utf-8")
    partes = RE_MARCA.split(texto)
    secciones = []
    for i in range(1, len(partes), 3):
        bloque = partes[i + 2].strip().splitlines()
        titulo = re.sub(r"^#+\s*", "", bloque[0]).strip() if bloque else ""
        secciones.append(
            {
                "id": int(partes[i]),
                "estado": partes[i + 1],
                "titulo": titulo,
                "cuerpo": "\n".join(bloque[1:]).strip(),
            }
        )
    return secciones


def escribir(ruta: Path, guion: dict, secciones: list[dict]) -> None:
    lineas = [
        f"# {guion.get('titulo', 'Documento')}",
        "",
        "<!-- Borrador de Nova. Corrige lo que quieras aqui mismo. Para que Nova no vuelva a tocar una seccion: "
        "redactar.py bloquear --seccion N -->",
        "",
    ]
    for s in secciones:
        lineas += [
            f"<!-- nova:seccion id={s['id']} estado={s['estado']} -->",
            f"## {s['titulo']}",
            "",
            s["cuerpo"],
            "",
        ]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def generar(guion: dict, ficha: dict, ruta: Path) -> list[dict]:
    secciones = []
    lista = secciones_del_guion(guion, ficha)
    for sec in lista:
        print(f"  -> [{sec['id']}/{len(lista)}] {sec['titulo']}", flush=True)
        cuerpo = redactar_seccion(guion, ficha, sec)
        secciones.append(
            {
                "id": sec["id"],
                "estado": "bloqueada" if sec.get("literal") else "borrador",
                "titulo": sec["titulo"],
                "cuerpo": cuerpo,
            }
        )
        escribir(
            ruta, guion, secciones
        )  # se guarda seccion a seccion: si algo falla no se pierde lo hecho
    return secciones


def rehacer(
    guion: dict, ficha: dict, ruta: Path, ids: list[int], nota: str = ""
) -> list[str]:
    secciones = leer(ruta)
    guion_por_id = {s["id"]: s for s in secciones_del_guion(guion, ficha)}
    hechas = []
    for s in secciones:
        if s["id"] not in ids:
            continue
        if s["estado"] == "bloqueada":
            print(
                f"[aviso] La seccion {s['id']} esta bloqueada: no se toca (desbloqueala si quieres rehacerla)."
            )
            continue
        base = guion_por_id.get(s["id"], {"titulo": s["titulo"], "puntos": []})
        base = {**base, "titulo": s["titulo"], "literal": None}
        print(f"  -> rehaciendo {s['id']}: {s['titulo']}", flush=True)
        s["cuerpo"] = redactar_seccion(
            guion, ficha, base, nota=nota, texto_previo=s["cuerpo"] if nota else ""
        )
        hechas.append(s["titulo"])
    escribir(ruta, guion, secciones)
    return hechas


def cambiar_estado(guion: dict, ruta: Path, ids: list[int] | None, estado: str) -> None:
    secciones = leer(ruta)
    for s in secciones:
        if ids is None or s["id"] in ids:
            s["estado"] = estado
    escribir(ruta, guion, secciones)


def resumen(ruta: Path) -> str:
    filas = []
    for s in leer(ruta):
        n_pend = s["cuerpo"].count(MARCA_PENDIENTE)
        filas.append(
            f"  {s['id']:>2}. [{s['estado']:<9}] {s['titulo']}  ({len(s['cuerpo'].split())} palabras"
            + (f", {n_pend} PENDIENTE" if n_pend else "")
            + ")"
        )
    return "\n".join(filas)


# ------------------------------------------------------------- exportar


def a_word(guion: dict, ficha: dict, secciones: list[dict], destino: Path) -> None:
    estilo = guion.get("estilo") or ficha.get("estilo", "formal")
    doc = estilos.abrir(estilo)
    tipo_portada = ficha.get("portada") if guion.get("portada", True) else None
    if tipo_portada:
        word.portada(doc, guion, tipo_portada)
    elif guion.get("titulo"):
        doc.add_paragraph(guion["titulo"], style="Title")
        datos = " · ".join(str(guion[k]) for k in ("autor", "fecha") if guion.get(k))
        if datos:
            doc.add_paragraph(datos, style="Nota")
    numerar = ficha.get("numerar_secciones", False)
    tema = estilo if estilo in estilos.TEMAS else None
    for n, s in enumerate(secciones, start=1):
        doc.add_heading(f"{n}. {s['titulo']}" if numerar else s["titulo"], level=1)
        word.markdown_a_word(doc, s["cuerpo"], tema=tema)
    if guion.get("referencias"):
        doc.add_heading("Referencias", level=1)
        for ref in guion["referencias"]:
            p = doc.add_paragraph(ref)
            if estilo == "apa":  # sangria francesa APA 7
                p.paragraph_format.left_indent = Cm(1.27)
                p.paragraph_format.first_line_indent = Cm(-1.27)
    doc.save(str(destino))


def a_markdown(guion: dict, secciones: list[dict], destino: Path) -> None:
    """Markdown limpio (sin marcas de Nova), para documentacion de software o para pegar en otro sitio."""
    lineas = [f"# {guion.get('titulo', 'Documento')}", ""]
    for s in secciones:
        lineas += [f"## {s['titulo']}", "", s["cuerpo"], ""]
    destino.write_text("\n".join(lineas).rstrip() + "\n", encoding="utf-8")
