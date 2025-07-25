import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")

if not all([BOT_TOKEN, DEEPL_API_KEY, SOURCE_CHANNEL_ID, TARGET_CHANNEL_ID]):
    raise ValueError(
        "Одна или несколько переменных окружения не установлены. "
        "Пожалуйста, проверьте ваш .env файл."
    )

try:
    SOURCE_CHANNEL_ID = int(SOURCE_CHANNEL_ID)
    TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID)
except ValueError:
    raise ValueError("ID of channels must be integers.")

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
