from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from database import async_session, User, ReferralLog, WithdrawRequest
from handlers.start import main_menu_kb
from config import config

router = Router()


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]
    ])


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏠 Bosh menyu:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "referral_info")
async def referral_info(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    async with async_session() as session:
        count_result = await session.execute(
            select(func.count()).select_from(ReferralLog).where(ReferralLog.inviter_id == user_id)
        )
        total_refs = count_result.scalar() or 0

        paid_result = await session.execute(
            select(func.count()).select_from(ReferralLog)
            .where(ReferralLog.inviter_id == user_id, ReferralLog.reward_paid == True)  # noqa: E712
        )
        paid_refs = paid_result.scalar() or 0

    text = (
        "👥 <b>Referal dasturi</b>\n\n"
        f"Sizning havolangiz:\n<code>{ref_link}</code>\n\n"
        f"📊 Jami taklif qilinganlar: {total_refs}\n"
        f"✅ Mukofot to'langanlar: {paid_refs}\n\n"
        f"💰 Har bir faol referal uchun: {config.REFERRAL_REWARD_SUM} so'm\n"
        f"⚠️ Mukofot referal kamida {config.REFERRAL_MIN_ACTIVE_DAYS} kun faol bo'lgach beriladi "
        "(soxta akkauntlarning oldini olish uchun)"
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")


@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    text = (
        "💰 <b>Sizning balansingiz</b>\n\n"
        f"TON: {user.balance_ton:.3f}\n"
        f"So'm (referal): {user.balance_sum} so'm\n\n"
        "Yechib olish uchun /withdraw buyrug'ini yuboring."
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")


async def process_referral_rewards(bot: Bot):
    """
    Fon vazifasi (scheduler orqali kuniga bir marta ishga tushiriladi):
    REFERRAL_MIN_ACTIVE_DAYS kun faol bo'lgan, hali mukofot olmagan referallarni topib,
    taklif qilgan foydalanuvchiga so'm balansini qo'shadi.
    """
    async with async_session() as session:
        cutoff = datetime.now() - timedelta(days=config.REFERRAL_MIN_ACTIVE_DAYS)

        result = await session.execute(
            select(ReferralLog).where(ReferralLog.reward_paid == False)  # noqa: E712
        )
        pending = result.scalars().all()

        for ref in pending:
            invited_result = await session.execute(
                select(User).where(User.id == ref.invited_id)
            )
            invited_user = invited_result.scalar_one_or_none()

            if invited_user and not invited_user.is_banned and invited_user.joined_at <= cutoff:
                inviter_result = await session.execute(
                    select(User).where(User.id == ref.inviter_id)
                )
                inviter = inviter_result.scalar_one_or_none()
                if inviter:
                    inviter.balance_sum += config.REFERRAL_REWARD_SUM
                    ref.reward_paid = True
                    try:
                        await bot.send_message(
                            inviter.id,
                            f"🎉 Sizning referalingiz faollashdi! "
                            f"+{config.REFERRAL_REWARD_SUM} so'm balansingizga qo'shildi."
                        )
                    except Exception:
                        pass

        await session.commit()
