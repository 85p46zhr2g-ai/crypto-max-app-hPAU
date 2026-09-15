import asyncio
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ================== الإعدادات ==================
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8724497887:AAHOfyPLaBGMFfoaYV20Eh-MR7AmLlj0AaM")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/index.html")
HOST       = os.getenv("HOST", "0.0.0.0")
PORT       = int(os.getenv("PORT", "8080"))
DB_PATH    = os.getenv("DB_PATH", "lionmax.db")

ADMIN_ID    = 8183652969
SUPPORT_URL = "https://t.me/FastHelp3"
TON_WALLET  = "UQBrfxfxzB5-op8FGLs-BxnZgOBv0CveJ8VJbC3Xc9pVXZ5X"

TASK_CHANNELS = {1: "@CRYBTO_MAX_1", 2: "@olka_ad"}
TASK_REWARDS  = {1: 0.01, 2: 0.01}

# ================== كتالوج القوالب ==================
TEMPLATES = {
    "lion_tired": {
        "id": "lion_tired", "emoji": "🦁",
        "name_key": "tpl_lion_tired", "desc_key": "tpl_lion_tired_desc",
        "level": 1, "stats": {"str": 5, "spd": 3, "cha": 2},
        "price": 0, "owned_default": True,
    },
    "tiger": {
        "id": "tiger", "emoji": "🐯",
        "name_key": "tpl_tiger", "desc_key": "tpl_tiger_desc",
        "level": 3, "stats": {"str": 12, "spd": 9, "cha": 6},
        "price": 2.5, "owned_default": False,
    },
    "wolf": {
        "id": "wolf", "emoji": "🐺",
        "name_key": "tpl_wolf", "desc_key": "tpl_wolf_desc",
        "level": 5, "stats": {"str": 18, "spd": 22, "cha": 10},
        "price": 7.0, "owned_default": False,
    },
    "bear": {
        "id": "bear", "emoji": "🐻",
        "name_key": "tpl_bear", "desc_key": "tpl_bear_desc",
        "level": 8, "stats": {"str": 35, "spd": 8, "cha": 15},
        "price": 15.0, "owned_default": False,
    },
    "eagle": {
        "id": "eagle", "emoji": "🦅",
        "name_key": "tpl_eagle", "desc_key": "tpl_eagle_desc",
        "level": 12, "stats": {"str": 20, "spd": 40, "cha": 25},
        "price": 30.0, "owned_default": False,
    },
}

INVEST_LEVELS = {
    1: (1.0, 24, 0.02),
    2: (2.0, 24, 0.05),
    3: (5.0, 48, 0.15),
    4: (7.0, 72, 0.25),
    5: (10.0, 96, 0.40),
}

INITDATA_MAX_AGE = 3600


# ================== قاعدة البيانات ==================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            photo_url   TEXT,
            balance     REAL DEFAULT 0,
            total_earn  REAL DEFAULT 0,
            referrals   INTEGER DEFAULT 0,
            referrer_id INTEGER,
            wallet      TEXT,
            language    TEXT DEFAULT 'ar',
            active_template TEXT DEFAULT 'lion_tired',
            created_at  INTEGER
        );
        CREATE TABLE IF NOT EXISTS completed_tasks (
            user_id  INTEGER,
            task_id  INTEGER,
            ts       INTEGER,
            PRIMARY KEY (user_id, task_id)
        );
        CREATE TABLE IF NOT EXISTS investments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            level        INTEGER,
            amount       REAL,
            payout       REAL,
            started_at   INTEGER,
            ends_at      INTEGER,
            claimed      INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS owned_templates (
            user_id      INTEGER,
            template_id  TEXT,
            acquired_at  INTEGER,
            PRIMARY KEY (user_id, template_id)
        );
        CREATE INDEX IF NOT EXISTS idx_inv_user ON investments(user_id);
        CREATE INDEX IF NOT EXISTS idx_own_user ON owned_templates(user_id);
        """)
        await db.commit()


async def ensure_default_template(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO owned_templates(user_id, template_id, acquired_at) VALUES(?,?,?)",
            (uid, "lion_tired", int(time.time())),
        )
        await db.commit()


async def get_or_create_user(user: dict, referrer_id: int | None = None):
    uid = user["id"]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, first_name=?, photo_url=? WHERE user_id=?",
                (user.get("username"), user.get("first_name"), user.get("photo_url"), uid),
            )
            await db.commit()
        else:
            if referrer_id and referrer_id != uid:
                cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (referrer_id,))
                if await cur.fetchone():
                    await db.execute(
                        "UPDATE users SET referrals = referrals + 1, balance = balance + 0.01 WHERE user_id=?",
                        (referrer_id,),
                    )
                else:
                    referrer_id = None
            await db.execute(
                """INSERT INTO users(user_id, username, first_name, photo_url, referrer_id, created_at)
                   VALUES(?,?,?,?,?,?)""",
                (uid, user.get("username"), user.get("first_name"),
                 user.get("photo_url"), referrer_id, int(time.time())),
            )
            await db.commit()
    await ensure_default_template(uid)


# ================== التحقق من initData ==================
def verify_init_data(init_data: str) -> dict:
    if not init_data:
        raise ValueError("empty initData")
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        raise ValueError("bad signature")
    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > INITDATA_MAX_AGE:
        raise ValueError("expired")
    return json.loads(pairs["user"])


def auth_middleware(handler):
    async def wrapper(request: web.Request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "bad json"}, status=400)
        try:
            user = verify_init_data(body.get("initData", ""))
        except Exception as e:
            return web.json_response({"error": f"unauthorized: {e}"}, status=401)
        request["tg_user"] = user
        request["body"] = body
        return await handler(request)
    return wrapper


# ================== API ==================
@auth_middleware
async def api_me(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT balance,total_earn,referrals,wallet,language,active_template FROM users WHERE user_id=?",
            (uid,),
        )
        b, te, r, w, lang, active = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM completed_tasks WHERE user_id=?", (uid,))
        (tasks_done,) = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*) FROM investments WHERE user_id=? AND claimed=0 AND ends_at>?",
            (uid, int(time.time())),
        )
        (active_inv,) = await cur.fetchone()
    return web.json_response({
        "balance": b, "totalEarnings": te, "referrals": r,
        "tasksCompleted": tasks_done, "activeInvestments": active_inv,
        "wallet": w, "language": lang or "ar", "activeTemplate": active or "lion_tired",
    })


@auth_middleware
async def api_set_language(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    lang = (request["body"].get("language") or "ar").lower()
    if lang not in ("ar", "en", "tr"):
        return web.json_response({"error": "invalid language"}, status=400)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user["id"]))
        await db.commit()
    return web.json_response({"success": True, "language": lang})


@auth_middleware
async def api_templates(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT template_id FROM owned_templates WHERE user_id=?", (uid,))
        owned = {row[0] for row in await cur.fetchall()}
        cur = await db.execute("SELECT active_template FROM users WHERE user_id=?", (uid,))
        (active,) = await cur.fetchone()
    items = []
    for t in TEMPLATES.values():
        t2 = dict(t)
        t2["owned"] = t["id"] in owned
        t2["active"] = t["id"] == active
        items.append(t2)
    return web.json_response({"items": items, "active": active})


@auth_middleware
async def api_buy_template(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    tid = request["body"].get("templateId")
    tpl = TEMPLATES.get(tid)
    if not tpl:
        return web.json_response({"error": "template not found"}, status=404)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM owned_templates WHERE user_id=? AND template_id=?", (uid, tid)
        )
        if await cur.fetchone():
            return web.json_response({"error": "already owned"}, status=400)
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        (bal,) = await cur.fetchone()
        if bal < tpl["price"]:
            return web.json_response({"error": "insufficient balance"}, status=400)
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (tpl["price"], uid))
        await db.execute(
            "INSERT INTO owned_templates(user_id, template_id, acquired_at) VALUES(?,?,?)",
            (uid, tid, int(time.time())),
        )
        await db.execute("UPDATE users SET active_template=? WHERE user_id=?", (tid, uid))
        await db.commit()
    return web.json_response({"success": True})


@auth_middleware
async def api_activate_template(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    tid = request["body"].get("templateId")
    if tid not in TEMPLATES:
        return web.json_response({"error": "template not found"}, status=404)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM owned_templates WHERE user_id=? AND template_id=?", (uid, tid)
        )
        if not await cur.fetchone():
            return web.json_response({"error": "not owned"}, status=400)
        await db.execute("UPDATE users SET active_template=? WHERE user_id=?", (tid, uid))
        await db.commit()
    return web.json_response({"success": True})


@auth_middleware
async def api_verify_task(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    task_id = int(request["body"].get("taskId", 0))
    channel = TASK_CHANNELS.get(task_id)
    if not channel:
        return web.json_response({"error": "task not found"}, status=400)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM completed_tasks WHERE user_id=? AND task_id=?", (uid, task_id)
        )
        if await cur.fetchone():
            return web.json_response({"error": "already done"}, status=400)
    try:
        member = await bot.get_chat_member(channel, uid)
        if member.status not in ("member", "administrator", "creator"):
            return web.json_response({"error": "not subscribed"}, status=400)
    except Exception as e:
        return web.json_response({"error": f"verify failed: {e}"}, status=400)
    reward = TASK_REWARDS[task_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO completed_tasks(user_id, task_id, ts) VALUES(?,?,?)",
            (uid, task_id, int(time.time())),
        )
        await db.execute(
            "UPDATE users SET balance=balance+?, total_earn=total_earn+? WHERE user_id=?",
            (reward, reward, uid),
        )
        await db.commit()
    return web.json_response({"success": True, "reward": reward})


@auth_middleware
async def api_invest(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    uid = user["id"]
    level = int(request["body"].get("level", 0))
    conf = INVEST_LEVELS.get(level)
    if not conf:
        return web.json_response({"error": "invalid level"}, status=400)
    amount, hours, rate = conf
    payout = round(amount * (1 + rate), 4)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        (bal,) = await cur.fetchone()
        if bal < amount:
            return web.json_response({"error": "insufficient balance"}, status=400)
        now = int(time.time())
        await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, uid))
        await db.execute(
            """INSERT INTO investments(user_id,level,amount,payout,started_at,ends_at)
               VALUES(?,?,?,?,?,?)""",
            (uid, level, amount, payout, now, now + hours * 3600),
        )
        await db.commit()
    return web.json_response({"success": True, "payout": payout, "endsAt": now + hours * 3600})


@auth_middleware
async def api_claim(request: web.Request):
    user = request["tg_user"]
    uid = user["id"]
    inv_id = int(request["body"].get("investmentId", 0))
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT payout,ends_at,claimed FROM investments WHERE id=? AND user_id=?",
            (inv_id, uid),
        )
        row = await cur.fetchone()
        if not row:
            return web.json_response({"error": "not found"}, status=404)
        payout, ends_at, claimed = row
        if claimed:
            return web.json_response({"error": "already claimed"}, status=400)
        if now < ends_at:
            return web.json_response({"error": "not finished"}, status=400)
        await db.execute("UPDATE investments SET claimed=1 WHERE id=?", (inv_id,))
        await db.execute(
            "UPDATE users SET balance=balance+?, total_earn=total_earn+? WHERE user_id=?",
            (payout, payout, uid),
        )
        await db.commit()
    return web.json_response({"success": True, "payout": payout})


@auth_middleware
async def api_investments(request: web.Request):
    user = request["tg_user"]
    uid = user["id"]
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT id,level,amount,payout,started_at,ends_at,claimed
               FROM investments WHERE user_id=? ORDER BY id DESC""",
            (uid,),
        )
        rows = await cur.fetchall()
    items = [{
        "id": r[0], "level": r[1], "amount": r[2], "payout": r[3],
        "startedAt": r[4], "endsAt": r[5], "claimed": bool(r[6]),
        "ready": (not r[6]) and now >= r[5],
    } for r in rows]
    return web.json_response({"items": items})


@auth_middleware
async def api_save_wallet(request: web.Request):
    user = request["tg_user"]
    await get_or_create_user(user)
    addr = (request["body"].get("address") or "").strip()
    if not (addr.startswith(("EQ", "UQ", "EQC", "0:")) and len(addr) >= 20):
        return web.json_response({"error": "invalid address"}, status=400)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET wallet=? WHERE user_id=?", (addr, user["id"]))
        await db.commit()
    return web.json_response({"success": True})


@auth_middleware
async def api_unlink_wallet(request: web.Request):
    user = request["tg_user"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET wallet=NULL WHERE user_id=?", (user["id"],))
        await db.commit()
    return web.json_response({"success": True})


@auth_middleware
async def api_config(request: web.Request):
    return web.json_response({
        "support": SUPPORT_URL,
        "tonWallet": TON_WALLET,
        "tasks": [
            {"id": 1, "channel": TASK_CHANNELS[1], "reward": TASK_REWARDS[1]},
            {"id": 2, "channel": TASK_CHANNELS[2], "reward": TASK_REWARDS[2]},
        ],
        "levels": [
            {"level": k, "price": v[0], "hours": v[1], "rate": v[2]}
            for k, v in INVEST_LEVELS.items()
        ],
    })


# ================== البوت ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(maxsplit=1)
    ref = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref = int(args[1][4:])
        except ValueError:
            ref = None
    await get_or_create_user({
        "id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "photo_url": None,
    }, referrer_id=ref)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🦁 فتح LION MAX", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "🦁 <b>LION MAX</b>\n"
        "━━━━━━━━━━━━━━\n"
        "👑 من أسد هزيل... إلى ملك الغابة\n\n"
        "🍖 أطعم أسدك\n"
        "📈 استثمر أرباحك\n"
        "🛒 اشترِ قوالب أقوى\n"
        "🎁 اجمع المكافآت\n\n"
        "اضغط الزر لتبدأ رحلتك:",
        reply_markup=kb,
        parse_mode="HTML",
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), SUM(balance), SUM(total_earn) FROM users")
        cnt, total_bal, total_earn = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM owned_templates")
        (owned,) = await cur.fetchone()
    await message.answer(
        f"📊 <b>LION MAX — Admin</b>\n\n"
        f"👥 المستخدمون: {cnt or 0}\n"
        f"💰 مجموع الأرصدة: {(total_bal or 0):.4f} TON\n"
        f"📈 مجموع الأرباح: {(total_earn or 0):.4f} TON\n"
        f"🦁 القوالب المملوكة: {owned or 0}\n\n"
        f"💳 محفظة: <code>{TON_WALLET}</code>",
        parse_mode="HTML",
    )


# ================== Web Server ==================
def make_app():
    app = web.Application()
    app.router.add_post("/api/me", api_me)
    app.router.add_post("/api/language", api_set_language)
    app.router.add_post("/api/templates", api_templates)
    app.router.add_post("/api/templates/buy", api_buy_template)
    app.router.add_post("/api/templates/activate", api_activate_template)
    app.router.add_post("/api/verify-task", api_verify_task)
    app.router.add_post("/api/invest", api_invest)
    app.router.add_post("/api/claim", api_claim)
    app.router.add_post("/api/investments", api_investments)
    app.router.add_post("/api/wallet", api_save_wallet)
    app.router.add_delete("/api/wallet", api_unlink_wallet)
    app.router.add_post("/api/config", api_config)
    app.router.add_get("/", lambda r: web.FileResponse("index.html"))
    return app


async def main():
    await init_db()
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"✅ LION MAX API على http://{HOST}:{PORT}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
