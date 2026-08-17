import os
from datetime import datetime, timedelta

from aiohttp import web
import aiohttp_cors
from sqlalchemy import select, func

from database import async_session, User, CaseOpenLog, ReferralLog
from config import config
from webapp_auth import validate_init_data
from handlers.case import pick_prize, get_today_spent, add_today_spent
from handlers.start import is_user_subscribed


def _extract_user(request_json: dict):
    """initData'ni tekshirib, ichidan Telegram user obyektini ajratib oladi"""
    init_data = request_json.get("initData", "")
    parsed = validate_init_data(init_data, config.BOT_TOKEN)
    if not parsed or "user" not in parsed:
        return None
    return parsed["user"]


async def get_or_create_user(session, tg_user: dict) -> User:
    result = await session.execute(select(User).where(User.id == tg_user["id"]))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=tg_user["id"],
            username=tg_user.get("username"),
            full_name=f'{tg_user.get("first_name","")} {tg_user.get("last_name","")}'.strip(),
        )
        session.add(user)
        await session.flush()
    return user


async def handle_state(request: web.Request):
    """Mini-ilova ochilganda kerakli barcha ma'lumotni qaytaradi"""
    body = await request.json()
    tg_user = _extract_user(body)
    if not tg_user:
        return web.json_response({"error": "invalid_init_data"}, status=401)

    bot = request.app["bot"]

    async with async_session() as session:
        user = await get_or_create_user(session, tg_user)

        subscribed = await is_user_subscribed(bot, user.id)

        cooldown_remaining = 0
        if user.last_case_open:
            elapsed = datetime.now() - user.last_case_open
            remain = timedelta(hours=config.CASE_COOLDOWN_HOURS) - elapsed
            cooldown_remaining = max(0, int(remain.total_seconds()))

        total_refs = (await session.execute(
            select(func.count()).select_from(ReferralLog).where(ReferralLog.inviter_id == user.id)
        )).scalar() or 0
        active_refs = (await session.execute(
            select(func.count()).select_from(ReferralLog)
            .where(ReferralLog.inviter_id == user.id, ReferralLog.reward_paid == True)  # noqa: E712
        )).scalar() or 0

        history_result = await session.execute(
            select(CaseOpenLog).where(CaseOpenLog.user_id == user.id)
            .order_by(CaseOpenLog.opened_at.desc()).limit(5)
        )
        history = [
            {
                "type": h.prize_type,
                "value": h.prize_value,
                "time": h.opened_at.strftime("%d-%m %H:%M"),
            }
            for h in history_result.scalars().all()
        ]

        await session.commit()

        bot_info = await bot.get_me()

        return web.json_response({
            "user": {
                "id": user.id,
                "name": user.full_name or user.username or "Foydalanuvchi",
            },
            "subscribed": subscribed,
            "required_channel": config.REQUIRED_CHANNEL,
            "balance_ton": round(user.balance_ton, 3),
            "balance_sum": user.balance_sum,
            "cooldown_remaining": cooldown_remaining,
            "referral_link": f"https://t.me/{bot_info.username}?start={user.id}",
            "referral_total": total_refs,
            "referral_active": active_refs,
            "referral_reward_sum": config.REFERRAL_REWARD_SUM,
            "referral_min_days": config.REFERRAL_MIN_ACTIVE_DAYS,
            "history": history,
            "odds": config.CASE_PRIZES,
        })


async def handle_open_case(request: web.Request):
    body = await request.json()
    tg_user = _extract_user(body)
    if not tg_user:
        return web.json_response({"error": "invalid_init_data"}, status=401)

    bot = request.app["bot"]

    if not await is_user_subscribed(bot, tg_user["id"]):
        return web.json_response({"error": "not_subscribed"}, status=403)

    async with async_session() as session:
        user = await get_or_create_user(session, tg_user)

        if user.is_banned:
            return web.json_response({"error": "banned"}, status=403)

        if user.last_case_open:
            elapsed = datetime.now() - user.last_case_open
            if elapsed < timedelta(hours=config.CASE_COOLDOWN_HOURS):
                remain = timedelta(hours=config.CASE_COOLDOWN_HOURS) - elapsed
                return web.json_response({
                    "error": "cooldown",
                    "cooldown_remaining": int(remain.total_seconds()),
                }, status=429)

        prize = pick_prize()

        if prize["type"] == "ton":
            spent = await get_today_spent(session)
            if spent + prize["value"] > config.DAILY_TON_BUDGET:
                prize = {"type": "empty", "value": 0}

        if prize["type"] == "ton":
            user.balance_ton += prize["value"]
            await add_today_spent(session, prize["value"])

        user.last_case_open = datetime.now()
        session.add(CaseOpenLog(
            user_id=user.id,
            prize_type=prize["type"],
            prize_value=str(prize["value"]),
        ))
        await session.commit()

        return web.json_response({
            "prize": prize,
            "balance_ton": round(user.balance_ton, 3),
            "cooldown_remaining": config.CASE_COOLDOWN_HOURS * 3600,
        })


async def handle_leaderboard(request: web.Request):
    """Eng ko'p TON yutganlar reytingi (barcha vaqt bo'yicha, oddiy versiya)"""
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.balance_ton.desc()).limit(10))
        users = result.scalars().all()
        data = [
            {
                "name": (u.username or u.full_name or "Foydalanuvchi")[:12],
                "score": round(u.balance_ton, 3),
            }
            for u in users
        ]
        return web.json_response({"leaderboard": data})


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    })

    resources = [
        app.router.add_post("/api/state", handle_state),
        app.router.add_post("/api/open-case", handle_open_case),
        app.router.add_get("/api/leaderboard", handle_leaderboard),
    ]
    for r in resources:
        cors.add(r)

    return app


async def start_webserver(bot):
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner
