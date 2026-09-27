import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
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
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# لوحة التحكم الرئيسية
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username or ""

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, username) VALUES (?, ?, ?)", 
                       (user_id, first_name, username))
        conn.commit()

    conn.close()
    await update.message.reply_text(
        "أهلاً بك في بوت GRAM MAX! 🚀\nاختر من القائمة أدناه للبدء:",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if text == "⚙️ الإعدادات":
        await update.message.reply_text(
            f"⚙️ **الإعدادات والتواصل:**\n\nللتواصل مع الدعم الفني: {SUPPORT_USERNAME}",
            parse_mode="Markdown"
        )
    elif text == "💬 الدعم الفني":
        await update.message.reply_text(f"يمكنك التواصل مع الدعم الفني عبر: {SUPPORT_USERNAME}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("البوت يعمل بنجاح...")
    app.run_polling()
