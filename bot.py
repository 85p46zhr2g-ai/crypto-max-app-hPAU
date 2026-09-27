import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# التوكن ورابط الاستضافة الخاصين بك
BOT_TOKEN = "7972826317:AAG9Nq9L4P2tXJ06g15T3_l8O_B1Z_wJ_fM"
BASE_URL = "https://gram-max.vercel.app/index.html" # أو رابط GitHub Pages الخاص بك

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    
    # رابط متغير لكسر كاش وتخزين تليجرام المؤقت
    versioned_url = f"{BASE_URL}?v={int(time.time())}"
    
    welcome_message = (
        f"أهلاً بك يا {user_first_name} في بوت **GRAM MAX**! 🚀\n\n"
        "منصة التداول والاستثمار الذكي عبر شبكة TON.\n"
        "اضغط على الزر أدناه لفتح التطبيق المصغر والبدء فوراً."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 فتح التطبيق (Open App)", web_app=WebAppInfo(url=versioned_url))
        ],
        [
            InlineKeyboardButton("💬 الدعم الفني (Fast Support)", url="https://t.me/FastHelp3")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("GRAM MAX Bot is active and running...")
    app.run_polling()
