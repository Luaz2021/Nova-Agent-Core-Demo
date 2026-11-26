import argparse
from pathlib import Path
import sys
import urllib.parse
import webbrowser

from server import create_server, run_scan


def _print_cli_report(scan: dict, sql_dialect: str | None) -> None:
    http = scan["http"]
    backend = scan["backend"]
    pag = scan["pagination"]
    model = scan["model"]
    print(f"=== API X-Ray | {http['url']} ===")
    print(f"HTTP {http['status']} | {http['latency_ms']} ms | {backend['label']}")
    print(f"Backend: {backend['summary']}")
    print(f"Métodos: {', '.join(http['methods'])} | CORS: {http['cors_origin']}")
    print(
        f"Registros escaneados: {pag['scanned']} / {pag['total']} (páginas: {pag['pages_fetched']})"
    )
    print("\n--- Modelo relacional inferido ---")
    for tbl in model["tables"]:
        cols = ", ".join(
            f"{c['name']}({'PK' if c['pk'] else ('FK' if c.get('fk_target') else c['primary_type'])})"
            for c in tbl["columns"]
        )
        print(f"  [{tbl['role']}] {tbl['name']} ({tbl['row_count']} filas): {cols}")
    if model["relations"]:
        print("\n--- Relaciones ---")
        for rel in model["relations"]:
            print(
                f"  {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} ({rel['cardinality']})"
            )
    if scan["diagnostics"]["alerts"]:
        print("\n--- Diagnóstico ---")
        for al in scan["diagnostics"]["alerts"]:
            print(f"  [{al['severity'].upper()}] {al['title']}: {al['detail']}")
    if sql_dialect:
        print(f"\n--- DDL ({sql_dialect}) ---")
        print(scan["ddl"].get(sql_dialect, scan["ddl"]["sqlite"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="API X-Ray: escáner universal de APIs JSON y generador de esquema SQL."
    )
    parser.add_argument(
        "--port", type=int, default=0, help="Puerto local (0 = automático)"
    )
    parser.add_argument(
        "--url", default="", help="URL inicial para escanear al abrir la UI"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir el navegador automáticamente",
    )
    parser.add_argument(
        "--cli", default="", help="Escanea una URL directo en consola y sale"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Recorre todas las páginas disponibles en modo --cli",
    )
    parser.add_argument(
        "--sql",
        choices=["sqlite", "mysql", "postgres"],
        help="Muestra el DDL SQL en modo --cli",
    )
    args = parser.parse_args(argv)

    if args.cli:
        try:
            scan = run_scan(args.cli, fetch_all=args.all)
        except Exception as exc:
            print(f"Error al escanear: {exc}", file=sys.stderr)
            return 1
        _print_cli_report(scan, args.sql)
        return 0

    srv = create_server(args.port)
    port = srv.server_address[1]
    base_url = f"http://127.0.0.1:{port}/"
    if args.url:
        base_url = f"{base_url}?{urllib.parse.urlencode({'url': args.url})}"
    print(f"API X-Ray activo en {base_url}")
    print(f"Raíz del proyecto: {Path(__file__).resolve().parent}")
    print("Pulsa Ctrl+C para detener el servidor.")
    if not args.no_browser:
        webbrowser.open(base_url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
