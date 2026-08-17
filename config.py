import os
from dataclasses import dataclass, field
from typing import List


def _normalize_db_url(url: str) -> str:
    """Railway (va boshqa provayderlar) odatda 'postgresql://' yoki 'postgres://'
    formatida URL beradi. Bizga asyncpg drayveri kerak, shuning uchun avtomatik
    to'g'irlaymiz."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@dataclass
class Config:
    # Bot tokeni - @BotFather dan olinadi
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8617473134:AAEDWapRqHtJpLHQ6IRIzCFNmsstWsA0k_w")

    # Ma'lumotlar bazasi ulanish manzili (PostgreSQL)
    DATABASE_URL: str = _normalize_db_url(os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/freegift"
    ))

    # Admin(lar) Telegram ID raqami (pul so'rovlarini tasdiqlash uchun)
    ADMIN_IDS: List[int] = field(default_factory=lambda: [8600950595])

    # Majburiy obuna kanali (username, @ belgisisiz)
    # Hozircha bo'sh — kanal tayyor bo'lgach shu yerga username kiritiladi va tekshiruv avtomatik yoqiladi
    REQUIRED_CHANNEL: str = ""

    # Kunlik keys ochish sovrinlari (qiymat -> ehtimollik og'irligi)
    # "gift" - maxsus sovg'a (2 ta cheklangan), qolganlari TON miqdori
    CASE_PRIZES = [
        {"type": "ton", "value": 0.1, "weight": 40},
        {"type": "ton", "value": 0.2, "weight": 25},
        {"type": "ton", "value": 0.3, "weight": 10},
        {"type": "gift", "value": "Maxsus sovg'a #1", "weight": 2},
        {"type": "gift", "value": "Maxsus sovg'a #2", "weight": 2},
        {"type": "empty", "value": 0, "weight": 21},  # "bo'sh chiqish" ehtimoli - byudjetni himoya qiladi
    ]

    # Kunlik keys ochish limiti (soatda, cooldown)
    CASE_COOLDOWN_HOURS: int = 24

    # Referal uchun mukofot (so'm)
    REFERRAL_REWARD_SUM: int = 1000

    # Referal faol hisoblanishi uchun minimal kun (bot farmga qarshi)
    REFERRAL_MIN_ACTIVE_DAYS: int = 3

    # Kunlik umumiy TON byudjet limiti (barcha foydalanuvchilar uchun)
    DAILY_TON_BUDGET: float = 50.0

config = Config()
