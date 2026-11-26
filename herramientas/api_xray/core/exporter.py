import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from core.sql_generator import generate_schema_ddl, quote_id


def _sql_cell(val: Any) -> Any:
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, dict | list):
        return json.dumps(val, ensure_ascii=False)
    return val


def build_sqlite_bytes(model: dict[str, Any]) -> bytes:
    ddl = generate_schema_ddl(model, "sqlite")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api_xray_export.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(ddl)
            with conn:
                for tbl in model["tables"]:
                    rows = model["table_rows"].get(tbl["name"], [])
                    if not rows:
                        continue
                    cols = [c["name"] for c in tbl["columns"]]
                    qcols = ", ".join(quote_id(c, "sqlite") for c in cols)
                    placeholders = ", ".join("?" for _ in cols)
                    sql = f"INSERT INTO {quote_id(tbl['name'], 'sqlite')} ({qcols}) VALUES ({placeholders})"
                    values = [
                        tuple(_sql_cell(row.get(c)) for c in cols) for row in rows
                    ]
                    conn.executemany(sql, values)
            fk_issues = conn.execute("PRAGMA foreign_key_check;").fetchall()
            if fk_issues:
                raise ValueError(
                    f"Error de integridad referencial al exportar SQLite: {fk_issues[:3]}"
                )
        finally:
            conn.close()
        return db_path.read_bytes()


def build_markdown_report(scan: dict[str, Any]) -> str:
    http = scan["http"]
    backend = scan["backend"]
    pag = scan["pagination"]
    model = scan["model"]
    alerts = scan["diagnostics"]["alerts"]
    lines = [
        f"# Informe API X-Ray: {model['root_table']}",
        "",
        "## 1. Radiografía y Backend",
        f"- URL: {http['url']}",
        f"- Estado HTTP: {http['status']} ({http['latency_ms']} ms)",
        f"- Clasificación: {backend['label']}",
        f"- Resumen: {backend['summary']}",
        f"- Métodos permitidos: {', '.join(http['methods'])}",
        f"- CORS: {http['cors_origin']}",
        f"- Registros escaneados: {pag['scanned']} / {pag['total']}",
        "",
        "## 2. Tablas e Integridad",
        *[
            f"- {t['name']} ({t['role']}): {t['row_count']} filas, {len(t['columns'])} columnas"
            for t in model["tables"]
        ],
        "",
        "## 3. Relaciones",
        *(
            [
                f"- {r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']} ({r['cardinality']})"
                for r in model["relations"]
            ]
            or ["- Sin relaciones externas"]
        ),
        "",
        "## 4. Diagnóstico",
        *[f"- [{a['severity'].upper()}] {a['title']}: {a['detail']}" for a in alerts],
        "",
        "## 5. DDL SQLite",
        "```sql",
        scan["ddl"]["sqlite"].strip(),
        "```",
    ]
    return "\n".join(lines) + "\n"
