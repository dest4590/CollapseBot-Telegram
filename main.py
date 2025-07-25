import asyncio
import logging
import sys
import requests

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

try:
    from config import (BOT_TOKEN, DEEPL_API_KEY, DEEPL_API_URL,
                        SOURCE_CHANNEL_ID, TARGET_CHANNEL_ID)
except (ImportError, ValueError) as e:
    print(f"Configuration import error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=BOT_TOKEN, parse_mode="Markdown")
dp = Dispatcher()

def translate_text(text: str) -> str | None:
    if not text or not text.strip():
        return ""

    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": [text],
        "target_lang": "EN-GB",
    }

    try:
        response = requests.post(DEEPL_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if result.get("translations"):
            return result["translations"][0]["text"]
            
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred during translation request: {e}")
        
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
    
    translated_text = await asyncio.to_thread(translate_text, text_to_translate)

    if text_to_translate and translated_text is None:
        logging.warning(f"Failed to translate message ID: {message.message_id}. Skipping.")
        return
        
    sent_message = None
    try:
        if message.text:
            sent_message = await bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=translated_text,
                disable_web_page_preview=True
            )
        else:
            sent_message = await message.copy(
                chat_id=TARGET_CHANNEL_ID,
                caption=translated_text
            )
        logging.info(f"Message {message.message_id} successfully translated and sent.")

    except TelegramBadRequest as e:
        if "can't be empty" in e.message:
            logging.warning("Attempted to send media with an empty caption. Copying without caption.")
            sent_message = await message.copy(chat_id=TARGET_CHANNEL_ID, caption=None)
        else:
            logging.error(f"BadRequest error while sending to target channel: {e}")
    except Exception as e:
        logging.error(f"Failed to send message to target channel: {e}")
        return

    if add_link_back and sent_message:
        try:
            link_to_translation = sent_message.get_url()
            link_text = f"\n\n[English Version]({link_to_translation})"
            
            final_text = text_to_translate + link_text

            if message.text:
                await bot.edit_message_text(
                    text=final_text,
                    chat_id=message.chat.id,
                    message_id=message.message_id
                )
            elif message.caption is not None:
                await bot.edit_message_caption(
                    caption=final_text,
                    chat_id=message.chat.id,
                    message_id=message.message_id
                )
            logging.info(f"Link to translation added to original message {message.message_id}")
            
        except TelegramBadRequest as e:
            if "not modified" not in e.message:
                 logging.error(f"BadRequest error while editing original message: {e}")
        except Exception as e:
            logging.error(f"Failed to edit original message: {e}")

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Hello!")

async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot has been stopped.")
