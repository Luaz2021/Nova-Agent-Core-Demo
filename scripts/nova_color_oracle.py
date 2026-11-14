"""
NOVA COLOR ORACLE v1.0
Consulta OpenRouter para generar paletas de color de autor no-cliché basadas en categorías de diseño.
"""

import os
import sys
import json
import urllib.request
import argparse

CURATED_FALLBACKS = {
    "editorial": [
        {
            "id": "lino-mineral",
            "nombre": "Lino & Espresso (The Row / Céline)",
            "descripcion": "Yeso cálido, lino lavado, espresso amargo y pizarra mineral. Cero dorados.",
            "tokens": {
                "--bg-canvas": "#F4F1EA",
                "--bg-surface": "#EAE5DC",
                "--bg-card": "#FFFFFF",
                "--ink-primary": "#1A1412",
                "--ink-secondary": "#5C5652",
                "--ink-muted": "#8E8883",
                "--accent-primary": "#4A4E44",
                "--accent-hover": "#2E312B",
                "--border-subtle": "rgba(26, 20, 18, 0.08)",
                "--border-focus": "#4A4E44"
            }
        },
        {
            "id": "noche-abisal",
            "nombre": "Noche Abisal & Platino (Vendôme Nocturne)",
            "descripcion": "Pizarra marina profunda, platino frío y bruma de jade pálido.",
            "tokens": {
                "--bg-canvas": "#0B0F14",
                "--bg-surface": "#121820",
                "--bg-card": "#18202A",
                "--ink-primary": "#E2E8F0",
                "--ink-secondary": "#94A3B8",
                "--ink-muted": "#64748B",
                "--accent-primary": "#3D7068",
                "--accent-hover": "#4F8D83",
                "--border-subtle": "rgba(226, 232, 240, 0.08)",
                "--border-focus": "#3D7068"
            }
        },
        {
            "id": "terracota-atelier",
            "nombre": "Terracota & Arcilla (Loewe / Jacquemus)",
            "descripcion": "Papel avena crudo, arcilla de terracota quemada, umber y oliva seco.",
            "tokens": {
                "--bg-canvas": "#FBF8F3",
                "--bg-surface": "#F2EBE0",
                "--bg-card": "#FFFFFF",
                "--ink-primary": "#241B18",
                "--ink-secondary": "#63554F",
                "--ink-muted": "#968780",
                "--accent-primary": "#B2533E",
                "--accent-hover": "#8F3E2C",
                "--border-subtle": "rgba(36, 27, 24, 0.08)",
                "--border-focus": "#B2533E"
            }
        }
    ]
}

def query_openrouter(sector, category):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("[ORACLE] No OPENROUTER_API_KEY found. Using curated fallbacks.")
        return CURATED_FALLBACKS.get("editorial")

    prompt = f"""
Actúa como un Director de Arte de élite (ganador de Awwwards).
Genera 3 paletas de colores de autor radicalmente diferentes para una web del sector: "{sector}" en la categoría "{category}".
REGLAS ESTRICTAS ANTI-CLICHÉ:
1. Si es Lujo/Editorial: PROHIBIDO usar negro puro (#000000) combinado con dorado (#D4AF37). Explora yeso cálido, lino, espresso, azul pizarra abisal, verde jade, terracota o carbón apagado.
2. Cada paleta debe contener exactamente estos tokens CSS semánticos:
   --bg-canvas (60% fondo dominante)
   --bg-surface (fondo secundario o despieces)
   --bg-card (fondo de tarjetas o módulos)
   --ink-primary (texto principal legible, WCAG AA min 4.5:1)
   --ink-secondary (subtítulos y metadatos)
   --ink-muted (textos tenues)
   --accent-primary (10% botón interactivo, tags)
   --accent-hover (estado hover)
   --border-subtle (bordes semitransparentes)
   --border-focus (foco accesible)

Devuelve ÚNICAMENTE un JSON válido con este formato:
{{
  "paletas": [
    {{
      "id": "slug-identificador",
      "nombre": "Nombre Editorial de Autor",
      "descripcion": "Breve justificación estética",
      "tokens": {{
        "--bg-canvas": "#...",
        "--bg-surface": "#...",
        "--bg-card": "#...",
        "--ink-primary": "#...",
        "--ink-secondary": "#...",
        "--ink-muted": "#...",
        "--accent-primary": "#...",
        "--accent-hover": "#...",
        "--border-subtle": "...",
        "--border-focus": "#..."
      }}
    }}
  ]
}}
"""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://antigravity.ai",
                "X-Title": "Nova Color Oracle"
            },
            data=json.dumps({
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = json.loads(res.read())
            content = raw["choices"][0]["message"]["content"]
            # Clean markdown JSON wraps
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)
            return data.get("paletas", CURATED_FALLBACKS.get("editorial"))
    except Exception as e:
        print(f"[ORACLE] Error en OpenRouter: {e}. Usando paletas maestras curadas.")
        return CURATED_FALLBACKS.get("editorial")

def main():
    parser = argparse.ArgumentParser(description="Nova Color Oracle")
    parser.add_argument("--sector", default="Haute Coiffure & Atelier de Lujo", help="Sector o nicho")
    parser.add_argument("--category", default="1. Editorial & Luxury", help="Categoría de diseño")
    parser.add_argument("--output", default=None, help="Archivo JSON de salida")
    args = parser.parse_args()

    paletas = query_openrouter(args.sector, args.category)
    print(json.dumps(paletas, indent=2, ensure_ascii=False))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(paletas, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Paletas guardadas en {args.output}")

if __name__ == "__main__":
    main()
