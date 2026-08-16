from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from database import async_session, User, ReferralLog
from config import config

router = Router()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Kunlik keys", callback_data="open_case")],
        [InlineKeyboardButton(text="👥 Referal", callback_data="referral_info")],
        [InlineKeyboardButton(text="💰 Balans", callback_data="balance")],
    ])


def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Kanalga obuna bo'lish",
            url=f"https://t.me/{config.REQUIRED_CHANNEL}"
        )],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")],
    ])


async def is_user_subscribed(bot, user_id: int) -> bool:
    """Foydalanuvchi kanalga obuna ekanligini tekshiradi.
    Agar REQUIRED_CHANNEL sozlanmagan bo'lsa (bo'sh), tekshiruv o'tkazib yuboriladi."""
    if not config.REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(f"@{config.REQUIRED_CHANNEL}", user_id)
        return member.status not in ("left", "kicked")
    except TelegramBadRequest:
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot):
    user_id = message.from_user.id
    referrer_id = None

    # /start 123456789 formatidagi referal linkni parse qilish
    if command.args and command.args.isdigit():
        candidate = int(command.args)
        if candidate != user_id:
            referrer_id = candidate

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        is_new = False
        if user is None:
            is_new = True
            user = User(
                id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                invited_by=referrer_id,
            )
            session.add(user)
            await session.flush()

            # Referal yozuvini yaratish (mukofot keyinchalik, faollikni tekshirgach beriladi)
            if referrer_id:
                ref_check = await session.execute(
                    select(User).where(User.id == referrer_id)
                )
                if ref_check.scalar_one_or_none():
                    session.add(ReferralLog(inviter_id=referrer_id, invited_id=user_id))

        await session.commit()

    subscribed = await is_user_subscribed(bot, user_id)

    if not subscribed:
        await message.answer(
            "👋 Xush kelibsiz, Free ICT Gift botiga!\n\n"
            "Botdan foydalanish uchun avval trading kanalimizga obuna bo'ling:",
            reply_markup=subscribe_kb()
        )
        return

    greeting = "Xush kelibsiz" if is_new else "Qaytganingizdan xursandmiz"
    await message.answer(
        f"👋 {greeting}, Free ICT Gift botiga!\n\n"
        "🎁 Har kuni bepul keys oching\n"
        "👥 Do'stlaringizni taklif qiling va mukofot oling\n\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback, bot):
    subscribed = await is_user_subscribed(bot, callback.from_user.id)
    if subscribed:
        await callback.message.edit_text(
            "✅ Obuna tasdiqlandi! Endi botdan to'liq foydalanishingiz mumkin.",
            reply_markup=main_menu_kb()
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmagansiz", show_alert=True)

