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

def marketplace_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Ozon"), KeyboardButton(text="WB")],
        [KeyboardButton(text="Яндекс Маркет")],
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")],
    ], resize_keyboard=True)

def weight_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="250 г"), KeyboardButton(text="300 г")],
        [KeyboardButton(text="500 г"), KeyboardButton(text="1000 г")],
        [KeyboardButton(text="Свой вариант")],
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")],
    ], resize_keyboard=True)

def comment_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⏭ Пропустить")],
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")],
    ], resize_keyboard=True)

def confirm_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Утверждено / Подтвердить")],
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")],
    ], resize_keyboard=True)

def regulation_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Ознакомлен, продолжить")]], resize_keyboard=True)

def contact_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить мой контакт", request_contact=True)], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
