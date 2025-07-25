import asyncio
import logging
import sys
from typing import List

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, MessageEntity

from admin import is_translation_enabled, setup_admin_handlers

try:
    from config import (
        BOT_TOKEN,
        DEEPL_API_KEY,
        DEEPL_API_URL,
        SOURCE_CHANNEL_ID,
        TARGET_CHANNEL_ID,
    )
except (ImportError, ValueError) as e:
    print(f"Error importing configuration: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

setup_admin_handlers(dp)


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
            return response.json()["translations"][0]["text"]
    except httpx.HTTPStatusError as e:
        logging.error(f"DeepL API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logging.error(f"An error occurred during translation: {e}")
    return None


def adjust_entities(
    entities: List[MessageEntity], original_text: str, translated_text: str
) -> List[MessageEntity]:
    if not entities or not original_text or not translated_text:
        return entities

    original_length = len(original_text)
    translated_length = len(translated_text)
    scale = translated_length / original_length if original_length > 0 else 1

    adjusted_entities = []
    for entity in entities:
        new_offset = int(entity.offset * scale)
        new_length = int(entity.length * scale)
        if new_offset + new_length <= translated_length:
            adjusted_entity = MessageEntity(
                type=entity.type,
                offset=new_offset,
                length=new_length,
                url=entity.url,
                user=entity.user,
                language=entity.language,
                custom_emoji_id=entity.custom_emoji_id,
            )
            adjusted_entities.append(adjusted_entity)
    return adjusted_entities


@dp.channel_post(F.chat.id == SOURCE_CHANNEL_ID)
async def handle_channel_post(message: Message):
    if not is_translation_enabled():
        logging.info(f"Translation disabled, skipping message {message.message_id}")
        return

    original_text = message.text or message.caption or ""
    add_link_back = False

    if original_text.endswith("@"):
        add_link_back = True
        text_to_translate = original_text[:-1].strip()
    else:
        text_to_translate = original_text

    translated_text = await translate_text(text_to_translate)

    if translated_text is None:
        logging.warning(f"Failed to translate message ID: {message.message_id}")
        return

    entities = message.entities or message.caption_entities or []
    adjusted_entities = adjust_entities(entities, text_to_translate, translated_text)

    try:
        if message.photo:
            sent_message = await bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.video:
            sent_message = await bot.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=message.video.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.document:
            sent_message = await bot.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=message.document.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.audio:
            sent_message = await bot.send_audio(
                chat_id=TARGET_CHANNEL_ID,
                audio=message.audio.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.voice:
            sent_message = await bot.send_voice(
                chat_id=TARGET_CHANNEL_ID,
                voice=message.voice.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.video_note:
            sent_message = await bot.send_video_note(
                chat_id=TARGET_CHANNEL_ID,
                video_note=message.video_note.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        elif message.sticker:
            sent_message = await bot.send_sticker(
                chat_id=TARGET_CHANNEL_ID,
                sticker=message.sticker.file_id,
            )
        elif message.animation:
            sent_message = await bot.send_animation(
                chat_id=TARGET_CHANNEL_ID,
                animation=message.animation.file_id,
                caption=translated_text,
                caption_entities=adjusted_entities,
            )
        else:
            sent_message = await bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=translated_text,
                entities=adjusted_entities,
            )

        logging.info(f"Message {message.message_id} translated and sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send message to the target channel: {e}")
        return

    if add_link_back:
        try:
            link_to_translation = sent_message.get_url()
            link_text = f"\n\n[English Version]({link_to_translation})"

            new_entities = entities.copy() if entities else []
            link_offset = len(text_to_translate) + 2
            link_entity = MessageEntity(
                type="text_link",
                offset=link_offset,
                length=len("[English Version]"),
                url=link_to_translation,
            )
            new_entities.append(link_entity)

            if message.text:
                await bot.edit_message_text(
                    text=text_to_translate + link_text,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    entities=new_entities,
                )
            elif message.caption:
                await bot.edit_message_caption(
                    caption=text_to_translate + link_text,
                    message_id=message.message_id,
                    caption_entities=new_entities,
                )
            logging.info(
                f"Link to translation added to the original message {message.message_id}"
            )
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
