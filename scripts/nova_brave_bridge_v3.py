r"""
Nova Brave Bridge v4.0 (09/11/2026, Claude: pase de pago de un solo uso; el archivo conserva el nombre _v3 por los .vbs)
Puente local (WebSocket + HTTP) entre Nova y la extension de Brave.

v4: POST /pase_pago (cabecera X-Nova-Clave) -> la extension permite UN pago durante 10 min. La clave vive en
    nova_core\.pase_pago.clave: la lee el hook de turno cuando Alexander escribe "autorizo el pago"; nova_hook.py
    impide que Nova la lea o llame a /pase_pago. /execute rechaza las acciones del pase (Nova no puede darselo).

- WebSocket /ws : solo acepta conexiones de extensiones (Origin chrome-extension://).
- HTTP /execute, /snapshot, /screenshot, /status : solo para procesos locales (PowerShell/Python).
  Se rechaza cualquier peticion que venga de un navegador (cabecera Origin / Sec-Fetch-Site),
  asi una web abierta en Brave no puede usar el puente para manejar tu navegador.
- Las capturas se guardan en disco y se devuelve la ruta (no un base64 enorme).
"""

import asyncio
import base64
import json
import os
import time
import uuid
from pathlib import Path

from aiohttp import web

HOST = "127.0.0.1"
PORT = int(os.environ.get("NOVA_BRAVE_PORT", "5005"))
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
# Opcional: fijar el ID de la extension (brave://extensions) para rechazar otras extensiones.
PINNED_EXTENSION_ID = os.environ.get("NOVA_BRAVE_EXTENSION_ID", "").strip()
DEFAULT_TIMEOUT = 20.0
MAX_TIMEOUT = 60.0
SCREENSHOT_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".gemini" / "antigravity" / "brave_screenshots"
MAX_SCREENSHOTS = 30

CLAVE_PASE = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".gemini" / "nova_core" / ".pase_pago.clave"
ACCIONES_RESERVADAS = {"GRANT_PAYMENT_PASS"}  # solo por /pase_pago

active_ws = None
pending_requests = {}


def clave_pase():
    """Clave secreta del pase de pago (se crea la primera vez). Solo la leen este puente y el hook de turno."""
    import secrets
    try:
        return CLAVE_PASE.read_text(encoding="utf-8").strip()
    except OSError:
        clave = secrets.token_hex(32)
        CLAVE_PASE.parent.mkdir(parents=True, exist_ok=True)
        CLAVE_PASE.write_text(clave, encoding="utf-8")
        return clave


def log(msg):
    print(f"[Nova Bridge v3.1] {msg}", flush=True)


@web.middleware
async def guard_middleware(request, handler):
    # Anti DNS-rebinding: solo nombres locales.
    if request.host not in ALLOWED_HOSTS:
        return web.json_response({"ok": False, "error": "Host no permitido"}, status=403)

    if request.path in ("/", "/ws"):
        origin = request.headers.get("Origin", "")
        if not origin.startswith("chrome-extension://"):
            log(f"WebSocket rechazado (Origin={origin or 'ninguno'})")
            return web.Response(status=403, text="Solo la extension de Brave puede conectarse")
        if PINNED_EXTENSION_ID and origin != f"chrome-extension://{PINNED_EXTENSION_ID}":
            log(f"WebSocket rechazado: extension no autorizada ({origin})")
            return web.Response(status=403, text="Extension no autorizada")
        return await handler(request)

    # API HTTP: los navegadores siempre envian Origin o Sec-Fetch-Site; PowerShell/Python no.
    fetch_site = request.headers.get("Sec-Fetch-Site", "")
    if request.headers.get("Origin") or (fetch_site and fetch_site != "none"):
        log(f"Peticion HTTP desde navegador bloqueada: {request.path} (Origin={request.headers.get('Origin')})")
        return web.json_response({"ok": False, "error": "Peticiones desde paginas web no permitidas"}, status=403)
    return await handler(request)


def traer_brave_delante(titulo):
    """Trae delante la ventana de Brave cuyo titulo empieza por el de la pestaña (Windows no deja a Brave hacerlo solo).
    Truco estandar: pulsar y soltar Alt antes de SetForegroundWindow desbloquea el cambio de primer plano."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    candidatas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        n = u.GetWindowTextLengthW(h)
        if n and u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            t = b.value
            if t.endswith("Brave") and (not titulo or t.startswith(titulo[:60])):
                candidatas.append(h)
        return True

    u.EnumWindows(cb, 0)
    if not candidatas:
        log(f"traer_delante: no encontre la ventana de Brave ('{titulo[:40]}')")
        return False
    h = candidatas[0]
    if u.IsIconic(h):
        u.ShowWindow(h, 9)  # SW_RESTORE
    u.keybd_event(0x12, 0, 0, 0)  # Alt abajo
    ok = bool(u.SetForegroundWindow(h))
    u.keybd_event(0x12, 0, 2, 0)  # Alt arriba
    log(f"traer_delante: '{titulo[:40]}' -> {ok}")
    return ok


def fail_pending(reason):
    for fut in list(pending_requests.values()):
        if not fut.done():
            fut.set_result({"ok": False, "error": reason})


async def websocket_handler(request):
    global active_ws
    ws = web.WebSocketResponse(heartbeat=None, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)

    if active_ws is not None and not active_ws.closed:
        log("Nueva conexion de la extension: se reemplaza la anterior.")
        await active_ws.close()
    active_ws = ws
    log(f"Extension conectada ({request.headers.get('Origin')}).")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue
                mtype = data.get("type")
                if mtype == "ping":
                    await ws.send_str(json.dumps({"type": "pong", "timestamp": data.get("timestamp")}))
                    continue
                if mtype == "hello":
                    log(f"Extension v{data.get('version')} lista.")
                    await ws.send_str(json.dumps({"type": "welcome"}))
                    continue
                if mtype == "traer_delante":  # la extension necesita que Brave se vea para el raton real
                    ok = traer_brave_delante(str(data.get("titulo") or ""))
                    await ws.send_str(json.dumps({"type": "respuesta_puente", "ref": data.get("ref"), "ok": ok}))
                    continue
                req_id = data.get("id")
                fut = pending_requests.get(req_id)
                if fut and not fut.done():
                    fut.set_result(data)
            elif msg.type == web.WSMsgType.ERROR:
                log(f"Error en WebSocket: {ws.exception()}")
    finally:
        if active_ws is ws:
            active_ws = None
            fail_pending("La extension se desconecto durante el comando")
        log("Extension desconectada.")
    return ws


def save_screenshot(result):
    data = result.get("data") if isinstance(result, dict) else None
    image = data.get("image") if isinstance(data, dict) else None
    if not isinstance(image, str) or not image.startswith("data:image/"):
        return result
    header, b64 = image.split(",", 1)
    ext = "png" if "png" in header else "jpg"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"brave_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.{ext}"
    path.write_bytes(base64.b64decode(b64))
    # Rotacion: conservar solo las ultimas MAX_SCREENSHOTS capturas.
    shots = sorted(SCREENSHOT_DIR.glob("brave_*"), key=lambda p: p.stat().st_mtime)
    for old in shots[:-MAX_SCREENSHOTS]:
        try:
            old.unlink()
        except OSError:
            pass
    del data["image"]
    data["imagePath"] = str(path)
    return result


async def send_command(action, args, timeout=DEFAULT_TIMEOUT):
    if not active_ws or active_ws.closed:
        return 503, {
            "ok": False,
            "error": "La extension de Brave no esta conectada. Abre Brave y revisa que 'Nova Agent para Brave' este activa en brave://extensions.",
        }
    req_id = f"cmd_{uuid.uuid4().hex[:10]}"
    fut = asyncio.get_running_loop().create_future()
    pending_requests[req_id] = fut
    try:
        await active_ws.send_str(json.dumps({"id": req_id, "action": action, "args": args or {}}))
        result = await asyncio.wait_for(fut, timeout=timeout)
        result.pop("id", None)
        return 200, save_screenshot(result)
    except asyncio.TimeoutError:
        return 504, {"ok": False, "error": f"Timeout ({timeout:.0f}s) esperando a Brave en la accion '{action}'."}
    finally:
        pending_requests.pop(req_id, None)


async def execute_handler(request):
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Cuerpo invalido (se esperaba JSON)."}, status=400)
    action = payload.get("action") if isinstance(payload, dict) else None
    if not action:
        return web.json_response({"ok": False, "error": "Parametro 'action' requerido."}, status=400)
    if str(action).upper() == "UPLOAD_FILE":  # que el archivo exista (la extension no puede mirar el disco)
        a = payload.get("args") or {}
        files = a.get("files") if isinstance(a.get("files"), list) else [a.get("file") or a.get("path")]
        faltan = [str(f) for f in files if not f or not os.path.isfile(str(f))]
        if faltan:
            return web.json_response({"ok": False, "error": f"No existen estos archivos: {faltan}"}, status=400)
    if str(action).upper() in ACCIONES_RESERVADAS:
        log(f"/execute intento usar una accion reservada ({action}): rechazado")
        return web.json_response({"ok": False, "error": "El permiso de pago solo lo da Alexander (escribiendo 'autorizo el pago')."},
                                 status=403)
    try:
        timeout = min(float(payload.get("timeout", DEFAULT_TIMEOUT)), MAX_TIMEOUT)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    status, body = await send_command(action, payload.get("args") or {}, timeout)
    return web.json_response(body, status=status)


async def snapshot_handler(request):
    status, body = await send_command("SNAPSHOT", {})
    return web.json_response(body, status=status)


async def screenshot_handler(request):
    status, body = await send_command("SCREENSHOT", {})
    return web.json_response(body, status=status)


async def pase_pago_handler(request):
    import hmac
    if not hmac.compare_digest(request.headers.get("X-Nova-Clave", ""), clave_pase()):
        log("/pase_pago con clave incorrecta: rechazado")
        return web.json_response({"ok": False, "error": "Clave incorrecta"}, status=403)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    args = {"minutes": payload.get("minutos", 10), "motivo": str(payload.get("motivo", ""))[:200]}
    status, body = await send_command("GRANT_PAYMENT_PASS", args)
    log(f"Pase de pago concedido por Alexander ({args['minutes']} min): {body}")
    return web.json_response(body, status=status)


async def status_handler(request):
    return web.json_response({
        "status": "online",
        "brave_connected": bool(active_ws and not active_ws.closed),
        "protocol": "Nova Brave WebSocket Bridge v4.0",
        "port": PORT,
    })


def create_app():
    app = web.Application(middlewares=[guard_middleware], client_max_size=4 * 1024 * 1024)
    app.router.add_get("/", websocket_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_post("/execute", execute_handler)
    app.router.add_get("/status", status_handler)
    app.router.add_get("/snapshot", snapshot_handler)
    app.router.add_get("/screenshot", screenshot_handler)
    app.router.add_post("/pase_pago", pase_pago_handler)
    return app


if __name__ == "__main__":
    clave_pase()  # que exista desde el arranque (el hook la necesita)
    log(f"Iniciando en http://{HOST}:{PORT} ...")
    web.run_app(create_app(), host=HOST, port=PORT, print=lambda m: log(m))
