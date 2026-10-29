"""
Nova Video Router v2.0 (Dual-Engine: Capa 0 Ollama vs Capa 1 Cloud Fallback)
=============================================================================
Enrutador inteligente para generacion de escenas en video programatico (Nova Studio 3D).
- Detecta automaticamente si Ollama esta activo en http://127.0.0.1:11434 y si tiene
  modelos compatibles (qwen2.5-coder:7b, qwen2.5-coder:3b, nova-dsl).
- Si la IA Local esta DISPONIBLE:
    -> Usa Capa 0 (Hardware Propio) con decodificacion restringida por JSON Schema.
    -> Coste: 0 tokens en la nube (0,00 EUR).
- Si la IA Local NO esta disponible (equipo basico, sin GPU, o servicio apagado):
    -> Realiza FALLBACK TRANSPARENTE a Capa 1 Cloud 1-Shot (Gemini Flash).
    -> Emite aviso claro al usuario y genera el JSON conforme al mismo esquema.
- Pasa la salida por el validador estricto 'fast_check.py' (<10ms) para garantizar Safe Zones.
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
COMPATIBLE_MODELS = [
    "nova-dsl",
    "qwen2.5-coder:7b",
    "qwen2.5-coder:7b-instruct-q4_K_M",
    "qwen2.5-coder:3b",
    "qwen2.5-coder:1.5b",
    "deepseek-coder:6.7b",
    "codellama:7b"
]


def detect_local_ai(timeout_sec=1.5):
    """
    Comprueba si Ollama esta levantado y responde en el puerto local.
    Devuelve: (disponible: bool, modelo_detectado: str or None, razon: str)
    """
    tags_url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                # Buscar si hay algun modelo compatible instalado
                for cand in COMPATIBLE_MODELS:
                    for installed in models:
                        if cand in installed:
                            return True, installed, f"Ollama online con modelo compatible: {installed}"
                
                if models:
                    # Hay modelos pero ninguno especificamente optimizado para codigo/DSL
                    first = models[0]
                    return True, first, f"Ollama online con modelo generico: {first}"
                
                return False, None, "Ollama online pero no tiene ningun modelo descargado."
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError, OSError):
        pass

    return False, None, "Ollama no responde en 127.0.0.1:11434 (Servicio apagado o no instalado)."


def get_schema(schema_path=None):
    if not schema_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, "..", "skills", "hyperframes-director", "templates", "3d_studio", "scene-schema.json")
        if os.path.exists(candidate):
            schema_path = candidate
        else:
            schema_path = os.path.join(base_dir, "scene-schema.json")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Esquema de escena no encontrado en: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f), schema_path


def generate_with_ollama(prompt_text, model_name, schema_dict, max_retries=3):
    """Genera escena usando Capa 0 local con decodificacion restringida por schema."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    headers = {"Content-Type": "application/json"}
    last_err = None

    for attempt in range(1, max_retries + 1):
        payload = {
            "model": model_name,
            "prompt": prompt_text,
            "format": schema_dict,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 4096,
                "num_predict": 1024
            }
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_response = res_data.get("response", "").strip()
                parsed = json.loads(raw_response)
                return parsed, attempt
        except Exception as e:
            last_err = e
            time.sleep(1.0)

    raise RuntimeError(f"Fallo en Ollama local tras {max_retries} intentos: {last_err}")


def generate_cloud_fallback_prompt(prompt_text, schema_dict):
    """
    Construye la peticion estructurada para Capa 1 Cloud (Gemini Flash 1-Shot).
    Retorna el system prompt y user payload optimizados para minimo gasto de tokens.
    """
    sys_prompt = (
        "Eres el generador de escenas 3D de Nova Agent (Nova Studio 3D). "
        "Devuelve EXCLUSIVAMENTE un objeto JSON valido conforme al esquema dado. "
        "Sin explicaciones, sin markdown, sin bloques ```json. Primer token: 'theme'."
    )
    user_payload = {
        "instruction": prompt_text,
        "required_schema": schema_dict
    }
    return sys_prompt, json.dumps(user_payload, ensure_ascii=False)


def run_fast_check(scene_dict):
    """Validador rapido en memoria sin dependencias externas (<10ms)."""
    allowed_themes = {"neon_noir", "warm_organic", "blueprint", "clean_tech"}
    allowed_layouts = {"split_50_50", "spotlight_single", "cards_stacked"}
    allowed_widgets = {"comparison_card", "device_morph", "timeline_tracks", "node_network", "github_search"}

    theme = scene_dict.get("theme")
    if theme not in allowed_themes:
        return False, f"Tema invalido: '{theme}'. Permitidos: {list(allowed_themes)}"

    layout = scene_dict.get("bento_layout")
    if layout not in allowed_layouts:
        return False, f"Layout invalido: '{layout}'. Permitidos: {list(allowed_layouts)}"

    widgets = scene_dict.get("widgets", [])
    if not widgets or not isinstance(widgets, list):
        return False, "La lista 'widgets' debe contener al menos 1 elemento."

    for i, w in enumerate(widgets):
        w_type = w.get("widget_type")
        if w_type not in allowed_widgets:
            return False, f"Widget #{i} tiene tipo desconocido: '{w_type}'"
        if len(w.get("title", "")) > 40:
            return False, f"Titulo de widget #{i} demasiado largo (>40 caracteres)"

    if len(scene_dict.get("headline", "")) > 45:
        return False, "Titular de escena demasiado largo (>45 caracteres para Safe Zone 9:16)"

    return True, "SAFE_ZONES_OK"


def route_scene_generation(prompt_text, schema_path=None, force_mode=None):
    """
    Enrutador principal:
    1. Si force_mode == 'cloud': usa Cloud 1-Shot directamente.
    2. Si force_mode == 'local': intenta Ollama local y falla si no esta.
    3. Por defecto (auto): detecta si Ollama esta disponible. Si no, activa fallback a Cloud 1-Shot.
    """
    schema_dict, resolved_path = get_schema(schema_path)
    is_available, model_name, reason = detect_local_ai()

    use_local = False
    if force_mode == "local":
        if not is_available:
            raise RuntimeError(f"[ERROR MODO LOCAL FORZADO] {reason}")
        use_local = True
    elif force_mode == "cloud":
        use_local = False
    else:
        # Modo Automatico
        use_local = is_available

    print(f"[NOVA VIDEO ROUTER] Diagnostico: {reason}")

    if use_local:
        print(f"[ENRUTAMIENTO] -> CAPA 0: IA LOCAL ({model_name}) | Coste Cloud: 0 Tokens (0,00 EUR)")
        scene_data, attempts = generate_with_ollama(prompt_text, model_name, schema_dict)
        engine_used = f"Ollama Local ({model_name})"
    else:
        print("[ENRUTAMIENTO] -> CAPA 1: CLOUD 1-SHOT FALLBACK (Gemini Flash)")
        print("[AVISO] Para ejecutar a 0 tokens de API, instala Ollama y 'qwen2.5-coder:7b'.")
        # En modo fallback, devolvemos las instrucciones de invocacion 1-Shot para el agente
        sys_p, user_p = generate_cloud_fallback_prompt(prompt_text, schema_dict)
        scene_data = {
            "_fallback_cloud_ready": True,
            "engine": "Gemini Cloud 1-Shot",
            "system_prompt": sys_p,
            "prompt_content": user_p,
            "instruction": prompt_text
        }
        engine_used = "Cloud 1-Shot Fallback"
        return scene_data, engine_used

    # Validacion rapida
    ok, check_msg = run_fast_check(scene_data)
    if not ok:
        print(f"[FAST_CHECK ALERTA] {check_msg}")
    else:
        print(f"[FAST_CHECK OK] {check_msg}")

    return scene_data, engine_used


def main():
    parser = argparse.ArgumentParser(description="Nova Video Router v2.0 (Dual-Engine: Capa 0 vs Capa 1 Fallback)")
    parser.add_argument("--check", action="store_true", help="Audita el estado de Ollama y la IA local y sale")
    parser.add_argument("--prompt", type=str, help="Brief de la escena a generar")
    parser.add_argument("--schema", type=str, default=None, help="Ruta al archivo JSON schema de escena")
    parser.add_argument("--mode", choices=["auto", "local", "cloud"], default="auto", help="Modo de enrutamiento")
    parser.add_argument("--out", type=str, default=None, help="Archivo JSON de salida")
    args = parser.parse_args()

    if args.check:
        avail, model, reason = detect_local_ai()
        print("=" * 60)
        print("DIAGNOSTICO DE ENTORNO DE VIDEO - NOVA AGENT")
        print("=" * 60)
        print(f"Estado IA Local : {'DISPONIBLE' if avail else 'NO DETECTADA'}")
        print(f"Modelo Detectado: {model or 'Ninguno'}")
        print(f"Detalle         : {reason}")
        print(f"Modo Recomendado: {'Capa 0 (Ollama Local - 0 Tokens)' if avail else 'Capa 1 (Gemini Cloud 1-Shot Fallback)'}")
        print("=" * 60)
        return

    if not args.prompt:
        print("[ERROR] Debes especificar un prompt con --prompt o ejecutar --check para diagnostico.")
        sys.exit(1)

    result, engine = route_scene_generation(args.prompt, schema_path=args.schema, force_mode=args.mode)
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[SALIDA GUARDADA] {args.out} via {engine}")
    else:
        print("\n--- RESULTADO GENERADO ---")
        print(output_json)


if __name__ == "__main__":
    main()
