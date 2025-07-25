import configparser
import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

ADMIN_USER_ID = 1047311374
CONFIG_FILE = (
    "/app/config/config.ini" if os.path.exists("/app/config") else "config.ini"
)

translation_enabled = True


def load_config():
    """Load configuration from config.ini file"""
    global translation_enabled
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        translation_enabled = config.getboolean(
            "settings", "translation_enabled", fallback=True
        )
    return translation_enabled


def save_config(enabled: bool):
    """Save configuration to config.ini file"""
    global translation_enabled
    translation_enabled = enabled
    config = configparser.ConfigParser()
    config["settings"] = {"translation_enabled": str(enabled).lower()}

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def get_admin_keyboard():
    """Generate inline keyboard for admin panel"""
    status_text = "✅ Включен" if translation_enabled else "❌ Выключен"
    toggle_text = "Выключить" if translation_enabled else "Включить"
    toggle_action = "disable" if translation_enabled else "enable"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Автоперевод: {status_text}", callback_data="status"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔄 {toggle_text}", callback_data=f"toggle_{toggle_action}"
                )
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh")],
        ]
    )
    return keyboard


def get_admin_text():
    status = "включен" if translation_enabled else "выключен"
    return (
        f"🤖 <b>Админ-панель бота</b>\n\n"
        f"📊 Статус автоперевода: <b>{status}</b>\n\n"
        f"Используйте кнопки ниже для управления:"
    )


def setup_admin_handlers(dp: Dispatcher):
    @dp.message(Command("admin"), F.from_user.id == ADMIN_USER_ID)
    async def admin_panel(message: Message):
        await message.answer(
            get_admin_text(), reply_markup=get_admin_keyboard(), parse_mode="HTML"
        )

    @dp.callback_query(F.data.startswith("toggle_"), F.from_user.id == ADMIN_USER_ID)
    async def toggle_translation(callback: CallbackQuery):
        action = callback.data.split("_")[1]
        new_state = action == "enable"
        save_config(new_state)

        status_text = "включен" if new_state else "выключен"
        await callback.answer(f"Автоперевод {status_text}")

        await callback.message.edit_text(
            get_admin_text(), reply_markup=get_admin_keyboard(), parse_mode="HTML"
        )

    @dp.callback_query(F.data == "refresh", F.from_user.id == ADMIN_USER_ID)
    async def refresh_panel(callback: CallbackQuery):
        await callback.answer("Панель обновлена")
        await callback.message.edit_text(
            get_admin_text(), reply_markup=get_admin_keyboard(), parse_mode="HTML"
        )

    @dp.callback_query(F.data == "status", F.from_user.id == ADMIN_USER_ID)
    async def show_status(callback: CallbackQuery):
        status = "включен" if translation_enabled else "выключен"
        await callback.answer(f"Автоперевод: {status}", show_alert=True)


def is_translation_enabled():
    return translation_enabled


load_config()
