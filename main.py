import asyncio
import logging
import sys
import requests

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

try:
    from config import (BOT_TOKEN, DEEPL_API_KEY, DEEPL_API_URL,
                        SOURCE_CHANNEL_ID, TARGET_CHANNEL_ID)
except (ImportError, ValueError) as e:
    print(f"Configuration import error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def sync_translate_request(text: str) -> str | None:
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": [text],
        "target_lang": "EN",
    }
    try:
        response = requests.post(DEEPL_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["translations"][0]["text"]
    except requests.RequestException as e:
        logging.error(f"DeepL API request error: {e}")
        return None

async def translate_text(text: str) -> str | None:
    if not text:
        return ""
    return await asyncio.to_thread(sync_translate_request, text)


@dp.channel_post(F.chat.id == SOURCE_CHANNEL_ID)
async def handle_channel_post(message: Message):
    original_text = message.text or message.caption or ""
    add_link_back = False

    if original_text.endswith('@'):
        add_link_back = True
        text_to_translate = original_text[:-1].strip()
    else:
        text_to_translate = original_text

    translated_text = await translate_text(text_to_translate)

    if translated_text is None:
        logging.warning(f"Could not translate message ID: {message.message_id}")
        return

    sent_message = None
    try:
        if message.text:
            sent_message = await bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=translated_text,
                parse_mode=None
            )
        else:
            sent_message = await message.send_copy(
                chat_id=TARGET_CHANNEL_ID,
                caption=translated_text,
                parse_mode=None
            )
        logging.info(f"Message {message.message_id} successfully translated and sent.")
    except Exception as e:
        logging.error(f"Failed to send message to target channel: {e}")
        return

    if add_link_back and sent_message:
        try:
            link_to_translation = sent_message.get_url(quote=False)
            link_text = f"\n\n[English Version]({link_to_translation})"
            
            new_text_content = text_to_translate + link_text

            if message.text:
                await bot.edit_message_text(
                    text=new_text_content,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    parse_mode="Markdown"
                )
            elif message.caption:
                await bot.edit_message_caption(
                    caption=new_text_content,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    parse_mode="Markdown"
                )
            logging.info(f"Link back added to original message {message.message_id}")
        except Exception as e:
            logging.error(f"Failed to edit original message to add link back: {e}")


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Hello! I am a bot for translating channel posts. ")


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
