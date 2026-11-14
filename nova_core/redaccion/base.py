"""Utilidades comunes: fichas de tipo, carpetas, numeros y llamada a Qwen."""

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIR_TIPOS = RAIZ / "tipos"
DIR_ESTILOS = RAIZ / "estilos"
DOCUMENTOS_GENERADOS = Path.home() / ".gemini" / "antigravity" / "documentos_generados"
MARCA_PENDIENTE = "[PENDIENTE"


def listar_tipos() -> dict[str, dict]:
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(DIR_TIPOS.glob("*.json"))
    }


def cargar_ficha(tipo: str) -> dict:
    ruta = DIR_TIPOS / f"{tipo}.json"
    if not ruta.exists():
        disponibles = ", ".join(listar_tipos())
        raise SystemExit(
            f"[error] Tipo '{tipo}' no existe. Tipos disponibles: {disponibles}"
        )
    return json.loads(ruta.read_text(encoding="utf-8"))


def resolver_carpeta(carpeta: str) -> Path:
    """Un nombre suelto va a documentos_generados/<nombre>; una ruta se respeta."""
    ruta = Path(carpeta)
    if not ruta.is_absolute() and len(ruta.parts) == 1:
        ruta = DOCUMENTOS_GENERADOS / ruta
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def nombre_archivo(guion: dict) -> str:
    base = (
        guion.get("archivo")
        or guion.get("titulo")
        or guion.get("asunto")
        or "documento"
    )
    base = re.sub(r"[^\w\- ]+", "", base, flags=re.UNICODE).strip().replace(" ", "_")
    return base[:80] or "documento"


def dinero(valor) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formato_numero(valor, estilo: str = "pe") -> str:
    """pe: 1,760.00 (Peru, EE. UU.)  es: 1.760,00 (Espana)."""
    texto = f"{dinero(valor):,.2f}"
    if estilo == "es":
        texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return texto


def estilo_numeros(guion: dict) -> str:
    if guion.get("formato_numeros") in ("pe", "es"):
        return guion["formato_numeros"]
    return "es" if "€" in str(guion.get("moneda", "")) else "pe"


def pendientes(texto: str) -> list[str]:
    return re.findall(r"\[PENDIENTE[^\]]*\]", texto)


def _modelo_nova(clave: str = "coder", defecto: str = "qwen3.5:9b") -> str:
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8"))[clave]
    except Exception:
        return defecto


def qwen(
    prompt: str, sistema: str, max_tokens: int = 1500, modelo: str | None = None
) -> str:
    """Qwen local (0 tokens de nube)."""
    sys.path.insert(0, str(RAIZ.parent))
    from ollama_comun import ensure_ollama_service, generar_qwen

    ensure_ollama_service()
    texto, cortado = generar_qwen(
        prompt,
        modelo or _modelo_nova("coder"),
        sistema=sistema,
        num_predict=max_tokens,
        num_ctx=8192,
        temperatura=0.3,
        timeout=600,
    )
    if cortado:
        texto += "\n\n[PENDIENTE: la seccion quedo cortada, pide rehacerla]"
    return texto.strip()


def limpiar_salida_qwen(texto: str, titulo: str, permitir_codigo: bool = False) -> str:
    """Quita lo que Qwen anade de mas: titulo repetido, saludos, encabezados de nivel 1/2 y vallas de markdown."""
    lineas = texto.strip().splitlines()
    normal = re.sub(r"\W+", " ", titulo).strip().lower()
    while lineas:
        primera = lineas[0].strip()
        sin_marcas = re.sub(r"^[#*\s]+|[*\s]+$", "", primera)
        if not primera or re.sub(r"\W+", " ", sin_marcas).strip().lower() == normal:
            lineas.pop(0)
            continue
        if re.match(
            r"(?i)^(claro|aqu[ií] tienes|a continuaci[oó]n te|por supuesto)\b",
            sin_marcas,
        ):
            lineas.pop(0)
            continue
        break
    salida = []
    for linea in lineas:
        if not permitir_codigo and linea.strip().startswith("```"):
            continue
        if re.match(r"^#{1,2}\s", linea):  # los niveles 1 y 2 los pone el redactor
            linea = "### " + linea.lstrip("# ")
        salida.append(linea.rstrip())
    return "\n".join(salida).strip()
