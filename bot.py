from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bot_database import Database
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN")
    print("📝 Добавьте переменную BOT_TOKEN в настройках Railway")
    exit(1)

DEPARTMENTS = ["IT", "Маркетинг", "Продажи", "Бухгалтерия", "HR", "Разработка", "Поддержка", "Другое"]
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = """
🤖 Добро пожаловать в бот уведомлений компании!

**Назначение бота:**
• Сбои в работе систем
• Технические работы  
• Важные объявления
• Экстренные ситуации

Выберите ваш отдел: 👇
    """
    
    keyboard = []
    for dept in DEPARTMENTS:
        keyboard.append([InlineKeyboardButton(dept, callback_data=f"dept_{dept}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("dept_"):
        department = data.split("_")[1]
        db.update_department(user_id, department)
        
        is_admin = (department.upper() == "IT")
        confirmation_text = f"✅ Вы выбрали отдел: **{department}**"
        
        if is_admin:
            confirmation_text += "\n\n🎛 **Вы администратор!** Доступна панель управления."
            keyboard = [
                [InlineKeyboardButton("📢 Создать уведомление", callback_data="create_post")],
                [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
                [InlineKeyboardButton("🔄 Сменить отдел", callback_data="change_department")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Сменить отдел", callback_data="change_department")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(confirmation_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "change_department":
        keyboard = []
        for dept in DEPARTMENTS:
            keyboard.append([InlineKeyboardButton(dept, callback_data=f"dept_{dept}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите ваш отдел:", reply_markup=reply_markup)
    
    elif data == "create_post":
        await start_post_creation(query, context)
    
    elif data == "show_stats":
        await show_statistics(query)
    
    elif data == "back_to_main":
        await return_to_main_menu(query)

async def start_post_creation(query, context):
    """Начинает процесс создания поста"""
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data[4]:
        await query.answer("❌ Только для администраторов", show_alert=True)
        return
    
    keyboard = []
    for i in range(0, len(DEPARTMENTS), 2):
        row = []
        for j in range(2):
            if i + j < len(DEPARTMENTS):
                dept = DEPARTMENTS[i + j]
                row.append(InlineKeyboardButton(dept, callback_data=f"target_{dept}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🎯 Всем сотрудникам", callback_data="target_ALL")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📢 **Создание уведомления**\n\nВыберите, кому отправить:", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_target_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор цели уведомления"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("target_"):
        target = query.data.replace("target_", "")
        context.user_data['post_target'] = target
        context.user_data['waiting_for_message'] = True
        
        target_text = "всем сотрудникам" if target == "ALL" else f"отделу {target}"
        await query.edit_message_text(f"🎯 **Получатели:** {target_text}\n\n📝 Теперь введите текст уведомления:", parse_mode='Markdown')

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод текста уведомления"""
    if context.user_data.get('waiting_for_message'):
        message_text = update.message.text
        target = context.user_data.get('post_target')
        user_id = update.effective_user.id
        
        user_data = db.get_user(user_id)
        if not user_data or not user_data[4]:
            await update.message.reply_text("❌ Ошибка прав доступа")
            context.user_data.clear()
            return
        
        if target == "ALL":
            user_ids = db.get_all_users()
            target_text = "всем сотрудникам"
        else:
            user_ids = db.get_users_by_department(target)
            target_text = f"отделу {target}"
        
        sent_count = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📢 **Важное уведомление**\n\n{message_text}\n\n_Отправлено для {target_text}_",
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                logging.error(f"Ошибка отправки пользователю {uid}: {e}")
        
        db.save_post(user_id, target, message_text)
        context.user_data.clear()
        
        result_text = f"✅ **Уведомление отправлено!**\n\n• 📤 Успешно: {sent_count} сотрудников\n• 🎯 Получатели: {target_text}"
        keyboard = [
            [InlineKeyboardButton("📢 Новое уведомление", callback_data="create_post")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_statistics(query):
    """Показывает статистику бота"""
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data[4]:
        await query.answer("❌ Только для администраторов", show_alert=True)
        return
    
    total_users = len(db.get_all_users())
    departments_stats = {}
    
    for dept in DEPARTMENTS:
        count = len(db.get_users_by_department(dept))
        if count > 0:
            departments_stats[dept] = count
    
    stats_text = "📊 **Статистика бота**\n\n"
    stats_text += f"👥 Всего пользователей: **{total_users}**\n\n"
    
    if departments_stats:
        stats_text += "**По отделам:**\n"
        for dept, count in departments_stats.items():
            admin_indicator = " 👑" if dept.upper() == "IT" else ""
            stats_text += f"• {dept}: {count} чел.{admin_indicator}\n"
    
    keyboard = [
        [InlineKeyboardButton("📢 Создать уведомление", callback_data="create_post")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def return_to_main_menu(query):
    """Возвращает в главное меню"""
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if user_data:
        department = user_data[3] or "Не выбран"
        is_admin = user_data[4]
        
        text = f"🏠 **Главное меню**\n\n✅ Ваш отдел: **{department}**"
        
        if is_admin:
            text += "\n\n🎛 Вы администратор бота"
            keyboard = [
                [InlineKeyboardButton("📢 Создать уведомление", callback_data="create_post")],
                [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
                [InlineKeyboardButton("🔄 Сменить отдел", callback_data="change_department")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Сменить отдел", callback_data="change_department")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(dept_|change_department|create_post|show_stats|back_to_main)$"))
    application.add_handler(CallbackQueryHandler(handle_target_selection, pattern="^target_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_input))
    
    print("🚀 Бот запущен и готов к работе!")
    print("📱 Откройте Telegram и напишите /start вашему боту")
    application.run_polling()

if __name__ == '__main__':
    main()