import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.diagnostics import analyze_diagnostics  # noqa: E402
from core.exporter import build_sqlite_bytes  # noqa: E402
from core.http_probe import _extract_records  # noqa: E402
from core.schema_engine import infer_model  # noqa: E402
from core.sql_generator import generate_schema_ddl  # noqa: E402
from server import create_server  # noqa: E402


class ApiXRayTests(unittest.TestCase):
    def test_wrapper_relations_nullable_and_sqlite_export(self) -> None:
        payload = {
            "products": [
                {
                    "id": 1,
                    "title": "Mascara",
                    "brand": "Essence",
                    "price": 9.99,
                    "active": True,
                    "dimensions": {"width": 10.5, "height": 4.2},
                    "tags": ["beauty", "makeup"],
                    "reviews": [{"rating": 5, "comment": "Genial"}],
                },
                {
                    "id": 2,
                    "title": "Otro producto",
                    "price": 12,
                    "active": False,
                    "dimensions": {"width": 8.0, "height": 3.0},
                    "tags": ["generic"],
                    "reviews": [{"rating": 3, "comment": "Correcto"}],
                },
            ],
            "total": 2,
        }
        records, root_name, root_shape, wrapper = _extract_records(
            payload, "https://api.test/products"
        )
        self.assertEqual(
            (root_name, root_shape, wrapper), ("products", "object_wrapper", "products")
        )

        model = infer_model(records, root_name)
        table_names = {t["name"] for t in model["tables"]}
        self.assertEqual(
            table_names,
            {"products", "products_dimensions", "products_tags", "products_reviews"},
        )

        main_cols = {c["name"]: c for c in model["tables"][0]["columns"]}
        self.assertTrue(main_cols["brand"]["nullable"])
        self.assertEqual(main_cols["price"]["primary_type"], "float")
        self.assertEqual(main_cols["active"]["primary_type"], "boolean")

        probe = {
            "pagination": {"detected": True, "scanned": 2, "total": 2},
            "backend": {
                "label": "Mock",
                "writes_persist": False,
                "summary": "Solo lectura",
            },
        }
        diag = analyze_diagnostics(probe, model)
        self.assertTrue(any(a["column"] == "brand" for a in diag["alerts"]))

        raw_sqlite = build_sqlite_bytes(model)
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            db_path.write_bytes(raw_sqlite)
            conn = sqlite3.connect(db_path)
            try:
                self.assertEqual(
                    conn.execute("PRAGMA integrity_check;").fetchone()[0], "ok"
                )
                self.assertEqual(
                    conn.execute("PRAGMA foreign_key_check;").fetchall(), []
                )
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], 2
                )
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM products_tags").fetchone()[0], 3
                )
            finally:
                conn.close()

    def test_root_array_and_single_object_shapes(self) -> None:
        arr_recs, arr_root, arr_shape, _ = _extract_records(
            [{"name": "Ana"}, {"name": "Luis"}], "https://api.test/users"
        )
        self.assertEqual((arr_root, arr_shape, len(arr_recs)), ("users", "array", 2))
        arr_model = infer_model(arr_recs, arr_root)
        self.assertTrue(arr_model["tables"][0]["columns"][0]["synthetic"])

        obj_recs, obj_root, obj_shape, _ = _extract_records(
            {"id": 7, "title": "Solo uno"}, "https://api.test/products/7"
        )
        self.assertEqual(
            (obj_root, obj_shape, len(obj_recs)), ("products", "single_object", 1)
        )

    def test_sql_reserved_words_quoted_across_dialects(self) -> None:
        records = [{"order": 1, "group": "A", "select": "yes"}]
        model = infer_model(records, "items")
        for dialect, q in (("sqlite", '"'), ("postgres", '"'), ("mysql", "`")):
            ddl = generate_schema_ddl(model, dialect)
            self.assertIn(f"{q}order{q}", ddl)
            self.assertIn(f"{q}group{q}", ddl)
            self.assertIn(f"{q}select{q}", ddl)

    def test_http_server_health_and_bad_scan_url(self) -> None:
        srv = create_server(0)
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=3
            ) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {"ok": True})

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/scan",
                data=json.dumps({"url": "not a valid url"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(ctx.exception.code, 400)
            body = json.loads(io.BytesIO(ctx.exception.read()).read().decode("utf-8"))
            ctx.exception.close()
            self.assertIn("error", body)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
