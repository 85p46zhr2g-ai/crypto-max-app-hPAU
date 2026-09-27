import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# إعداد التسجيلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن ورابط التطبيق
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
MINI_APP_URL = "https://gram-max.vercel.app/index.html?v=6.0"

# الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # ضبط القائمة السفلية للبوت لتكون قائمة تطبيق مصغر دائماً
    await context.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonWebApp(text="🚀 فتح التطبيق", web_app=WebAppInfo(url=MINI_APP_URL))
    )

    welcome_text = (
        f"🎉 **أهلاً بك في GRAM MAX**\n\n"
        f"مرحباً بك يا {user.first_name} 👋\n"
        f"من خلال البوت يمكنك إدارة حسابك، متابعة رصيدك، تنفيذ المهام، الاستثمار، وربط محفظتك.\n"
    )

    # أزرار التفاعل تحت الرسالة الترحيبية
    keyboard = [
        [
            InlineKeyboardButton("📢 القناة الرسمية", url="https://t.me/GramMaxChannel"),
            InlineKeyboardButton("🆘 الدعم", url="https://t.me/FastHelp3")
        ],
        [
            InlineKeyboardButton("🚀 فتح التطبيق المصغر", web_app=WebAppInfo(url=MINI_APP_URL))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# قائمة /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لأي استفسار أو مساعدة، تواصل مع الدعم الفني: @FastHelp3")

# دالة إرسال إشعار سحب / إيداع من السيرفر
async def send_notification(app: Application, user_id: int, title: str, details: str):
    msg = f"🔔 **{title}**\n\n{details}"
    await app.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    print("GRAM MAX Bot is Running...")
    application.run_polling()

if __name__ == '__main__':
    main()
