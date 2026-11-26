import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "API-XRay/1.0"
MOCK_HOSTS = {
    "dummyjson.com",
    "jsonplaceholder.typicode.com",
    "fakestoreapi.com",
    "reqres.in",
    "pokeapi.co",
}
LIST_KEYS = (
    "products",
    "data",
    "items",
    "results",
    "records",
    "users",
    "posts",
    "entries",
)


def normalize_url(raw_url: str) -> str:
    clean = raw_url.strip()
    if not clean or " " in clean:
        raise ValueError("La URL no es válida o está vacía.")
    if not clean.startswith(("http://", "https://")):
        clean = f"https://{clean}"
    parsed = urllib.parse.urlparse(clean)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("La URL debe incluir un dominio válido (http o https).")
    return clean


def _request(
    url: str, method: str, headers: dict[str, str], timeout: int = 12
) -> dict[str, Any]:
    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, */*;q=0.8",
        **headers,
    }
    req = urllib.request.Request(url, headers=req_headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = b"" if method == "HEAD" else resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "status": resp.status,
                "headers": hdrs,
                "body": body,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "final_url": resp.geturl(),
            }
    except urllib.error.HTTPError as exc:
        with exc:  # cerrar la respuesta de error (antes quedaba abierta: ResourceWarning)
            body = b"" if method == "HEAD" else exc.read()
            hdrs = {k.lower(): v for k, v in exc.headers.items()}
        return {
            "status": exc.code,
            "headers": hdrs,
            "body": body,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "final_url": url,
        }


def _probe_methods(url: str, headers: dict[str, str]) -> dict[str, Any]:
    methods: set[str] = {"GET"}
    cors_origin = ""
    for m in ("OPTIONS", "HEAD"):
        try:
            res = _request(url, m, headers, timeout=4)
        except Exception:
            continue
        if res["status"] < 400 and m == "HEAD":
            methods.add("HEAD")
        hdrs = res["headers"]
        cors_origin = cors_origin or hdrs.get("access-control-allow-origin", "")
        raw_allow = (
            f"{hdrs.get('allow', '')},{hdrs.get('access-control-allow-methods', '')}"
        )
        methods.update(
            tok.strip().upper() for tok in raw_allow.split(",") if tok.strip()
        )
    return {"methods": sorted(methods), "cors_origin": cors_origin or "No especificado"}


def _classify_backend(
    host: str, hdrs: dict[str, str], pagination: dict[str, Any], methods: dict[str, Any]
) -> dict[str, Any]:
    clean_host = host.lower().removeprefix("www.")
    if any(clean_host == m or clean_host.endswith(f".{m}") for m in MOCK_HOSTS):
        return {
            "kind": "mock",
            "label": "API Mock / Simulada",
            "writes_persist": False,
            "summary": f"{clean_host} simula escritura (POST/PUT/DELETE), pero solo persiste lectura.",
        }
    dynamic = bool(
        pagination["detected"]
        or any(m in methods["methods"] for m in ("POST", "PUT", "PATCH", "DELETE"))
        or "x-powered-by" in hdrs
    )
    if dynamic:
        srv = hdrs.get("server") or hdrs.get("x-powered-by") or "REST dinámico"
        return {
            "kind": "rest",
            "label": "API REST / Backend activo",
            "writes_persist": True,
            "summary": f"Backend dinámico detectado ({srv}) con soporte de consulta en vivo.",
        }
    return {
        "kind": "static",
        "label": "JSON estático o solo lectura",
        "writes_persist": False,
        "summary": "Respuesta sin paginación ni métodos de escritura declarados; se comporta como fuente de solo lectura.",
    }


def _root_from_url(url: str) -> str:
    parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    if not parts:
        return "records"
    last = parts[-1]
    return parts[-2] if last.isdigit() and len(parts) > 1 else last


def _extract_records(
    payload: Any, url: str
) -> tuple[list[dict[str, Any]], str, str, str | None]:
    if isinstance(payload, list):
        recs = [r if isinstance(r, dict) else {"value": r} for r in payload]
        return recs, _root_from_url(url), "array", None
    if isinstance(payload, dict):
        for key in LIST_KEYS:
            val = payload.get(key)
            if isinstance(val, list) and all(isinstance(x, dict) for x in val):
                return val, key, "object_wrapper", key
        for key, val in payload.items():
            if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
                return val, key, "object_wrapper", key
        return [payload], _root_from_url(url), "single_object", None
    return [{"value": payload}], _root_from_url(url), "scalar", None


def _detect_pagination(payload: Any, count: int) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "detected": False,
            "total": count,
            "skip": 0,
            "limit": count,
            "next": None,
        }
    total = next(
        (payload[k] for k in ("total", "count") if isinstance(payload.get(k), int)),
        count,
    )
    skip = payload.get("skip") if isinstance(payload.get("skip"), int) else 0
    limit = next(
        (payload[k] for k in ("limit", "per_page") if isinstance(payload.get(k), int)),
        count,
    )
    nxt = payload.get("next") if isinstance(payload.get("next"), str) else None
    page = payload.get("page") if isinstance(payload.get("page"), int) else None
    detected = any(
        k in payload for k in ("total", "skip", "limit", "page", "per_page", "next")
    )
    # Cada API pagina a su manera: con un link "next", con ?page=N o con ?skip=&limit=.
    # Usar siempre skip/limit hacia que las APIs de ?page= devolvieran la pagina 1 una y otra vez.
    style = "next" if nxt else ("page" if page is not None else "skip")
    return {
        "detected": detected,
        "total": total,
        "skip": skip,
        "limit": limit,
        "next": nxt,
        "page": page,
        "style": style,
    }


def _next_url(url: str, skip: int, limit: int) -> str:
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
    q.update({"skip": str(skip), "limit": str(limit)})
    return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))


def _page_url(url: str, page: int) -> str:
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
    q["page"] = str(page)
    return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))


def _fingerprint(rec: Any) -> str:
    return json.dumps(rec, sort_keys=True, default=str)


def _fetch_remaining(
    url: str,
    headers: dict[str, str],
    records: list[dict[str, Any]],
    list_key: str | None,
    pag: dict[str, Any],
    max_records: int,
) -> tuple[list[dict[str, Any]], int]:
    all_recs = list(records)
    seen = {_fingerprint(r) for r in records}
    pages = 1
    style = pag.get("style", "skip")
    nxt = pag.get("next")
    current_page = pag.get("page") or 1
    prev_url = url
    target = min(int(pag.get("total") or len(records)), max_records)
    while len(all_recs) < target and pages < 15:
        if style == "next":
            if not nxt:
                break
            # "next" suele venir relativo (/users?page=2): se resuelve contra la URL anterior
            page_url = urllib.parse.urljoin(prev_url, nxt)
        elif style == "page":
            page_url = _page_url(url, current_page + 1)
        else:
            step = max(len(records), int(pag.get("limit") or 30))
            page_url = _next_url(url, len(all_recs), min(step, target - len(all_recs)))
        res = _request(page_url, "GET", headers)
        if res["status"] >= 400:
            break
        data = json.loads(res["body"].decode("utf-8", errors="replace"))
        chunk = (
            data.get(list_key, [])
            if isinstance(data, dict) and list_key
            else (data if isinstance(data, list) else [])
        )
        if not chunk:
            break
        nuevos = [r if isinstance(r, dict) else {"value": r} for r in chunk]
        nuevos = [r for r in nuevos if _fingerprint(r) not in seen]
        if not nuevos:
            # la API ignoro el parametro de pagina y devolvio lo mismo: parar en vez de duplicar
            break
        seen.update(_fingerprint(r) for r in nuevos)
        all_recs.extend(nuevos)
        prev_url = page_url
        current_page += 1
        nxt = data.get("next") if isinstance(data, dict) and isinstance(data.get("next"), str) else None
        pages += 1
    return all_recs[:max_records], pages


def _probe_related_routes(
    url: str, headers: dict[str, str], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    base = url.split("?", 1)[0].rstrip("/")
    sample_id = next(
        (r.get("id") for r in records if isinstance(r.get("id"), int | str)), None
    )
    candidates = (
        [f"{base}/{sample_id}"]
        if sample_id is not None and not base.endswith(f"/{sample_id}")
        else []
    ) + [f"{base}/categories"]
    found: list[dict[str, Any]] = []
    for cand in candidates[:2]:
        try:
            res = _request(cand, "HEAD", headers, timeout=3)
            if res["status"] == 405:
                res = _request(cand, "GET", headers, timeout=3)
            if res["status"] < 400:
                found.append({"url": cand, "status": res["status"]})
        except Exception:
            continue
    return found


def probe_endpoint(
    raw_url: str,
    headers: dict[str, str] | None = None,
    fetch_all: bool = False,
    max_records: int = 500,
) -> dict[str, Any]:
    url = normalize_url(raw_url)
    hdr_map = {
        str(k).strip(): str(v).strip()
        for k, v in (headers or {}).items()
        if str(k).strip()
    }
    res = _request(url, "GET", hdr_map)
    if res["status"] >= 400:
        raise ValueError(f"La API respondió con HTTP {res['status']}.")
    payload = json.loads(res["body"].decode("utf-8", errors="replace"))
    records, root_name, root_shape, list_key = _extract_records(payload, url)
    pag = _detect_pagination(payload, len(records))
    pages_fetched = 1
    if fetch_all and (pag["detected"] and pag["total"] > len(records)):
        records, pages_fetched = _fetch_remaining(
            url, hdr_map, records, list_key, pag, max_records
        )
    methods = _probe_methods(url, hdr_map)
    host = urllib.parse.urlparse(res["final_url"]).netloc
    return {
        "http": {
            "url": url,
            "final_url": res["final_url"],
            "status": res["status"],
            "latency_ms": res["latency_ms"],
            "size_bytes": len(res["body"]),
            "headers": res["headers"],
            **methods,
        },
        "backend": _classify_backend(host, res["headers"], pag, methods),
        "pagination": {**pag, "pages_fetched": pages_fetched, "scanned": len(records)},
        "related_routes": _probe_related_routes(url, hdr_map, records),
        "root_name": root_name,
        "root_shape": root_shape,
        "wrapper_key": list_key,
        "records": records,
    }
