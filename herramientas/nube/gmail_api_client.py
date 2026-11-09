r"""
Gmail Zero-Token IMAP Client
Ubicacion: <NOVA_HOME>\antigravity\herramientas\nube\gmail_api_client.py
Principio API/CLI First: Busqueda y lectura de correos en Gmail a 0 tokens de navegador (<500ms).
Soporta sintaxis nativa del buscador de Gmail mediante la extension IMAP X-GM-RAW.
"""

import os
import sys
import json
import imaplib
import email
from email.header import decode_header
import re
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip = True
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.result.append(data)

    def get_text(self):
        raw = "".join(self.result)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def load_vault_credentials():
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    if user and pwd:
        return user, pwd.replace(" ", "")

    for _ in [0]:
        for vault_path in [os.path.join(os.path.expanduser("~"), ".gemini", "config", "secrets.env")]:
            if os.path.exists(vault_path):
                try:
                    with open(vault_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GMAIL_USER="):
                                user = line.split("=", 1)[1].strip()
                            elif line.startswith("GMAIL_APP_PASSWORD="):
                                pwd = line.split("=", 1)[1].strip().replace(" ", "")
                    if user and pwd:
                        return user, pwd
                except Exception:
                    pass
    return user, pwd


def decode_mime_str(val):
    if not val:
        return ""
    parts = decode_header(val)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(str(text))
    return "".join(out)


def extract_body(msg):
    plain_body = ""
    html_body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition") or "")
            filename = part.get_filename()
            if filename:
                attachments.append(decode_mime_str(filename))
                continue
            if "attachment" in cdisp:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if ctype == "text/plain" and not plain_body:
                    plain_body = decoded
                elif ctype == "text/html" and not html_body:
                    html_body = decoded
            except Exception:
                pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    html_body = decoded
                else:
                    plain_body = decoded
        except Exception:
            pass

    if plain_body.strip():
        return plain_body.strip(), attachments
    if html_body.strip():
        parser = HTMLTextExtractor()
        parser.feed(html_body)
        return parser.get_text(), attachments
    return "", attachments


def connect_imap():
    user, pwd = load_vault_credentials()
    if not user or not pwd:
        raise RuntimeError("Faltan GMAIL_USER o GMAIL_APP_PASSWORD en ~/.gemini/config/secrets.env (ejecuta nova_claves.py)")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(user, pwd)
    return mail


def search_emails(query, max_results=10, include_body=True):
    try:
        mail = connect_imap()
        # Intentar carpeta Todos ([Gmail]/Todos o [Gmail]/All Mail) o INBOX
        selected = False
        for folder in ['"[Gmail]/Todos"', '"[Gmail]/All Mail"', "INBOX"]:
            typ, _ = mail.select(folder, readonly=True)
            if typ == "OK":
                selected = True
                break
        if not selected:
            mail.select("INBOX", readonly=True)

        # Usar X-GM-RAW de Gmail para soportar cualquier busqueda igual que en la web
        escaped_q = query.replace('"', '\\"')
        typ, data = mail.uid("SEARCH", "CHARSET", "UTF-8", "X-GM-RAW", f'"{escaped_q}"')
        if typ != "OK" or not data or not data[0]:
            # Fallback a busqueda estandar
            typ, data = mail.uid("SEARCH", None, "ALL")

        uids = data[0].split() if (data and data[0]) else []
        uids = uids[-max_results:][::-1]  # Mas recientes primero

        results = []
        for uid in uids:
            typ, msg_data = mail.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = decode_mime_str(msg.get("Subject"))
            sender = decode_mime_str(msg.get("From"))
            date_str = decode_mime_str(msg.get("Date"))
            body, attachments = extract_body(msg)

            item = {
                "uid": uid.decode("utf-8"),
                "subject": subject,
                "from": sender,
                "date": date_str,
                "attachments": attachments,
            }
            if include_body:
                item["body"] = body[:6000]
            else:
                item["snippet"] = body[:300].replace("\n", " ")
            results.append(item)

        mail.logout()
        print(json.dumps({"status": "ok", "query": query, "count": len(results), "emails": results}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso:")
        print('  python gmail_api_client.py search "<consulta_gmail>" [max_results]')
        print("  python gmail_api_client.py recent [max_results]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else "in:inbox"
        m = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search_emails(q, m, include_body=True)
    elif cmd == "recent":
        m = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        search_emails("in:inbox", m, include_body=False)
