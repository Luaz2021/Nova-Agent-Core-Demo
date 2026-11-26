from typing import Any


def analyze_diagnostics(probe: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    alerts: list[dict[str, str]] = []
    quality_matrix: list[dict[str, Any]] = []
    pag = probe["pagination"]
    backend = probe["backend"]
    if pag["detected"] and pag["scanned"] < pag["total"]:
        alerts.append(
            {
                "severity": "media",
                "title": "Escaneo parcial de registros",
                "detail": f"Se analizaron {pag['scanned']} de {pag['total']} registros totales. Activa 'Escanear todo' para detectar columnas nulas o largos máximos reales en toda la API.",
                "table": model["root_table"],
                "column": "*",
            }
        )
    if not backend["writes_persist"]:
        alerts.append(
            {
                "severity": "info",
                "title": backend["label"],
                "detail": backend["summary"],
                "table": model["root_table"],
                "column": "*",
            }
        )
    child_1_1 = sum(1 for t in model["tables"] if t["role"] == "1:1")
    child_1_n = sum(1 for t in model["tables"] if t["role"] == "1:N")
    if child_1_1 or child_1_n:
        alerts.append(
            {
                "severity": "info",
                "title": "Normalización relacional inferida",
                "detail": f"Se separó la respuesta en 1 tabla principal, {child_1_1} tablas 1:1 y {child_1_n} tablas 1:N con claves foráneas.",
                "table": model["root_table"],
                "column": "*",
            }
        )
    for tbl in model["tables"]:
        for col in tbl["columns"]:
            quality_matrix.append(
                {
                    "table": tbl["name"],
                    "column": col["name"],
                    "type": col["primary_type"],
                    "fill_pct": col["fill_pct"],
                    "max_length": col["max_length"],
                    "format": col.get("format") or "-",
                    "nullable": col["nullable"],
                    "role": "PK"
                    if col["pk"]
                    else ("FK" if col.get("fk_target") else "-"),
                }
            )
            if col.get("mixed_types"):
                alerts.append(
                    {
                        "severity": "alta",
                        "title": f"Tipos mezclados en {tbl['name']}.{col['name']}",
                        "detail": "Este campo cambia de tipo entre registros; se mapeó a texto para evitar errores de inserción.",
                        "table": tbl["name"],
                        "column": col["name"],
                    }
                )
            if (
                not col["pk"]
                and not col.get("fk_target")
                and (col["missing_count"] > 0 or col["null_count"] > 0)
            ):
                alerts.append(
                    {
                        "severity": "media",
                        "title": f"Campo opcional o nulo: {tbl['name']}.{col['name']}",
                        "detail": f"Falta en {col['missing_count']} registros y viene null en {col['null_count']}. Déjalo como NULL en SQL para que no falle el INSERT.",
                        "table": tbl["name"],
                        "column": col["name"],
                    }
                )
            if col["primary_type"] == "string" and col["max_length"] > 255:
                alerts.append(
                    {
                        "severity": "media",
                        "title": f"Texto largo en {tbl['name']}.{col['name']} ({col['max_length']} chars)",
                        "detail": "Supera 255 caracteres; en MySQL o PostgreSQL usa TEXT en lugar de VARCHAR(255).",
                        "table": tbl["name"],
                        "column": col["name"],
                    }
                )
    order = {"alta": 0, "media": 1, "info": 2}
    alerts.sort(key=lambda a: order.get(a["severity"], 3))
    return {"alerts": alerts, "quality_matrix": quality_matrix}
