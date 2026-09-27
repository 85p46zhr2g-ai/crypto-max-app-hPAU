import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# إعدادات التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن ورابط التطبيق الخاص بك
BOT_TOKEN = "7901357038:AAFi2I3r0K89iGjAn8_VvY8_fO1Qy0WzU9M"  # ضع التوكن الخاص بك هنا إذا كان مختلفاً
MINI_APP_URL = "https://gram-max.vercel.app/index.html?v=6.0"
ADMIN_ID = 5821731671 # ID الأدمن الخاص بك لاستلام الإشعارات

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # تثبيت زر التطبيق المصغر في القائمة السفلية للبوت دائماً
    await context.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonWebApp(text="🚀 فتح التطبيق", web_app=WebAppInfo(url=MINI_APP_URL))
    )

    welcome_text = (
        f"🎉 **أهلاً بك في GRAM MAX**\n\n"
        f"مرحباً بك يا {user.first_name} 👋\n"
        f"من خلال البوت يمكنك إدارة حسابك، متابعة رصيدك، تنفيذ المهام، الاستثمار، وربط محفظتك.\n"
    )

    # الأزرار الرئيسية
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

# الأوامر القائمة المختصرة
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 **الدعم الفني**\n\nلأي استفسار أو مشكلة في الإيداع والسحب، تواصل مع الدعم: @FastHelp3", parse_mode='Markdown')

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 **الشروط والأحكام**\n\n1. يمنع استخدام أكثر من حساب بطرق غير مشروعة.\n2. جميع عمليات السحب تخضع للمراجعة وتنفذ خلال 24 ساعة.\n3. رسوم السحب هي 2%.", parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("terms", terms_command))

    print("GRAM MAX Bot is Running...")
    application.run_polling()

if __name__ == '__main__':
    main()
