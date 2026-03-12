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

import asyncio
import json

TRANSLATIONS = {
    "ru": {
        "start": "🤖 <b>CollapseBot v1.4</b>\n\nВведите @{username} в любом чате для поиска сниппетов.\n\n<b>Команды:</b>\n📡 /status - Состояние серверов\n📦 /version - Версии лоадера\n🔔 /subscribe - Подписка на обновления\n🔕 /unsubscribe - Отписаться",
        "status_title": "📊 <b>Статус серверов Collapse:</b>",
        "version_title": "📦 <b>Версии CollapseLoader:</b>",
        "stable": "✅ <b>Стабильная:</b>",
        "pre": "🧪 <b>Пре-релиз:</b>",
        "sub_ok": "✅ Вы подписались на уведомления об обновлениях!",
        "unsub_ok": "🔕 Вы отписались от уведомлений.",
        "new_update": "🚀 <b>Вышло обновление!</b>\n\nВерсия: <code>{tag}</code>\nСсылка: <a href='{url}'>GitHub</a>",
        "online": "Онлайн",
        "error": "Ошибки",
    },
    "en": {
        "start": "🤖 <b>CollapseBot v1.4</b>\n\nType @{username} in any chat to search snippets.\n\n<b>Commands:</b>\n📡 /status - Server status\n📦 /version - Loader versions\n🔔 /subscribe - Subscribe to updates\n🔕 /unsubscribe - Unsubscribe",
        "status_title": "📊 <b>Collapse Server Status:</b>",
        "version_title": "📦 <b>CollapseLoader Versions:</b>",
        "stable": "✅ <b>Stable:</b>",
        "pre": "🧪 <b>Pre-release:</b>",
        "sub_ok": "✅ You have subscribed to update notifications!",
        "unsub_ok": "🔕 You have unsubscribed from notifications.",
        "new_update": "🚀 <b>New update available!</b>\n\nVersion: <code>{tag}</code>\nLink: <a href='{url}'>GitHub</a>",
        "online": "Online",
        "error": "Error",
    }
}

def get_msg(key, lang="ru", **kwargs):
    lang = lang if lang in TRANSLATIONS else "ru"
    return TRANSLATIONS[lang].get(key, key).format(**kwargs)

_client = None

async def get_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=True,
            headers={"User-Agent": "CollapseBot/2.5"}
        )
    return _client

_cache_locks = {
    "status": asyncio.Lock(),
    "version": asyncio.Lock(),
    "refresh_status": asyncio.Lock(),
    "refresh_version": asyncio.Lock()
}

async def get_cached_status(lang="ru"):
    now = time.time()
    cache_key = f"status_{lang}"
    
    if cache_key in cache and now - cache[cache_key]["time"] < 60:
        return cache[cache_key]["data"]
    
    if cache_key in cache and cache[cache_key]["data"]:
        # Background refresh if not already refreshing
        if not _cache_locks["refresh_status"].locked():
            asyncio.create_task(refresh_status_cache(lang))
        return cache[cache_key]["data"]

    async with _cache_locks["status"]:
        if cache_key in cache and cache[cache_key]["data"]:
            return cache[cache_key]["data"]
        return await refresh_status_cache(lang)

async def refresh_status_cache(lang="ru"):
    if _cache_locks["refresh_status"].locked() and not _cache_locks["status"].locked():
         # Avoid redundant concurrent refreshes
         return cache.get(f"status_{lang}", {}).get("data", "❌ Initializing...")

    async with _cache_locks["refresh_status"]:
        now = time.time()
        cache_key = f"status_{lang}"
        
        services = {
            "Atlas": "https://atlas.collapseloader.org"
        }

        async def check_service(name, url, client):
            start = time.perf_counter()
            try:
                resp = await client.get(url)
                elapsed = int((time.perf_counter() - start) * 1000)
                if resp.status_code < 400:
                    return f"✅ {name}: Online ({elapsed}ms)"
                else:
                    return f"⚠️ {name}: Error {resp.status_code} ({elapsed}ms)"
            except Exception:
                return f"❌ {name}: Offline"

        try:
            client = await get_client()
            tasks = [check_service(name, url, client) for name, url in services.items()]
            results = await asyncio.gather(*tasks)
            
            status = "\n".join(results)
            cache[cache_key] = {"data": status, "time": now}
            return status
        except Exception as e:
            logger.error(f"Error refreshing status cache: {e}")
            return cache.get(cache_key, {}).get("data", "❌ Error fetching status")

async def get_cached_versions():
    now = time.time()
    if cache["version"]["data"]:
        if now - cache["version"]["time"] > 300:
            if not _cache_locks["refresh_version"].locked():
                asyncio.create_task(refresh_version_cache())
        return cache["version"]["data"]
    
    async with _cache_locks["version"]:
        if cache["version"]["data"]:
            return cache["version"]["data"]
        return await refresh_version_cache()

async def refresh_version_cache():
    if _cache_locks["refresh_version"].locked() and not _cache_locks["version"].locked():
        return cache["version"]["data"]

    async with _cache_locks["refresh_version"]:
        now = time.time()
        try:
            url_latest = "https://api.github.com/repos/dest4590/collapseloader/releases/latest"
            url_all = "https://api.github.com/repos/dest4590/collapseloader/releases"
            
            client = await get_client()
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
        except Exception as e:
            logger.error(f"Error refreshing version cache: {e}")
            return cache["version"]["data"] or {"latest": ("N/A", ""), "pre": ("N/A", "")}


SUBS_FILE = "subscribers.json"

def get_subscribers():
    if not os.path.exists(SUBS_FILE):
        return []
    with open(SUBS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def add_subscriber(user_id):
    subs = set(get_subscribers())
    subs.add(user_id)
    with open(SUBS_FILE, "w") as f:
        json.dump(list(subs), f)

def remove_subscriber(user_id):
    subs = set(get_subscribers())
    subs.discard(user_id)
    with open(SUBS_FILE, "w") as f:
        json.dump(list(subs), f)
