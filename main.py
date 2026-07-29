# main.py
#!/usr/bin/env python3
# ============================================================
# TELEGRAM SUPPORT BOT — Полная версия
# ============================================================

import logging
import sys
from datetime import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from config import TOKEN, ADMIN_ID
from database import Database
from handlers import Handlers
from admin import AdminHandlers
from keyboards import get_admin_tickets_list, get_ticket_buttons, get_back_button

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

# ============================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await Handlers.start(update, context)

async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /new - создание обращения"""
    await Handlers.new_ticket(update, context)

async def stop_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stop - закрытие обращения"""
    await Handlers.stop_ticket(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await Handlers.help_command(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin"""
    await AdminHandlers.admin_panel(update, context)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ban"""
    await AdminHandlers.ban_user(update, context)

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unban"""
    await AdminHandlers.unban_user(update, context)

async def list_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /bans"""
    await AdminHandlers.list_bans(update, context)

# ============================================================
# CALLBACK ОБРАБОТЧИКИ
# ============================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback запросов"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Callback: {data} from user {user_id}")
    
    # === ОБРАЩЕНИЯ ===
    
    if data == "back_to_tickets":
        await AdminHandlers.back_to_tickets(update, context)
        return
    
    if data == "refresh_tickets":
        await AdminHandlers.refresh_tickets(update, context)
        return
    
    if data.startswith("tickets_page_"):
        page = int(data.split("_")[2])
        await AdminHandlers.tickets_page(update, context, page)
        return
    
    if data.startswith("open_"):
        ticket_number = data.replace("open_", "")
        await AdminHandlers.open_ticket(update, context, ticket_number)
        return
    
    if data.startswith("close_"):
        ticket_number = data.replace("close_", "")
        await AdminHandlers.close_ticket(update, context, ticket_number)
        return
    
    if data.startswith("reply_"):
        ticket_number = data.replace("reply_", "")
        query = update.callback_query
        await query.edit_message_text(
            f"✉️ *Ответ на обращение {ticket_number}*\n\n"
            f"Отправьте сообщение пользователю.\n"
            f"Поддерживаются все типы сообщений.",
            parse_mode='Markdown',
            reply_markup=get_back_button()
        )
        # Сохраняем в контексте
        context.user_data['admin_ticket'] = ticket_number
        return
    
    if data.startswith("refresh_"):
        ticket_number = data.replace("refresh_", "")
        await AdminHandlers.open_ticket(update, context, ticket_number)
        return
    
    # === БАН ===
    
    if data.startswith("ban_"):
        target_id = int(data.replace("ban_", ""))
        
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        if db.is_user_banned(target_id):
            await query.edit_message_text(f"ℹ️ Пользователь `{target_id}` уже заблокирован.")
            return
        
        db.ban_user(target_id, "Заблокирован через админ-панель", user_id)
        
        await query.edit_message_text(
            f"✅ *Пользователь заблокирован*\n\n"
            f"🆔 ID: `{target_id}`",
            parse_mode='Markdown',
            reply_markup=get_back_button()
        )
        
        # Уведомляем пользователя
        try:
            bot = context.bot
            await bot.send_message(
                chat_id=target_id,
                text="🚫 *Вы заблокированы в службе поддержки.*",
                parse_mode='Markdown'
            )
        except:
            pass
        return
    
    if data.startswith("unban_"):
        target_id = int(data.replace("unban_", ""))
        
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        if not db.is_user_banned(target_id):
            await query.edit_message_text(f"ℹ️ Пользователь `{target_id}` не заблокирован.")
            return
        
        db.unban_user(target_id)
        
        await query.edit_message_text(
            f"✅ *Пользователь разблокирован*\n\n"
            f"🆔 ID: `{target_id}`",
            parse_mode='Markdown',
            reply_markup=get_back_button()
        )
        
        # Уведомляем пользователя
        try:
            bot = context.bot
            await bot.send_message(
                chat_id=target_id,
                text="✅ *Вы разблокированы в службе поддержки.*",
                parse_mode='Markdown'
            )
        except:
            pass
        return
    
    if data == "back_to_admin":
        await AdminHandlers.admin_panel(update, context)
        return
    
    if data == "readonly":
        await query.edit_message_text(
            "ℹ️ Обращение закрыто. Доступен только просмотр.",
            parse_mode='Markdown'
        )
        return
    
    # Неизвестный callback
    await query.edit_message_text("❌ Неизвестная команда.")

# ============================================================
# ОБРАБОТКА СООБЩЕНИЙ
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    user_id = update.effective_user.id
    
    # Если сообщение от администратора
    if user_id == ADMIN_ID:
        # Проверяем, есть ли активное обращение
        active_ticket = context.user_data.get('admin_ticket')
        if active_ticket:
            await Handlers.handle_admin_message(update, context)
        else:
            # Обработка текстовых команд через кнопки
            text = update.message.text
            if text == "📋 Активные обращения":
                await AdminHandlers.admin_panel(update, context)
            elif text == "👥 Заблокированные пользователи":
                await AdminHandlers.list_bans(update, context)
            elif text == "📊 Статистика":
                stats = db.get_stats()
                await update.message.reply_text(
                    f"📊 *Статистика бота*\n\n"
                    f"👥 Пользователей: {stats['users']}\n"
                    f"📋 Обращений: {stats['tickets']}\n"
                    f"💬 Сообщений: {stats['messages']}\n"
                    f"🚫 Заблокировано: {stats['bans']}",
                    parse_mode='Markdown'
                )
            elif text == "❓ Помощь админа":
                await Handlers.help_command(update, context)
            else:
                await update.message.reply_text(
                    "Используйте админ-панель: /admin",
                    reply_markup=AdminHandlers.get_admin_keyboard()
                )
        return
    
    # Проверка блокировки
    if db.is_user_banned(user_id):
        await update.message.reply_text("🚫 Вы заблокированы. Обращения недоступны.")
        return
    
    # Обработка текстовых команд через кнопки
    text = update.message.text
    if text == "📝 Создать обращение":
        await Handlers.new_ticket(update, context)
        return
    elif text == "❓ Помощь":
        await Handlers.help_command(update, context)
        return
    
    # Обычное сообщение пользователя
    await Handlers.handle_user_message(update, context)

# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def setup_commands(app):
    """Настройка команд для меню Telegram"""
    await app.bot.set_my_commands([
        BotCommand("start", "Главное меню"),
        BotCommand("new", "Создать обращение"),
        BotCommand("stop", "Закрыть обращение"),
        BotCommand("help", "Помощь"),
        BotCommand("admin", "Админ-панель (для администратора)"),
        BotCommand("ban", "Заблокировать пользователя"),
        BotCommand("unban", "Разблокировать пользователя"),
        BotCommand("bans", "Список заблокированных"),
    ])

def main():
    """Главная функция запуска"""
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Регистрируем команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("new", new_ticket))
        app.add_handler(CommandHandler("stop", stop_ticket))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("unban", unban_user))
        app.add_handler(CommandHandler("bans", list_bans))
        
        # Callback запросы
        app.add_handler(CallbackQueryHandler(handle_callback))
        
        # Сообщения
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
        
        # Настройка команд в меню
        app.post_init = setup_commands
        
        # Запуск
        logger.info("🚀 Бот запущен!")
        logger.info(f"👤 Администратор: {ADMIN_ID}")
        logger.info("=" * 40)
        
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
