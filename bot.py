import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ---------------------------------------------------------
# الإعدادات الرئيسية
# ---------------------------------------------------------
TOKEN = "8307817242:AAFXPfxIENWJU7jNq5ReHbky_pPspks20j0"
ADMIN_ID = 8183652969
SUPPORT_USERNAME = "@FastHelp3"

# ---------------------------------------------------------
# تهيئة قاعدة البيانات SQLite
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        language TEXT DEFAULT 'ar',
        balance REAL DEFAULT 0.0,
        wallet_address TEXT DEFAULT NULL,
        referred_by INTEGER DEFAULT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        wallet_address TEXT,
        status TEXT DEFAULT 'PENDING'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        level INTEGER,
        amount REAL,
        status TEXT DEFAULT 'ACTIVE'
    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# لوحة التحكم الرئيسية (الأزرار الأساسية)
# ---------------------------------------------------------
def get_main_keyboard():
    keyboard = [
        ["🏠 الرئيسية", "⭐ Star"],
        ["📈 الاستثمار", "📋 المهام"],
        ["💳 ربط المحفظة", "💸 السحب"],
        ["👥 الإحالات", "👤 الملف الشخصي"],
        ["🌐 اختيار اللغة", "⚙️ الإعدادات"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------------------------------------------------
# أمر البداية /start
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username or ""
    
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, username, referred_by) VALUES (?, ?, ?, ?)", 
                       (user_id, first_name, username, referrer_id))
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET balance = balance + 0.1 WHERE user_id = ?", (referrer_id,))
            try:
                await context.bot.send_message(
                    chat_id=referrer_id, 
                    text="🎉 انضم مستخدم جديد عبر رابط الإحالة الخاص بك! حصلت على 0.1 GRAM"
                )
            except Exception:
                pass
        conn.commit()

    conn.close()

    # زر شفاف لفتح Mini App
    miniapp_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 فتح التطبيق المصغر", web_app=WebAppInfo(url="https://crypto-max-app-hpau.onrender.com"))]
    ])

    await update.message.reply_text(
        "أهلاً بك في بوت GRAM MAX! 🚀\nيمكنك استخدام الأزرار أدناه أو فتح التطبيق المصغر مباشرة:",
        reply_markup=get_main_keyboard()
    )
    await update.message.reply_text(
        "اضغط أدناه لفتح واجهة GRAM MAX المصغرة:",
        reply_markup=miniapp_keyboard
    )

# ---------------------------------------------------------
# معالجة الرسائل والقوائم
# ---------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, username) VALUES (?, ?, ?)", 
                       (user_id, update.effective_user.first_name, update.effective_user.username or ""))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    balance = user[4] if user else 0.0
    wallet = user[5] if user else None

    # 1. 👤 الملف الشخصي
    if text == "👤 الملف الشخصي":
        wallet_text = wallet if wallet else "غير مرتبطة"
        msg = f"👤 **الملف الشخصي**\n\n🆔 المعرف: `{user_id}`\n💰 الرصيد: **{balance:.2f} GRAM**\n💳 المحفظة: `{wallet_text}`"
        await update.message.reply_text(msg, parse_mode="Markdown")

    # 2. 👥 الإحالات
    elif text == "👥 الإحالات":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        msg = f"👥 **نظام الإحالات**\n\nقم بدعوة أصدقائك واحصل على عمولات مجزية:\n• المستوى 1: 5%\n• المستوى 2: 3%\n• المستوى 3: 2%\n\nرابط الإحالة الخاص بك:\n`{ref_link}`"
        await update.message.reply_text(msg, parse_mode="Markdown")

    # 3. 💳 ربط المحفظة
    elif text == "💳 ربط المحفظة":
        await update.message.reply_text("أرسل عنوان محفظة TON الخاصة بك الآن (مثال: `EQ...` أو `UQ...`):", parse_mode="Markdown")

    elif text.startswith("EQ") or text.startswith("UQ") or (len(text) > 30 and not text.startswith("/")):
        cursor.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (text.strip(), user_id))
        conn.commit()
        await update.message.reply_text(f"✅ تم حفظ عنوان المحفظة بنجاح:\n`{text.strip()}`", parse_mode="Markdown")

    # 4. 📈 الاستثمار
    elif text == "📈 الاستثمار":
        cursor.execute("SELECT * FROM investments WHERE user_id = ? AND status = 'ACTIVE'", (user_id,))
        active_inv = cursor.fetchone()
        if active_inv:
            await update.message.reply_text("🔒 لا يمكن بدء استثمار جديد إلا بعد انتهاء الاستثمار السابق.")
        else:
            keyboard = [
                [InlineKeyboardButton("المستوى 1 (1 GRAM / 12h)", callback_data="invest_1")],
                [InlineKeyboardButton("المستوى 2 (2 GRAM / 24h)", callback_data="invest_2")],
                [InlineKeyboardButton("المستوى 3 (5 GRAM / 48h)", callback_data="invest_3")],
                [InlineKeyboardButton("المستوى 4 (7 GRAM / 72h)", callback_data="invest_4")],
                [InlineKeyboardButton("المستوى 5 (10 GRAM / 120h)", callback_data="invest_5")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💰 **خطط الاستثمار المتاحة:**\n\nاختر المستوى الذي يناسبك للبدء:", reply_markup=reply_markup, parse_mode="Markdown")

    # 5. 💸 السحب
    elif text == "💸 السحب":
        if not wallet:
            await update.message.reply_text("⚠️ لم تقم بربط محفظتك بعد! اضغط على (💳 ربط المحفظة) أولاً.")
        elif balance <= 0:
            await update.message.reply_text("❌ رصيدك غير كافٍ لإتمام عملية السحب.")
        else:
            cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
            cursor.execute("INSERT INTO withdraw_requests (user_id, amount, wallet_address) VALUES (?, ?, ?)", 
                           (user_id, balance, wallet))
            conn.commit()
            req_id = cursor.lastrowid
            
            await update.message.reply_text("✅ تم تسجيل طلب السحب بنجاح وسيتم مراجعته من الإدارة.")
            
            # إرسال إشعار للأدمن
            admin_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{req_id}"),
                 InlineKeyboardButton("❌ رفض وإعادة الرصيد", callback_data=f"reject_{req_id}")]
            ])
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 **طلب سحب جديد #{req_id}**\n\nالمستخدم: {update.effective_user.first_name} (`{user_id}`)\nالمبلغ: **{balance:.2f} GRAM**\nالمحفظة: `{wallet}`",
                parse_mode="Markdown",
                reply_markup=admin_btn
            )

    # 6. 📋 المهام
    elif text == "📋 المهام":
        await update.message.reply_text("📋 **المهام المتاحة:**\n\nلا توجد مهام متاحة حالياً، يرجى المتابعة لاحقاً.")

    # 7. ⭐ Star
    elif text == "⭐ Star":
        await update.message.reply_text("⭐ **شراء نجوم Telegram Stars**\n\nيمكنك دعم البوت أو الشراء من خلال Telegram Stars الرسمية.")

    # 8. ⚙️ الإعدادات والدعم الفني
    elif text in ["⚙️ الإعدادات", "🌐 اختيار اللغة"]:
        support_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
        ])
        await update.message.reply_text(f"⚙️ **الإعدادات والتواصل:**\n\nللتواصل مع الدعم الفني: {SUPPORT_USERNAME}", reply_markup=support_btn, parse_mode="Markdown")

    elif text == "🏠 الرئيسية":
        await update.message.reply_text("أهلاً بك في الرئيسية!", reply_markup=get_main_keyboard())

    conn.close()

# ---------------------------------------------------------
# معالجة الأزرار التفاعلية (Callback Query)
# ---------------------------------------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if data.startswith("approve_"):
        req_id = data.split("_")[1]
        cursor.execute("UPDATE withdraw_requests SET status = 'APPROVED' WHERE id = ?", (req_id,))
        conn.commit()
        await query.edit_message_text(f"✅ **تمت الموافقة على الطلب #{req_id}**", parse_mode="Markdown")

    elif data.startswith("reject_"):
        req_id = data.split("_")[1]
        cursor.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (req_id,))
        req = cursor.fetchone()
        if req:
            u_id, amt = req
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, u_id))
            cursor.execute("UPDATE withdraw_requests SET status = 'REJECTED' WHERE id = ?", (req_id,))
            conn.commit()
            await context.bot.send_message(u_id, "❌ تم رفض طلب السحب الخاص بك وإعادة المبلغ لرصيدك.")
            await query.edit_message_text(f"❌ **تم رفض الطلب #{req_id} وإعادة المبلغ.**", parse_mode="Markdown")

    conn.close()

# ---------------------------------------------------------
# تشغيل البوت
# ---------------------------------------------------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("البوت يعمل بنجاح...")
    app.run_polling()
