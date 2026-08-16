from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from database import async_session, User, WithdrawRequest
from config import config

router = Router()


class WithdrawStates(StatesGroup):
    choosing_type = State()
    entering_wallet = State()


def withdraw_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON yechish", callback_data="wd_ton")],
        [InlineKeyboardButton(text="💵 So'm yechish", callback_data="wd_sum")],
    ])


@router.message(Command("withdraw"))
async def cmd_withdraw(message: Message):
    await message.answer(
        "Qaysi balansni yechib olmoqchisiz?",
        reply_markup=withdraw_type_kb()
    )


@router.callback_query(F.data.in_({"wd_ton", "wd_sum"}))
async def choose_withdraw_type(callback: CallbackQuery, state: FSMContext):
    wtype = "ton" if callback.data == "wd_ton" else "sum"
    await state.update_data(amount_type=wtype)
    await state.set_state(WithdrawStates.entering_wallet)

    prompt = (
        "TON hamyon manzilingizni yuboring:" if wtype == "ton"
        else "Karta raqamingizni yuboring:"
    )
    await callback.message.edit_text(prompt)


@router.message(WithdrawStates.entering_wallet)
async def receive_wallet(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    wtype = data["amount_type"]
    user_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        available = user.balance_ton if wtype == "ton" else user.balance_sum

        if not available or available <= 0:
            await message.answer("❌ Balansingizda yetarli mablag' yo'q.")
            await state.clear()
            return

        req = WithdrawRequest(
            user_id=user_id,
            amount_type=wtype,
            amount=available,
            wallet_or_card=message.text,
        )
        session.add(req)

        # Balansni darhol nolga tushirmaymiz - admin tasdiqlagach yechamiz (approve_withdraw da)
        await session.commit()
        req_id = req.id

    await message.answer(
        "✅ So'rovingiz qabul qilindi! Admin tekshirib, 24 soat ichida to'lov qiladi."
    )
    await state.clear()

    # Adminlarga xabar yuborish
    unit = "TON" if wtype == "ton" else "so'm"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_wd_{req_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_wd_{req_id}"),
        ]
    ])
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💸 <b>Yangi yechish so'rovi #{req_id}</b>\n"
                f"Foydalanuvchi: {user_id}\n"
                f"Miqdor: {available} {unit}\n"
                f"Manzil/karta: {message.text}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("approve_wd_"))
async def approve_withdraw(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    req_id = int(callback.data.split("_")[-1])
    async with async_session() as session:
        result = await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
        req = result.scalar_one_or_none()
        if not req or req.status != "pending":
            await callback.answer("So'rov topilmadi yoki allaqachon ishlov berilgan", show_alert=True)
            return

        user_result = await session.execute(select(User).where(User.id == req.user_id))
        user = user_result.scalar_one_or_none()

        # Balansdan yechish (admin TON'ni qo'lda hamyondan yuborgach shu yerda tasdiqlaydi)
        if req.amount_type == "ton":
            user.balance_ton = max(0, user.balance_ton - req.amount)
        else:
            user.balance_sum = max(0, user.balance_sum - req.amount)

        req.status = "approved"
        await session.commit()

    await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI")
    try:
        await bot.send_message(req.user_id, f"✅ So'rovingiz #{req_id} to'landi!")
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_wd_"))
async def reject_withdraw(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    req_id = int(callback.data.split("_")[-1])
    async with async_session() as session:
        result = await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
        req = result.scalar_one_or_none()
        if not req or req.status != "pending":
            await callback.answer("So'rov topilmadi yoki allaqachon ishlov berilgan", show_alert=True)
            return
        req.status = "rejected"
        await session.commit()
        user_id = req.user_id

    await callback.message.edit_text(callback.message.text + "\n\n❌ RAD ETILDI")
    try:
        await bot.send_message(user_id, f"❌ So'rovingiz #{req_id} rad etildi. Admin bilan bog'laning.")
    except Exception:
        pass

