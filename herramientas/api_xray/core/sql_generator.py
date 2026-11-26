from typing import Any

DIALECT_QUOTES = {"sqlite": '"', "mysql": "`", "postgres": '"'}
PK_SYNTAX = {
    "sqlite": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "mysql": "INT AUTO_INCREMENT PRIMARY KEY",
    "postgres": "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
}


def quote_id(name: str, dialect: str) -> str:
    q = DIALECT_QUOTES.get(dialect, '"')
    return f"{q}{name}{q}"


def _varchar_len(max_len: int) -> int:
    for bucket in (50, 100, 150, 255):
        if max_len <= bucket:
            return bucket
    return 255


def map_sql_type(col: dict[str, Any], dialect: str) -> str:
    ptype = col["primary_type"]
    fmt = col.get("format")
    max_len = int(col.get("max_length") or 0)
    if ptype == "boolean":
        return "INTEGER" if dialect == "sqlite" else "BOOLEAN"
    if ptype == "integer":
        return {"sqlite": "INTEGER", "mysql": "BIGINT", "postgres": "BIGINT"}.get(
            dialect, "INTEGER"
        )
    if ptype == "float":
        return {
            "sqlite": "REAL",
            "mysql": "DOUBLE",
            "postgres": "DOUBLE PRECISION",
        }.get(dialect, "REAL")
    if fmt == "iso_datetime":
        return {"sqlite": "TEXT", "mysql": "DATETIME", "postgres": "TIMESTAMPTZ"}.get(
            dialect, "TEXT"
        )
    if fmt == "iso_date":
        return "TEXT" if dialect == "sqlite" else "DATE"
    if fmt == "uuid" and dialect == "postgres":
        return "UUID"
    if dialect == "sqlite":
        return "TEXT"
    return "TEXT" if max_len > 255 else f"VARCHAR({_varchar_len(max_len)})"


def _col_definition(col: dict[str, Any], dialect: str) -> str:
    qname = quote_id(col["name"], dialect)
    if col.get("pk") and col.get("synthetic"):
        return f"  {qname} {PK_SYNTAX.get(dialect, PK_SYNTAX['sqlite'])}"
    sql_type = map_sql_type(col, dialect)
    parts = [f"  {qname}", sql_type]
    if col.get("pk"):
        parts.append("PRIMARY KEY")
    elif not col.get("nullable"):
        parts.append("NOT NULL")
    if col.get("unique") and not col.get("pk"):
        parts.append("UNIQUE")
    return " ".join(parts)


def generate_table_ddl(table: dict[str, Any], dialect: str = "sqlite") -> str:
    d = dialect if dialect in DIALECT_QUOTES else "sqlite"
    tname = quote_id(table["name"], d)
    lines = [_col_definition(col, d) for col in table["columns"]]
    for col in table["columns"]:
        if col.get("fk_target"):
            ref_tbl, ref_col = col["fk_target"].split(".", 1)
            lines.append(
                f"  FOREIGN KEY ({quote_id(col['name'], d)}) REFERENCES {quote_id(ref_tbl, d)} ({quote_id(ref_col, d)}) ON DELETE CASCADE"
            )
    tbl_raw = table["name"]
    ddl = f"CREATE TABLE IF NOT EXISTS {tname} (\n" + ",\n".join(lines) + "\n);"
    idx_lines = [
        f"CREATE INDEX IF NOT EXISTS {quote_id('idx_' + tbl_raw + '_' + col['name'], d)} ON {tname} ({quote_id(col['name'], d)});"
        for col in table["columns"]
        if col.get("fk_target")
    ]
    return "\n".join([ddl, *idx_lines])


def generate_schema_ddl(model: dict[str, Any], dialect: str = "sqlite") -> str:
    d = dialect if dialect in DIALECT_QUOTES else "sqlite"
    header = f"-- API X-Ray · Esquema generado para {d.upper()} ({len(model['tables'])} tablas)"
    blocks = [generate_table_ddl(tbl, d) for tbl in model["tables"]]
    return "\n\n".join([header, *blocks]) + "\n"
