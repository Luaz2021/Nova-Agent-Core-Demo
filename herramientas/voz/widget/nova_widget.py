"""
NOVA WIDGET (17/11/2026, Claude) - el monito de Nova FUERA de Antigravity: ventanita flotante sobre el escritorio.
================================================================================================================
- Ventana de Windows transparente de verdad (bordes suaves), siempre encima, sin icono en la barra de tareas.
- Se arrastra con el raton; recuerda donde la dejaste. Clic derecho: menu (ocultar bocadillo / salir).
- Las caras son los fotogramas de fotogramas\\ (generar_fotogramas.py, mismo dibujo que mascota.js).
- Nova Voz Live le cambia la cara por UDP local (127.0.0.1:5011), mensajes JSON: {"estado": "hablando"}
  Estados: espera · mirando · escuchando · pensando · hablando · error · pausa.  {"cmd": "salir"} lo cierra.

    pythonw nova_widget.py          (lo arranca solo Nova Voz Live; si ya hay uno abierto, este se cierra)
Sin dependencias raras: solo Pillow + la API de Windows (ctypes).
"""

from __future__ import annotations

import ctypes
import glob
import json
import os
import re
import socket
import sys
import threading
import zlib
from ctypes import wintypes as wt

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
FOTOGRAMAS = os.path.join(AQUI, "fotogramas")
POSICION = os.path.join(AQUI, "posicion.json")
VOZ_APAGADA = os.path.expanduser(r"~\.gemini\antigravity\voice_cache\voz_apagada.flag")
PUERTO = 5011
FPS_MS = 100        # los fotogramas estan hechos cada 100 ms
TAM_BASE = 150      # ancho del monito a 100 % de escala de Windows (los fotogramas son de 300 px)
_HOJAS: dict = {}   # hoja WebP ya descomprimida (solo la del estado que se esta cargando)


def _abrir_fotograma(f):
    """Un fotograma: ruta de PNG suelto (formato viejo) o (hoja, indice, w, h, columnas) de hojas.json."""
    if isinstance(f, str):
        return Image.open(f)
    ruta, i, w, h, cols = f
    hoja = _HOJAS.get(ruta)  # referencia local: la precarga (otro hilo) puede vaciar _HOJAS a la vez
    if hoja is None:
        with Image.open(ruta) as im:
            hoja = im.convert("RGBA")
        _HOJAS.clear()
        _HOJAS[ruta] = hoja
    x, y = (i % cols) * w, (i // cols) * h
    return hoja.crop((x, y, x + w, y + h))

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

WS_POPUP = 0x80000000
WS_EX_LAYERED, WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80000, 0x8, 0x80, 0x08000000
WM_DESTROY, WM_TIMER, WM_NCHITTEST, WM_NCRBUTTONUP, WM_EXITSIZEMOVE = 0x0002, 0x0113, 0x0084, 0x00A5, 0x0232
HTCAPTION = 2
ULW_ALPHA, AC_SRC_OVER, AC_SRC_ALPHA = 2, 0, 1
SW_SHOWNOACTIVATE, SW_HIDE = 4, 0
TPM_RETURNCMD, TPM_RIGHTBUTTON = 0x100, 0x2
MF_STRING, MF_SEPARATOR, MF_CHECKED = 0x0, 0x800, 0x8


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte), ("SourceConstantAlpha", ctypes.c_ubyte),
                ("AlphaFormat", ctypes.c_ubyte)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wt.HWND), ("message", wt.UINT), ("wParam", wt.WPARAM), ("lParam", wt.LPARAM),
                ("time", wt.DWORD), ("pt", wt.POINT)]


def _firmas():
    user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
    user32.CreateWindowExW.restype = wt.HWND
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.UpdateLayeredWindow.argtypes = [wt.HWND, wt.HDC, ctypes.POINTER(wt.POINT), ctypes.POINTER(wt.SIZE), wt.HDC,
                                           ctypes.POINTER(wt.POINT), wt.COLORREF, ctypes.POINTER(BLENDFUNCTION), wt.DWORD]
    user32.SetTimer.argtypes = [wt.HWND, ctypes.c_size_t, wt.UINT, wt.LPVOID]
    user32.GetDC.restype = wt.HDC
    user32.GetDC.argtypes = [wt.HWND]
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    user32.CreatePopupMenu.restype = wt.HMENU
    user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
    user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.LPVOID]
    user32.DestroyMenu.argtypes = [wt.HMENU]
    user32.SetForegroundWindow.argtypes = [wt.HWND]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    user32.DestroyWindow.argtypes = [wt.HWND]
    user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
    user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wt.HWND, wt.UINT, wt.UINT]
    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.restype = LRESULT
    gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi32.CreateCompatibleDC.restype = wt.HDC
    gdi32.CreateDIBSection.argtypes = [wt.HDC, ctypes.POINTER(BITMAPINFOHEADER), wt.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD]
    gdi32.CreateDIBSection.restype = wt.HBITMAP
    gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi32.SelectObject.restype = wt.HGDIOBJ
    kernel32.GetModuleHandleW.restype = wt.HMODULE
    user32.LoadCursorW.argtypes = [wt.HINSTANCE, wt.LPVOID]
    user32.LoadCursorW.restype = wt.HANDLE
    user32.GetForegroundWindow.restype = wt.HWND
    user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
    user32.MonitorFromWindow.restype = wt.HANDLE
    user32.GetMonitorInfoW.argtypes = [wt.HANDLE, ctypes.c_void_p]


def escala_pantalla() -> float:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # pixeles reales: nada borroso
    except Exception:
        pass
    try:
        return user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


class Widget:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.escala = escala_pantalla()
        self.ancho = int(TAM_BASE * self.escala)
        self.estado = "espera"
        self.bocadillo = True
        # 26/11: fotogramas en hojas WebP (hojas.json, una por estado) o, si no hay, los PNG sueltos de antes
        self.frames: dict[str, list] = {}
        hojas = os.path.join(FOTOGRAMAS, "hojas.json")
        if os.path.exists(hojas):
            with open(hojas, encoding="utf-8") as f:
                for estado, m in json.load(f).items():
                    ruta = os.path.join(FOTOGRAMAS, m["hoja"])
                    if os.path.exists(ruta):
                        self.frames[estado] = [(ruta, i, m["w"], m["h"], m["columnas"]) for i in range(m["n"])]
        if not self.frames:
            for ruta in sorted(glob.glob(os.path.join(FOTOGRAMAS, "*.png"))):
                mm = re.match(r"(.+)_(\d+)\.png$", os.path.basename(ruta))
                if mm:
                    self.frames.setdefault(mm.group(1), []).append(ruta)
        if "espera" not in self.frames:
            raise SystemExit("No hay fotogramas: ejecuta generar_fotogramas.py")
        with _abrir_fotograma(self.frames["espera"][0]) as im:
            self.alto = int(im.height * self.ancho / im.width)
        self.cache: dict[str, list[bytes]] = {}
        self.i = 0
        self.escondido = False  # True mientras hay un juego o app a pantalla completa
        self._crear_ventana()

    # ---------------------------------------------------------------- fotogramas -> bytes BGRA premultiplicados
    def _precargar(self):
        """Todas las caras listas en segundo plano: el cambio de cara es instantaneo (y ~10 MB comprimidas)."""
        for estado in list(self.frames):
            self._cargar(estado)

    def _cargar(self, estado: str) -> list[bytes]:
        cache, con_bocadillo = self.cache, self.bocadillo  # si cambian a mitad (menu), no se mezclan
        if estado not in cache:
            lista = []
            for ruta in self.frames.get(estado) or self.frames["espera"]:
                with _abrir_fotograma(ruta) as im:
                    im = im.convert("RGBA").resize((self.ancho, self.alto), Image.LANCZOS)
                    if not con_bocadillo:  # el bocadillo ocupa la franja de arriba (~18 %)
                        recorte = int(self.alto * 0.18)
                        transparente = Image.new("RGBA", (self.ancho, recorte), (0, 0, 0, 0))
                        im.paste(transparente, (0, 0))
                    lista.append(zlib.compress(im.convert("RGBa").tobytes("raw", "BGRa"), 1))
            cache[estado] = lista
            _HOJAS.clear()  # la hoja descomprimida ocupa ~30 MB: fuera en cuanto el estado esta en cache
        return cache[estado]

    # ---------------------------------------------------------------- ventana
    def _crear_ventana(self):
        _firmas()
        hinst = kernel32.GetModuleHandleW(None)
        self._wndproc = WNDPROC(self._proc)  # guardar referencia: si no, Python la libera y Windows peta
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32649))  # mano
        wc.lpszClassName = "NovaWidget"
        user32.RegisterClassExW(ctypes.byref(wc))
        x, y = self._posicion_inicial()
        self.hwnd = user32.CreateWindowExW(WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                                           "NovaWidget", "Nova", WS_POPUP, x, y, self.ancho, self.alto,
                                           None, None, hinst, None)
        pantalla = user32.GetDC(None)
        self.hdc = gdi32.CreateCompatibleDC(pantalla)
        user32.ReleaseDC(None, pantalla)
        bmi = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=self.ancho, biHeight=-self.alto,
                               biPlanes=1, biBitCount=32, biCompression=0)
        self.bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(self.hdc, ctypes.byref(bmi), 0, ctypes.byref(self.bits), None, 0)
        gdi32.SelectObject(self.hdc, hbmp)
        self.pos = wt.POINT(x, y)
        self._pintar()
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetTimer(self.hwnd, 1, FPS_MS, None)
        threading.Thread(target=self._precargar, daemon=True).start()

    def _posicion_inicial(self) -> tuple[int, int]:
        try:
            with open(POSICION, encoding="utf-8") as f:
                d = json.load(f)
            x, y = int(d["x"]), int(d["y"])
            # que no quede fuera de la pantalla (p. ej. al cambiar de monitor)
            vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
            vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
            if vx - 50 <= x <= vx + vw - 50 and vy - 50 <= y <= vy + vh - 50:
                return x, y
        except Exception:
            pass
        area = wt.RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0)  # SPI_GETWORKAREA: sin la barra de tareas
        return area.right - self.ancho - 24, area.bottom - self.alto - 12

    def _guardar_posicion(self):
        r = wt.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(r))
        self.pos = wt.POINT(r.left, r.top)
        try:
            with open(POSICION, "w", encoding="utf-8") as f:
                json.dump({"x": r.left, "y": r.top}, f)
        except OSError:
            pass

    def _pintar(self):
        lista = self._cargar(self.estado)
        datos = zlib.decompress(lista[self.i % len(lista)])
        ctypes.memmove(self.bits, datos, len(datos))
        r = wt.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(r))
        destino = wt.POINT(r.left, r.top)
        tam = wt.SIZE(self.ancho, self.alto)
        origen = wt.POINT(0, 0)
        mezcla = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        user32.UpdateLayeredWindow(self.hwnd, None, ctypes.byref(destino), ctypes.byref(tam), self.hdc,
                                   ctypes.byref(origen), 0, ctypes.byref(mezcla), ULW_ALPHA)

    # ---------------------------------------------------------------- mensajes de Nova Voz Live
    def _leer_udp(self):
        while True:
            try:
                datos, _ = self.sock.recvfrom(4096)
            except (BlockingIOError, OSError):
                return
            try:
                msg = json.loads(datos.decode("utf-8"))
            except ValueError:
                continue
            if msg.get("cmd") == "salir":
                user32.DestroyWindow(self.hwnd)
                return
            estado = msg.get("estado")
            if estado and estado != self.estado:
                self.estado = estado if estado in self.frames else "espera"
                self.i = 0

    def _menu(self):
        m = user32.CreatePopupMenu()
        user32.AppendMenuW(m, MF_STRING | (MF_CHECKED if self.bocadillo else 0), 1, "Mostrar bocadillo")
        user32.AppendMenuW(m, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(m, MF_STRING, 3, "Apagar Nova Voz (hasta reabrir Antigravity)")
        user32.AppendMenuW(m, MF_STRING, 2, "Cerrar solo el monito")
        p = wt.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        user32.SetForegroundWindow(self.hwnd)
        op = user32.TrackPopupMenu(m, TPM_RETURNCMD | TPM_RIGHTBUTTON, p.x, p.y, 0, self.hwnd, None)
        user32.DestroyMenu(m)
        if op == 1:
            self.bocadillo = not self.bocadillo
            self.cache = {}
            threading.Thread(target=self._precargar, daemon=True).start()
        elif op == 2:
            user32.DestroyWindow(self.hwnd)
        elif op == 3:  # Nova Voz Live ve la marca y se cierra (y cierra el monito); el guardian la respeta
            try:
                with open(VOZ_APAGADA, "w", encoding="utf-8") as f:
                    f.write("apagada desde el monito")
            except OSError:
                pass

    # ---------------------------------------------------------------- juegos / pantalla completa
    def _pantalla_completa(self) -> bool:
        """17/11 (el usuario: "que no se superponga a juegos, luego me banean"): True si la ventana de delante ocupa
        TODA su pantalla (juego, video, presentacion...) o Windows dice que hay algo a pantalla completa."""
        try:
            estado = ctypes.c_int(0)
            if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(estado)) == 0 and estado.value in (2, 3, 4):
                return True  # 2 ocupado (pantalla completa) · 3 juego Direct3D · 4 modo presentacion
        except Exception:
            pass
        fg = user32.GetForegroundWindow()
        if not fg or fg == self.hwnd:
            return False
        clase = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(fg, clase, 64)
        if clase.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            return False  # el escritorio no cuenta
        r = wt.RECT()
        user32.GetWindowRect(fg, ctypes.byref(r))
        mon = user32.MonitorFromWindow(fg, 2)  # MONITOR_DEFAULTTONEAREST
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(mon, ctypes.byref(info)):
            return False
        m = info.rcMonitor
        return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom

    def _proc(self, hwnd, msg, wp, lp):
        try:
            if msg == WM_NCHITTEST:
                return HTCAPTION  # toda la ventana se arrastra
            if msg == WM_TIMER:
                self._leer_udp()
                self.i += 1
                if self.i % 5 == 0:  # cada medio segundo: ¿hay un juego o algo a pantalla completa?
                    completa = self._pantalla_completa()
                    if completa != self.escondido:
                        self.escondido = completa
                        user32.ShowWindow(self.hwnd, SW_HIDE if completa else SW_SHOWNOACTIVATE)
                if not self.escondido:  # escondido no se dibuja nada (ni gasta CPU)
                    self._pintar()
                return 0
            if msg == WM_EXITSIZEMOVE:
                self._guardar_posicion()
                return 0
            if msg == WM_NCRBUTTONUP:
                self._menu()
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def bucle(self):
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", PUERTO))
    except OSError:
        sys.exit(0)  # ya hay un monito abierto
    sock.setblocking(False)
    Widget(sock).bucle()


if __name__ == "__main__":
    main()
