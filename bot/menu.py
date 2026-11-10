from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📋 Подать заявку"), KeyboardButton(text="📦 Мои заявки")],
        [KeyboardButton(text="⏳ Проверить очередь"), KeyboardButton(text="📚 Регламент")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    if is_admin:
        rows.insert(0, [KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
