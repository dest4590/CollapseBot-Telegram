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
    "version": {"data": None, "time": 0},
    "clients": {"data": None, "time": 0},
    "clients_raw": {"data": {}, "time": 0}
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
        "start": "<b>CollapseBot </b>\n\nВведите @{username} в любом чате для поиска сниппетов.\n\n<b>Команды:</b>\n/status - Состояние серверов\n/version - Версии лоадера\n/clients - Доступные клиенты\n/client &lt;id&gt; - Подробно о клиенте\n/changelog - Что нового\n/help - Справка",
        "help": "<b>Справка по CollapseBot:</b>\n\n<b>Основные команды:</b>\n/status - Текущее состояние серверов Atlas\n/version - Версии лоадера (stable / pre-release)\n/clients - Выборка доступных клиентов (Vanilla, Fabric, Forge)\n\n<b>Лоадер и Клиенты:</b>\n/changelog - Посмотреть, что нового в свежей версии лоадера\n/client <code>&lt;id/название&gt;</code> - Детальная статистика по клиенту (запуски, статус)\n\n<b>Уведомления:</b>\n/subscribe - Получать пуши о новых обновлениях и статусе серверов\n/unsubscribe - Отписаться от рассылки\n\n<b>Поиск параметров (Инлайн):</b>\nНапишите <code>@{username} запрос</code> в любом чате, чтобы найти руководство или сниппет лоадера.",
        "status_title": "<b>Статус серверов Collapse:</b>",
        "version_title": "<b>Версии CollapseLoader:</b>",
        "stable": "<b>Стабильная:</b>",
        "pre": "<b>Пре-релиз:</b>",
        "sub_ok": "Вы подписались на уведомления об обновлениях!",
        "unsub_ok": "Вы отписались от уведомлений.",
        "new_update": "<b>Вышло обновление!</b>\n\nВерсия: <code>{tag}</code>\nСсылка: <a href='{url}'>GitHub</a>",
        "online": "Онлайн",
        "error": "Ошибки",
        "clients_title": "<b>Доступные клиенты:</b>",
        "clients_empty": "Нет доступных клиентов."
    },
    "en": {
        "start": "<b>CollapseBot </b>\n\nType @{username} in any chat to search snippets.\n\n<b>Commands:</b>\n/status - Server status\n/version - Loader versions\n/clients - Available clients\n/client &lt;id&gt; - Client details\n/changelog - What's new\n/help - Help message",
        "help": "<b>CollapseBot Help:</b>\n\n<b>Commands:</b>\n/status - Check Atlas server status\n/version - View loader versions\n/clients - View clients list \n\n<b>Loader & Clients:</b>\n/changelog - Check what's new in the latest loader update\n/client <code>&lt;id/name&gt;</code> - View detailed info about a specific client (launches, status)\n\n<b>Notifications:</b>\n/subscribe - Get push notifications for updates & downtime\n/unsubscribe - Opt out of notifications\n\n<b>Inline Search:</b>\nType <code>@{username} [query]</code> in any chat to search loader snippets.",
        "status_title": "<b>Collapse Server Status:</b>",
        "version_title": "<b>CollapseLoader Versions:</b>",
        "stable": "<b>Stable:</b>",
        "pre": "<b>Pre-release:</b>",
        "sub_ok": "You have subscribed to update notifications!",
        "unsub_ok": "You have unsubscribed from notifications.",
        "new_update": "<b>New update available!</b>\n\nVersion: <code>{tag}</code>\nLink: <a href='{url}'>GitHub</a>",
        "online": "Online",
        "error": "Error",
        "clients_title": "<b>Available clients:</b>",
        "clients_empty": "No clients available."
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
    "clients": asyncio.Lock(),
    "refresh_status": asyncio.Lock(),
    "refresh_version": asyncio.Lock(),
    "refresh_clients": asyncio.Lock()
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
         return cache.get(f"status_{lang}", {}).get("data", "Initializing...")

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
                    return f"{name}: Online ({elapsed}ms)"
                else:
                    return f"{name}: Error {resp.status_code} ({elapsed}ms)"
            except Exception:
                return f"{name}: Offline"

        try:
            client = await get_client()
            tasks = [check_service(name, url, client) for name, url in services.items()]
            results = await asyncio.gather(*tasks)
            
            status = "\n".join(results)
            cache[cache_key] = {"data": status, "time": now}
            return status
        except Exception as e:
            logger.error(f"Error refreshing status cache: {e}")
            return cache.get(cache_key, {}).get("data", "Error fetching status")

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
                "latest": (data_l.get("tag_name", "N/A"), data_l.get("html_url", ""), data_l.get("body", "Нет данных")),
                "pre": (pre.get("tag_name", "N/A"), pre.get("html_url", ""), pre.get("body", "Нет данных")) if pre else ("N/A", "", "Нет данных")
            }
            cache["version"] = {"data": result, "time": now}
            return result
        except Exception as e:
            logger.error(f"Error refreshing version cache: {e}")
            return cache["version"]["data"] or {"latest": ("N/A", ""), "pre": ("N/A", "")}

async def get_cached_clients(lang="ru"):
    now = time.time()
    cache_key = f"clients_{lang}"
    
    if cache_key in cache and cache[cache_key].get("data"):
        if now - cache[cache_key]["time"] > 300:
            if not _cache_locks["refresh_clients"].locked():
                asyncio.create_task(refresh_clients_cache(lang))
        return cache[cache_key]["data"]
    
    async with _cache_locks["clients"]:
        if cache_key in cache and cache[cache_key].get("data"):
            return cache[cache_key]["data"]
        return await refresh_clients_cache(lang)

async def refresh_clients_cache(lang="ru"):
    if _cache_locks["refresh_clients"].locked() and not _cache_locks["clients"].locked():
        return cache.get(f"clients_{lang}", {}).get("data", get_msg("clients_empty", lang))

    async with _cache_locks["refresh_clients"]:
        now = time.time()
        cache_key = f"clients_{lang}"
        try:
            urls = {
                "Vanilla / Custom": "https://atlas.collapseloader.org/api/v1/clients",
                "Fabric": "https://atlas.collapseloader.org/api/v1/fabric-clients",
                "Forge": "https://atlas.collapseloader.org/api/v1/forge-clients"
            }
            client = await get_client()
            
            lines = []
            raw_clients_map = {}
            for category, url in urls.items():
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    clients_list = data.get("data", [])
                    if clients_list:
                        lines.append(f"\n<b>{category}</b>:")
                        for c in clients_list:
                            name = c.get("name", "Unknown")
                            version = c.get("version", "N/A")
                            client_id = c.get("id", "N/A")
                            lines.append(f"<b>{name}</b> (v{version}) - ID: {client_id}")
                            raw_clients_map[str(client_id)] = c
                            raw_clients_map[name.lower()] = c
                else:
                    lines.append(f"\n<b>{category}</b>: Error {resp.status_code}")
                    
            if lines:
                result = "\n".join(lines).strip()
            else:
                result = get_msg("clients_empty", lang)
                
            cache[cache_key] = {"data": result, "time": now}
            cache["clients_raw"] = {"data": raw_clients_map, "time": now}
            return result
        except Exception as e:
            logger.error(f"Error refreshing clients cache: {e}")
            return cache.get(cache_key, {}).get("data", get_msg("clients_empty", lang))


SUBS_FILE = "subscribers.json"

async def get_client_info(query):
    now = time.time()
    if not cache["clients_raw"]["data"] or now - cache["clients_raw"]["time"] > 300:
        await refresh_clients_cache("ru")
        
    raw_data = cache["clients_raw"]["data"]
    query = str(query).lower()
    return raw_data.get(query)

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
