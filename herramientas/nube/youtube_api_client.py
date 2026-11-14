r"""
YouTube Zero-Token API Client
Ubicacion: <GoogleDrive>\Antigravity\scripts\scrapers\youtube_api_client.py
Principio API/CLI First: Consultas a YouTube Data API v3 a coste 0 tokens en <250ms.
"""

import os
import sys
import json
import urllib.request
import urllib.parse

def get_api_key():
    # 1. Variable de entorno directa
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key

    # 2. Buscar en vault de Drive
    for letter in "GDEFGHIJKLMNOPQRSTUVWXYZC":
        vault_path = os.path.join(f"{letter}:\\", r"Mi unidad\Antigravity\vault\google_cloud.env")
        if os.path.exists(vault_path):
            try:
                with open(vault_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("YOUTUBE_API_KEY="):
                            return line.split("=", 1)[1].strip()
            except Exception:
                pass
    return None

def search_videos(query, max_results=5):
    api_key = get_api_key()
    if not api_key:
        print(json.dumps({"error": "No se encontro YOUTUBE_API_KEY en el vault"}))
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
        with urllib.request.urlopen(req) as resp:
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

def get_video_details(video_id):
    api_key = get_api_key()
    if not api_key:
        print(json.dumps({"error": "No se encontro YOUTUBE_API_KEY"}))
        return

    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    url = f"https://www.googleapis.com/youtube/v3/videos?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NovaClient/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            if not items:
                print(json.dumps({"error": "Video no encontrado"}))
                return
            v = items[0]
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            res = {
                "title": snippet.get("title"),
                "channelTitle": snippet.get("channelTitle"),
                "views": stats.get("viewCount"),
                "likes": stats.get("likeCount"),
                "commentCount": stats.get("commentCount"),
                "publishedAt": snippet.get("publishedAt"),
                "description": snippet.get("description")
            }
            print(json.dumps({"status": "ok", "details": res}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso:")
        print("  python youtube_api_client.py search <query> [max_results]")
        print("  python youtube_api_client.py details <video_id>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        q = sys.argv[2]
        m = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search_videos(q, m)
    elif cmd == "details":
        vid = sys.argv[2]
        get_video_details(vid)
