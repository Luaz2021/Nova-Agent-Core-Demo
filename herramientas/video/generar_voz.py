# Genera la narración de cada escena. 15/11: con la voz de MARINA (clonada en local, herramientas\voz_clon);
# si no está montada en este equipo, con voz neuronal de Microsoft Edge (gratis, necesita internet).
# Requisitos (una sola vez):   pip install edge-tts
# Uso: abre una terminal EN ESTA CARPETA y ejecuta:   python generar_voz.py
# Necesita conexión a internet. Crea audio/escena1.mp3 ... escena7.mp3
import asyncio
from pathlib import Path
import edge_tts

# Voces femeninas de España: "es-ES-ElviraNeural" (cálida, recomendada) o "es-ES-XimenaNeural"
VOZ = "es-ES-ElviraNeural"
VELOCIDAD = "+0%"    # velocidad natural; el ritmo final se ajusta en la web (selector Velocidad)
TONO = "-2Hz"        # ligeramente más grave = más suave

SALIDA = Path(__file__).resolve().parent / "audio"
SALIDA.mkdir(exist_ok=True)

ESCENAS = [
  {
    "n": "El problema",
    "t": "Esto es PrintLab. Ocho impresoras 3D, un montón de encargos de prototipos y un encargado que decide qué máquina usar mirando una hoja de cálculo. Los pedidos se acumulan. Una impresora falla y nadie se entera. Y el cliente, mientras tanto, no sabe nada de su pedido."
  },
  {
    "n": "La solución",
    "t": "¿La solución? Digitalizar PrintLab. Un sistema con cuatro piezas: el cliente, la gestión, la planta y el dashboard."
  },
  {
    "n": "El formulario",
    "t": "Todo empieza en el formulario web. El cliente pone sus datos y especificaciones, y sube su modelo 3D. El sistema lo valida al instante. Si la pieza es pequeña, la cotización es automática: precio y fecha de entrega con cinco días de margen. Si es grande, la solicitud pasa al jefe, que la revisa y devuelve la cotización. En los dos casos, el cliente acepta las condiciones, paga por adelantado y recibe su factura."
  },
  {
    "n": "IT y OT",
    "t": "Aquí conviven dos mundos. Arriba, el mundo IT: la web, el servidor, la base de datos y el algoritmo. Abajo, el mundo OT: las impresoras, sus sensores y sus motores. Los une un puente: pequeños gateways como una Raspberry Pi, y una capa de adaptadores para que todas las máquinas hablen el mismo idioma."
  },
  {
    "n": "El viaje del pedido",
    "t": "Sigamos un pedido. Entra en la cola. Cuando una impresora queda libre, el algoritmo elige el pedido con la entrega más ajustada, y si hay empate, el del color que ya está cargado. La impresora trabaja capa a capa y envía su temperatura y su avance al dashboard en tiempo real. ¿Y si falla? Se registra la incidencia y la pieza se reimprime sola en otra máquina. Al terminar, el operario valida la calidad, y el cliente recibe el aviso por WhatsApp."
  },
  {
    "n": "Qué cambia",
    "t": "¿Qué cambia en la empresa? El encargado deja la hoja de cálculo y pasa a supervisar. Los operarios registran calidad e incidencias en una tablet. Ventajas: más eficiencia y trazabilidad total. Retos: máquinas muy distintas entre sí, y el coste de adaptarse al cambio."
  },
  {
    "n": "Cierre",
    "t": "PrintLab. De la hoja de cálculo, a la fábrica inteligente."
  }
]

def voz_marina() -> bool:
    """15/11 (decision del usuario): la voz de los videos es MARINA (locutora), clonada en local con herramientas\\voz_clon.
    Genera todas las escenas con UNA sola carga del modelo. Si no esta montado, se usa la voz de Edge de siempre."""
    import json
    import os
    import subprocess
    import tempfile

    clonador = Path.home() / ".gemini" / "antigravity" / "herramientas" / "voz_clon" / "clonador.py"
    py = Path.home() / "nova_voz_clon" / "env_fq" / "Scripts" / "python.exe"
    if not (clonador.exists() and py.exists()):
        return False
    tareas = [{"texto": e["t"], "salida": str(SALIDA / f"escena{i}.wav"), "mp3": True} for i, e in enumerate(ESCENAS, 1)]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(tareas, f, ensure_ascii=False)
    print("Narracion con la voz de Marina (locutora). Tarda unas 4-9 veces lo que dura el audio...")
    r = subprocess.run([str(py), str(clonador), "lote", "--voz", "videos", "--json", f.name])
    os.unlink(f.name)
    return r.returncode == 0 and all((SALIDA / f"escena{i}.mp3").exists() for i in range(1, len(ESCENAS) + 1))


async def main():
    for i, e in enumerate(ESCENAS, 1):
        destino = SALIDA / f"escena{i}.mp3"
        print(f"Escena {i}: {e['n']}")
        if narrar_con_marina(e["t"], destino):  # v3.2: pack de voz instalado -> narra Marina (estilo locutora)
            continue
        await edge_tts.Communicate(e["t"], VOZ, rate=VELOCIDAD, pitch=TONO).save(str(destino))
    # Voces embebidas: la web las usa para crear el vídeo sin pedir archivos
    import base64, json
    voces = [base64.b64encode((SALIDA / f"escena{i}.mp3").read_bytes()).decode() for i in range(1, len(ESCENAS) + 1)]
    (SALIDA / "voces.js").write_text("window.VOCES=" + json.dumps(voces) + ";\n", encoding="utf-8")
    print("\nListo. Abre printlab_video.html: el vídeo ya usa estas voces.")

def narrar_con_marina(texto: str, destino: Path) -> bool:
    """v3.2: con el pack de voz de Nova (y su licencia aceptada) la narradora es MARINA, estilo locutora.
    Uso permitido: videos hechos con Nova, sin fines comerciales (LICENCIA_VOCES.md). Si no, voz de Edge."""
    import os
    import subprocess
    import sys
    base = Path.home() / "nova_voz_clon"
    py = base / "env_fq" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    clon = Path.home() / ".gemini" / "antigravity" / "herramientas" / "voz_clon" / "clonador.py"
    if not (py.exists() and clon.exists() and (base / "licencia_voces_aceptada.json").exists()):
        return False
    r = subprocess.run([str(py), str(clon), "decir", "--voz", "videos", "--estilo", "locutora", "--texto", texto,
                        "--salida", str(destino), "--mp3"], capture_output=True, text=True)
    if r.returncode != 0 or not destino.with_suffix(".mp3").exists():
        print(f"   (Marina no disponible: {(r.stdout + r.stderr).strip()[-120:]}; uso la voz de Edge)", file=sys.stderr)
        return False
    return True


asyncio.run(main())
