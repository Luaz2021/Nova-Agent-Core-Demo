"""Casos que rompian API X-Ray (20/11, revision de Claude). Ver errores.md.

Levanta una API falsa en 127.0.0.1 (sin internet) que imita APIs reales:
paginacion por ?page=, link "next" relativo, claves que chocan al pasarlas a SQL e id repetido.
"""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import build_sqlite_bytes  # noqa: E402
from server import create_server, run_scan  # noqa: E402

USERS = [{"id": i, "name": f"u{i}"} for i in range(1, 13)]


class _ApiFalsa(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        return

    def do_GET(self) -> None:
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        page = int(q.get("page", ["1"])[0])
        if u.path == "/paginas":  # estilo reqres.in: ignora skip/limit
            body = {"page": page, "per_page": 6, "total": 12, "data": USERS[(page - 1) * 6 : page * 6]}
        elif u.path == "/siguiente":  # estilo Django REST / swapi: next relativo
            body = {
                "count": 12,
                "next": f"/siguiente?page={page + 1}" if page < 2 else None,
                "results": USERS[(page - 1) * 6 : page * 6],
            }
        elif u.path == "/ignora":  # dice que hay 12 pero siempre devuelve lo mismo
            body = {"total": 12, "limit": 6, "skip": 0, "items": USERS[:6]}
        elif u.path == "/choque":
            body = [{"id": 1, "userId": 5, "user_id": 5}, {"id": 2, "userId": 6, "user_id": 6}]
        elif u.path == "/idrepetido":
            body = [{"id": 1, "x": "a"}, {"id": 1, "x": "b"}]
        elif u.path == "/html":
            raw = b"<html>hola</html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        else:
            self.send_response(404)
            self.end_headers()
            return
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_HEAD = do_GET


class CasosDificilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _ApiFalsa)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.srv.shutdown()
        cls.srv.server_close()

    def _sqlite_ok(self, scan: dict) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            db.write_bytes(build_sqlite_bytes(scan["model"]))
            conn = sqlite3.connect(db)
            try:
                self.assertEqual(conn.execute("PRAGMA integrity_check;").fetchone()[0], "ok")
            finally:
                conn.close()

    def test_paginacion_por_page_sin_duplicados(self) -> None:
        scan = run_scan(f"{self.base}/paginas", fetch_all=True)
        ids = [r["id"] for r in scan["records"]]
        self.assertEqual(ids, list(range(1, 13)))
        self.assertEqual(scan["model"]["tables"][0]["columns"][0]["synthetic"], False)
        self._sqlite_ok(scan)

    def test_next_relativo(self) -> None:
        scan = run_scan(f"{self.base}/siguiente", fetch_all=True)
        self.assertEqual([r["id"] for r in scan["records"]], list(range(1, 13)))

    def test_api_que_ignora_la_paginacion_no_duplica(self) -> None:
        scan = run_scan(f"{self.base}/ignora", fetch_all=True)
        self.assertEqual(len(scan["records"]), 6)
        self._sqlite_ok(scan)

    def test_claves_que_chocan_en_sql(self) -> None:
        scan = run_scan(f"{self.base}/choque")
        nombres = [c["name"] for c in scan["model"]["tables"][0]["columns"]]
        self.assertEqual(len(nombres), len(set(nombres)), nombres)
        self.assertIn("user_id_val", nombres)
        self._sqlite_ok(scan)

    def test_id_repetido_usa_pk_sintetica_sin_chocar(self) -> None:
        scan = run_scan(f"{self.base}/idrepetido")
        cols = scan["model"]["tables"][0]["columns"]
        nombres = [c["name"] for c in cols]
        self.assertEqual(nombres, ["id", "id_val", "x"])
        self.assertTrue(cols[0]["synthetic"])
        self._sqlite_ok(scan)

    def test_servidor_responde_siempre(self) -> None:
        srv = create_server(0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        try:
            for body, codigo in (
                ({"url": f"{self.base}/html"}, 502),  # no es JSON: mensaje claro, no "Expecting value"
                (["no", "es", "objeto"], 400),
            ):
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/scan",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(ctx.exception.code, codigo)
                self.assertIn("error", json.loads(ctx.exception.read().decode()))
                ctx.exception.close()
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
