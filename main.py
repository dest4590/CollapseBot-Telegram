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
    get_cached_versions
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
    await message.answer(
        f"🤖 <b>CollapseBot v1.3</b>\n\n"
        f"Введите @{bot_info.username} в любом чате для поиска сниппетов.\n\n"
        f"<b>Доступные команды:</b>\n"
        f"📡 /status - Проверка состояния серверов\n"
        f"📦 /version - Версии лоадера",
        parse_mode="HTML"
    )

@dp.message(F.text == "/status")
async def cmd_status(message: types.Message):
    status_text = await get_cached_status()
    await message.answer(
        f"📊 <b>Статус серверов Collapse:</b>\n\n{status_text}",
        parse_mode="HTML"
    )

@dp.message(F.text == "/version")
async def cmd_version(message: types.Message):
    v = await get_cached_versions()
    tag_l, link_l = v["latest"]
    tag_p, link_p = v["pre"]
    
    await message.answer(
        f"📦 <b>Версии CollapseLoader:</b>\n\n"
        f"✅ <b>Стабильная:</b> <code>{tag_l}</code> (<a href='{link_l}'>GitHub</a>)\n"
        f"🧪 <b>Пре-релиз:</b> <code>{tag_p}</code> (<a href='{link_p}'>GitHub</a>)",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    increment_stat("snippet_searches")
    query_text = query.query.lower().strip()
    results = []

    status_val = await get_cached_status()
    v = await get_cached_versions()
    tag_l, link_l = v["latest"]
    tag_p, link_p = v["pre"]

    dynamic_items = [
        {
            "id": "dynamic_status",
            "title": f"📡 Статус: {status_val.split(': ')[1]}",
            "description": "Нажмите, чтобы отправить отчет о серверах",
            "msg": f"📊 <b>Статус серверов Collapse:</b>\n\n{status_val}",
            "keywords": ["status", "статус", "сервер", "server", "атлас", "atlas"]
        },
        {
            "id": "dynamic_versions",
            "title": f"📦 Версии: {tag_l} | 🧪 {tag_p}",
            "description": "Нажмите, чтобы отправить инфо о версиях",
            "msg": (
                f"📦 <b>Версии CollapseLoader:</b>\n\n"
                f"✅ <b>Стабильная:</b> <code>{tag_l}</code> (<a href='{link_l}'>GitHub</a>)\n"
                f"🧪 <b>Пре-релиз:</b> <code>{tag_p}</code> (<a href='{link_p}'>GitHub</a>)"
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

async def main():
    bot_info = await bot.get_me()
    logger.info(f"Starting bot @{bot_info.username}")
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
