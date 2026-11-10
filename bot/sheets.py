import asyncio
import logging

import gspread
import aiohttp
from google.oauth2.service_account import Credentials

from bot.config import load_settings

logger = logging.getLogger(__name__)
settings = load_settings()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _worksheet():
    if not settings.sheet_id or settings.sheet_id.startswith("PASTE_"):
        return None
    if not settings.service_account_file.exists():
        logger.warning("Файл сервисного аккаунта Google не найден: %s", settings.service_account_file)
        return None
    credentials = Credentials.from_service_account_file(str(settings.service_account_file), scopes=SCOPES)
    return gspread.authorize(credentials).open_by_key(settings.sheet_id).worksheet("Заявки")


async def append_request(row: list[object]) -> bool:
    if settings.sheets_webhook_url and not settings.sheets_webhook_url.startswith("PASTE_"):
        try:
            async with aiohttp.ClientSession() as client:
                async with client.post(settings.sheets_webhook_url, json={"secret": settings.sheets_webhook_secret, "action": "append_request", "row": row}, timeout=20) as response:
                    return response.status == 200
        except Exception:
            logger.exception("Не удалось отправить заявку через Apps Script")
            return False

    def write() -> bool:
        worksheet = _worksheet()
        if worksheet is None:
            return False
        worksheet.append_row(["" if value is None else value for value in row], value_input_option="USER_ENTERED")
        return True

    try:
        return await asyncio.to_thread(write)
    except Exception:
        logger.exception("Не удалось записать заявку в Google Таблицу")
        return False
