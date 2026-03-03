import httpx
import time
import re
import html
import yaml
import os
import logging

logger = logging.getLogger(__name__)

cache = {
    "status": {"data": None, "time": 0},
    "version": {"data": None, "time": 0}
}

def load_snippets():
    if not os.path.exists("snippets.yaml"):
        logger.error("snippets.yaml not found!")
        return {}
    with open("snippets.yaml", "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing snippets.yaml: {e}")
            return {}

def safe_format(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text

async def get_cached_status():
    now = time.time()
    if cache["status"]["data"] and now - cache["status"]["time"] < 60:
        return cache["status"]["data"]
    
    url = "https://atlas.collapseloader.org"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            status = "✅ Atlas: Online" if resp.status_code < 400 else f"⚠️ Atlas: Error {resp.status_code}"
    except Exception:
        status = "❌ Atlas: Offline"
    
    cache["status"] = {"data": status, "time": now}
    return status

async def get_cached_versions():
    now = time.time()
    if cache["version"]["data"] and now - cache["version"]["time"] < 300:
        return cache["version"]["data"]
    
    try:
        url_latest = "https://api.github.com/repos/dest4590/collapseloader/releases/latest"
        url_all = "https://api.github.com/repos/dest4590/collapseloader/releases"
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp_l = await client.get(url_latest)
            data_l = resp_l.json() if resp_l.status_code == 200 else {}
            
            resp_all = await client.get(url_all)
            releases = resp_all.json() if resp_all.status_code == 200 else []
            pre = next((r for r in releases if r.get("prerelease")), None)

            result = {
                "latest": (data_l.get("tag_name", "N/A"), data_l.get("html_url", "")),
                "pre": (pre.get("tag_name", "N/A"), pre.get("html_url", "")) if pre else ("N/A", "")
            }
            cache["version"] = {"data": result, "time": now}
            return result
    except Exception:
        return {"latest": ("N/A", ""), "pre": ("N/A", "")}
