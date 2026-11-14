"""NOVA HORARIO - widget de escritorio con el horario de clase de Luaz (12/11/2026, Claude).

- Muestra la semana real (lunes a viernes con sus fechas), sabe si es Semana A o B y marca hoy y la clase en curso.
- Clic en cualquier cuadro -> escribir una nota para ESE dia (recuperacion, tutoria, entrega...). Vacio = borrar.
- Arrastrar por la barra de arriba para moverlo. "-" lo minimiza a una barrita, "x" lo cierra. "fijar" = siempre delante.
- Si A/B se desfasa (festivos, vacaciones), clic en la etiqueta "Semana A/B" y se invierte desde esa semana.
- Boton "apuntes": libro de pendientes en 3 pestanas (Estudios, Personal, Proyectos). Escribir + Enter = anadir,
  clic en el texto = hecho / no hecho, "x" = borrar, "limpiar hechos" = quitar los tachados.
- Notas, apuntes y posicion en herramientas\\datos\\horario\\ (viaja por Drive: lo mismo en PC y Laptop).
- Sin librerias extra: tkinter viene con Python.

Uso:  pythonw nova_horario.py             (abrir)
      python  nova_horario.py --acceso    (crear "Horario Nova" en el Escritorio de este equipo)
"""
from __future__ import annotations

import datetime as dt
import json
import socket
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import simpledialog

AQUI = Path(__file__).resolve().parent
DATOS = AQUI.parent / "datos" / "horario"
NOTAS = DATOS / "notas.json"
AJUSTES = DATOS / "ajustes.json"
APUNTES = DATOS / "apuntes.json"
FASES = ["Estudios", "Personal", "Proyectos"]

ANCLA_A = dt.date(2026, 11, 9)  # lunes de una Semana A (el martes 10/11 hubo Ingles y PSP)
HORAS = ["18:30", "19:30", "20:30"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie"]

# (dia 0-4, hora) -> modulo. Semana A = semanas impares del curso, B = pares.
CLASES = {
    "A": {
        (0, "18:30"): "Desarrollo de interfaces", (0, "19:30"): "Programación en Python",
        (1, "18:30"): "Inglés profesional", (1, "19:30"): "Prog. servicios y procesos",
        (2, "18:30"): "Itinerario empleabilidad II",
    },
    "B": {
        (0, "19:30"): "Prog. multimedia y móviles",
        (1, "19:30"): "Sist. de gestión empresarial",
        (2, "18:30"): "Acceso a datos", (2, "19:30"): "Digitalización", (2, "20:30"): "Sostenibilidad",
    },
}

C = {  # colores: oscuro como las cajas del escritorio
    "fondo": "#15171c", "celda": "#1f232b", "texto": "#e8e8ea", "suave": "#8b8f98",
    "A": "#e9c46a", "B": "#8ecae6", "hoy": "#2a3140", "ahora": "#f4a261", "nota": "#f6bd60",
    "Estudios": "#8ecae6", "Personal": "#b5e48c", "Proyectos": "#e9c46a",
}
FUENTE = "Segoe UI"


def leer(ruta: Path, defecto: dict) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def guardar(ruta: Path, datos: dict) -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def lunes_de(dia: dt.date) -> dt.date:
    return dia - dt.timedelta(days=dia.weekday())


def letra_semana(lunes: dt.date, inversiones: list[str]) -> str:
    base = ((lunes - ANCLA_A).days // 7) % 2
    giros = sum(1 for d in inversiones if dt.date.fromisoformat(d) <= lunes)
    return "AB"[(base + giros) % 2]


def crear_acceso() -> None:
    pyw = Path(sys.executable).with_name("pythonw.exe")
    escritorio = Path.home() / "Desktop"
    ps = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{escritorio / 'Horario Nova.lnk'}');"
        f"$s.TargetPath='{pyw}';$s.Arguments='\"{Path(__file__).resolve()}\"';"
        f"$s.WorkingDirectory='{AQUI}';$s.Description='Horario de clase (Nova)';$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print(f"Acceso creado: {escritorio / 'Horario Nova.lnk'}")


class Horario(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.notas = leer(NOTAS, {})
        self.apuntes = leer(APUNTES, {f: [] for f in FASES})
        self.ajustes = leer(AJUSTES, {"x": 120, "y": 120, "fijo": False, "inversiones": []})
        self.lunes = lunes_de(dt.date.today())
        self.minimizado = False
        self.vista = "horario"
        self.fase = "Estudios"
        self.overrideredirect(True)
        self.attributes("-alpha", 0.97)
        self.attributes("-topmost", self.ajustes["fijo"])
        self.configure(bg=C["fondo"])
        self.geometry(f"+{self.ajustes['x']}+{self.ajustes['y']}")
        self.pintar()
        self.after(60_000, self.latido)

    # ---------- dibujo ----------
    def pintar(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self.barra()
        if not self.minimizado:
            self.rejilla() if self.vista == "horario" else self.libreta()

    def boton(self, padre: tk.Widget, texto: str, accion, color: str | None = None) -> tk.Label:
        b = tk.Label(padre, text=texto, bg=C["fondo"], fg=color or C["suave"], font=(FUENTE, 10, "bold"), cursor="hand2", padx=6)
        b.bind("<Button-1>", lambda _e: accion())
        return b

    def barra(self) -> None:
        letra = letra_semana(self.lunes, self.ajustes["inversiones"])
        fin = self.lunes + dt.timedelta(days=4)
        b = tk.Frame(self, bg=C["fondo"], padx=8, pady=6)
        b.pack(fill="x")
        es_horario = self.vista == "horario"
        texto = f"Horario  ·  {self.lunes:%d/%m} - {fin:%d/%m}" if es_horario else "Apuntes"
        titulo = tk.Label(b, text=texto, bg=C["fondo"], fg=C["texto"], font=(FUENTE, 11, "bold"))
        titulo.pack(side="left")
        for w in (b, titulo):
            w.bind("<ButtonPress-1>", self.coger)
            w.bind("<B1-Motion>", self.mover)
        if es_horario:
            self.boton(b, f"Semana {letra}", self.invertir, C[letra]).pack(side="left", padx=(8, 0))
        self.boton(b, "x", self.salir).pack(side="right")
        self.boton(b, "-", self.plegar).pack(side="right")
        self.boton(b, "fijar" if not self.ajustes["fijo"] else "fijado", self.fijar, C["A"] if self.ajustes["fijo"] else None).pack(side="right")
        self.boton(b, "apuntes" if es_horario else "horario", self.cambiar_vista, C["texto"]).pack(side="right")
        if es_horario:
            self.boton(b, ">", lambda: self.saltar(7)).pack(side="right")
            self.boton(b, "hoy", lambda: self.saltar(0)).pack(side="right")
            self.boton(b, "<", lambda: self.saltar(-7)).pack(side="right")

    def libreta(self) -> None:
        cuerpo = tk.Frame(self, bg=C["fondo"], padx=10)
        cuerpo.pack(fill="both", pady=(0, 10))
        pestanas = tk.Frame(cuerpo, bg=C["fondo"])
        pestanas.pack(fill="x", pady=(0, 6))
        for f in FASES:
            pend = sum(1 for a in self.apuntes.get(f, []) if not a["hecho"])
            activa = f == self.fase
            p = tk.Label(pestanas, text=f"{f} ({pend})", bg=C["celda"] if activa else C["fondo"],
                         fg=C[f] if activa else C["suave"], font=(FUENTE, 10, "bold"), padx=10, pady=4, cursor="hand2")
            p.pack(side="left", padx=(0, 4))
            p.bind("<Button-1>", lambda _e, fase=f: self.elegir_fase(fase))
        lista = tk.Frame(cuerpo, bg=C["celda"], padx=8, pady=6, width=720)
        lista.pack(fill="x")
        items = self.apuntes.setdefault(self.fase, [])
        if not items:
            tk.Label(lista, text="Nada pendiente aqui. Escribe abajo y pulsa Enter.", bg=C["celda"], fg=C["suave"],
                     font=(FUENTE, 9)).pack(anchor="w")
        for i, a in enumerate(items):
            fila = tk.Frame(lista, bg=C["celda"])
            fila.pack(fill="x", pady=1)
            marca = "[x]" if a["hecho"] else "[ ]"
            fuente = (FUENTE, 10, "overstrike") if a["hecho"] else (FUENTE, 10)
            t = tk.Label(fila, text=f"{marca}  {a['texto']}", bg=C["celda"], fg=C["suave"] if a["hecho"] else C["texto"],
                         font=fuente, anchor="w", justify="left", wraplength=620, cursor="hand2")
            t.pack(side="left", fill="x", expand=True)
            t.bind("<Button-1>", lambda _e, n=i: self.marcar(n))
            tk.Label(fila, text=a.get("fecha", "")[5:].replace("-", "/"), bg=C["celda"], fg=C["suave"], font=(FUENTE, 8)).pack(side="right")
            x = tk.Label(fila, text="x", bg=C["celda"], fg=C["suave"], font=(FUENTE, 10, "bold"), cursor="hand2", padx=6)
            x.pack(side="right")
            x.bind("<Button-1>", lambda _e, n=i: self.borrar(n))
        pie = tk.Frame(cuerpo, bg=C["fondo"])
        pie.pack(fill="x", pady=(6, 0))
        entrada = tk.Entry(pie, bg=C["celda"], fg=C["texto"], insertbackground=C["texto"], relief="flat", font=(FUENTE, 10), width=55)
        entrada.pack(side="left", fill="x", expand=True, ipady=4)
        entrada.bind("<Return>", lambda _e: self.anadir(entrada.get()))
        entrada.focus_set()
        self.boton(pie, "limpiar hechos", self.limpiar).pack(side="right")

    def guardar_apuntes(self) -> None:
        guardar(APUNTES, self.apuntes)
        self.pintar()

    def anadir(self, texto: str) -> None:
        if texto.strip():
            self.apuntes[self.fase].append({"texto": texto.strip(), "hecho": False, "fecha": dt.date.today().isoformat()})
            self.guardar_apuntes()

    def marcar(self, n: int) -> None:
        item = self.apuntes[self.fase][n]
        item["hecho"] = not item["hecho"]
        self.guardar_apuntes()

    def borrar(self, n: int) -> None:
        del self.apuntes[self.fase][n]
        self.guardar_apuntes()

    def limpiar(self) -> None:
        self.apuntes[self.fase] = [a for a in self.apuntes[self.fase] if not a["hecho"]]
        self.guardar_apuntes()

    def elegir_fase(self, fase: str) -> None:
        self.fase = fase
        self.pintar()

    def cambiar_vista(self) -> None:
        self.vista = "apuntes" if self.vista == "horario" else "horario"
        self.pintar()

    def rejilla(self) -> None:
        letra = letra_semana(self.lunes, self.ajustes["inversiones"])
        hoy, ahora = dt.date.today(), dt.datetime.now()
        g = tk.Frame(self, bg=C["fondo"], padx=8, pady=(0))
        g.pack(fill="both", pady=(0, 8))
        for d, nombre in enumerate(DIAS):
            fecha = self.lunes + dt.timedelta(days=d)
            es_hoy = fecha == hoy
            tk.Label(g, text=f"{nombre} {fecha:%d}", bg=C["fondo"], fg=C[letra] if es_hoy else C["suave"],
                     font=(FUENTE, 9, "bold")).grid(row=0, column=d + 1, pady=(0, 3))
        for h, hora in enumerate(HORAS):
            tk.Label(g, text=hora, bg=C["fondo"], fg=C["suave"], font=(FUENTE, 9)).grid(row=h + 1, column=0, padx=(0, 6))
            for d in range(5):
                fecha = self.lunes + dt.timedelta(days=d)
                self.celda(g, fecha, d, hora, letra, hoy, ahora).grid(row=h + 1, column=d + 1, padx=2, pady=2, sticky="nsew")

    def celda(self, padre, fecha, d, hora, letra, hoy, ahora) -> tk.Frame:
        clase = CLASES[letra].get((d, hora), "")
        nota = self.notas.get(f"{fecha.isoformat()} {hora}", "")
        inicio = dt.datetime.combine(fecha, dt.time(*map(int, hora.split(":"))))
        en_curso = inicio <= ahora < inicio + dt.timedelta(hours=1)
        fondo = C["hoy"] if fecha == hoy else C["celda"]
        f = tk.Frame(padre, bg=fondo, width=150, height=52, cursor="hand2",
                     highlightthickness=2 if en_curso else 1,
                     highlightbackground=C["ahora"] if en_curso else (C[letra] if clase else fondo))
        f.grid_propagate(False)
        f.pack_propagate(False)
        textos = [(clase, C["texto"], 9, "bold")] if clase else []
        textos += [(nota, C["nota"], 8, "normal")] if nota else []
        textos = textos or [("+", C["suave"], 11, "normal")]
        for t, color, tam, peso in textos:
            tk.Label(f, text=t, bg=fondo, fg=color, font=(FUENTE, tam, peso), wraplength=140, justify="center").pack(expand=True)
        for w in [f, *f.winfo_children()]:
            w.bind("<Button-1>", lambda _e, k=f"{fecha.isoformat()} {hora}", c=clase: self.anotar(k, c))
        return f

    # ---------- acciones ----------
    def anotar(self, clave: str, clase: str) -> None:
        titulo = f"{clase} · {clave}" if clase else clave
        texto = simpledialog.askstring("Nota", f"{titulo}\n(vacio = borrar)", initialvalue=self.notas.get(clave, ""), parent=self)
        if texto is None:
            return
        if texto.strip():
            self.notas[clave] = texto.strip()
        else:
            self.notas.pop(clave, None)
        guardar(NOTAS, self.notas)
        self.pintar()

    def invertir(self) -> None:
        inv = self.ajustes["inversiones"]
        clave = self.lunes.isoformat()
        inv.remove(clave) if clave in inv else inv.append(clave)
        guardar(AJUSTES, self.ajustes)
        self.pintar()

    def saltar(self, dias: int) -> None:
        self.lunes = lunes_de(dt.date.today()) if dias == 0 else self.lunes + dt.timedelta(days=dias)
        self.pintar()

    def fijar(self) -> None:
        self.ajustes["fijo"] = not self.ajustes["fijo"]
        self.attributes("-topmost", self.ajustes["fijo"])
        guardar(AJUSTES, self.ajustes)
        self.pintar()

    def plegar(self) -> None:
        self.minimizado = not self.minimizado
        self.pintar()

    def coger(self, e) -> None:
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def mover(self, e) -> None:
        x, y = e.x_root - self._dx, e.y_root - self._dy
        self.geometry(f"+{x}+{y}")
        self.ajustes.update(x=x, y=y)

    def latido(self) -> None:  # cada minuto: refresca "hoy" y la clase en curso (no en apuntes: borraria lo que escribes)
        if self.vista == "horario":
            self.pintar()
        self.after(60_000, self.latido)

    def salir(self) -> None:
        guardar(AJUSTES, self.ajustes)
        self.destroy()


def nitido() -> None:
    """Sin esto Windows estira la ventana con el zoom de pantalla y se ve borrosa."""
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def main() -> None:
    nitido()
    if "--acceso" in sys.argv:
        crear_acceso()
        return
    candado = socket.socket()
    try:
        candado.bind(("127.0.0.1", 47613))  # una sola ventana abierta a la vez
    except OSError:
        return
    Horario().mainloop()


if __name__ == "__main__":
    main()
