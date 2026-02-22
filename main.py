import asyncio
import logging
import yaml
import os
import subprocess
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import CommandStart
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

snippets = load_snippets()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(
        f"Hello! I am an inline bot. Type @{bot_info.username} in any chat to see my snippets."
    )

@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    query_text = query.query.lower().strip()
    results = []

    for key, data in snippets.items():
        title = data.get("title", key)
        content = data.get("content", "")

        if (
            not query_text 
            or query_text in key.lower()
            or query_text in title.lower()
            or query_text in content.lower()
        ):
            description = content.split("\n")[0] if content else "No content"
            if len(description) > 50:
                description = description[:47] + "..."

            results.append(
                InlineQueryResultArticle(
                    id=key,
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text=content, parse_mode="Markdown"
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
