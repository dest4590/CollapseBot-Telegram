import asyncio
import logging
import sys

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

try:
    from config import (BOT_TOKEN, DEEPL_API_KEY, DEEPL_API_URL,
                        SOURCE_CHANNEL_ID, TARGET_CHANNEL_ID)
except (ImportError, ValueError) as e:
    print(f"Configuration import error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def translate_content(text: str) -> str | None:
    if not text:
        return ""

    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": [text],
        "target_lang": "EN",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(DEEPL_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            deepl_api_response = response.json()
            translated_text = deepl_api_response["translations"][0]["text"]
            return translated_text
            
    except httpx.HTTPStatusError as e:
        logging.error(f"DeepL API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logging.error(f"An error occurred during translation: {e}")
        
    return None


@dp.channel_post(F.chat.id == SOURCE_CHANNEL_ID)
async def process_source_channel_post(message: Message):
    content_to_process = message.text or message.caption or ""
    add_backlink_to_original = False

    if content_to_process.endswith('@'):
        add_backlink_to_original = True
        cleaned_content = content_to_process[:-1].strip()
    else:
        cleaned_content = content_to_process

    translated_text = await translate_content(cleaned_content)

    if translated_text is None:
        logging.warning(f"Failed to translate message ID: {message.message_id}")
        return

    try:
        sent_message_in_target = await message.copy(
            chat_id=TARGET_CHANNEL_ID,
            text=translated_text if message.text else None,
            caption=translated_text if message.caption else None,
        )
        logging.info(f"Message {message.message_id} successfully translated and sent to target channel.")
    except Exception as e:
        logging.error(f"Failed to send translated message to target channel: {e}")
        return

    if add_backlink_to_original:
        try:
            link_to_translated_post = sent_message_in_target.get_url(quote=False)

            backlink_markdown = f"\n\n[English Version]({link_to_translated_post})"
            
            if message.text:
                await bot.edit_message_text(
                    text=cleaned_content + backlink_markdown,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    parse_mode="Markdown"
                )
            elif message.caption:
                await bot.edit_message_caption(
                    caption=cleaned_content + backlink_markdown,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    parse_mode="Markdown"
                )
            logging.info(f"Backlink added to original message {message.message_id}")
        except Exception as e:
            logging.error(f"Failed to edit original message: {e}")


@dp.message(CommandStart())
async def start_command_handler(message: Message) -> None:
    await message.answer("Hi!")

async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
