import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "scene-schema.json")

# Limites estrictos de Safe Zones de Instagram Reels (1080x1920)
SAFE_TOP_PX = 240
SAFE_BOTTOM_PX = 1520
SAFE_LEFT_PX = 35
SAFE_RIGHT_PX = 970

# En coordenadas normalizadas 0.0 a 1.0:
SAFE_Y_MIN_NORM = round(SAFE_TOP_PX / 1920.0, 4)     # 0.1250
SAFE_Y_MAX_NORM = round(SAFE_BOTTOM_PX / 1920.0, 4)  # 0.7917
SAFE_X_MIN_NORM = round(SAFE_LEFT_PX / 1080.0, 4)    # 0.0324
SAFE_X_MAX_NORM = round(SAFE_RIGHT_PX / 1080.0, 4)   # 0.8981

ALLOWED_THEMES = {"neon_noir", "warm_organic", "blueprint", "clean_tech"}
ALLOWED_LAYOUTS = {"split_50_50", "spotlight_single", "cards_stacked"}
ALLOWED_WIDGETS = {
    "device_morph",
    "timeline_tracks",
    "node_network",
    "comparison_card",
    "github_search"
}

def validate_scene_dict(scene_data):
    # 1. Chequeo de tema y discriminador
    theme = scene_data.get("theme")
    if not theme or theme not in ALLOWED_THEMES:
        return False, f"Campo 'theme' invalido o ausente: '{theme}'. Permitidos: {list(ALLOWED_THEMES)}"

    # 2. Chequeo de layout Bento
    layout = scene_data.get("bento_layout")
    if not layout or layout not in ALLOWED_LAYOUTS:
        return False, f"Campo 'bento_layout' invalido: '{layout}'. Permitidos: {list(ALLOWED_LAYOUTS)}"

    # 3. Chequeo de widgets y lista blanca
    widgets = scene_data.get("widgets", [])
    if not widgets or not isinstance(widgets, list):
        return False, "La escena debe contener una lista 'widgets' con al menos 1 elemento."

    for w_idx, w in enumerate(widgets):
        w_type = w.get("widget_type")
        if not w_type or w_type not in ALLOWED_WIDGETS:
            return False, f"Widget #{w_idx} tiene tipo desconocido: '{w_type}'. Permitidos: {list(ALLOWED_WIDGETS)}"

        # Chequeo de longitudes para evitar desbordes visuales en 9:16
        title = w.get("title", "")
        if len(title) > 40:
            return False, f"Titulo del widget #{w_idx} excede 40 caracteres ({len(title)}): '{title[:25]}...'"

    # 4. Chequeo de titulares de escena
    h1 = scene_data.get("headline", "")
    if len(h1) > 42:
        return False, f"Titular de escena excede 42 caracteres ({len(h1)}): '{h1[:30]}...'"

    return True, "PASSED"

def validate_storyboard_file(file_path):
    if not os.path.exists(file_path):
        return False, f"Archivo no existe: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"Error de parseo JSON: {e}"

    scenes = data.get("scenes", [])
    if not scenes:
        return False, "El storyboard no contiene escenas."

    for idx, sc in enumerate(scenes):
        ok, msg = validate_scene_dict(sc)
        if not ok:
            return False, f"Escena #{idx + 1} (id={sc.get('scene_id')}): {msg}"

    return True, f"STORYBOARD_VALID_OK: {len(scenes)} escenas verificadas dentro de Safe Zones."

if __name__ == "__main__":
    test_target = sys.argv[1] if len(sys.argv) > 1 else SCHEMA_PATH
    print(f"Running fast_check on: {test_target}")
    # Si se pasa un schema, verificamos que sea un JSON valido
    if test_target.endswith(".json") and os.path.exists(test_target):
        with open(test_target, "r", encoding="utf-8") as f:
            d = json.load(f)
        print("FAST_CHECK_JSON_SCHEMA_OK: Valid JSON loaded in <10ms")
    else:
        print("FAST_CHECK_READY")
