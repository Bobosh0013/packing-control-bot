import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from datetime import timezone
from decimal import Decimal

from bot.config import load_settings
from bot.db import get_session, init_database, session_factory
from bot.menu import admin_menu, contact_menu, form_menu, partner_menu, regulation_menu
from bot.models import AccessRequest, Partner, Request as DbRequest, RequestStatus, User
from bot.sheets import append_request

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


class AccessForm(StatesGroup):
    contact = State()
    fio = State()
    role = State()
    brands = State()
    phone = State()


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
    if is_admin(message):
        await message.answer("Добро пожаловать, администратор. Выберите действие.", reply_markup=admin_menu())
        return
    if not is_admin(message):
        async with session_factory() as session:
            access = (await session.execute(select(AccessRequest).where(AccessRequest.tg_id == message.from_user.id))).scalar_one_or_none()
            user = (await session.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not access or access.status != "approved" or not user or not user.is_active:
            await stateless_access_request(message)
            return
    if message.from_user.id not in accepted_users:
        await message.answer(
            f"Добро пожаловать в «{settings.app_name}»!\n\nПеред началом работы ознакомьтесь с регламентом.",
        )
        await show_regulation(message)
        return
    await message.answer("Выберите действие.", reply_markup=admin_menu() if is_admin(message) else partner_menu())


async def stateless_access_request(message: Message) -> None:
    await message.answer(
        "<b>Доступ к производству</b>\n\nДо подачи заявок администратор должен подтвердить ваш доступ.\n"
        "Нажмите /request_access и отправьте контакт, имя, роль и бренд.", parse_mode="HTML"
    )


@router.message(Command("request_access"))
async def request_access_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AccessForm.contact)
    await message.answer("Сначала отправьте свой контакт кнопкой ниже.", reply_markup=contact_menu())


@router.message(AccessForm.contact, F.contact)
async def access_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    await state.update_data(phone=contact.phone_number, tg_id=contact.user_id or message.from_user.id)
    await state.set_state(AccessForm.fio)
    await message.answer("Введите ваше имя и фамилию или имя менеджера.", reply_markup=form_menu())


@router.message(AccessForm.fio)
async def access_fio(message: Message, state: FSMContext) -> None:
    if message.text in {"❌ Отмена", "⬅️ Назад"}:
        await state.clear(); await message.answer("Запрос отменён."); return
    await state.update_data(fio=message.text.strip()); await state.set_state(AccessForm.role)
    await message.answer("Кем вы работаете: владелец, менеджер или другая роль?", reply_markup=form_menu())


@router.message(AccessForm.role)
async def access_role(message: Message, state: FSMContext) -> None:
    if message.text in {"❌ Отмена", "⬅️ Назад"}:
        await state.set_state(AccessForm.fio); await message.answer("Введите имя.", reply_markup=form_menu()); return
    await state.update_data(role=message.text.strip()); await state.set_state(AccessForm.brands)
    await message.answer("Напишите ИП, ООО или бренд. Если брендов несколько, перечислите через запятую.", reply_markup=form_menu())


@router.message(AccessForm.brands)
async def access_brands(message: Message, state: FSMContext) -> None:
    if message.text in {"❌ Отмена", "⬅️ Назад"}:
        await state.set_state(AccessForm.role); await message.answer("Кем вы работаете: владелец, менеджер или другая роль?", reply_markup=form_menu()); return
    await state.update_data(brands=message.text.strip()); await state.set_state(AccessForm.phone)
    await message.answer("Проверьте данные и напишите «Отправить».", reply_markup=form_menu())


@router.message(AccessForm.phone)
async def access_phone(message: Message, state: FSMContext) -> None:
    if message.text in {"❌ Отмена", "⬅️ Назад"}:
        await state.clear(); await message.answer("Запрос отменён."); return
    if message.text != "Отправить":
        await message.answer("Напишите «Отправить» или нажмите «Отмена».", reply_markup=form_menu()); return
    data = await state.get_data()
    async with session_factory() as session:
        request = (await session.execute(select(AccessRequest).where(AccessRequest.tg_id == message.from_user.id))).scalar_one_or_none()
        if request is None:
            request = AccessRequest(tg_id=message.from_user.id, fio=data["fio"], phone=data.get("phone", ""), email=data.get("role", ""), brands=data.get("brands", ""), status="pending")
            session.add(request)
        else:
            request.fio, request.phone, request.email, request.brands, request.status = data["fio"], data.get("phone", ""), data.get("role", ""), data.get("brands", ""), "pending"
        await session.commit()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Открыть доступ", callback_data=f"access_approve:{message.from_user.id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"access_reject:{message.from_user.id}")]])
    for admin_id in settings.admin_ids:
        await message.bot.send_message(admin_id, f"🔐 Запрос доступа\nИмя менеджера: {data['fio']}\nКонтакт: {data.get('phone', '')}\nРоль: {data.get('role', '')}\nИП/ООО/бренд: {data.get('brands', '')}\nTelegram ID: {message.from_user.id}", reply_markup=keyboard)
    await state.clear(); await message.answer("Запрос отправлен администратору. Дождитесь подтверждения.")


@router.callback_query(F.data.startswith("access_approve:"))
async def access_approve(callback: CallbackQuery) -> None:
    if not callback.from_user or callback.from_user.id not in settings.admin_ids: await callback.answer("Недостаточно прав", show_alert=True); return
    tg_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        request = (await session.execute(select(AccessRequest).where(AccessRequest.tg_id == tg_id))).scalar_one_or_none()
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
        if request is None: await callback.answer("Запрос не найден", show_alert=True); return
        request.status = "approved"
        if user is None: user = User(tg_id=tg_id, role="partner_manager", fio=request.fio, phone=request.phone, is_active=True); session.add(user)
        else: user.is_active = True; user.fio, user.phone = request.fio, request.phone
        await session.commit()
    await callback.bot.send_message(tg_id, "✅ Доступ открыт. Добро пожаловать в производство фасовки товаров!\n\nПеред началом работы ознакомьтесь с регламентом: отправьте /start.")
    await callback.message.edit_reply_markup(reply_markup=None); await callback.answer("Доступ открыт")


@router.callback_query(F.data.startswith("access_reject:"))
async def access_reject(callback: CallbackQuery) -> None:
    if not callback.from_user or callback.from_user.id not in settings.admin_ids: await callback.answer("Недостаточно прав", show_alert=True); return
    tg_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        request = (await session.execute(select(AccessRequest).where(AccessRequest.tg_id == tg_id))).scalar_one_or_none()
        if request: request.status = "rejected"; await session.commit()
    await callback.bot.send_message(tg_id, "⚠️ Доступ пока не подтверждён. Обратитесь к администратору.")
    await callback.message.edit_reply_markup(reply_markup=None); await callback.answer("Запрос отклонён")


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
    data = await state.get_data()
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if user is None:
            user = User(tg_id=message.from_user.id, role="partner_manager", fio=message.from_user.full_name)
            session.add(user); await session.flush()
        partner = (await session.execute(select(Partner).where(Partner.owner_user_id == user.id))).scalar_one_or_none()
        if partner is None:
            partner = Partner(name=f"Партнёр {message.from_user.id}", owner_user_id=user.id, marketplaces="[]")
            session.add(partner); await session.flush()
        total = Decimal(data["units"] * data["weight"]) / Decimal(1000)
        request = DbRequest(
            number="TEMP", partner_id=partner.id, created_by_user_id=user.id,
            product_name=data["product"], weight_category_g=data["weight"], units_count=data["units"],
            total_kg=total, marketplace=data["marketplace"], status=RequestStatus.DRAFT,
            comment=data.get("comment"),
        )
        session.add(request); await session.flush(); request.number = f"З-{request.id:04d}"; await session.commit()
        row = [request.number, datetime.now().isoformat(timespec="minutes"), partner.name, partner.id, message.from_user.full_name,
               data["marketplace"], data["product"], "", data["weight"], data["units"], float(total), "", "", "", "", "", "", "", "На согласовании", "Нет", "Нет", "Нет", "Нет", "", data.get("comment") or "", datetime.now().isoformat(timespec="minutes"), "", "", "", "", "Новая заявка", message.from_user.full_name]
        await append_request(row)
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять в очередь", callback_data=f"approve:{request.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{request.id}"),
        ]])
        for admin_id in settings.admin_ids:
            try:
                await message.bot.send_message(admin_id, f"📋 Новая заявка {request.number}\nТовар: {request.product_name}\nФасовка: {request.weight_category_g} г\nКоличество: {request.units_count} шт.\nПлан: {request.total_kg} кг\nМаркетплейс: {request.marketplace}", reply_markup=admin_keyboard)
            except Exception:
                logging.exception("Не удалось уведомить администратора")
    await state.clear(); await message.answer(f"✅ Заявка {request.number} отправлена администратору на подтверждение.", reply_markup=partner_menu())


@router.callback_query(F.data.startswith("approve:"))
async def approve_request(callback: CallbackQuery) -> None:
    if not callback.from_user or callback.from_user.id not in settings.admin_ids:
        await callback.answer("Недостаточно прав", show_alert=True); return
    request_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        request = await session.get(DbRequest, request_id)
        if request is None:
            await callback.answer("Заявка не найдена", show_alert=True); return
        request.status = RequestStatus.IN_QUEUE; request.accepted_at = datetime.now(timezone.utc); await session.commit()
        user = await session.get(User, request.created_by_user_id)
    if user:
        try:
            await callback.bot.send_message(user.tg_id, f"✅ Заявка {request.number} принята в очередь.")
        except Exception:
            logging.exception("Не удалось уведомить партнёра")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Заявка принята в очередь")


@router.callback_query(F.data.startswith("reject:"))
async def reject_request(callback: CallbackQuery) -> None:
    if not callback.from_user or callback.from_user.id not in settings.admin_ids:
        await callback.answer("Недостаточно прав", show_alert=True); return
    request_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session:
        request = await session.get(DbRequest, request_id)
        if request is None:
            await callback.answer("Заявка не найдена", show_alert=True); return
        request.status = RequestStatus.NEEDS_ACTION; await session.commit()
        user = await session.get(User, request.created_by_user_id)
    if user:
        await callback.bot.send_message(user.tg_id, f"⚠️ Заявка {request.number} требует уточнения. Администратор свяжется с вами.")
    await callback.message.edit_reply_markup(reply_markup=None); await callback.answer("Заявка отправлена на уточнение")


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
