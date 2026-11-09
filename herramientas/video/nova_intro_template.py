"""
NOVA - intro de logo cyberpunk, 10 s, 1920x1080, 30 fps, con pista de ritmo sintetizada (120 BPM).

    python nova_intro.py            -> nova_intro.mp4
    python nova_intro.py --frames 75,150,240   -> solo guarda esos fotogramas en PNG (para revisar)

Todo se dibuja con codigo (numpy + Pillow) y se codifica con FFmpeg. Sin recursos externos.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
W, H, FPS, DUR = 1920, 1080, 30, 10.0
N_FR = int(FPS * DUR)
BEAT = 0.5  # 120 BPM
FUENTE = r"C:\Windows\Fonts\bahnschrift.ttf"

NEGRO = (5, 6, 10)
CIAN = (0, 240, 255)
MAGENTA = (255, 43, 214)
ACIDO = (232, 255, 58)
BLANCO = (245, 247, 255)

rng = np.random.default_rng(7)


# ------------------------------------------------------------------ utilidades
def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def tramo(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


@lru_cache(maxsize=64)
def fuente(tam, estilo=b"Bold Condensed"):
    f = ImageFont.truetype(FUENTE, tam)
    f.set_variation_by_name(estilo)
    return f


def texto_centrado(draw, txt, tam, color, cx=W / 2, cy=H / 2, estilo=b"Bold Condensed", espaciado=0):
    f = fuente(int(tam), estilo)
    if espaciado:
        anchos = [draw.textlength(c, font=f) for c in txt]
        total = sum(anchos) + espaciado * (len(txt) - 1)
        x = cx - total / 2
        for c, a in zip(txt, anchos):
            draw.text((x, cy), c, font=f, fill=color, anchor="lm")
            x += a + espaciado
    else:
        draw.text((cx, cy), txt, font=f, fill=color, anchor="mm")


def brillo(capa: Image.Image, radios=(6, 18, 42), fuerza=(1.0, 0.8, 0.6)) -> np.ndarray:
    """Glow: suma de desenfoques (calculado a media resolucion para ir rapido)."""
    peq = capa.resize((W // 2, H // 2), Image.BILINEAR)
    acc = np.zeros((H // 2, W // 2, 3), np.float32)
    for r, k in zip(radios, fuerza):
        acc += np.asarray(peq.filter(ImageFilter.GaussianBlur(r / 2)), np.float32) * k
    return np.asarray(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)


def aberracion(a: np.ndarray, px: int) -> np.ndarray:
    if px == 0:
        return a
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], px, axis=1)
    out[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return out


def glitch_bandas(a: np.ndarray, fuerza: float, semilla: int) -> np.ndarray:
    if fuerza <= 0:
        return a
    r = np.random.default_rng(semilla)
    out = a.copy()
    for _ in range(int(6 + 10 * fuerza)):
        y = r.integers(0, H - 40)
        h = r.integers(6, 40)
        dx = int(r.integers(-120, 120) * fuerza)
        out[y:y + h] = np.roll(a[y:y + h], dx, axis=1)
    return out


# máscaras fijas
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VINETA = np.clip(1.15 - ((xx - W / 2) ** 2 / (W * 0.62) ** 2 + (yy - H / 2) ** 2 / (H * 0.72) ** 2), 0.55, 1.0)[..., None]
SCAN = np.where((np.arange(H) % 3) == 0, 0.86, 1.0).astype(np.float32)[:, None, None]


# ------------------------------------------------------------------ logo (coordenadas unidad, y hacia abajo)
SKEW = 0.22


def sk(p):
    x, y = p
    return (x - SKEW * y, y)


TRAZOS_N = [
    [(-0.52, 0.62), (-0.52, -0.62), (-0.30, -0.62), (-0.30, 0.62)],                 # pierna izquierda
    [(-0.30, -0.62), (-0.10, -0.62), (0.52, 0.62), (0.30, 0.62)],                    # diagonal
    [(0.30, 0.62), (0.30, -0.10), (0.52, -0.30), (0.52, 0.62)],                      # pierna derecha (corte en bisel)
]
# hexagono con lado plano arriba; faltan el lado de arriba-derecha (ahi nace la estrella) y el de abajo-izquierda
HEX = [(math.cos(math.radians(60 * k)) * 1.2, math.sin(math.radians(60 * k)) * 1.2) for k in range(6)]
HUECOS_HEX = {2, 5}
ESTRELLA = (0.92, -0.56)  # en el hueco de arriba-derecha (sin inclinar)


def poli_parcial(pts, p, cerrar=True):
    """Puntos de la polilinea recorrida hasta la fraccion p de su longitud."""
    seq = pts + ([pts[0]] if cerrar else [])
    seg = [math.dist(a, b) for a, b in zip(seq, seq[1:])]
    objetivo, out = sum(seg) * min(max(p, 0), 1), [seq[0]]
    for (a, b), L in zip(zip(seq, seq[1:]), seg):
        if objetivo >= L:
            out.append(b)
            objetivo -= L
        else:
            k = objetivo / L if L else 0
            out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            break
    return out


def a_pantalla(p, cx, cy, s, rot=0.0, inclinar=True):
    x, y = sk(p) if inclinar else p
    c, si = math.cos(rot), math.sin(rot)
    return (cx + (x * c - y * si) * s, cy + (x * si + y * c) * s)


def puntos_logo(n):
    """n puntos repartidos sobre los contornos del logo (destino de las particulas)."""
    """Cada punto lleva si va inclinado (la N) o recto (el hexagono)."""
    pts = []
    formas = [(t, True) for t in TRAZOS_N] + [([HEX[k], HEX[(k + 1) % 6]], False) for k in range(6) if k not in HUECOS_HEX]
    for _ in range(n):
        forma, es_n = formas[rng.integers(len(formas))]
        seq = forma + ([forma[0]] if es_n else [])
        i = rng.integers(len(seq) - 1)
        k = rng.random()
        a, b = seq[i], seq[i + 1]
        pts.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, es_n))
    return pts


N_PART = 900
DESTINO = puntos_logo(N_PART)
ORIGEN = [(rng.uniform(-3.2, 3.2), rng.uniform(-1.9, 1.9)) for _ in range(N_PART)]
RETRASO = rng.uniform(0, 0.45, N_PART)
COLOR_PART = [CIAN if rng.random() < 0.7 else MAGENTA for _ in range(N_PART)]


def dibujar_logo(capa_linea: ImageDraw.ImageDraw, capa_relleno: ImageDraw.ImageDraw, t_logo, cx, cy, s, rot_hex=0.0,
                 relleno=1.0, grosor=5):
    """t_logo: 0..1 progreso de construccion."""
    # hexagono roto
    ph = ease_in_out(tramo(t_logo, 0.0, 0.55))
    for k in range(6):
        if k in HUECOS_HEX:
            continue
        a, b = HEX[k], HEX[(k + 1) % 6]
        pk = tramo(ph, k / 6, (k + 1) / 6)
        if pk <= 0:
            continue
        fin = (a[0] + (b[0] - a[0]) * pk, a[1] + (b[1] - a[1]) * pk)
        p1 = a_pantalla(a, cx, cy, s, rot_hex, inclinar=False)
        p2 = a_pantalla(fin, cx, cy, s, rot_hex, inclinar=False)
        capa_linea.line([p1, p2], fill=CIAN, width=grosor - 1)
        # muescas en las esquinas
        capa_linea.ellipse([p1[0] - 5, p1[1] - 5, p1[0] + 5, p1[1] + 5], fill=CIAN)
    # N
    for i, trazo in enumerate(TRAZOS_N):
        pt = ease_in_out(tramo(t_logo, 0.2 + i * 0.15, 0.62 + i * 0.15))
        if pt <= 0:
            continue
        col = MAGENTA if i == 1 else CIAN
        if relleno > 0 and pt >= 1:
            capa_relleno.polygon([a_pantalla(p, cx, cy, s) for p in trazo],
                                 fill=tuple(int(c * 0.22 * relleno) for c in col))
        capa_linea.line([a_pantalla(p, cx, cy, s) for p in poli_parcial(trazo, pt)], fill=col, width=grosor, joint="curve")
    # estrella nova
    pe = ease_out(tramo(t_logo, 0.78, 1.0))
    if pe > 0:
        ex, ey = a_pantalla(ESTRELLA, cx, cy, s, rot_hex, inclinar=False)
        r = s * 0.16 * pe
        ang = t_logo * 2.0
        for k in range(4):
            a = ang + k * math.pi / 2
            capa_linea.polygon([(ex + math.cos(a) * r, ey + math.sin(a) * r),
                                (ex + math.cos(a + 0.5) * r * 0.18, ey + math.sin(a + 0.5) * r * 0.18),
                                (ex, ey),
                                (ex + math.cos(a - 0.5) * r * 0.18, ey + math.sin(a - 0.5) * r * 0.18)], fill=ACIDO)


def rejilla(draw, t, intensidad=1.0, horizonte=0.64):
    hy = H * horizonte
    col = tuple(int(c * 0.55 * intensidad) for c in MAGENTA)
    for k in range(-14, 15):
        draw.line([(W / 2 + k * 18, hy), (W / 2 + k * 260, H + 40)], fill=col, width=2)
    off = (t * 1.6) % 1.0
    for k in range(14):
        z = (k + off) / 14
        y = hy + (H - hy) * z ** 2.2
        draw.line([(0, y), (W, y)], fill=tuple(int(c * (0.25 + 0.75 * z)) for c in col), width=2)
    draw.line([(0, hy), (W, hy)], fill=tuple(int(c * 0.9 * intensidad) for c in CIAN), width=2)


# ------------------------------------------------------------------ escenas
PALABRAS = [(0.50, "CÓDIGO"), (0.75, "LUZ"), (1.00, "VELOCIDAD"), (1.25, "VISIÓN"), (1.50, "FUTURO"),
            (1.75, "PULSO"), (2.00, "NOVA"), (2.25, "///")]
LEMA = [(6.50, "CREA"), (6.83, "SIN"), (7.16, "LÍMITES")]


def golpe(t, cada=BEAT, desde=0.5):
    """1 justo en cada golpe y decae: para flashes y glitch."""
    if t < desde:
        return 0.0
    fase = ((t - desde) % cada) / cada
    return math.exp(-fase * 9)


def frame(i: int) -> np.ndarray:
    t = i / FPS
    img = Image.new("RGB", (W, H), NEGRO)
    d = ImageDraw.Draw(img)
    linea = Image.new("RGB", (W, H), (0, 0, 0))
    dl = ImageDraw.Draw(linea)
    relleno = Image.new("RGB", (W, H), (0, 0, 0))
    dr = ImageDraw.Draw(relleno)
    aberr, glitch, flash = 0, 0.0, 0.0

    if t < 0.5:  # ---------------- 1. chispa
        y = H * ease_in_out(t / 0.5)
        dl.line([(0, y), (W, y)], fill=CIAN, width=2)
        r = 4 + 60 * (t / 0.5) ** 3
        dl.ellipse([W / 2 - r, H / 2 - r / 6, W / 2 + r, H / 2 + r / 6], fill=ACIDO)
    elif t < 2.5:  # -------------- 2. palabras estroboscopicas
        idx = max(k for k, (t0, _) in enumerate(PALABRAS) if t >= t0)
        t0, palabra = PALABRAS[idx]
        local = (t - t0) / 0.25
        invertido = idx % 2 == 1
        if invertido:
            d.rectangle([0, 0, W, H], fill=BLANCO)
        tam = 330 * (1.0 + 0.10 * local) if palabra != "///" else 420
        col = NEGRO if invertido else (ACIDO if palabra == "NOVA" else BLANCO)
        texto_centrado(d, palabra, tam, col)
        if not invertido:
            texto_centrado(dl, palabra, tam, MAGENTA if idx % 4 == 0 else CIAN)
        # barras de "interfaz"
        dl.rectangle([80, H - 120, 80 + 520 * min(local, 1), H - 112], fill=CIAN)
        texto_centrado(d, f"NV-{idx:02d} // {t:05.2f}s", 26, MAGENTA if not invertido else NEGRO, cx=260, cy=90,
                       estilo=b"SemiBold SemiCondensed")
        aberr = int(14 * (1 - min(local, 1)))
        glitch = 0.6 if local < 0.25 else 0.0
    elif t < 7.5:  # -------------- 3-4. construccion + heroe + lema
        rejilla(dl, t, intensidad=ease_out(tramo(t, 2.5, 3.2)))
        empuje = 1.0 + 0.06 * ease_in_out(tramo(t, 5.0, 7.5))
        s = 300 * empuje
        cx, cy = W / 2, H * 0.43
        t_logo = tramo(t, 2.6, 4.9)
        # particulas que convergen
        if t < 5.2:
            for (ox, oy), (dx, dy, es_n), ret, col in zip(ORIGEN, DESTINO, RETRASO, COLOR_PART):
                k = ease_out(tramo(t, 2.5 + ret, 4.3 + ret))
                px, py = ox + (dx - ox) * k, oy + (dy - oy) * k
                X, Y = a_pantalla((px, py), cx, cy, s, inclinar=es_n)
                a = 1.0 - 0.8 * tramo(t, 4.6, 5.2)
                rr = 1.6 + 1.6 * (1 - k)
                dl.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=tuple(int(c * a) for c in col))
        dibujar_logo(dl, dr, t_logo, cx, cy, s, rot_hex=0.05 * math.sin(t * 1.3), relleno=tramo(t, 4.6, 5.2))
        # barrido de luz
        if 5.0 <= t < 6.5:
            bx = -300 + (W + 600) * ease_in_out(tramo(t, 5.0, 6.2))
            dl.polygon([(bx, 0), (bx + 90, 0), (bx - 260, H), (bx - 350, H)], fill=(60, 70, 90))
        # lema en cortes rapidos
        if t >= 6.5:
            idx = max(k for k, (t0, _) in enumerate(LEMA) if t >= t0)
            t0, palabra = LEMA[idx]
            local = (t - t0) / 0.33
            d.rectangle([0, 0, W, H], fill=BLANCO if idx == 1 else NEGRO)
            linea = Image.new("RGB", (W, H), (0, 0, 0))
            dl = ImageDraw.Draw(linea)
            relleno = Image.new("RGB", (W, H), (0, 0, 0))
            texto_centrado(d, palabra, 360 * (1 + 0.08 * local), NEGRO if idx == 1 else ACIDO)
            if idx != 1:
                texto_centrado(dl, palabra, 360 * (1 + 0.08 * local), MAGENTA)
            aberr = int(16 * (1 - min(local, 1)))
            glitch = 0.5 if local < 0.2 else 0.0
        else:
            aberr = int(3 + 10 * golpe(t, BEAT, 2.5))
            glitch = 0.45 * golpe(t, BEAT * 2, 5.0) if t >= 5.0 else 0.0
            flash = 0.55 * (1 - tramo(t, 2.5, 2.7)) + (0.35 * (1 - tramo(t, 5.0, 5.15)) if t >= 5.0 else 0.0)
    else:  # ------------------------ 5. cierre
        rejilla(dl, t, intensidad=0.55)
        k = ease_out(tramo(t, 7.5, 8.1))
        s = 175
        cx, cy = W / 2 - 330 * k, H * 0.45
        dibujar_logo(dl, dr, 1.0, cx, cy, s * (1.35 - 0.35 * k), rot_hex=0.04 * math.sin(t * 1.3), grosor=4)
        ka = ease_out(tramo(t, 7.75, 8.35))
        tx = W / 2 + 190
        texto_centrado(d, "NOVA", 260, BLANCO, cx=tx, cy=H * 0.42, espaciado=int(60 * ka + 10))
        texto_centrado(dl, "NOVA", 260, CIAN, cx=tx, cy=H * 0.42, espaciado=int(60 * ka + 10))
        if t >= 8.3:
            kb = ease_out(tramo(t, 8.3, 8.8))
            d.rectangle([tx - 300, H * 0.56, tx - 300 + 600 * kb, H * 0.56 + 4], fill=MAGENTA)
            if t >= 8.6:
                texto_centrado(d, "INTELIGENCIA QUE CONSTRUYE", 46, BLANCO, cx=tx, cy=H * 0.62,
                               estilo=b"SemiBold SemiCondensed", espaciado=6)
                texto_centrado(d, "2026 // 2027", 30, ACIDO, cx=tx, cy=H * 0.69, estilo=b"SemiBold SemiCondensed", espaciado=10)
        aberr = int(18 * (1 - tramo(t, 7.5, 7.9))) + 2
        glitch = 0.8 * (1 - tramo(t, 7.5, 7.75)) + (0.35 if 9.0 <= t < 9.07 else 0)
        flash = 0.9 * (1 - tramo(t, 7.5, 7.62))

    base = np.asarray(img, np.float32)
    lineas = np.asarray(linea, np.float32)
    rel = np.asarray(relleno, np.float32)
    out = base + rel + lineas + brillo(linea) * 0.9
    out = aberracion(np.clip(out, 0, 255), aberr)
    out = glitch_bandas(out, glitch, i)
    out = out + flash * 255
    out = out * SCAN * VINETA
    out += rng.normal(0, 4.0, (H, W, 1)).astype(np.float32)  # grano
    if t > DUR - 0.35:
        out *= 1 - tramo(t, DUR - 0.35, DUR)
    return np.clip(out, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ audio (sintetizado, 120 BPM)
def audio(ruta: Path, sr=44100):
    n = int(DUR * sr)
    tt = np.arange(n) / sr
    a = np.zeros(n, np.float32)

    def poner(senal, t0, gan=1.0):
        i0 = int(t0 * sr)
        j = min(n, i0 + len(senal))
        a[i0:j] += senal[: j - i0] * gan

    def bombo(dur=0.35):
        x = np.arange(int(dur * sr)) / sr
        f = 45 + 110 * np.exp(-x * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-x * 9)

    def ruido(dur, decae):
        x = np.arange(int(dur * sr)) / sr
        r = np.random.default_rng(1).normal(0, 1, len(x))
        r = r - np.convolve(r, np.ones(6) / 6, "same")  # agudos
        return r * np.exp(-x * decae)

    def impacto():
        x = np.arange(int(1.2 * sr)) / sr
        return (np.sin(2 * np.pi * 38 * x) * np.exp(-x * 3) * 1.2 + ruido(1.2, 6) * 0.5)

    def subida(dur):
        x = np.arange(int(dur * sr)) / sr
        r = np.random.default_rng(2).normal(0, 1, len(x))
        return r * (x / dur) ** 2 * 0.35 + np.sin(2 * np.pi * (200 + 1800 * (x / dur) ** 2) * x) * (x / dur) ** 3 * 0.15

    poner(subida(0.5), 0.0)
    poner(subida(0.5), 2.0, 0.8)
    poner(subida(0.5), 7.0, 0.8)
    for k in range(int((DUR - 0.5) / BEAT)):
        t0 = 0.5 + k * BEAT
        if 7.5 <= t0 < 7.6 or t0 >= 9.6:
            continue
        poner(bombo(), t0, 0.9)
    for k in range(int((DUR - 0.5) / (BEAT / 2))):
        t0 = 0.5 + k * BEAT / 2
        if t0 < 9.5:
            poner(ruido(0.06, 60), t0 + BEAT / 4, 0.18 if 0.5 <= t0 < 2.5 else 0.10)
    for t0 in (2.5, 5.0, 7.5):
        poner(impacto(), t0, 0.9)
    bajo = np.sin(2 * np.pi * 55 * tt) * 0.12 * (np.sin(2 * np.pi * tt / BEAT * 0.5) ** 2) * (tt > 2.5) * (tt < 9.6)
    a += bajo.astype(np.float32)
    a /= max(1e-6, np.abs(a).max()) / 0.8
    a *= np.clip((DUR - tt) / 0.4, 0, 1)
    pcm = (np.stack([a, a], 1) * 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", help="solo guardar estos fotogramas como PNG, ej: 20,90,150")
    args = ap.parse_args()
    if args.frames:
        for k in map(int, args.frames.split(",")):
            Image.fromarray(frame(k)).save(AQUI / f"revision_{k:03d}.png")
        return
    wav = AQUI / "nova_pista.wav"
    audio(wav)
    salida = AQUI / "nova_intro.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           str(salida)], stdin=subprocess.PIPE)
    for i in range(N_FR):
        ff.stdin.write(frame(i).tobytes())
        if i % 30 == 0:
            print(f"  {i // 30}s / 10s", flush=True)
    ff.stdin.close()
    ff.wait()
    wav.unlink(missing_ok=True)
    print("OK ->", salida)


if __name__ == "__main__":
    main()
