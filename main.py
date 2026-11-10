"""Точка запуска для хостингов, которые принимают только имя Python-файла."""

from bot.main import main
import asyncio


if __name__ == "__main__":
    asyncio.run(main())
