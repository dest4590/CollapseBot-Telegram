# CollapseBot - Telegram Inline Bot
# Author: dest4590, w1xced
# Version: 1.4
# Description: Telegram Inline Bot with advanced statistics tracking and crash-safe workers

import asyncio
import logging
import os
import subprocess
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import CommandStart
from config import BOT_TOKEN
from thefuzz import process, fuzz
from utils import (
    load_snippets, 
    safe_format, 
    get_cached_status, 
    get_cached_versions,
    get_msg,
    add_subscriber,
    remove_subscriber,
    get_subscribers
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
snippets = load_snippets()

STATS_FILE = "stats.json"

def increment_stat(stat_name):
    try:
        stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats = json.load(f)
        
        stats[stat_name] = stats.get(stat_name, 0) + 1
        
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f)
    except Exception as e:
        logger.error(f"Error updating stats: {e}")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    increment_stat("start_count")
    bot_info = await bot.get_me()
    lang = message.from_user.language_code
    await message.answer(
        get_msg("start", lang, username=bot_info.username),
        parse_mode="HTML"
    )

@dp.message(F.text == "/status")
async def cmd_status(message: types.Message):
    lang = message.from_user.language_code
    status_text = await get_cached_status(lang)
    await message.answer(
        f"{get_msg('status_title', lang)}\n\n{status_text}",
        parse_mode="HTML"
    )

@dp.message(F.text == "/version")
async def cmd_version(message: types.Message):
    lang = message.from_user.language_code
    v = await get_cached_versions()
    tag_l, link_l = v["latest"]
    tag_p, link_p = v["pre"]
    
    await message.answer(
        f"{get_msg('version_title', lang)}\n\n"
        f"{get_msg('stable', lang)} <code>{tag_l}</code> (<a href='{link_l}'>GitHub</a>)\n"
        f"{get_msg('pre', lang)} <code>{tag_p}</code> (<a href='{link_p}'>GitHub</a>)",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(F.text == "/subscribe")
async def cmd_subscribe(message: types.Message):
    add_subscriber(message.from_user.id)
    await message.answer(get_msg("sub_ok", message.from_user.language_code))

@dp.message(F.text == "/unsubscribe")
async def cmd_unsubscribe(message: types.Message):
    remove_subscriber(message.from_user.id)
    await message.answer(get_msg("unsub_ok", message.from_user.language_code))

@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    increment_stat("snippet_searches")
    query_text = query.query.lower().strip()
    lang = query.from_user.language_code
    results = []

    status_val = await get_cached_status(lang)
    v = await get_cached_versions()
    tag_l, link_l = v["latest"]
    tag_p, link_p = v["pre"]

    all_ok = all(s.startswith("✅") for s in status_val.split("\n"))
    status_summary = get_msg("online" if all_ok else "error", lang)

    dynamic_items = [
        {
            "id": "dynamic_status",
            "title": f"📡 {get_msg('status_title', lang).replace('<b>', '').replace('</b>', '')} {status_summary}",
            "description": "Atlas, Auth, API",
            "msg": f"{get_msg('status_title', lang)}\n\n{status_val}",
            "keywords": ["status", "статус", "сервер", "server", "атлас", "atlas", "auth", "api"]
        },
        {
            "id": "dynamic_versions",
            "title": f"📦 {tag_l} | 🧪 {tag_p}",
            "description": get_msg('version_title', lang).replace('<b>', '').replace('</b>', ''),
            "msg": (
                f"{get_msg('version_title', lang)}\n\n"
                f"{get_msg('stable', lang)} <code>{tag_l}</code> (<a href='{link_l}'>GitHub</a>)\n"
                f"{get_msg('pre', lang)} <code>{tag_p}</code> (<a href='{link_p}'>GitHub</a>)"
            ),
            "keywords": ["version", "версия", "update", "обнова", "pre", "пре", "релиз"]
        }
    ]

    if not query_text:
        for item in dynamic_items:
            results.append(
                InlineQueryResultArticle(
                    id=item["id"],
                    title=item["title"],
                    description=item["description"],
                    input_message_content=InputTextMessageContent(
                        message_text=item["msg"], parse_mode="HTML", disable_web_page_preview=True
                    )
                )
            )
    else:
        for item in dynamic_items:
            if any(k in query_text for k in item["keywords"]):
                results.append(
                    InlineQueryResultArticle(
                        id=item["id"],
                        title=item["title"],
                        description=item["description"],
                        input_message_content=InputTextMessageContent(
                            message_text=item["msg"], parse_mode="HTML", disable_web_page_preview=True
                        )
                    )
                )

    choices = []
    for key, data in snippets.items():
        if key in ["status", "version"]:
            continue
        search_text = f"{key} {data.get('title', '')} {data.get('content', '')}".lower()
        choices.append((key, search_text))

    if query_text:
        matches = process.extract(
            query_text, 
            {k: s for k, s in choices}, 
            limit=15, 
            scorer=fuzz.partial_token_set_ratio
        )
        matched_keys = [m[2] for m in matches if m[1] > 40]
    else:
        matched_keys = [k for k in snippets.keys() if k not in ["status", "version"]]

    for key in matched_keys:
        data = snippets.get(key)
        if not data: continue
        
        title = data.get("title", key)
        content = data.get("content", "")
        description = content.split("\n")[0] if content else "No content"
        
        if len(description) > 50:
            description = description[:47] + "..."

        formatted_content = safe_format(content)

        results.append(
            InlineQueryResultArticle(
                id=key,
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=formatted_content, parse_mode="HTML"
                ),
            )
        )

    await query.answer(results[:50], cache_time=1)

async def check_updates_task():
    last_tag = None
    while True:
        try:
            v = await get_cached_versions()
            tag = v["latest"][0]
            url = v["latest"][1]
            
            if last_tag is None:
                last_tag = tag
                
            if tag != last_tag and tag != "N/A":
                last_tag = tag
                logger.info(f"New version detected: {tag}")
                subs = get_subscribers()
                for user_id in subs:
                    try:
                        # We use Russian by default for broadcasts or check user preference if stored
                        await bot.send_message(
                            user_id, 
                            get_msg("new_update", "ru", tag=tag, url=url),
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error in check_updates_task: {e}")
        
        await asyncio.sleep(1800) # 30 mins

async def main():
    bot_info = await bot.get_me()
    logger.info(f"Starting bot @{bot_info.username}")
    asyncio.create_task(check_updates_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    import sys
    
    if "--worker" in sys.argv or os.name != 'nt' or os.environ.get("DOCKER_ENV"):
        try:
            if os.name == 'nt':
                os.system(f"title CollapseBot Logs")
            
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopped!")
    else:
        try:
            subprocess.Popen(
                [sys.executable, "manager.py"], 
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            asyncio.run(main())
