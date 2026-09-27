import logging
import sqlite3
import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    WebAppInfo,
    LabeledPrice
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters
)

# ---------------------------------------------------------
# الإعدادات الرئيسية
# ---------------------------------------------------------
TOKEN = "8307817242:AAFXPfxIENWJU7jNq5ReHbky_pPspks20j0"
ADMIN_ID = 8183652969  # Telegram ID الخاص بالأدمن الحصري
BOT_NAME = "GRAM MAX"
SUPPORT_USERNAME = "@FastHelp3"
MINI_APP_URL = "https://crypto-max-app-hpau.onrender.com"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# تهيئة وتحديث قاعدة البيانات الموحدة SQLite
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # جدول المستخدمين المطور
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        language TEXT DEFAULT 'ar',
        balance REAL DEFAULT 0.0,
        profit_balance REAL DEFAULT 0.0,
        ref_balance REAL DEFAULT 0.0,
        wallet_address TEXT DEFAULT NULL,
        referred_by INTEGER DEFAULT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول الإيداعات المطور
    cursor.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        currency TEXT DEFAULT 'TON',
        wallet_address TEXT,
        tx_hash TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'PENDING'
    )''')

    # جدول طلبات السحب المطور
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        fee REAL DEFAULT 0.0,
        net_amount REAL,
        wallet_address TEXT,
        tx_hash TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'PENDING'
    )''')

    # جدول الاستثمارات الحالية
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        level INTEGER,
        amount REAL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول المدفوعات عبر Telegram Stars
    cursor.execute('''CREATE TABLE IF NOT EXISTS star_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        stars_amount INTEGER,
        telegram_charge_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول سجل العمليات المالية
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول إعدادات النظام والإشعارات
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # الإعدادات الافتراضية للإشعارات
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notify_new_user', '1')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notify_deposit', '1')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notify_withdraw', '1')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notify_wallet', '1')")

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# مساعدات الإشعارات والأدوات
# ---------------------------------------------------------
def log_action(user_id, action, details):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else '1'

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ---------------------------------------------------------
# لوحة المفاتيح والترحيب (/start)
# ---------------------------------------------------------
def get_main_reply_keyboard(user_id: int):
    keyboard = [
        ["🏠 الرئيسية", "⭐ Stars"],
        ["📈 الاستثمار", "📋 المهام"],
        ["💳 ربط المحفظة", "💸 السحب"],
        ["👥 الإحالات", "👤 الملف الشخصي"],
        ["🌐 اختيار اللغة", "⚙️ الإعدادات"]
    ]
    if is_admin(user_id):
        keyboard.append(["👑 لوحة الإدارة"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_welcome_inline_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 فتح التطبيق", web_app=WebAppInfo(url=MINI_APP_URL)),
            InlineKeyboardButton("⭐ Stars", callback_data="show_stars_menu")
        ],
        [
            InlineKeyboardButton("💰 الرصيد", callback_data="user_balance_info"),
            InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="user_referral_info")
        ],
        [
            InlineKeyboardButton("📋 المهام", callback_data="user_tasks_info"),
            InlineKeyboardButton("🎁 المكافآت", callback_data="user_bonuses_info")
        ],
        [
            InlineKeyboardButton("📜 الشروط والأحكام", callback_data="user_terms_info"),
            InlineKeyboardButton("🆘 الدعم", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or ""
    username = user.username or ""

    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_db = cursor.fetchone()

    is_new_user = False
    if not user_db:
        is_new_user = True
        cursor.execute(
            "INSERT INTO users (user_id, first_name, username, referred_by) VALUES (?, ?, ?, ?)",
            (user_id, first_name, username, referrer_id)
        )
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET ref_balance = ref_balance + 0.1, balance = balance + 0.1 WHERE user_id = ?", (referrer_id,))
            log_action(referrer_id, "REFERRAL_BONUS", f"New referral bonus from user {user_id}")
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text="🎉 انضم مستخدم جديد عبر رابط الإحالة الخاص بك! حصلت على 0.1 GRAM"
                )
            except Exception:
                pass
        conn.commit()
    conn.close()

    if is_new_user and get_setting('notify_new_user') == '1':
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"👤 **مستخدم جديد انضم للبوت!**\n\n🆔 Telegram ID: `{user_id}`\n👨 الاسم: {first_name}\n🔗 Username: @{username if username else 'بدون'}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    welcome_text = (
        f"👋 أهلاً بك في {BOT_NAME}!\n\n"
        "🚀 مرحبًا بك في عالم المكافآت والمهام والألعاب.\n\n"
        "من خلال البوت يمكنك الوصول إلى:\n\n"
        "💰 الرصيد\n"
        "📱 التطبيق المصغر\n"
        "🎁 المكافآت\n"
        "👥 دعوة الأصدقاء\n"
        "📋 المهام\n"
        "⭐ Telegram Stars\n"
        "💸 السحب\n"
        "🆘 الدعم\n\n"
        "ابدأ الآن واستكشف جميع الأقسام المتاحة لك.\n\n"
        "⚠️ تذكير:\n"
        "استخدم الخدمة وفق الشروط والأحكام، ولا تشارك أبدًا كلمة مرور Telegram أو رمز تسجيل الدخول أو عبارة استرداد محفظتك مع أي شخص."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_reply_keyboard(user_id)
    )
    await update.message.reply_text(
        "اختر من القائمة أدناه للبدء السريع:",
        reply_markup=get_welcome_inline_keyboard()
    )

# ---------------------------------------------------------
# ⭐ قسم Telegram Stars الرسمية
# ---------------------------------------------------------
def get_stars_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ 10 Stars", callback_data="buy_stars_10"), InlineKeyboardButton("⭐ 25 Stars", callback_data="buy_stars_25")],
        [InlineKeyboardButton("⭐ 50 Stars", callback_data="buy_stars_50"), InlineKeyboardButton("⭐ 100 Stars", callback_data="buy_stars_100")],
        [InlineKeyboardButton("⭐ 250 Stars", callback_data="buy_stars_250"), InlineKeyboardButton("⭐ 500 Stars", callback_data="buy_stars_500")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_stars_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "⭐ **Telegram Stars**\n\nاختر الباقة المناسبة لشراء النجوم ودعم الحساب رسميًا:"
    if update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=get_stars_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=get_stars_keyboard(), parse_mode="Markdown")

async def buy_stars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stars_amount = int(query.data.split("_")[2])

    title = f"شراء {stars_amount} Telegram Stars"
    description = f"باقة شحن {stars_amount} نجوم تليجرام الرسمية لحسابك."
    payload = f"stars_purchase_{query.from_user.id}_{stars_amount}"
    currency = "XTR"
    prices = [LabeledPrice(f"{stars_amount} Stars", stars_amount)]

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # فارغ دائماً للعملة الرسمية XTR
        currency=currency,
        prices=prices
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    telegram_charge_id = payment.telegram_payment_charge_id
    stars_amount = payment.total_amount

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM star_payments WHERE telegram_charge_id = ?", (telegram_charge_id,))
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute(
        "INSERT INTO star_payments (user_id, stars_amount, telegram_charge_id) VALUES (?, ?, ?)",
        (user_id, stars_amount, telegram_charge_id)
    )
    # إضافة مكافأة الرصيد بموجب شراء النجوم
    bonus_gram = stars_amount * 0.1
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus_gram, user_id))
    conn.commit()
    conn.close()

    log_action(user_id, "BUY_STARS", f"Bought {stars_amount} stars. Charge ID: {telegram_charge_id}")

    success_msg = f"✅ تمت عملية الدفع بنجاح\n\n⭐ Stars:\n{stars_amount}\n\nشكرًا لك ❤️"
    await update.message.reply_text(success_msg)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⭐ **عملية شراء جديدة Stars!**\n\n👤 المستخدم: @{update.effective_user.username or user_id}\n🆔 ID: `{user_id}`\n⭐ عدد النجوم: {stars_amount}\n💳 Charge ID: `{telegram_charge_id}`",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ---------------------------------------------------------
# 👑 لوحة التحكم والإدارة — ADMIN PANEL
# ---------------------------------------------------------
def get_admin_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users"), InlineKeyboardButton("💰 الإيداعات", callback_data="admin_deposits")],
        [InlineKeyboardButton("💸 طلبات السحب", callback_data="admin_withdraws"), InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 المكافآت", callback_data="admin_bonuses"), InlineKeyboardButton("👥 الإحالات", callback_data="admin_referrals")],
        [InlineKeyboardButton("📋 المهام", callback_data="admin_tasks"), InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings")],
        [InlineKeyboardButton("📢 إرسال إشعار", callback_data="admin_broadcast"), InlineKeyboardButton("📜 سجل العمليات", callback_data="admin_logs")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    await update.message.reply_text(
        "👑 **لوحة الإدارة - ADMIN PANEL**\n\nمرحباً بك في وحدة التحكم الكاملة بالبوت:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

# --- قسم المستخدمين ---
async def admin_users_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'ACTIVE'")
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-1 day')")
    new_users = cursor.fetchone()[0]

    conn.close()

    text = (
        "👥 **قسم إدارة المستخدمين**\n\n"
        f"📊 إجمالي المستخدمين: {total_users}\n"
        f"🟢 المستخدمون النشطون: {active_users}\n"
        f"🆕 المستخدمون الجدد (24h): {new_users}\n\n"
        "للبحث عن مستخدم معيّن، أرسل أمره كالتالي:\n"
        "`/find ID` أو `/find @username`"
    )
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="admin_main")]])
    await query.edit_message_text(text, reply_markup=btn, parse_mode="Markdown")

async def admin_find_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("⚠️ يرجى إدخال ID أو Username كالتالي:\n`/find 8183652969`", parse_mode="Markdown")
        return

    search_term = context.args[0].replace("@", "")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if search_term.isdigit():
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (int(search_term),))
    else:
        cursor.execute("SELECT * FROM users WHERE username = ?", (search_term,))

    u = cursor.fetchone()
    conn.close()

    if not u:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم المطلوب.")
        return

    # u: user_id, first_name, username, language, balance, profit_balance, ref_balance, wallet_address, referred_by, status, created_at
    msg = (
        f"👤 **بيانات المستخدم التفصيلية:**\n\n"
        f"🆔 ID: `{u[0]}`\n"
        f"👨 الاسم: {u[1]}\n"
        f"🔗 Username: @{u[2] if u[2] else 'بدون'}\n"
        f"💰 الرصيد الرئيسي: `{u[4]:.2f} GRAM`\n"
        f"💎 رصيد الأرباح: `{u[5]:.2f} GRAM`\n"
        f"👥 رصيد الإحالات: `{u[6]:.2f} GRAM`\n"
        f"💼 المحفظة: `{u[7] if u[7] else 'غير مرتبطة'}`\n"
        f"📅 تاريخ التسجيل: {u[10]}\n"
        f"📊 حالة الحساب: **{u[9]}**"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة رصيد", callback_data=f"usr_add_{u[0]}"), InlineKeyboardButton("➖ خصم رصيد", callback_data=f"usr_sub_{u[0]}")],
        [InlineKeyboardButton("🚫 تجميد الحساب" if u[9] == 'ACTIVE' else "🔓 إلغاء التجميد", callback_data=f"usr_toggle_{u[0]}")],
        [InlineKeyboardButton("📜 سجل العمليات", callback_data=f"usr_logs_{u[0]}")],
        [InlineKeyboardButton("🔙 العودة", callback_data="admin_users")]
    ])
    await update.message.reply_text(msg, reply_markup=btn, parse_mode="Markdown")

# --- قسم الإيداعات ---
async def admin_deposits_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, currency, status, created_at FROM deposits ORDER BY id DESC LIMIT 10")
    deps = cursor.fetchall()
    conn.close()

    text = "💰 **سجل الإيداعات الأخيرة:**\n\n"
    if not deps:
        text += "لا توجد عمليات إيداع مسجلة."
    else:
        for d in deps:
            text += f"🆔 #{d[0]} | المستخدم: `{d[1]}` | المبلغ: {d[2]} {d[3]} | الحالة: {d[4]} | {d[5]}\n"

    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="admin_main")]])
    await query.edit_message_text(text, reply_markup=btn, parse_mode="Markdown")

# --- قسم طلبات السحب ---
async def admin_withdraws_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, net_amount, status, created_at FROM withdraw_requests ORDER BY id DESC LIMIT 10")
    wths = cursor.fetchall()
    conn.close()

    text = "💸 **سجل طلبات السحب الأخيرة:**\n\n"
    if not wths:
        text += "لا توجد طلبات سحب مسجلة."
    else:
        for w in wths:
            text += f"🆔 #{w[0]} | المستخدم: `{w[1]}` | الصافي: {w[3]} TON | الحالة: {w[4]} | {w[5]}\n"

    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="admin_main")]])
    await query.edit_message_text(text, reply_markup=btn, parse_mode="Markdown")

# --- معالجة الإيداعات والتأكيدات للأدمن ---
async def handle_deposit_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, dep_id = data[1], int(data[2])

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, currency, tx_hash, status FROM deposits WHERE id = ?", (dep_id,))
    dep = cursor.fetchone()

    if not dep:
        conn.close()
        await query.edit_message_text("❌ لم يتم العثور على العملية.")
        return

    user_id, amount, currency, tx_hash, status = dep

    if status != 'PENDING':
        conn.close()
        await query.edit_message_text(f"⚠️ تمت معالجة هذه العملية مسبقاً (الحالة: {status}).")
        return

    if action == "confirm":
        cursor.execute("UPDATE deposits SET status = 'COMPLETED' WHERE id = ?", (dep_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        log_action(user_id, "DEPOSIT_CONFIRMED", f"Deposit #{dep_id} of {amount} {currency} confirmed.")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **تم تأكيد الإيداع**\n\n💰 المبلغ:\n{amount} {currency}\n\nتمت إضافة المبلغ إلى رصيدك بنجاح."
            )
        except Exception:
            pass
        await query.edit_message_text(f"✅ تم تأكيد الإيداع #{dep_id} وتحديث رصيد المستخدم بنجاح.")

    elif action == "reject":
        cursor.execute("UPDATE deposits SET status = 'REJECTED' WHERE id = ?", (dep_id,))
        conn.commit()
        log_action(user_id, "DEPOSIT_REJECTED", f"Deposit #{dep_id} rejected.")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ **تم رفض الإيداع**\n\n💰 المبلغ:\n{amount} {currency}\n\nيرجى التواصل مع الدعم إذا كنت تعتقد أن هناك خطأ."
            )
        except Exception:
            pass
        await query.edit_message_text(f"❌ تم رفض الإيداع #{dep_id}.")

    conn.close()

# --- معالجة طلبات السحب للأدمن ---
async def handle_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, req_id = data[1], int(data[2])

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, fee, net_amount, wallet_address, status FROM withdraw_requests WHERE id = ?", (req_id,))
    req = cursor.fetchone()

    if not req:
        conn.close()
        await query.edit_message_text("❌ لم يتم العثور على الطلب.")
        return

    user_id, amount, fee, net_amount, wallet, status = req

    if status != 'PENDING':
        conn.close()
        await query.edit_message_text(f"⚠️ تمت معالجة هذا الطلب مسبقاً (الحالة: {status}).")
        return

    if action == "approve":
        tx_hash = f"tx_ton_{int(datetime.datetime.now().timestamp())}"
        cursor.execute("UPDATE withdraw_requests SET status = 'PAID', tx_hash = ? WHERE id = ?", (tx_hash, req_id))
        conn.commit()
        log_action(user_id, "WITHDRAW_APPROVED", f"Withdraw #{req_id} approved.")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **تم تنفيذ طلب السحب**\n\n💰 المبلغ:\n{amount}\n\n💸 الرسوم:\n{fee}\n\n💵 المبلغ المرسل:\n{net_amount}\n\n💼 المحفظة:\n{wallet}\n\n🔗 Transaction:\n`{tx_hash}`\n\nشكرًا لاستخدامك البوت.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(f"✅ تمت الموافقة على السحب #{req_id} وإرسال الإشعار للمستخدم.")

    elif action == "reject":
        cursor.execute("UPDATE withdraw_requests SET status = 'REJECTED' WHERE id = ?", (req_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        log_action(user_id, "WITHDRAW_REJECTED", f"Withdraw #{req_id} rejected & amount refunded.")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ **تم رفض طلب السحب**\n\n💰 المبلغ:\n{amount}\n\nيرجى التواصل مع الدعم لمعرفة السبب."
            )
        except Exception:
            pass
        await query.edit_message_text(f"❌ تم رفض السحب #{req_id} وإعادة المبلغ لحساب المستخدم.")

    conn.close()

# --- إعدادات وتنشيط الإشعارات ---
async def admin_settings_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    n_user = "🟢" if get_setting('notify_new_user') == '1' else "🔴"
    n_dep = "🟢" if get_setting('notify_deposit') == '1' else "🔴"
    n_wth = "🟢" if get_setting('notify_withdraw') == '1' else "🔴"
    n_wall = "🟢" if get_setting('notify_wallet') == '1' else "🔴"

    msg = (
        "⚙️ **إعدادات إشعارات الأدمن التلقائية:**\n\n"
        f"{n_user} إشعار مستخدم جديد\n"
        f"{n_dep} إشعار إيداع جديد\n"
        f"{n_wth} إشعار طلب سحب\n"
        f"{n_wall} إشعار ربط محفظة"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{n_user} مستخدم جديد", callback_data="toggle_setting_notify_new_user")],
        [InlineKeyboardButton(f"{n_dep} إيداع جديد", callback_data="toggle_setting_notify_deposit")],
        [InlineKeyboardButton(f"{n_wth} طلب سحب", callback_data="toggle_setting_notify_withdraw")],
        [InlineKeyboardButton(f"{n_wall} ربط محفظة", callback_data="toggle_setting_notify_wallet")],
        [InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="admin_main")]
    ])
    await query.edit_message_text(msg, reply_markup=btn, parse_mode="Markdown")

async def toggle_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    key = query.data.replace("toggle_setting_", "")
    current = get_setting(key)
    new_val = '0' if current == '1' else '1'

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, key))
    conn.commit()
    conn.close()

    await admin_settings_view(update, context)

# ---------------------------------------------------------
# معالجة رسائل وأزرار المستخدم والربط المالي
# ---------------------------------------------------------
async def handle_user_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username or ""

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    # التحقق من تجميد الحساب
    if user[9] == 'FROZEN':
        conn.close()
        await update.message.reply_text("🚫 حسابك مجمد حالياً. يرجى التواصل مع الدعم الفني.")
        return

    balance, profit_balance, ref_balance, wallet = user[4], user[5], user[6], user[7]

    # 1. 👤 الملف الشخصي
    if text == "👤 الملف الشخصي":
        wallet_text = wallet if wallet else "غير مرتبطة"
        msg = f"👤 **الملف الشخصي**\n\n🆔 المعرف: `{user_id}`\n💰 الرصيد الرئيسي: **{balance:.2f} GRAM**\n💎 الأرباح: **{profit_balance:.2f} GRAM**\n👥 رصيد الإحالات: **{ref_balance:.2f} GRAM**\n💼 المحفظة: `{wallet_text}`"
        await update.message.reply_text(msg, parse_mode="Markdown")

    # 2. 👥 الإحالات
    elif text == "👥 الإحالات":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        msg = f"👥 **نظام الإحالات**\n\nقم بدعوة أصدقائك واحصل على عمولات مجزية:\n• 0.1 GRAM لكل إحالة مباشرة\n• 10% من أرباح أصدقائك الاستثمارية\n\nرابط الإحالة الخاص بك:\n`{ref_link}`"
        await update.message.reply_text(msg, parse_mode="Markdown")

    # 3. 💳 ربط المحفظة
    elif text == "💳 ربط المحفظة":
        await update.message.reply_text("أرسل عنوان محفظة TON الخاصة بك الآن (مثال: `EQ...` أو `UQ...`):", parse_mode="Markdown")

    elif text.startswith("EQ") or text.startswith("UQ") or (len(text) > 30 and not text.startswith("/")):
        cursor.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (text.strip(), user_id))
        conn.commit()
        log_action(user_id, "LINK_WALLET", f"Linked wallet: {text.strip()}")
        await update.message.reply_text(f"✅ تم حفظ عنوان المحفظة بنجاح:\n`{text.strip()}`", parse_mode="Markdown")

        if get_setting('notify_wallet') == '1':
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🔗 **ربط محفظة جديد!**\n\n👤 المستخدم: @{username or user_id}\n🆔 ID: `{user_id}`\n💼 المحفظة: `{text.strip()}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # 4. 📈 الاستثمار
    elif text == "📈 الاستثمار":
        cursor.execute("SELECT * FROM investments WHERE user_id = ? AND status = 'ACTIVE'", (user_id,))
        if cursor.fetchone():
            await update.message.reply_text("🔒 لديك خطة استثمارية نشطة حالياً. انتظر حتى انتهائها لبدء خطة جديدة.")
        else:
            keyboard = [
                [InlineKeyboardButton("المستوى 1 (1 GRAM / 12h)", callback_data="invest_1")],
                [InlineKeyboardButton("المستوى 2 (2 GRAM / 24h)", callback_data="invest_2")],
                [InlineKeyboardButton("المستوى 3 (5 GRAM / 48h)", callback_data="invest_3")]
            ]
            await update.message.reply_text("💰 **خطط الاستثمار المتاحة:**\n\nاختر المستوى المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # 5. 💸 السحب
    elif text == "💸 السحب":
        if not wallet:
            await update.message.reply_text("⚠️ لم تقم بربط محفظتك بعد! اضغط على (💳 ربط المحفظة) أولاً.")
        elif balance <= 0:
            await update.message.reply_text("❌ رصيدك غير كافٍ لإتمام عملية السحب.")
        else:
            fee = 0.05
            net_amount = max(0.0, balance - fee)
            
            cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
            cursor.execute(
                "INSERT INTO withdraw_requests (user_id, amount, fee, net_amount, wallet_address) VALUES (?, ?, ?, ?, ?)",
                (user_id, balance, fee, net_amount, wallet)
            )
            conn.commit()
            req_id = cursor.lastrowid
            log_action(user_id, "WITHDRAW_REQUEST", f"Withdraw request #{req_id} for {balance} GRAM")

            await update.message.reply_text("✅ تم تسجيل طلب السحب بنجاح وسيتم مراجعته من الإدارة.")

            if get_setting('notify_withdraw') == '1':
                admin_btn = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ الموافقة على السحب", callback_data=f"wth_approve_{req_id}"),
                        InlineKeyboardButton("❌ رفض السحب", callback_data=f"wth_reject_{req_id}")
                    ]
                ])
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                admin_msg = (
                    f"🚨 **طلب سحب جديد**\n\n"
                    f"👤 المستخدم:\n@{username if username else user_id}\n\n"
                    f"🆔 Telegram ID:\n`{user_id}`\n\n"
                    f"💰 المبلغ المطلوب:\n{balance:.2f} GRAM\n\n"
                    f"💸 رسوم السحب:\n{fee} TON\n\n"
                    f"💵 صافي المبلغ:\n{net_amount:.2f} TON\n\n"
                    f"💼 محفظة TON:\n`{wallet}`\n\n"
                    f"🕐 الوقت:\n{now_str}\n\n"
                    f"📊 الحالة:\n⏳ قيد المراجعة"
                )
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown", reply_markup=admin_btn)
                except Exception:
                    pass

    # 6. ⭐ Stars
    elif text == "⭐ Stars":
        await send_stars_menu(update, context)

    # 7. 👑 لوحة الإدارة
    elif text == "👑 لوحة الإدارة" and is_admin(user_id):
        await admin_panel_command(update, context)

    # 8. 📋 المهام و باقي القوائم
    elif text == "📋 المهام":
        await update.message.reply_text("📋 **المهام المتاحة:**\n\nانضم إلى القناة الرسمية لتحصل على +0.1 GRAM مجاناً.")

    elif text in ["⚙️ الإعدادات", "🌐 اختيار اللغة"]:
        support_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
        ])
        await update.message.reply_text(f"⚙️ **الإعدادات والدعم الفني:**\n\nللتواصل المباشر مع الدعم: {SUPPORT_USERNAME}", reply_markup=support_btn, parse_mode="Markdown")

    elif text == "🏠 الرئيسية":
        await start(update, context)

    conn.close()

# ---------------------------------------------------------
# الموجه العام للأزرار التفاعلية Callbacks
# ---------------------------------------------------------
async def global_callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "admin_main":
        await query.edit_message_text("👑 **لوحة الإدارة - ADMIN PANEL**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
    elif data == "admin_users":
        await admin_users_view(update, context)
    elif data == "admin_deposits":
        await admin_deposits_view(update, context)
    elif data == "admin_withdraws":
        await admin_withdraws_view(update, context)
    elif data == "admin_settings":
        await admin_settings_view(update, context)
    elif data.startswith("toggle_setting_"):
        await toggle_setting_callback(update, context)
    elif data.startswith("dep_"):
        await handle_deposit_action(update, context)
    elif data.startswith("wth_"):
        await handle_withdraw_action(update, context)
    elif data == "show_stars_menu":
        await send_stars_menu(update, context)
    elif data.startswith("buy_stars_"):
        await buy_stars_callback(update, context)
    elif data == "user_balance_info":
        await query.answer("زر الرصيد: استخدم القائمة الرئيسية أو افتح Mini App.", show_alert=True)
    elif data == "user_referral_info":
        await query.answer("زر الإحالات: شارك البوت مع أصدقائك برابطك المباشر.", show_alert=True)
    else:
        await query.answer()

# ---------------------------------------------------------
# نقطة تشغيل التطبيق الرئيسية
# ---------------------------------------------------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # الأوامر الرئيسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel_command))
    app.add_handler(CommandHandler("find", admin_find_user))

    # أزرار ومعاملات Telegram Stars
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # استقبال الرسائل والأزرار التفاعلية
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_text_messages))
    app.add_handler(CallbackQueryHandler(global_callback_query_handler))

    logger.info("تم تشغيل البوت ولوحة التحكم بنجاح...")
    app.run_polling()
