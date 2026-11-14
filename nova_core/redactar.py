"""Redactor de documentos de Nova por TIPOS (sustituye a redactor.py). Formal y sin colores.

Tipos:  python redactar.py tipos                 (lista y ejemplo de guion:  python redactar.py tipos presupuesto)

Datos (presupuesto, solicitud_presupuesto): sin IA, cuentas hechas por el codigo.
    python redactar.py nuevo --tipo presupuesto --guion guion.json --carpeta solar_iquitos

Redaccion (proyecto, academico, tesis, informe, doc_software): borrador por secciones -> corriges -> exportas.
    python redactar.py nuevo     --tipo tesis --guion guion.json --carpeta tfg
    python redactar.py revisar   --carpeta tfg
    python redactar.py rehacer   --carpeta tfg --seccion 3 --nota "mas corta y con el ejemplo de Iquitos"
    python redactar.py bloquear  --carpeta tfg --seccion 1,2      (o --seccion todas)
    python redactar.py exportar  --carpeta tfg [--formatos docx,pdf]

--carpeta con un nombre suelto = antigravity/documentos_generados/<nombre>.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redaccion import (  # noqa: E402
    base,
    borrador,
    calidad,
    datos,
    enunciado,
    excel,
    logica,
    ortografia,
    word,
)

GUION, BORRADOR = "guion.json", "borrador.md"


def _fuentes(carpeta: Path, guion: dict) -> str:
    """Todo lo que cuenta como 'dato dado': contexto, datos, puntos, titulo y el enunciado."""
    partes = [
        guion.get("titulo", ""),
        guion.get("subtitulo", ""),
        str(guion.get("contexto", "")),
        json.dumps(guion.get("datos", ""), ensure_ascii=False),
    ]
    partes += [p for s in guion.get("secciones", []) for p in s.get("puntos", [])]
    partes.append(enunciado.texto_guardado(carpeta))
    return "\n".join(partes)


def revision_final(
    secciones: list[dict],
    fuentes: str,
    reqs: list[dict] | None,
    con_logica: bool,
    cifras: bool = True,
) -> tuple[list[str], list[str]]:
    """Los filtros de antes de entregar: calidad (tildes, cifras, humano), ortografia de Word y logica de Qwen."""
    bloqueos, avisos = calidad.revisar(secciones, fuentes, cifras=cifras)
    texto = "\n\n".join(f"{s['titulo']}\n{s['cuerpo']}" for s in secciones)
    malas, gramatica = ortografia.revisar_texto(texto, extra=fuentes)
    if malas:
        bloqueos.append(
            f"[ORTOGRAFÍA] {len(malas)} palabra(s) mal escrita(s): {', '.join(malas[:15])}. "
            "Si alguna está bien (nombre propio, término técnico), añádela a redaccion/diccionario.txt."
        )
    avisos += [f"[GRAMÁTICA] Revisa: «{g}»" for g in gramatica[:10]]
    if con_logica:
        print(
            "[*] Revisión de lógica con Qwen en local (puede tardar un minuto)...",
            flush=True,
        )
        avisos += logica.revisar(texto, reqs)
    return bloqueos, avisos


def _informe(carpeta: Path, bloqueos: list[str], avisos: list[str]) -> None:
    lineas = [
        "# Revisión final",
        "",
        f"Bloqueos: {len(bloqueos)} · Avisos: {len(avisos)}",
        "",
    ]
    lineas += [f"- [BLOQUEO] {b}" for b in bloqueos] + [f"- {a}" for a in avisos]
    (carpeta / "revision.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _control(
    carpeta: Path, guion: dict, ficha: dict, forzar: bool, con_logica: bool = False
) -> bool:
    """Revision final + cobertura del enunciado. True = se puede exportar."""
    secciones = borrador.leer(carpeta / BORRADOR)
    reqs = enunciado.cargar(carpeta)[0] if ficha.get("enunciado") else None
    bloqueos, avisos = revision_final(
        secciones, _fuentes(carpeta, guion), reqs, con_logica
    )
    if ficha.get("enunciado"):
        faltan, avisos_enunciado = enunciado.cobertura(carpeta, guion)
        bloqueos += faltan
        avisos += avisos_enunciado
    _informe(carpeta, bloqueos, avisos)
    for a in avisos:
        print(f"[aviso] {a}")
    for b in bloqueos:
        print(f"[BLOQUEO] {b}")
    if bloqueos and not forzar:
        print(
            f"[NO EXPORTADO] {len(bloqueos)} bloqueos. Corrige el borrador (o rehacer --nota) y vuelve a exportar. "
            "Solo si Alexander lo pide: exportar --forzar."
        )
        return False
    return True


def _ids(texto: str | None) -> list[int] | None:
    if not texto or texto == "todas":
        return None
    return [int(x) for x in texto.replace(" ", "").split(",") if x]


def _cargar(carpeta: Path) -> tuple[dict, dict]:
    ruta = carpeta / GUION
    if not ruta.exists():
        raise SystemExit(
            f"[error] No hay {GUION} en {carpeta}. Empieza con: redactar.py nuevo --tipo ... --guion ..."
        )
    guion = json.loads(ruta.read_text(encoding="utf-8"))
    return guion, base.cargar_ficha(guion["tipo"])


def _formatos(args, ficha: dict) -> list[str]:
    return [
        f.strip().lower()
        for f in (args.formatos.split(",") if args.formatos else ficha["formatos"])
    ]


def _faltan_obligatorios(guion: dict, ficha: dict) -> list[str]:
    faltan = []
    for campo in ficha.get("obligatorio", []):
        valor = guion
        for parte in campo.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
        if not valor:
            faltan.append(campo)
    return faltan


def exportar(
    carpeta: Path, guion: dict, ficha: dict, formatos: list[str]
) -> list[Path]:
    nombre = base.nombre_archivo(guion)
    hechos: list[Path] = []
    quiere_word = "docx" in formatos or "pdf" in formatos
    docx = carpeta / f"{nombre}.docx"
    if ficha["clase"] == "datos":
        if quiere_word:
            constructor = (
                datos.presupuesto_docx
                if guion["tipo"] == "presupuesto"
                else datos.solicitud_docx
            )
            constructor(guion, docx)
            hechos.append(docx)
        if "xlsx" in formatos and guion["tipo"] == "presupuesto":
            datos.presupuesto_xlsx(guion, carpeta / f"{nombre}.xlsx")
            hechos.append(carpeta / f"{nombre}.xlsx")
        if "txt" in formatos and guion["tipo"] == "solicitud_presupuesto":
            (carpeta / f"{nombre}_correo.txt").write_text(
                datos.solicitud_correo(guion), encoding="utf-8"
            )
            hechos.append(carpeta / f"{nombre}_correo.txt")
    else:
        secciones = borrador.leer(carpeta / BORRADOR)
        if quiere_word:
            borrador.a_word(guion, ficha, secciones, docx)
            hechos.append(docx)
        if "md" in formatos:
            borrador.a_markdown(guion, secciones, carpeta / f"{nombre}.md")
            hechos.append(carpeta / f"{nombre}.md")
        if "gamma" in formatos:
            from redaccion import gamma

            hechos += gamma.generar(guion, secciones, carpeta, nombre)
    if "pdf" in formatos:
        pdf = word.a_pdf(docx)
        if pdf:
            hechos.append(pdf)
        else:
            print(
                "[aviso] No se pudo crear el PDF (ni Word ni LibreOffice). Queda el .docx."
            )
    return hechos


def cmd_tipos(args) -> None:
    tipos = base.listar_tipos()
    if args.tipo:
        ficha = base.cargar_ficha(args.tipo)
        print(f"{ficha['nombre']}: {ficha['descripcion']}\n")
        if ficha.get("ejemplo"):
            print(
                "Guion de ejemplo:\n"
                + json.dumps(ficha["ejemplo"], ensure_ascii=False, indent=2)
            )
        else:
            ejemplo = {
                "tipo": args.tipo,
                "titulo": "...",
                "autor": "...",
                "fecha": "...",
                "contexto": "datos verdaderos que la IA debe usar tal cual",
                "secciones": [
                    {"titulo": "...", "puntos": ["..."]},
                    {"titulo": "...", "literal": "texto tuyo tal cual"},
                ],
            }
            print(
                "Guion de ejemplo:\n"
                + json.dumps(ejemplo, ensure_ascii=False, indent=2)
            )
            print("Secciones por defecto si no las das:")
            for s in ficha["secciones"]:
                print(f"  - {s['titulo']}: {s['guia']}")
        return
    for clave, ficha in tipos.items():
        print(f"{clave:<22} {ficha['descripcion']}  [{', '.join(ficha['formatos'])}]")


def cmd_nuevo(args) -> None:
    guion = json.loads(Path(args.guion).read_text(encoding="utf-8"))
    guion["tipo"] = args.tipo or guion.get("tipo")
    if not guion["tipo"]:
        raise SystemExit("[error] Indica --tipo (python redactar.py tipos)")
    ficha = base.cargar_ficha(guion["tipo"])
    carpeta = base.resolver_carpeta(args.carpeta)
    (carpeta / GUION).write_text(
        json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[*] {ficha['nombre']} en {carpeta}")
    faltan = _faltan_obligatorios(guion, ficha)
    if faltan:
        print(
            f"[PENDIENTE] Faltan datos: {', '.join(faltan)}. Pideselos a Alexander; en el documento salen como [PENDIENTE]."
        )

    if ficha["clase"] == "datos":
        if guion["tipo"] == "presupuesto":
            c = datos.calcular(guion)
            for aviso in datos.comprobar_totales(guion, c):
                print(f"[aviso] {aviso}")
            print(datos.presupuesto_md(guion))
        for ruta in exportar(carpeta, guion, ficha, _formatos(args, ficha)):
            print(f"[ok] {ruta}")
        return

    if ficha.get("enunciado"):
        if not guion.get("enunciado"):
            raise SystemExit(
                '[error] El tipo \'actividad\' necesita "enunciado": "<ruta del enunciado>" en el guion. '
                "Primero: redactar.py enunciado --archivo <enunciado> --carpeta <carpeta>"
            )
        enunciado.preparar(Path(guion["enunciado"]), carpeta)
    borrador.generar(guion, ficha, carpeta / BORRADOR)
    print(
        f"[ok] Borrador: {carpeta / BORRADOR}\n{borrador.resumen(carpeta / BORRADOR)}"
    )
    listo = _control(carpeta, guion, ficha, forzar=False)
    print("Siguiente: Alexander lo lee y corrige -> rehacer / bloquear -> exportar.")
    if args.exportar and listo:
        for ruta in exportar(carpeta, guion, ficha, _formatos(args, ficha)):
            print(f"[ok] {ruta}")


def cmd_revisar(args) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    guion, ficha = _cargar(carpeta)
    if ficha["clase"] == "datos":
        print(
            datos.presupuesto_md(guion)
            if guion["tipo"] == "presupuesto"
            else datos.solicitud_correo(guion)
        )
        return
    print(borrador.resumen(carpeta / BORRADOR))


def cmd_rehacer(args) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    guion, ficha = _cargar(carpeta)
    ids = _ids(args.seccion)
    if ids is None:
        ids = [s["id"] for s in borrador.leer(carpeta / BORRADOR)]
    hechas = borrador.rehacer(guion, ficha, carpeta / BORRADOR, ids, args.nota or "")
    print(
        f"[ok] Rehechas: {', '.join(hechas) or 'ninguna'}\n{borrador.resumen(carpeta / BORRADOR)}"
    )


def cmd_estado(args, estado: str) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    guion, _ = _cargar(carpeta)
    borrador.cambiar_estado(guion, carpeta / BORRADOR, _ids(args.seccion), estado)
    print(borrador.resumen(carpeta / BORRADOR))


def cmd_exportar(args) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    guion, ficha = _cargar(carpeta)
    if ficha["clase"] == "redaccion":
        texto = (carpeta / BORRADOR).read_text(encoding="utf-8")
        if pend := base.pendientes(texto):
            print(
                f"[aviso] Quedan {len(pend)} [PENDIENTE] en el borrador: {'; '.join(pend[:5])}"
            )
        if not _control(
            carpeta, guion, ficha, args.forzar, con_logica=not args.sin_logica
        ):
            raise SystemExit(1)
    for ruta in exportar(carpeta, guion, ficha, _formatos(args, ficha)):
        print(f"[ok] {ruta}")


def _secciones_de_archivo(ruta: Path) -> list[dict]:
    """Texto por partes: una por diapositiva (pptx), por pagina (pdf) o por titulo (docx/md)."""
    import conversor

    ext = ruta.suffix.lower()
    if ext in (".pptx", ".pdf"):
        trozos = (conversor.extraer_pptx if ext == ".pptx" else conversor.extraer_pdf)(
            ruta
        )
        nombre = "Diapositiva" if ext == ".pptx" else "Página"
        return [
            {"titulo": f"{nombre} {n}", "cuerpo": t}
            for n, t in enumerate(trozos, 1)
            if t.strip()
        ]
    if ext == ".docx":
        lineas = enunciado.leer(ruta)
    else:
        lineas = [
            ("titulo" if ln.startswith("#") else "parrafo", ln.lstrip("# "))
            for ln in ruta.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    secciones = [{"titulo": "Inicio", "cuerpo": ""}]
    for tipo, texto in lineas:
        if tipo == "titulo":
            secciones.append({"titulo": texto, "cuerpo": ""})
        elif tipo != "fin_tabla":
            secciones[-1]["cuerpo"] += texto + "\n"
    return [s for s in secciones if s["cuerpo"].strip()]


def cmd_comprobar(args) -> None:
    ruta = Path(args.archivo)
    if not ruta.exists():
        raise SystemExit(f"[error] No existe {ruta}")
    secciones = _secciones_de_archivo(ruta)
    datos_txt = ""
    if args.datos:
        datos_txt = (
            Path(args.datos).read_text(encoding="utf-8")
            if Path(args.datos).exists()
            else args.datos
        )
    reqs, normas = [], {}
    if args.enunciado:
        lineas = enunciado.leer(Path(args.enunciado))
        reqs, normas = enunciado.extraer(lineas), enunciado.reglas(lineas)
        datos_txt += "\n" + "\n".join(t for _, t in lineas)
    print(
        f"[*] Revisando {ruta.name}: {len(secciones)} partes"
        + (f", enunciado con {len(reqs)} requisitos" if reqs else "")
    )
    bloqueos, avisos = revision_final(
        secciones,
        datos_txt,
        reqs,
        con_logica=not args.sin_logica,
        cifras=bool(args.datos),
    )
    if normas.get("formato") == "presentación" and ruta.suffix.lower() not in (
        ".pptx",
        ".pdf",
    ):
        bloqueos.append("[FORMATO] El enunciado pide una PRESENTACIÓN y esto no lo es.")
    _informe(ruta.parent if ruta.parent.exists() else Path.cwd(), bloqueos, avisos)
    for a in avisos:
        print(f"[aviso] {a}")
    for b in bloqueos:
        print(f"[PROBLEMA] {b}")
    print(
        f"[{'MAL' if bloqueos else 'OK'}] {len(bloqueos)} problemas y {len(avisos)} avisos. "
        f"Informe: {ruta.parent / 'revision.md'}"
    )
    if bloqueos:
        raise SystemExit(1)


def cmd_excel(args) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    tabla = excel.cargar(Path(args.datos))
    destino = (
        carpeta
        / f"{base.nombre_archivo({'archivo': tabla.get('archivo') or Path(args.datos).stem})}.xlsx"
    )
    excel.crear(tabla, destino)
    filas = sum(len(h["filas"]) for h in tabla["hojas"])
    print(f"[ok] {destino}  ({len(tabla['hojas'])} hoja(s), {filas} filas)")


def cmd_enunciado(args) -> None:
    carpeta = base.resolver_carpeta(args.carpeta)
    reqs, normas = enunciado.preparar(Path(args.archivo), carpeta)
    print(
        f"[REGLAS] formato: {normas['formato'].upper()} | modalidad: {normas['modalidad']} | "
        f"extensión: {', '.join(normas['extension']) or 'no indicada'} | normas: {', '.join(normas['normas']) or 'ninguna'}"
    )
    if normas["formato"] not in ("documento", "informe"):
        print(
            f"[FORMATO] Piden {normas['formato'].upper()}: un Word no basta. Presentación -> exportar --formatos gamma."
        )
    print(
        f"[ok] {len(reqs)} requisitos del enunciado (guardados en {carpeta / enunciado.REQUISITOS}):"
    )
    for r in reqs:
        print(f"  {r['id']:>4} [{r['clase']:<8}] {r['texto']}")
    plantilla = enunciado.plantilla_guion(Path(args.archivo), reqs, normas)
    (carpeta / "guion_plantilla.json").write_text(
        json.dumps(plantilla, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[ok] Plantilla de guion: {carpeta / 'guion_plantilla.json'}\n"
        'Siguiente: rellena cada seccion (literal o puntos) y su lista "cubre" con los ids que responde; '
        'pon en "datos" toda cifra que uses. Luego: redactar.py nuevo --guion <guion> --carpeta <carpeta>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Redactor de documentos de Nova por tipos (formal, 0 tokens de nube)"
    )
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("tipos")
    p.add_argument("tipo", nargs="?")
    p = sub.add_parser("nuevo")
    p.add_argument("--tipo")
    p.add_argument("--guion", required=True)
    p.add_argument("--carpeta", required=True)
    p.add_argument("--formatos")
    p.add_argument(
        "--exportar",
        action="store_true",
        help="Exportar ya, sin pasar por la revision del borrador",
    )
    for nombre in ("revisar", "rehacer", "bloquear", "desbloquear", "exportar"):
        p = sub.add_parser(nombre)
        p.add_argument("--carpeta", required=True)
        if nombre in ("rehacer", "bloquear", "desbloquear"):
            p.add_argument(
                "--seccion", required=nombre != "rehacer", help="1,2,3 o todas"
            )
        if nombre == "rehacer":
            p.add_argument("--nota", help="Que quiere cambiar Alexander")
        if nombre == "exportar":
            p.add_argument("--formatos", help="docx,pdf,xlsx,md,txt")
            p.add_argument(
                "--forzar",
                action="store_true",
                help="Exportar aunque haya bloqueos de calidad (SOLO si Alexander lo pide)",
            )
            p.add_argument(
                "--sin-logica",
                action="store_true",
                help="Saltar la revision de logica con Qwen",
            )
    p = sub.add_parser(
        "comprobar",
        help="Revision final de CUALQUIER archivo (docx, pptx, pdf, md, txt)",
    )
    p.add_argument("--archivo", required=True)
    p.add_argument(
        "--enunciado", help="Enunciado para comprobar que se responde todo lo que pide"
    )
    p.add_argument(
        "--datos",
        help="Texto o archivo con las cifras reales (si no, las cifras no se comprueban)",
    )
    p.add_argument("--sin-logica", action="store_true")
    p = sub.add_parser(
        "excel",
        help="Tabla (json, csv o markdown) -> .xlsx con formato. NUNCA entregar CSV",
    )
    p.add_argument("--datos", required=True)
    p.add_argument("--carpeta", required=True)
    p = sub.add_parser(
        "enunciado",
        help="Lee un enunciado y saca la lista de requisitos + plantilla de guion",
    )
    p.add_argument("--archivo", required=True)
    p.add_argument("--carpeta", required=True)
    args = ap.parse_args()
    acciones = {
        "tipos": cmd_tipos,
        "nuevo": cmd_nuevo,
        "revisar": cmd_revisar,
        "rehacer": cmd_rehacer,
        "bloquear": lambda a: cmd_estado(a, "bloqueada"),
        "desbloquear": lambda a: cmd_estado(a, "borrador"),
        "exportar": cmd_exportar,
        "enunciado": cmd_enunciado,
        "excel": cmd_excel,
        "comprobar": cmd_comprobar,
    }
    acciones[args.orden](args)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
