"""
PUENTE ANTIGRAVITY (17/11/2026, Claude) - las "manos" de Nova Voz Live dentro de Antigravity, por CDP.
==========================================================================================================
Todo lo que depende de la interfaz de Antigravity esta AQUI. Si una actualizacion de Antigravity rompe algo
(no escribe, no envia, no lee la respuesta), se arregla cambiando los SELECTORES de abajo y nada mas.

Uso desde otro script:
    import puente_antigravity as ag
    ok, info, antes = ag.enviar("crea una web ...")      # escribe en el chat y pulsa Enviar
    n, ultima = ag.leer_voz()                           # cuantas lineas 'VOZ:' hay y la ultima
Prueba rapida por terminal (no envia nada):
    python puente_antigravity.py prueba
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request

import websocket

# ------------------------------------------------------------------------------------------------------------------
# SELECTORES DE LA INTERFAZ DE ANTIGRAVITY (lo unico que hay que tocar si Antigravity cambia)
# ------------------------------------------------------------------------------------------------------------------
SEL_EDITOR = '[contenteditable="true"]'          # cuadro donde se escribe el mensaje
SEL_ENVIAR = 'button[aria-label="Send message"]'  # boton de enviar (aparece cuando hay texto)
MARCA_VOZ = "VOZ:"                                # Nova termina sus respuestas [voz] con una linea "VOZ: ..."
PREFIJO_ORDEN = "[voz] "                          # marca que pide a Nova esa linea VOZ: (regla en GEMINI.md)
INBOX = os.path.expanduser(r"~\.gemini\antigravity\nova_voice_inbox.txt")


def _puertos() -> list[int]:
    """Electron apunta su puerto de depuracion en DevToolsActivePort. Plan B: preguntar a Windows."""
    puertos = []
    for d in ("Antigravity", "antigravity"):
        try:
            with open(os.path.join(os.environ.get("APPDATA", ""), d, "DevToolsActivePort"), encoding="utf-8") as fh:
                primera = fh.readline().strip()
                if primera.isdigit():
                    puertos.append(int(primera))
        except OSError:
            pass
    if puertos:
        return list(dict.fromkeys(puertos))
    ps = ("Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in "
          "(Get-Process Antigravity -ErrorAction SilentlyContinue).Id } | Select-Object -ExpandProperty LocalPort")
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                           capture_output=True, text=True, timeout=12, creationflags=0x08000000)
        return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    except Exception:
        return []


def ws_url() -> str | None:
    """WebSocket de la ventana principal de Antigravity (no las paginas data: auxiliares)."""
    for port in _puertos():
        try:
            targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1.5).read())
        except Exception:
            continue
        pages = [t for t in targets if t.get("type") == "page" and not str(t.get("url", "")).startswith("data:")]
        pages.sort(key=lambda t: t.get("title") != "Antigravity")
        if pages:
            return pages[0]["webSocketDebuggerUrl"]
    return None


class Cdp:
    """Conexion CDP corta: with Cdp() as c: c.js('1+1')"""

    def __init__(self, timeout=5):
        url = ws_url()
        if not url:
            raise ConnectionError("Antigravity no esta abierto (o sin puerto de depuracion)")
        self.ws = websocket.create_connection(url, suppress_origin=True, timeout=timeout)
        self.n = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        try:
            self.ws.close()
        except Exception:
            pass

    def cmd(self, metodo, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params or {}}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                return r

    def js(self, expr):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def tecla(self, key, code, vk):
        for t in ("keyDown", "keyUp"):
            self.cmd("Input.dispatchKeyEvent", {"type": t, "key": key, "code": code, "windowsVirtualKeyCode": vk})


_JS_VOZ = ("(() => { const m = document.body.innerText.match(/(^|\\n)\\s*" + MARCA_VOZ + "[^\\n]*/g) || [];"
           " return JSON.stringify({n: m.length, ultima: m.length ? m[m.length - 1].replace(/^\\s*" + MARCA_VOZ +
           "\\s*/, '').trim() : ''}); })()")


def _leer_voz(c: Cdp) -> tuple[int, str]:
    d = json.loads(c.js(_JS_VOZ) or "{}")
    return int(d.get("n", 0)), d.get("ultima", "")


def leer_voz() -> tuple[int, str]:
    """(numero de lineas 'VOZ:' en el chat, texto de la ultima). (0, '') si Antigravity no esta."""
    try:
        with Cdp(timeout=4) as c:
            return _leer_voz(c)
    except Exception:
        return 0, ""


def enviar(texto: str) -> tuple[bool, str, int]:
    """Escribe la orden en el chat de Antigravity como un teclado real y pulsa Enviar.
    Devuelve (ok, detalle, lineas VOZ: que habia ANTES de enviar) para saber luego cual es la respuesta nueva."""
    try:
        with open(INBOX, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] (live) {texto}\n")
    except OSError:
        pass
    try:
        with Cdp() as c:
            sel = json.dumps(SEL_EDITOR)
            if not c.js(f"(() => {{ const el = document.querySelector({sel}); if (!el) return false; el.focus(); return true; }})()"):
                return False, "no encuentro el cuadro de mensaje de Antigravity", 0
            c.cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})  # sin foco real Chromium ignora el teclado
            antes, _ = _leer_voz(c)
            c.js(f"document.querySelector({sel}).focus()")
            restos = len((c.js(f"document.querySelector({sel}).innerText") or "").strip())
            for _ in range(restos + 2 if restos else 0):  # vaciar solo si habia algo a medio escribir
                c.tecla("Backspace", "Backspace", 8)
            c.cmd("Input.insertText", {"text": PREFIJO_ORDEN + texto})
            boton = json.dumps(SEL_ENVIAR)
            enviado = False
            for _ in range(10):  # el boton aparece cuando el editor registra el texto
                time.sleep(0.2)
                enviado = c.js(f"(() => {{ const b = document.querySelector({boton}); if (b && !b.disabled) {{ b.click(); return true; }} return false; }})()")
                if enviado:
                    break
            if not enviado:  # plan B: Enter como teclado real
                c.tecla("Enter", "Enter", 13)
            return True, "boton" if enviado else "enter", antes
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", 0


def esperar_respuesta(antes: int, limite_s: float = 20 * 60, estable_s: float = 0.8, parar=None) -> str | None:
    """Espera la linea 'VOZ:' NUEVA (la n.o antes+1) y la devuelve cuando lleva estable_s sin cambiar.
    None si se pasa el limite o si parar() devuelve True."""
    fin = time.time() + limite_s
    ultimo, desde = "", 0.0
    c = None
    try:
        while time.time() < fin:
            if parar and parar():
                return None
            time.sleep(0.5)
            try:
                if c is None:
                    c = Cdp(timeout=5)
                n, txt = _leer_voz(c)
            except Exception:
                if c is not None:
                    c.__exit__()
                c = None
                time.sleep(1.5)
                continue
            if n > antes and txt:
                if txt != ultimo:
                    ultimo, desde = txt, time.time()
                elif time.time() - desde >= estable_s:
                    return ultimo
    finally:
        if c is not None:
            c.__exit__()
    return None


# ------------------------------------------------------------------------------------------------------------------
# PERMISOS (17/11): cuando Nova se queda "Waiting for user input" con opciones tipo "Yes, allow this time / No"
# ------------------------------------------------------------------------------------------------------------------
MARCA_ESPERA = "Waiting for user input"
OPCION_SI = "Yes, allow this time"   # SOLO esta vez: Nova Voz nunca elige "always allow"
OPCION_NO = "No"
BOTON_ENVIAR_PERMISO = "Submit"

_JS_PERMISO = """(() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const si = [...document.querySelectorAll('label,button,[role=radio],[role=option]')]
               .filter(e => vis(e) && (e.innerText || '').trim().replace(/^\\d+\\s*/, '') === %s);  // "1 Yes, allow this time" -> sin el numero
  const t = document.body.innerText;
  const i = t.lastIndexOf(%s);
  if (i < 0 || !si.length) return JSON.stringify({pendiente: i >= 0 && t.length - i < 4000, clicable: false,
                                                  texto: i >= 0 ? t.slice(i, i + 1200) : ''});
  const j = t.indexOf(%s, i);
  return JSON.stringify({pendiente: true, clicable: true, texto: t.slice(i + %d, j > i ? j : i + 1200)});
})()""" % (json.dumps(OPCION_SI), json.dumps(MARCA_ESPERA), json.dumps(OPCION_SI), len(MARCA_ESPERA))


def permiso_pendiente() -> dict | None:
    """Si Nova espera un permiso: {'texto': lo que pide (pregunta, aviso, ruta o comando), 'clicable': bool}."""
    try:
        with Cdp(timeout=4) as c:
            d = json.loads(c.js(_JS_PERMISO) or "{}")
    except Exception:
        return None
    if not d.get("pendiente"):
        return None
    # fuera las lineas que Antigravity anima ("." ".." "...") y los numeros sueltos: el mismo permiso = mismo texto
    texto = "\n".join(l.strip() for l in d.get("texto", "").splitlines()
                      if l.strip().strip(".") and not l.strip().isdigit() and l.strip() != MARCA_ESPERA)
    return {"texto": texto.strip()[:900], "clicable": bool(d.get("clicable"))}


def responder_permiso(si: bool) -> tuple[bool, str]:
    """Elige 'Yes, allow this time' (si) o 'No' y pulsa Submit, como haria el usuario con el raton."""
    opcion = OPCION_SI if si else OPCION_NO
    js_opcion = """(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const el = [...document.querySelectorAll('label,button,[role=radio],[role=option]')]
                   .filter(e => vis(e) && (e.innerText || '').trim().replace(/^\\d+\\s*/, '') === %s);  // "1 Yes, allow this time" -> sin el numero
      if (!el.length) return false; el[el.length - 1].click(); return true;
    })()""" % json.dumps(opcion)
    js_enviar = """(() => {
      const b = [...document.querySelectorAll('button')].find(b => (b.innerText || '').trim().startsWith(%s) && !b.disabled);
      if (!b) return false; b.click(); return true;
    })()""" % json.dumps(BOTON_ENVIAR_PERMISO)
    try:
        with Cdp() as c:
            if not c.js(js_opcion):
                return False, f"no encuentro la opcion '{opcion}'"
            time.sleep(0.5)
            if not c.js(js_enviar):
                return False, "no encuentro el boton Submit"
            time.sleep(1.5)
            sigue = MARCA_ESPERA in (c.js("document.body.innerText.slice(-2500)") or "")
        return (not sigue), ("respondido" if not sigue else "pulsado, pero Antigravity sigue esperando")
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------------------------------------------------------
# MASCOTA 2D (mascota.js): se inyecta en la ventana de Antigravity y se le cambia la cara
# Estados: espera · mirando · escuchando · pensando · hablando · error · pausa
# ------------------------------------------------------------------------------------------------------------------
MASCOTA_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mascota.js")


def _version_mascota() -> int:
    try:
        with open(MASCOTA_JS, encoding="utf-8") as f:
            m = re.search(r"const VERSION = (\d+);", f.read())
        return int(m.group(1)) if m else 1
    except OSError:
        return 1


def mascota(estado: str, texto: str = "") -> bool:
    """Pone la cara de la mascota (si no esta en la ventana, o es vieja, la crea). False si Antigravity no esta."""
    try:
        with Cdp(timeout=4) as c:
            if not c.js(f"!!(window.__novaMascota && (window.__novaMascota.version || 1) >= {_version_mascota()})"):
                with open(MASCOTA_JS, encoding="utf-8") as f:
                    c.js(f.read())
            c.js(f"window.__novaMascota && window.__novaMascota.set({json.dumps(estado)}, {json.dumps(texto)})")
        return True
    except Exception:
        return False


def mascota_presente() -> bool:
    try:
        with Cdp(timeout=3) as c:
            return bool(c.js(f"!!(window.__novaMascota && (window.__novaMascota.version || 1) >= {_version_mascota()})"))
    except Exception:
        return True  # sin Antigravity no hay nada que reponer


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "prueba":
        url = ws_url()
        print("Antigravity (CDP):", "encontrado" if url else "NO encontrado")
        if url:
            with Cdp() as c:
                print("Cuadro de mensaje:", "si" if c.js(f"!!document.querySelector({json.dumps(SEL_EDITOR)})") else "NO")
                n, ult = _leer_voz(c)
                print(f"Lineas VOZ: {n} | ultima: {ult[:80]!r}")
    else:
        print(__doc__)
