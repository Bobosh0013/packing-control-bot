import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.config import load_settings
from bot.db import init_database
from bot.menu import main_menu

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)

router = Router()
settings = load_settings()


@router.message(CommandStart())
async def start(message: Message) -> None:
    is_admin = message.from_user is not None and message.from_user.id in settings.admin_ids
    await message.answer(
        f"Добро пожаловать в «{settings.app_name}»!\n\n"
        "Здесь партнёры подают заявки на фасовку, следят за очередью и получают уведомления.\n\n"
        "Важные правила:\n"
        "• максимум 23 кг товара в одном коробе;\n"
        "• максимум 30 грузомест в одном кластере;\n"
        "• одна заявка — один товар, одна фасовка и один маркетплейс.\n\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu(is_admin),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды системы:\n"
        "/start — начать работу\n"
        "/help — помощь\n"
        "/status — проверить доступность бота\n\n"
        "Полная регистрация партнёров и заявок будет включена после подключения базы данных."
    )


@router.message(Command("status"))
async def status_command(message: Message) -> None:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    await message.answer(f"Бот «{settings.app_name}» работает. Проверка: {now}.")


@router.message(lambda message: message.text == "📚 Регламент")
async def regulation(message: Message) -> None:
    await message.answer(
        "Регламент «Фасовка Контроль»:\n\n"
        "• одна заявка — один товар, одна фасовка и один маркетплейс;\n"
        "• максимум 23 кг товара в одном коробе;\n"
        "• максимум 30 грузомест в одном кластере;\n"
        "• документы и макеты отправляются до запуска заявки;\n"
        "• спорные вопросы фиксируются через бота с фото и документами."
    )


@router.message(lambda message: message.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    await help_command(message)


@router.message(lambda message: message.text == "⏳ Проверить очередь")
async def queue_placeholder(message: Message) -> None:
    await message.answer("Очередь пока пуста. После подключения базы и синхронизации здесь появятся заявки.")


@router.message(lambda message: message.text == "📋 Подать заявку")
async def request_placeholder(message: Message) -> None:
    await message.answer(
        "Мастер подачи заявки будет подключён следующим обновлением.\n"
        "Он проверит товар, количество, вес, документы и лимит грузомест до отправки заявки."
    )


async def main() -> None:
    try:
        await init_database()
    except Exception:
        logging.exception("База данных пока недоступна; запускаю Telegram-часть для проверки")
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    logging.info("Запуск бота «%s»", settings.app_name)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
