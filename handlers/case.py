import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database import async_session, User, CaseOpenLog, DailyBudget
from handlers.start import is_user_subscribed, main_menu_kb
from config import config

router = Router()


def pick_prize():
    """Og'irlik (weight) asosida tasodifiy sovrin tanlaydi"""
    prizes = config.CASE_PRIZES
    weights = [p["weight"] for p in prizes]
    return random.choices(prizes, weights=weights, k=1)[0]


async def get_today_spent(session) -> float:
    today = datetime.now().strftime("%Y-%m-%d")
    result = await session.execute(select(DailyBudget).where(DailyBudget.date == today))
    row = result.scalar_one_or_none()
    return row.spent_ton if row else 0.0


async def add_today_spent(session, amount: float):
    today = datetime.now().strftime("%Y-%m-%d")
    result = await session.execute(select(DailyBudget).where(DailyBudget.date == today))
    row = result.scalar_one_or_none()
    if row is None:
        row = DailyBudget(date=today, spent_ton=amount)
        session.add(row)
    else:
        row.spent_ton += amount


@router.callback_query(F.data == "open_case")
async def open_case(callback: CallbackQuery, bot):
    user_id = callback.from_user.id

    # Obunani qayta tekshirish (ba'zi userlar keyin kanaldan chiqib ketishi mumkin)
    if not await is_user_subscribed(bot, user_id):
        await callback.answer("❌ Avval kanalga obuna bo'ling", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or user.is_banned:
            await callback.answer("Xatolik yuz berdi", show_alert=True)
            return

        # Cooldown tekshiruvi
        if user.last_case_open:
            elapsed = datetime.now() - user.last_case_open
            if elapsed < timedelta(hours=config.CASE_COOLDOWN_HOURS):
                remaining = timedelta(hours=config.CASE_COOLDOWN_HOURS) - elapsed
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await callback.answer(
                    f"⏳ Keyingi keys {hours} soat {minutes} daqiqadan so'ng ochiladi",
                    show_alert=True
                )
                return

        prize = pick_prize()

        # Kunlik byudjet nazorati - agar TON sovrin bo'lsa
        if prize["type"] == "ton":
            spent = await get_today_spent(session)
            if spent + prize["value"] > config.DAILY_TON_BUDGET:
                # Byudjet tugagan - "bo'sh" natijaga almashtiramiz
                prize = {"type": "empty", "value": 0}

        # Natijani qo'llash
        if prize["type"] == "ton":
            user.balance_ton += prize["value"]
            await add_today_spent(session, prize["value"])
            text = f"🎉 Tabriklaymiz! Sizga {prize['value']} TON tushdi!"
        elif prize["type"] == "gift":
            text = f"🎁 Tabriklaymiz! Sizga {prize['value']} tushdi!\nAdmin siz bilan bog'lanadi."
        else:
            text = "😔 Bu safar hech narsa chiqmadi. Ertaga qayta urinib ko'ring!"

        user.last_case_open = datetime.now()

        session.add(CaseOpenLog(
            user_id=user_id,
            prize_type=prize["type"],
            prize_value=str(prize["value"]),
        ))

        await session.commit()

    await callback.message.edit_text(
        text + "\n\n⬇️ Menyuga qaytish uchun:",
        reply_markup=main_menu_kb()
    )
