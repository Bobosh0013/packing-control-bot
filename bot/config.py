from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    admin_username: str
    database_url: str
    sheet_id: str
    sheets_webhook_url: str
    sheets_webhook_secret: str
    service_account_file: Path
    timezone: str
    app_name: str


def load_settings() -> Settings:
    token = getenv("BOT_TOKEN", "").strip()
    if not token or token == "PASTE_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError("Укажите BOT_TOKEN в файле .env")

    raw_admin_ids = getenv("ADMIN_TG_IDS", "")
    admin_ids = frozenset(
        int(value.strip())
        for value in raw_admin_ids.split(",")
        if value.strip().isdigit()
    )
    if not admin_ids:
        raise RuntimeError("Укажите хотя бы один Telegram ID в ADMIN_TG_IDS")

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        admin_username=getenv("ADMIN_USERNAME", "").strip().lstrip("@"),
        database_url=getenv("DATABASE_URL", "sqlite+aiosqlite:///./packing_control.db"),
        sheet_id=getenv("SHEET_ID", "").strip(),
        sheets_webhook_url=getenv("SHEETS_WEBHOOK_URL", "").strip(),
        sheets_webhook_secret=getenv("SHEETS_WEBHOOK_SECRET", "").strip(),
        service_account_file=Path(
            getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/google-service-account.json")
        ),
        timezone=getenv("TIMEZONE", "Europe/Minsk"),
        app_name=getenv("APP_NAME", "Фасовка Контроль"),
    )
