r"""
YouTube Zero-Token API Client
Ubicacion: scripts/scrapers/youtube_api_client.py
Principio API/CLI First: Consultas a YouTube Data API v3 a coste 0 tokens en <250ms.
"""

import os
import sys
import json
import urllib.request
import urllib.parse


def load_secrets():
    secrets = {}
    candidates = [
        os.path.expanduser("~/.gemini/config/secrets.env"),
        os.path.expanduser("~/.gemini/antigravity/vault/secrets.env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            secrets[k.strip()] = v.strip()
                if secrets:
                    return secrets
            except Exception:
                pass
    return secrets


def get_api_key():
    key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    secrets = load_secrets()
    return secrets.get("YOUTUBE_API_KEY") or secrets.get("GOOGLE_API_KEY")


def search_videos(query, max_results=5):
    api_key = get_api_key()
    if not api_key:
        print(json.dumps({"error": "No se encontro YOUTUBE_API_KEY o GOOGLE_API_KEY en secrets.env"}))
        return

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": api_key
    }
    url = f"https://www.googleapis.com/youtube/v3/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NovaClient/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                items.append({
                    "title": snippet.get("title"),
                    "videoId": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channelTitle": snippet.get("channelTitle"),
                    "publishedAt": snippet.get("publishedAt"),
                    "description": snippet.get("description")
                })
            print(json.dumps({"status": "ok", "results": items}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print("Uso:")
        print("  python youtube_api_client.py search <query> [max_results]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        q = sys.argv[2]
        m = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search_videos(q, m)
