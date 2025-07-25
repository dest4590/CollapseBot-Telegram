import asyncio
import logging
import sys

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

try:
    from config import (BOT_TOKEN, DEEPL_API_KEY, DEEPL_API_URL,
                        SOURCE_CHANNEL_ID, TARGET_CHANNEL_ID)
except (ImportError, ValueError) as e:
    print(f"Error importing configuration: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()


async def translate_text(text: str) -> str | None:
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
            result = response.json()
            return result["translations"][0]["text"]
    except httpx.HTTPStatusError as e:
        logging.error(f"DeepL API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logging.error(f"An error occurred during translation: {e}")
    return None


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
        logging.warning(f"Failed to translate message ID: {message.message_id}")
        return

    try:
        if message.text:
            sent_message = await bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=translated_text
            )
        elif message.caption:
            if message.photo:
                sent_message = await bot.send_photo(
                    chat_id=TARGET_CHANNEL_ID,
                    photo=message.photo[-1].file_id,
                    caption=translated_text
                )
            elif message.video:
                sent_message = await bot.send_video(
                    chat_id=TARGET_CHANNEL_ID,
                    video=message.video.file_id,
                    caption=translated_text
                )
            elif message.document:
                sent_message = await bot.send_document(
                    chat_id=TARGET_CHANNEL_ID,
                    document=message.document.file_id,
                    caption=translated_text
                )
            else:
                sent_message = await bot.send_message(
                    chat_id=TARGET_CHANNEL_ID,
                    text=translated_text
                )
        else:
            sent_message = await bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=translated_text
            )
        
        logging.info(f"Message {message.message_id} translated and sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send message to the target channel: {e}")
        return

    if add_link_back:
        try:
            link_to_translation = sent_message.get_url(quote=False)
            link_text = f"\n\n[English Version]({link_to_translation})"
            
            if message.text:
                await bot.edit_message_text(
                    text=text_to_translate + link_text,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                )
            elif message.caption:
                await bot.edit_message_caption(
                    caption=text_to_translate + link_text,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                )
            logging.info(f"Link to translation added to the original message {message.message_id}")
        except Exception as e:
            logging.error(f"Failed to edit the original message: {e}")


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
