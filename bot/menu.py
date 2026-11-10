from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def partner_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Подать заявку"), KeyboardButton(text="📦 Мои заявки")],
        [KeyboardButton(text="⏳ Проверить очередь"), KeyboardButton(text="❓ Помощь")],
    ], resize_keyboard=True)

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛠 Админ-панель")],
        [KeyboardButton(text="📋 Принять заявку"), KeyboardButton(text="⏳ Очередь")],
        [KeyboardButton(text="📦 Грузоместа"), KeyboardButton(text="📸 Фотоотчёты")],
        [KeyboardButton(text="📊 Сводка"), KeyboardButton(text="❓ Помощь")],
    ], resize_keyboard=True)

def form_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def regulation_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Ознакомлен, продолжить")]], resize_keyboard=True)
