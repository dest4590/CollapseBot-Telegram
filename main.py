import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import CommandStart
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)


def load_snippets():
    with open("snippets.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


snippets = load_snippets()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! I am an inline bot. Type @CollapseLoader_bot to see my snippets."
    )


@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    query_text = query.query.lower().strip()
    results = []

    for key, data in snippets.items():
        title = data.get("title", key)
        content = data.get("content", "")

        if (
            query_text in key.lower()
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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
