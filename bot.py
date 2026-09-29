import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# ----------------------------------------------------
# ⚙️ إعدادات البوت والبيانات الإدارية
# ----------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8183652969"))  # ضع ID المشرف الخاص بك هنا

# إحصائيات وهمية/مؤقتة لغرض التطبيق (يتم ربطها بقاعدة البيانات لاحقاً)
db_data = {
    "users_count": 1420,
    "deposits_count": 385,
    "pending_withdrawals": 3,
    "alerts_count": 2
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------------------------------------------
# 🔐 التحقق من المشرف
# ----------------------------------------------------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ----------------------------------------------------
# 👑 لوحة التحكم الخاصة بالمشرف
# ----------------------------------------------------
def build_admin_panel_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📥 الإيداعات", callback_data="admin_deposits"),
            InlineKeyboardButton("💸 طلبات السحب", callback_data="admin_withdrawals")
        ],
        [
            InlineKeyboardButton("⚠️ تعدد الحسابات", callback_data="admin_multi_accounts"),
            InlineKeyboardButton("📢 الإشعارات", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings"),
            InlineKeyboardButton("🔄 تحديث", callback_data="admin_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_admin_panel_text() -> str:
    return (
        "👑 **GRAM MAX — لوحة المشرف**\n\n"
        "📊 **الإحصائيات**\n"
        f"👥 المستخدمون: {db_data['users_count']}\n"
        f"📥 الإيداعات: {db_data['deposits_count']}\n"
        f"💸 السحوبات المعلقة: {db_data['pending_withdrawals']}\n"
        f"⚠️ التنبيهات: {db_data['alerts_count']}"
    )

# ----------------------------------------------------
# 🚀 أمر البدء /start
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # إذا كان المستخدم هو المشرف تظهر له لوحة المشرف
    if is_admin(user.id):
        await update.message.reply_text(
            text=build_admin_panel_text(),
            reply_markup=build_admin_panel_markup(),
            parse_mode="Markdown"
        )
    else:
        # واجهة المستخدم العادي المنفصلة
        web_app_url = "https://your-github-username.github.io/your-repo-name/"  # رابط تطبيق الـ HTML
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 فتح تطبيق GRAM MAX", web_app={ "url": web_app_url })]
        ])
        await update.message.reply_text(
            f"أهلاً بك {user.first_name} في بوت **GRAM MAX**! 💎\nاضغط على الزر أدناه للبدء:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

# ----------------------------------------------------
# 👑 أمر فتح لوحة التحكم للمشرف (/admin)
# ----------------------------------------------------
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ غير مصرح لك بالوصول إلى هذا الأمر.")
        return

    await update.message.reply_text(
        text=build_admin_panel_text(),
        reply_markup=build_admin_panel_markup(),
        parse_mode="Markdown"
    )

# ----------------------------------------------------
# 🔘 معالج تفاعلات الأزرار للمشرف (Callback Queries)
# ----------------------------------------------------
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # حماية إضافية للتحقق من المشرف عند ضغط الأزرار
    if not is_admin(user_id):
        await query.answer("❌ لا تملك صلاحية استخدام هذه الأزرار.", show_alert=True)
        return

    data = query.data

    if data == "admin_refresh":
        await query.answer("🔄 تم تحديث البيانات")
        await query.edit_message_text(
            text=build_admin_panel_text(),
            reply_markup=build_admin_panel_markup(),
            parse_mode="Markdown"
        )

    elif data == "admin_stats":
        await query.answer()
        await query.edit_message_text(
            f"📊 **تفاصيل الإحصائيات:**\n\n"
            f"• إجمالي المستخدمين: {db_data['users_count']}\n"
            f"• إجمالي عمليات الإيداع: {db_data['deposits_count']}\n"
            f"• الطلبات المعلقة: {db_data['pending_withdrawals']}\n"
            f"• عدد التنبيهات: {db_data['alerts_count']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="admin_refresh")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_withdrawals":
        await query.answer()
        # مثال لطلب سحب معلق للواجهة
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تم التحويل", callback_data="wd_approve_125"),
                InlineKeyboardButton("❌ رفض السحب", callback_data="wd_reject_125")
            ],
            [InlineKeyboardButton("👤 بيانات المستخدم", callback_data="user_info_123456789")],
            [InlineKeyboardButton("🔙 العودة", callback_data="admin_refresh")]
        ])
        
        await query.message.reply_text(
            "💸 **طلب سحب جديد**\n\n"
            "👤 المستخدم: @username\n"
            "🆔 ID: 123456789\n\n"
            "💰 المبلغ: 5.00 GRAM\n"
            "💳 المحفظة:\n`UQxxxxxxxxxxxxxxxx`\n\n"
            "🔢 الرقم التسلسلي:\n#WD-000125\n\n"
            f"📅 التاريخ: {datetime.now().strftime('%d/%m/%Y')}\n"
            f"⏰ الوقت: {datetime.now().strftime('%H:%M')}\n\n"
            "⏳ الحالة: قيد المعالجة\n\n"
            "🕐 تتم معالجة الطلب خلال 24 ساعة.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    elif data.startswith("wd_approve_"):
        wd_id = data.split("_")[2]
        await query.answer("✅ تم القبول والتأكيد", show_alert=True)
        await query.edit_message_text(f"✅ **تمت معالجة طلب السحب #{wd_id} بنجاح وتم التحويل.**", parse_mode="Markdown")

    elif data.startswith("wd_reject_"):
        wd_id = data.split("_")[2]
        await query.answer("❌ تم رفض الطلب وإعادة الرصيد", show_alert=True)
        await query.edit_message_text(f"❌ **تم رفض طلب السحب #{wd_id} وإعادة المبلغ إلى حساب المستخدم.**", parse_mode="Markdown")

    elif data == "admin_multi_accounts":
        await query.answer()
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👁 عرض التفاصيل", callback_data="multi_details"),
                InlineKeyboardButton("🔎 مراجعة", callback_data="multi_review")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="admin_refresh")]
        ])
        await query.edit_message_text(
            "⚠️ **تنبيه تعدد حسابات**\n\n"
            "👤 الحساب الأول: @username1\n"
            "🆔 ID: 123456\n\n"
            "👤 الحساب الثاني: @username2\n"
            "🆔 ID: 789012\n\n"
            "📌 يحتاج إلى مراجعة المشرف.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

# ----------------------------------------------------
# 📥 دالة إرسال إشعار إيداع تلقائي إلى المشرف فقط
# ----------------------------------------------------
async def notify_admin_deposit(application, username: str, user_id: int, amount: float, tx_id: str):
    text = (
        "📥 **إيداع جديد**\n\n"
        f"👤 المستخدم: @{username}\n"
        f"🆔 ID: `{user_id}`\n\n"
        f"💰 المبلغ: {amount:.2f} GRAM\n"
        f"🔢 رقم العملية: #{tx_id}\n"
        f"⏰ الوقت: {datetime.now().strftime('%H:%M')}\n\n"
        "✅ تم تأكيد الإيداع تلقائياً"
    )
    await application.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="Markdown")

# ----------------------------------------------------
# 💸 دالة إرسال إشعار طلب سحب إلى المشرف فقط
# ----------------------------------------------------
async def notify_admin_withdrawal(application, username: str, user_id: int, amount: float, wallet: str, wd_id: str):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تم التحويل", callback_data=f"wd_approve_{wd_id}"),
            InlineKeyboardButton("❌ رفض السحب", callback_data=f"wd_reject_{wd_id}")
        ],
        [InlineKeyboardButton("👤 بيانات المستخدم", callback_data=f"user_info_{user_id}")]
    ])

    text = (
        "💸 **طلب سحب جديد**\n\n"
        f"👤 المستخدم: @{username}\n"
        f"🆔 ID: `{user_id}`\n\n"
        f"💰 المبلغ: {amount:.2f} GRAM\n"
        f"💳 المحفظة:\n`{wallet}`\n\n"
        f"🔢 الرقم التسلسلي:\n#{wd_id}\n\n"
        f"📅 التاريخ: {datetime.now().strftime('%d/%m/%Y')}\n"
        f"⏰ الوقت: {datetime.now().strftime('%H:%M')}\n\n"
        "⏳ الحالة: قيد المعالجة\n\n"
        "🕐 تتم معالجة الطلب خلال 24 ساعة."
    )
    await application.bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# ⚙️ التشغيل الرئيسي للمحرك
# ----------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback_handler))

    print("🤖 GRAM MAX Admin Bot Server Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
