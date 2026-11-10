import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import load_settings
from bot.db import init_database
from bot.menu import admin_menu, form_menu, partner_menu, regulation_menu

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
router = Router()
settings = load_settings()
accepted_users: set[int] = set()


class RequestForm(StatesGroup):
    product = State()
    marketplace = State()
    weight = State()
    units = State()
    comment = State()
    confirm = State()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


async def show_regulation(message: Message) -> None:
    await message.answer(
        f"<b>Регламент работы с «{settings.app_name}»</b>\n\n"
        "Одна заявка — один товар, одна фасовка и один маркетплейс.\n\n"
        "• В одном коробе максимум 23 кг товара.\n"
        "• В одном кластере максимум 30 грузомест.\n"
        "• Штрихкод и состав отправляются до передачи заявки в работу.\n"
        "• Фактический вес фиксируется после фасовки.\n"
        "• Недовес или перевес сохраняется в истории и отправляется партнёру.\n"
        "• Спор открывается через кнопку помощи с номером заявки и причиной.\n"
        "• Фото приёмки, фасовки и готовых коробок сохраняются к заявке.\n\n"
        "При проблеме с ботом нажмите «Помощь» и напишите администратору.",
        parse_mode="HTML", reply_markup=regulation_menu(),
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    if not message.from_user:
        return
    if message.from_user.id not in accepted_users:
        await message.answer(
            f"Добро пожаловать в «{settings.app_name}»!\n\nПеред началом работы ознакомьтесь с регламентом.",
        )
        await show_regulation(message)
        return
    await message.answer("Выберите действие.", reply_markup=admin_menu() if is_admin(message) else partner_menu())


@router.message(F.text == "✅ Ознакомлен, продолжить")
async def accept_regulation(message: Message) -> None:
    if message.from_user:
        accepted_users.add(message.from_user.id)
    await message.answer("Регламент принят. Теперь можно работать.", reply_markup=admin_menu() if is_admin(message) else partner_menu())


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_command(message: Message) -> None:
    if settings.admin_username:
        contact = f"<a href=\"https://t.me/{settings.admin_username}\">написать администратору</a>"
    else:
        contact = "ссылка администратора ещё не настроена"
    await message.answer(
        "<b>Помощь</b>\n\nУкажите номер заявки и подробно опишите проблему. Для спора приложите фото, видео или документ.\n\n"
        f"Администратор: {contact}", parse_mode="HTML"
    )


@router.message(Command("status"))
async def status_command(message: Message) -> None:
    await message.answer(f"Бот «{settings.app_name}» работает: {datetime.now():%d.%m.%Y %H:%M}.")


@router.message(F.text == "📋 Подать заявку")
async def request_start(message: Message, state: FSMContext) -> None:
    await state.set_state(RequestForm.product)
    await message.answer("Введите название товара или нажмите «Отмена».", reply_markup=form_menu())


@router.message(RequestForm.product)
async def request_product(message: Message, state: FSMContext) -> None:
    if message.text in {"❌ Отмена", "⬅️ Назад"}:
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=admin_menu() if is_admin(message) else partner_menu()); return
    await state.update_data(product=message.text.strip()); await state.set_state(RequestForm.marketplace)
    await message.answer("Укажите маркетплейс: Ozon, WB или Яндекс Маркет.", reply_markup=form_menu())


@router.message(RequestForm.marketplace)
async def request_marketplace(message: Message, state: FSMContext) -> None:
    if message.text == "⬅️ Назад":
        await state.set_state(RequestForm.product); await message.answer("Введите название товара.", reply_markup=form_menu()); return
    if message.text == "❌ Отмена":
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=partner_menu()); return
    await state.update_data(marketplace=message.text.strip()); await state.set_state(RequestForm.weight)
    await message.answer("Введите вес одной упаковки в граммах: например 250, 300, 500 или 1000.", reply_markup=form_menu())


@router.message(RequestForm.weight)
async def request_weight(message: Message, state: FSMContext) -> None:
    if message.text == "⬅️ Назад":
        await state.set_state(RequestForm.marketplace); await message.answer("Укажите маркетплейс.", reply_markup=form_menu()); return
    if message.text == "❌ Отмена":
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=partner_menu()); return
    try:
        weight = int(message.text.strip())
        if not 50 <= weight <= 5000: raise ValueError
    except ValueError:
        await message.answer("Введите целое число от 50 до 5000 граммов.", reply_markup=form_menu()); return
    await state.update_data(weight=weight); await state.set_state(RequestForm.units)
    await message.answer("Введите количество упаковок.", reply_markup=form_menu())


@router.message(RequestForm.units)
async def request_units(message: Message, state: FSMContext) -> None:
    if message.text == "⬅️ Назад":
        await state.set_state(RequestForm.weight); await message.answer("Введите вес в граммах.", reply_markup=form_menu()); return
    if message.text == "❌ Отмена":
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=partner_menu()); return
    try:
        units = int(message.text.strip())
        if units <= 0: raise ValueError
    except ValueError:
        await message.answer("Введите целое количество больше нуля.", reply_markup=form_menu()); return
    data = await state.update_data(units=units); await state.set_state(RequestForm.comment)
    await message.answer(f"Плановый вес: <b>{units * data.get('weight', 0) / 1000:.2f} кг</b>. Введите комментарий или напишите «нет».", parse_mode="HTML", reply_markup=form_menu())


@router.message(RequestForm.comment)
async def request_comment(message: Message, state: FSMContext) -> None:
    if message.text == "⬅️ Назад":
        await state.set_state(RequestForm.units); await message.answer("Введите количество упаковок.", reply_markup=form_menu()); return
    if message.text == "❌ Отмена":
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=partner_menu()); return
    await state.update_data(comment=None if message.text.lower() == "нет" else message.text.strip())
    data = await state.get_data(); total = data["units"] * data["weight"] / 1000; await state.set_state(RequestForm.confirm)
    await message.answer(
        f"<b>Предпросмотр заявки</b>\n\nТовар: {data['product']}\nМаркетплейс: {data['marketplace']}\nФасовка: {data['weight']} г\nКоличество: {data['units']} шт.\nПлан: {total:.2f} кг\n\nДля подтверждения напишите «Подтвердить» или нажмите «Отмена».",
        parse_mode="HTML", reply_markup=form_menu()
    )


@router.message(RequestForm.confirm)
async def request_confirm(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear(); await message.answer("Заявка отменена.", reply_markup=partner_menu()); return
    if message.text != "Подтвердить":
        await message.answer("Напишите «Подтвердить» или нажмите «Отмена».", reply_markup=form_menu()); return
    await state.clear(); await message.answer("✅ Заявка принята в черновик. После подключения синхронизации администратор получит уведомление.", reply_markup=partner_menu())


@router.message(F.text.in_({"🛠 Админ-панель", "📋 Принять заявку", "⏳ Очередь", "📦 Грузоместа", "📸 Фотоотчёты", "📊 Сводка"}))
async def admin_actions(message: Message) -> None:
    if not is_admin(message):
        await message.answer("Этот раздел доступен только администратору."); return
    await message.answer("<b>Админ-панель</b>\n\nЗдесь будут заявки партнёров, очередь, приёмка с фото, фасовка, грузоместа и месячные сводки.", parse_mode="HTML", reply_markup=admin_menu())


async def main() -> None:
    try:
        await init_database()
    except Exception:
        logging.exception("База данных пока недоступна; запускаю Telegram-часть для проверки")
    bot = Bot(token=settings.bot_token); dispatcher = Dispatcher(); dispatcher.include_router(router)
    logging.info("Запуск бота «%s»", settings.app_name); await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
