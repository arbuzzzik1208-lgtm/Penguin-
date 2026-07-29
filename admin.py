# admin.py
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from config import ADMIN_ID
from keyboards import get_admin_tickets_list, get_ticket_buttons, get_back_button

logger = logging.getLogger(__name__)
db = Database()

class AdminHandlers:
    
    @staticmethod
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Открытие админ-панели"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен. Вы не являетесь администратором.")
            return
        
        tickets = db.get_all_active_tickets()
        total_active = len(tickets)
        
        # Статистика
        stats = {
            'total': len(tickets),
            'users': len(set([t['user_id'] for t in tickets])),
            'messages': sum([t['messages_count'] for t in tickets])
        }
        
        text = f"""
👨‍💼 *Админ-панель*

📊 *Статистика:*
• Активных обращений: {stats['total']}
• Пользователей: {stats['users']}
• Всего сообщений: {stats['messages']}

📋 *Активные обращения:*
        """
        
        if not tickets:
            text += "\n✅ Нет активных обращений."
            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=get_back_button()
            )
            return
        
        # Сохраняем список обращений в контексте для пагинации
        context.user_data['admin_tickets'] = tickets
        context.user_data['admin_tickets_page'] = 0
        
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_admin_tickets_list(tickets, 0)
        )
    
    @staticmethod
    async def open_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_number: str):
        """Открытие конкретного обращения"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        ticket = db.get_ticket(ticket_number)
        if not ticket:
            await query.edit_message_text("❌ Обращение не найдено.")
            return
        
        # Сохраняем в контексте
        context.user_data['admin_ticket'] = ticket_number
        
        # Получаем сообщения
        messages = db.get_ticket_messages(ticket_number)
        
        # Формируем информацию
        text = f"""
📋 *Обращение {ticket_number}*

👤 Пользователь: {ticket['full_name'] or ticket['username'] or 'Неизвестно'}
🆔 ID: `{ticket['user_id']}`
📅 Создано: {ticket['created_at'][:16]}
💬 Сообщений: {ticket['messages_count']}
📊 Статус: {'🟢 Активно' if ticket['is_active'] else '🔴 Закрыто'}

📝 *История сообщений:*
        """
        
        if messages:
            for msg in messages[-10:]:  # Последние 10 сообщений
                sender = "👤 Пользователь" if msg['sender_type'] == 'user' else "👨‍💼 Админ"
                msg_type = msg['message_type']
                content = msg['content'] or f"[{msg_type}]"
                time = msg['created_at'][11:16]
                text += f"\n{sender} ({time}): {content[:100]}..."
        else:
            text += "\nНет сообщений."
        
        # Добавляем кнопки
        if ticket['is_active']:
            reply_markup = get_ticket_buttons(ticket_number, True)
        else:
            reply_markup = get_ticket_buttons(ticket_number, False)
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    @staticmethod
    async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_number: str):
        """Закрытие обращения"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        # Проверяем существование
        ticket = db.get_ticket(ticket_number)
        if not ticket:
            await query.edit_message_text("❌ Обращение не найдено.")
            return
        
        if not ticket['is_active']:
            await query.edit_message_text("ℹ️ Обращение уже закрыто.")
            return
        
        # Закрываем
        db.close_ticket(ticket_number)
        context.user_data['admin_ticket'] = None
        
        await query.edit_message_text(
            f"🔒 *Обращение {ticket_number} закрыто*\n\n"
            f"Пользователь уведомлен о закрытии.",
            parse_mode='Markdown',
            reply_markup=get_back_button()
        )
        
        # Уведомляем пользователя
        try:
            bot = context.bot
            await bot.send_message(
                chat_id=ticket['user_id'],
                text=f"🔒 *Обращение {ticket_number} закрыто администратором.*\n\n"
                     f"Если у вас остались вопросы, вы можете создать новое обращение.",
                parse_mode='Markdown',
                reply_markup=AdminHandlers.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Notify user about ticket close error: {e}")
    
    @staticmethod
    async def tickets_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        """Пагинация списка обращений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        tickets = context.user_data.get('admin_tickets', [])
        if not tickets:
            tickets = db.get_all_active_tickets()
            context.user_data['admin_tickets'] = tickets
        
        context.user_data['admin_tickets_page'] = page
        
        text = """
👨‍💼 *Админ-панель*

📋 *Активные обращения:*
        """
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_admin_tickets_list(tickets, page)
        )
    
    @staticmethod
    async def refresh_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление списка обращений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        tickets = db.get_all_active_tickets()
        context.user_data['admin_tickets'] = tickets
        context.user_data['admin_tickets_page'] = 0
        
        text = """
👨‍💼 *Админ-панель*

📋 *Активные обращения:*
        """
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_admin_tickets_list(tickets, 0)
        )
    
    @staticmethod
    async def back_to_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к списку обращений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Доступ запрещен.")
            return
        
        tickets = db.get_all_active_tickets()
        context.user_data['admin_tickets'] = tickets
        context.user_data['admin_tickets_page'] = 0
        
        text = """
👨‍💼 *Админ-панель*

📋 *Активные обращения:*
        """
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_admin_tickets_list(tickets, 0)
        )
    
    @staticmethod
    async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Блокировка пользователя"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен.")
            return
        
        # Проверяем аргументы
        if not context.args:
            await update.message.reply_text(
                "❌ *Использование:*\n"
                "/ban <user_id> [причина]\n\n"
                "Пример: `/ban 123456789 Спам`",
                parse_mode='Markdown'
            )
            return
        
        try:
            target_id = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
            
            if db.is_user_banned(target_id):
                await update.message.reply_text(f"ℹ️ Пользователь `{target_id}` уже заблокирован.")
                return
            
            db.ban_user(target_id, reason, user_id)
            
            await update.message.reply_text(
                f"✅ *Пользователь заблокирован*\n\n"
                f"🆔 ID: `{target_id}`\n"
                f"📝 Причина: {reason}",
                parse_mode='Markdown'
            )
            
            # Уведомляем пользователя
            try:
                bot = context.bot
                await bot.send_message(
                    chat_id=target_id,
                    text=f"🚫 *Вы заблокированы в службе поддержки.*\n\n"
                         f"📝 Причина: {reason}\n\n"
                         f"Для уточнения деталей обратитесь к администратору.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Notify banned user error: {e}")
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Используйте: `/ban 123456789`")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    @staticmethod
    async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разблокировка пользователя"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ *Использование:*\n"
                "/unban <user_id>\n\n"
                "Пример: `/unban 123456789`",
                parse_mode='Markdown'
            )
            return
        
        try:
            target_id = int(context.args[0])
            
            if not db.is_user_banned(target_id):
                await update.message.reply_text(f"ℹ️ Пользователь `{target_id}` не заблокирован.")
                return
            
            db.unban_user(target_id)
            
            await update.message.reply_text(
                f"✅ *Пользователь разблокирован*\n\n"
                f"🆔 ID: `{target_id}`",
                parse_mode='Markdown'
            )
            
            # Уведомляем пользователя
            try:
                bot = context.bot
                await bot.send_message(
                    chat_id=target_id,
                    text=f"✅ *Вы разблокированы в службе поддержки.*\n\n"
                         f"Теперь вы можете создавать обращения.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Notify unbanned user error: {e}")
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Используйте: `/unban 123456789`")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    @staticmethod
    async def list_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список заблокированных пользователей"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен.")
            return
        
        banned = db.get_banned_users()
        
        if not banned:
            await update.message.reply_text(
                "✅ *Список заблокированных пользователей пуст.*",
                parse_mode='Markdown'
            )
            return
        
        text = f"👥 *Заблокированные пользователи:*\n\n"
        for user in banned[:20]:
            text += f"🆔 `{user['user_id']}`\n"
            text += f"📝 {user['reason'] or 'Без причины'}\n"
            text += f"📅 {user['banned_at'][:10]}\n\n"
        
        if len(banned) > 20:
            text += f"\n...и еще {len(banned) - 20} пользователей."
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    @staticmethod
    def get_main_keyboard():
        from keyboards import get_main_keyboard
        return get_main_keyboard()
