import json
import re
from typing import Any

RE_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
RE_CLEAN = re.compile(r"[^a-z0-9_]+")
RE_DT = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_URL = re.compile(r"^https?://\S+$")
RE_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def sql_ident(name: str) -> str:
    snake = RE_CAMEL.sub(r"\1_\2", name).lower()
    cleaned = re.sub(r"_+", "_", RE_CLEAN.sub("_", snake)).strip("_") or "col"
    return f"c_{cleaned}" if cleaned[0].isdigit() else cleaned


def singularize(name: str) -> str:
    if name.endswith("ies") and len(name) > 4:
        return f"{name[:-3]}y"
    if name.endswith("s") and not name.endswith("ss") and len(name) > 2:
        return name[:-1]
    return name


def detect_format(val: str) -> str | None:
    formats = (
        ("iso_datetime", RE_DT),
        ("iso_date", RE_DATE),
        ("email", RE_EMAIL),
        ("url", RE_URL),
        ("uuid", RE_UUID),
    )
    return next((label for label, pat in formats if pat.match(val)), None)


def infer_scalar_type(val: Any) -> str:
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, int):
        return "integer"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "string"
    return "json"


def _resolve_kind(non_null: list[Any]) -> str:
    if any(isinstance(v, dict) for v in non_null):
        return "object"
    lists = [v for v in non_null if isinstance(v, list)]
    if not lists:
        return "scalar"
    return (
        "array_object"
        if any(isinstance(item, dict) for lst in lists for item in lst)
        else "array_scalar"
    )


def _resolve_type(types: set[str]) -> tuple[str, bool]:
    if not types:
        return "string", False
    if types == {"integer", "float"}:
        return "float", False
    if len(types) == 1:
        return next(iter(types)), False
    return "string", True


def _profile_key(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    total = max(len(rows), 1)
    missing = sum(1 for r in rows if key not in r)
    present = [r[key] for r in rows if key in r]
    nulls = sum(1 for v in present if v is None)
    non_null = [v for v in present if v is not None]
    kind = _resolve_kind(non_null)
    if kind != "scalar":
        return {
            "source_key": key,
            "name": sql_ident(key),
            "kind": kind,
            "primary_type": "json",
            "format": None,
            "nullable": (missing + nulls) > 0,
            "missing_count": missing,
            "null_count": nulls,
            "max_length": 0,
            "distinct_count": 0,
            "mixed_types": False,
            "samples": [],
            "fill_pct": round(((len(rows) - missing - nulls) / total) * 100, 1),
        }
    types = {infer_scalar_type(v) for v in non_null}
    ptype, mixed = _resolve_type(types)
    strs = [v for v in non_null if isinstance(v, str)]
    fmts = {detect_format(s) for s in strs if s}
    fmt = next(iter(fmts)) if len(fmts) == 1 else None
    samples = list(dict.fromkeys(str(v)[:60] for v in non_null))[:3]
    distinct = len(
        {
            json.dumps(v, sort_keys=True, default=str)
            if isinstance(v, dict | list)
            else v
            for v in non_null
        }
    )
    return {
        "source_key": key,
        "name": sql_ident(key),
        "kind": "scalar",
        "primary_type": ptype,
        "format": fmt,
        "nullable": (missing + nulls) > 0,
        "missing_count": missing,
        "null_count": nulls,
        "max_length": max((len(str(v)) for v in non_null), default=0),
        "distinct_count": distinct,
        "mixed_types": mixed,
        "samples": samples,
        "fill_pct": round(((len(rows) - missing - nulls) / total) * 100, 1),
    }


def _make_col(
    prof: dict[str, Any],
    pk: bool = False,
    synthetic: bool = False,
    fk_target: str | None = None,
    unique: bool = False,
) -> dict[str, Any]:
    return {
        "name": prof["name"],
        "source_key": prof["source_key"],
        "primary_type": prof["primary_type"],
        "format": prof["format"],
        "max_length": prof["max_length"],
        "nullable": False if (pk or fk_target) else prof["nullable"],
        "pk": pk,
        "synthetic": synthetic,
        "fk_target": fk_target,
        "unique": unique,
        "fill_pct": 100.0 if synthetic else prof["fill_pct"],
        "missing_count": prof["missing_count"],
        "null_count": prof["null_count"],
        "mixed_types": prof["mixed_types"],
        "samples": prof["samples"],
    }


def _synthetic_pk(name: str = "id") -> dict[str, Any]:
    return {
        "name": name,
        "source_key": None,
        "primary_type": "integer",
        "format": None,
        "max_length": 0,
        "nullable": False,
        "pk": True,
        "synthetic": True,
        "fk_target": None,
        "unique": True,
        "fill_pct": 100.0,
        "missing_count": 0,
        "null_count": 0,
        "mixed_types": False,
        "samples": ["1", "2"],
    }


def _scalar_val(val: Any) -> Any:
    return json.dumps(val, ensure_ascii=False) if isinstance(val, dict | list) else val


def _build_child_table(
    child_name: str,
    role: str,
    fk_col: str,
    parent_ref: str,
    parent_pk_type: str,
    child_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    keys = list(dict.fromkeys(k for r in child_rows for k in r if k != fk_col))
    cols = [
        _synthetic_pk("id"),
        _make_col(
            {
                "name": fk_col,
                "source_key": fk_col,
                "primary_type": parent_pk_type,
                "format": None,
                "max_length": 0,
                "nullable": False,
                "missing_count": 0,
                "null_count": 0,
                "mixed_types": False,
                "samples": [],
                "fill_pct": 100.0,
            },
            fk_target=parent_ref,
            unique=(role == "1:1"),
        ),
    ]
    used = {"id", fk_col}
    for k in keys:
        prof = _profile_key(child_rows, k)
        prof["name"] = _unique_name(prof["name"], used)
        cols.append(_make_col(prof))
    flat_rows = [
        {
            "id": idx + 1,
            fk_col: r[fk_col],
            **{c["name"]: _scalar_val(r.get(c["source_key"])) for c in cols[2:]},
        }
        for idx, r in enumerate(child_rows)
    ]
    rel = {
        "from_table": child_name,
        "from_column": fk_col,
        "to_table": parent_ref.split(".")[0],
        "to_column": parent_ref.split(".")[1],
        "cardinality": role,
    }
    return (
        {
            "name": child_name,
            "role": role,
            "row_count": len(flat_rows),
            "columns": cols,
            "x": 0,
            "y": 0,
        },
        flat_rows,
        rel,
    )


def _unique_name(name: str, used: set[str]) -> str:
    """Dos claves JSON distintas pueden dar el mismo nombre SQL (userId y user_id -> user_id; id de los datos
    y la PK sintetica 'id'). Una tabla no admite columnas repetidas: la segunda pasa a name_val, name_val2..."""
    final = name
    n = 1
    while final in used:
        final = f"{name}_val" if n == 1 else f"{name}_val{n}"
        n += 1
    used.add(final)
    return final


def _layout_tables(tables: list[dict[str, Any]]) -> None:
    ones = [t for t in tables if t["role"] == "1:1"]
    manys = [t for t in tables if t["role"] == "1:N"]
    main_h = min(340, 56 + len(tables[0]["columns"]) * 25)
    tables[0].update({"x": 40, "y": 40})
    y_left = 40 + main_h + 36
    for tbl in ones:
        tbl.update({"x": 40, "y": y_left})
        y_left += min(340, 56 + len(tbl["columns"]) * 25) + 32
    y_right = 40
    for tbl in manys:
        tbl.update({"x": 470, "y": y_right})
        y_right += min(340, 56 + len(tbl["columns"]) * 25) + 32


def infer_model(records: list[dict[str, Any]], root_name: str) -> dict[str, Any]:
    base = sql_ident(root_name) or "records"
    all_keys = list(dict.fromkeys(k for r in records for k in r))
    profiles = [_profile_key(records, k) for k in all_keys]
    pk_prof = next(
        (
            p
            for p in profiles
            if p["kind"] == "scalar"
            and p["name"] == "id"
            and not p["nullable"]
            and p["distinct_count"] == len(records)
            and p["primary_type"] in ("integer", "string")
        ),
        None,
    )
    # Nombres unicos: la PK (real o sintetica) se queda con "id"; lo demas que choque pasa a *_val
    used: set[str] = {"id"}
    for p in profiles:
        if p is not pk_prof:
            p["name"] = _unique_name(p["name"], used)
    main_cols = ([] if pk_prof else [_synthetic_pk("id")]) + [
        _make_col(p, pk=(p is pk_prof)) for p in profiles if p["kind"] == "scalar"
    ]
    pk_col = next(c for c in main_cols if c["pk"])
    parent_pks = [
        idx + 1 if pk_col["synthetic"] else r[pk_col["source_key"]]
        for idx, r in enumerate(records)
    ]
    main_rows = [
        {
            c["name"]: (
                parent_pks[idx]
                if c["synthetic"]
                else _scalar_val(r.get(c["source_key"]))
            )
            for c in main_cols
        }
        for idx, r in enumerate(records)
    ]
    tables: list[dict[str, Any]] = [
        {
            "name": base,
            "role": "main",
            "row_count": len(main_rows),
            "columns": main_cols,
            "x": 48,
            "y": 48,
        }
    ]
    table_rows: dict[str, list[dict[str, Any]]] = {base: main_rows}
    relations: list[dict[str, str]] = []
    fk_col = f"{singularize(base)}_id"
    parent_ref = f"{base}.{pk_col['name']}"
    for p in (pr for pr in profiles if pr["kind"] != "scalar"):
        cname = f"{base}_{p['name']}"
        if p["kind"] == "object":
            crows = [
                {fk_col: parent_pks[i], **r[p["source_key"]]}
                for i, r in enumerate(records)
                if isinstance(r.get(p["source_key"]), dict)
            ]
            role = "1:1"
        elif p["kind"] == "array_object":
            crows = [
                {fk_col: parent_pks[i], **item}
                for i, r in enumerate(records)
                for item in (r.get(p["source_key"]) or [])
                if isinstance(item, dict)
            ]
            role = "1:N"
        else:
            crows = [
                {fk_col: parent_pks[i], "value": item}
                for i, r in enumerate(records)
                for item in (r.get(p["source_key"]) or [])
                if item is not None
            ]
            role = "1:N"
        if not crows:
            continue
        tbl, frows, rel = _build_child_table(
            cname, role, fk_col, parent_ref, pk_col["primary_type"], crows
        )
        tables.append(tbl)
        table_rows[cname] = frows
        relations.append(rel)
    _layout_tables(tables)
    return {
        "root_table": base,
        "tables": tables,
        "relations": relations,
        "table_rows": table_rows,
        "records_scanned": len(records),
    }
