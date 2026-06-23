import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from bot.dispatcher import setup_dispatcher
from database.engine import init_db
from utils.logger import setup_logger


async def main():
    setup_logger()
    print("🚀 Запуск бота JobBot...")

    await init_db()
    print("✅ База данных SQLite готова")

    dp, bot = await setup_dispatcher()

    print("✅ Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())