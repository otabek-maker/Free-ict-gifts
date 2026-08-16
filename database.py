from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Integer, Float, DateTime, Boolean, ForeignKey, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config import config


class Base(DeclarativeBase):
    pass


class User(Base):
    """Har bir bot foydalanuvchisi"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=True)

    balance_sum: Mapped[int] = mapped_column(Integer, default=0)   # so'm balansi (referal uchun)
    balance_ton: Mapped[float] = mapped_column(Float, default=0.0)  # TON balansi (keys uchun)

    invited_by: Mapped[int] = mapped_column(BigInteger, nullable=True)  # kim taklif qilgan
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)  # kanalga obuna holati

    last_case_open: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)  # firibgarlar uchun


class CaseOpenLog(Base):
    """Har bir keys ochish tarixi - audit va byudjet nazorati uchun"""
    __tablename__ = "case_opens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    prize_type: Mapped[str] = mapped_column(String(16))   # ton / gift / empty
    prize_value: Mapped[str] = mapped_column(String(64))
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReferralLog(Base):
    """Referal orqali qo'shilganlar va mukofot holati"""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    invited_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    reward_paid: Mapped[bool] = mapped_column(Boolean, default=False)  # 3 kunlik faollikdan keyin to'lanadi
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WithdrawRequest(Base):
    """Foydalanuvchi pul/TON yechib olish so'rovi - admin qo'lda tasdiqlaydi"""
    __tablename__ = "withdraw_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount_type: Mapped[str] = mapped_column(String(8))   # "sum" yoki "ton"
    amount: Mapped[float] = mapped_column(Float)
    wallet_or_card: Mapped[str] = mapped_column(String(128))  # TON wallet manzili yoki karta raqami
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class DailyBudget(Base):
    """Kunlik sarflangan TON miqdorini kuzatish - byudjetdan oshib ketmaslik uchun"""
    __tablename__ = "daily_budget"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    spent_ton: Mapped[float] = mapped_column(Float, default=0.0)


engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """Baza jadvallarini yaratish - birinchi ishga tushirishda chaqiriladi"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
