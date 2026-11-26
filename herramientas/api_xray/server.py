from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
import urllib.error
import urllib.parse

from core.diagnostics import analyze_diagnostics
from core.exporter import build_markdown_report, build_sqlite_bytes
from core.http_probe import probe_endpoint
from core.schema_engine import infer_model
from core.sql_generator import generate_schema_ddl

STATIC_DIR = (Path(__file__).resolve().parent / "static").resolve()
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
}


class ScanStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._scan: dict[str, Any] | None = None

    def set(self, scan: dict[str, Any]) -> None:
        with self._lock:
            self._scan = scan

    def get(self) -> dict[str, Any] | None:
        with self._lock:
            return self._scan


def run_scan(
    url: str,
    headers: dict[str, str] | None = None,
    fetch_all: bool = False,
    max_records: int = 1000,
) -> dict[str, Any]:
    probe = probe_endpoint(
        url, headers=headers, fetch_all=fetch_all, max_records=max_records
    )
    model = infer_model(probe["records"], probe["root_name"])
    diagnostics = analyze_diagnostics(probe, model)
    ddl = {d: generate_schema_ddl(model, d) for d in ("sqlite", "mysql", "postgres")}
    return {**probe, "model": model, "diagnostics": diagnostics, "ddl": ddl}


class ApiXRayHandler(BaseHTTPRequestHandler):
    store: ScanStore

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send_bytes(
        self, status: int, body: bytes, content_type: str, filename: str | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header(
                "Content-Disposition", f'attachment; filename="{filename}"'
            )
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, raw, "application/json; charset=utf-8")

    def _serve_static(self, req_path: str) -> None:
        rel = req_path.removeprefix("/static/").lstrip("/") or "index.html"
        target = (STATIC_DIR / rel).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Recurso no encontrado."})
            return
        mime = MIME_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self._send_bytes(HTTPStatus.OK, target.read_bytes(), mime)

    def _handle_export(self, sub: str, query: dict[str, list[str]]) -> None:
        scan = self.store.get()
        if not scan:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Ejecuta un escaneo antes de exportar."},
            )
            return
        root = scan["model"]["root_table"]
        if sub == "/api/export/sql":
            dialect = (query.get("dialect") or ["sqlite"])[0].lower()
            text = scan["ddl"].get(dialect) or scan["ddl"]["sqlite"]
            self._send_bytes(
                HTTPStatus.OK,
                text.encode("utf-8"),
                "text/plain; charset=utf-8",
                f"{root}_{dialect}.sql",
            )
            return
        if sub == "/api/export/sqlite":
            self._send_bytes(
                HTTPStatus.OK,
                build_sqlite_bytes(scan["model"]),
                "application/x-sqlite3",
                f"{root}.sqlite",
            )
            return
        if sub == "/api/export/report":
            self._send_bytes(
                HTTPStatus.OK,
                build_markdown_report(scan).encode("utf-8"),
                "text/markdown; charset=utf-8",
                f"{root}_informe.md",
            )
            return
        if sub == "/api/export/json":
            raw = json.dumps(scan["records"], ensure_ascii=False, indent=2).encode(
                "utf-8"
            )
            self._send_bytes(
                HTTPStatus.OK,
                raw,
                "application/json; charset=utf-8",
                f"{root}_datos.json",
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Exportación no soportada."})

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True})
            return
        if parsed.path.startswith("/api/export/"):
            try:
                self._handle_export(parsed.path, urllib.parse.parse_qs(parsed.query))
            except Exception as exc:  # sin esto el navegador se quedaba esperando una respuesta que nunca llega
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": f"No se pudo exportar: {type(exc).__name__}: {exc}"},
                )
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        if self.path != "/api/scan":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("La peticion debe ser un objeto JSON con 'url'.")
            url = str(body.get("url") or "").strip()
            headers = (
                body.get("headers") if isinstance(body.get("headers"), dict) else {}
            )
            fetch_all = bool(body.get("fetch_all"))
            max_records = min(max(int(body.get("max_records") or 1000), 1), 2000)
            scan = run_scan(
                url, headers=headers, fetch_all=fetch_all, max_records=max_records
            )
            self.store.set(scan)
            self._send_json(HTTPStatus.OK, scan)
        # Orden importante: JSONDecodeError es hija de ValueError; si va detras, nunca se usa este mensaje.
        except json.JSONDecodeError as exc:
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": f"La URL no devolvio JSON valido (¿es una pagina web?): {exc}"},
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": f"No se pudo leer la API destino: {exc}"},
            )
        except Exception as exc:  # cualquier otro fallo: responder siempre, nunca dejar colgada la pagina
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Fallo interno al analizar: {type(exc).__name__}: {exc}"},
            )


def create_server(port: int = 0) -> ThreadingHTTPServer:
    store = ScanStore()

    class BoundHandler(ApiXRayHandler):
        pass

    BoundHandler.store = store
    return ThreadingHTTPServer(("127.0.0.1", port), BoundHandler)
