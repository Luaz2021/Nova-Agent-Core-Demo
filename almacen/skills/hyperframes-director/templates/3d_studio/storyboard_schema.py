import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_OUT_PATH = os.path.join(BASE_DIR, "scene-schema.json")

def generate_scene_schema():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "StoryboardSceneSchema",
        "type": "object",
        "required": ["theme", "scene_id", "kicker", "headline", "subheadline", "bento_layout", "widgets"],
        "properties": {
            "theme": {
                "type": "string",
                "enum": ["neon_noir", "warm_organic", "blueprint", "clean_tech"],
                "description": "Tema visual obligatorio como primer token (discriminador)"
            },
            "scene_id": {
                "type": "integer",
                "minimum": 1,
                "maximum": 8
            },
            "kicker": {
                "type": "string",
                "maxLength": 28,
                "description": "Sticker superior corto de Safe Zone"
            },
            "headline": {
                "type": "string",
                "maxLength": 42,
                "description": "Titular de escena para 9:16"
            },
            "subheadline": {
                "type": "string",
                "maxLength": 55,
                "description": "Subtitulo de escena"
            },
            "accent": {
                "type": "string",
                "pattern": "^#[0-9A-Fa-f]{6}$"
            },
            "bento_layout": {
                "type": "string",
                "enum": ["split_50_50", "spotlight_single", "cards_stacked"]
            },
            "widgets": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "required": ["widget_type", "title", "accent"],
                    "properties": {
                        "widget_type": {
                            "type": "string",
                            "enum": ["comparison_card", "device_morph", "timeline_tracks", "node_network", "github_search"]
                        },
                        "title": { "type": "string", "maxLength": 38 },
                        "accent": { "type": "string" },
                        "subheadline": { "type": "string" },
                        "myth_title": { "type": "string" },
                        "myth_desc": { "type": "string" },
                        "solution_title": { "type": "string" },
                        "solution_desc": { "type": "string" },
                        "tracks": {
                            "type": "array",
                            "items": { "type": "string" }
                        },
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": { "type": "string" },
                                    "sub": { "type": "string" }
                                }
                            }
                        },
                        "repo_name": { "type": "string" },
                        "cta_text": { "type": "string" }
                    }
                }
            }
        },
        "additionalProperties": False
    }

    with open(SCHEMA_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    print(f"SCHEMA_EXPORTED_OK (Standard Lib): {SCHEMA_OUT_PATH}")

if __name__ == "__main__":
    generate_scene_schema()
