import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database import init_db
from handlers import start, case, referral, withdraw

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(start.router)
    dp.include_router(case.router)
    dp.include_router(referral.router)
    dp.include_router(withdraw.router)

    # Bazani tayyorlash (jadvallarni yaratish)
    await init_db()

    # Har kuni referal mukofotlarini avtomatik hisoblash uchun scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        referral.process_referral_rewards,
        "interval",
        hours=6,
        args=[bot],
    )
    scheduler.start()

    logging.info("Bot ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
