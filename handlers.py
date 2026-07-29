# handlers.py
import logging
from telegram import Update, Message, InputFile
from telegram.ext import ContextTypes
from database import Database
from config import ADMIN_ID
import os
import tempfile

logger = logging.getLogger(__name__)
db = Database()

class Handlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        # Проверка блокировки
        if db.is_user_banned(user_id):
            await update.message.reply_text(
                "🚫 *Вы заблокированы*\n\n"
                "Вы не можете создавать обращения.\n"
                f"Для уточнения причины обратитесь к администратору.",
                parse_mode='Markdown'
            )
            return
        
        # Проверяем активное обращение
        active_ticket = db.get_user_active_ticket(user_id)
        
        if active_ticket:
            await update.message.reply_text(
                f"👋 *С возвращением!*\n\n"
                f"У вас есть активное обращение: {active_ticket['ticket_number']}\n"
                f"📅 Создано: {active_ticket['created_at'][:16]}\n"
                f"💬 Сообщений: {active_ticket['messages_count']}\n\n"
                f"Вы можете продолжить диалог или создать новое обращение.",
                parse_mode='Markdown',
                reply_markup=Handlers.get_ticket_keyboard()
            )
            return
        
        # Приветствие нового пользователя
        await update.message.reply_text(
            f"👋 *Добро пожаловать в службу поддержки!*\n\n"
            f"Здесь вы можете обратиться к администратору.\n\n"
            f"📌 *Для создания обращения:*\n"
            f"Нажмите кнопку «📝 Создать обращение»\n\n"
            f"После создания вы сможете общаться с администратором в этом чате.\n\n"
            f"💡 *Примечание:* Администратор не видит ваш номер телефона, "
            f"но видит ваш ID для идентификации.",
            parse_mode='Markdown',
            reply_markup=Handlers.get_main_keyboard()
        )
    
    @staticmethod
    def get_main_keyboard():
        from keyboards import get_main_keyboard
        return get_main_keyboard()
    
    @staticmethod
    def get_ticket_keyboard():
        from keyboards import get_main_keyboard
        return get_main_keyboard()
    
    @staticmethod
    async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание нового обращения"""
        user = update.effective_user
        user_id = user.id
        
        # Проверка блокировки
        if db.is_user_banned(user_id):
            await update.message.reply_text("🚫 Вы заблокированы и не можете создавать обращения.")
            return
        
        # Проверка активного обращения
        active_ticket = db.get_user_active_ticket(user_id)
        if active_ticket:
            await update.message.reply_text(
                f"⚠️ *У вас уже есть активное обращение!*\n\n"
                f"Номер: {active_ticket['ticket_number']}\n"
                f"Создано: {active_ticket['created_at'][:16]}\n\n"
                f"Закройте текущее обращение через команду /stop или кнопку «Закрыть», "
                f"чтобы создать новое.",
                parse_mode='Markdown'
            )
            return
        
        # Создание обращения
        ticket_number = db.create_ticket(
            user_id=user_id,
            username=user.username,
            full_name=user.full_name
        )
        
        if ticket_number:
            # Сохраняем номер обращения в контексте
            context.user_data['ticket_number'] = ticket_number
            context.user_data['ticket_active'] = True
            
            await update.message.reply_text(
                f"✅ *Обращение создано!*\n\n"
                f"📋 Номер: {ticket_number}\n"
                f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"✉️ Теперь вы можете отправлять сообщения администратору.\n"
                f"Они будут переданы напрямую.\n\n"
                f"🔒 Чтобы закрыть обращение, используйте команду /stop "
                f"или кнопку «Закрыть обращение» в админ-панели.",
                parse_mode='Markdown'
            )
            
            # Уведомление админу
            await Handlers.notify_admin_new_ticket(update, context, ticket_number, user)
        else:
            await update.message.reply_text("❌ Произошла ошибка при создании обращения. Попробуйте позже.")
    
    @staticmethod
    async def stop_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Закрытие обращения"""
        user_id = update.effective_user.id
        active_ticket = db.get_user_active_ticket(user_id)
        
        if not active_ticket:
            await update.message.reply_text(
                "ℹ️ У вас нет активных обращений.",
                parse_mode='Markdown'
            )
            return
        
        ticket_number = active_ticket['ticket_number']
        db.close_ticket(ticket_number)
        context.user_data['ticket_active'] = False
        
        await update.message.reply_text(
            f"🔒 *Обращение закрыто*\n\n"
            f"Номер: {ticket_number}\n"
            f"Дата закрытия: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Вы можете создать новое обращение в любое время.",
            parse_mode='Markdown',
            reply_markup=Handlers.get_main_keyboard()
        )
        
        # Уведомление админу
        await Handlers.notify_admin_ticket_closed(update, context, ticket_number, user_id)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user_id = update.effective_user.id
        
        if user_id == ADMIN_ID:
            await update.message.reply_text(
                "👨‍💼 *Помощь администратору*\n\n"
                "📋 Команды:\n"
                "/admin - Открыть админ-панель\n"
                "/ban <user_id> [причина] - Заблокировать пользователя\n"
                "/unban <user_id> - Разблокировать пользователя\n"
                "/bans - Список заблокированных\n\n"
                "📌 В админ-панели вы можете:\n"
                "- Просматривать активные обращения\n"
                "- Отвечать пользователям\n"
                "- Закрывать обращения\n"
                "- Просматривать историю",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            "📚 *Справка по боту*\n\n"
            "Доступные команды:\n"
            "/start - Главное меню\n"
            "/new - Создать обращение\n"
            "/stop - Закрыть обращение\n"
            "/help - Эта справка\n\n"
            "💡 *Как это работает:*\n"
            "1. Создайте обращение через /new\n"
            "2. Отправляйте сообщения администратору\n"
            "3. Администратор ответит вам в этом чате\n"
            "4. После решения закройте обращение через /stop\n\n"
            "❓ Если у вас возникли вопросы, просто напишите их в чат, "
            "и администратор получит ваше сообщение.",
            parse_mode='Markdown',
            reply_markup=Handlers.get_main_keyboard()
        )
    
    @staticmethod
    async def notify_admin_new_ticket(update, context, ticket_number, user):
        """Уведомление админа о новом обращении"""
        try:
            from telegram import Bot
            bot = context.bot
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🆕 *Новое обращение!*\n\n"
                     f"📋 Номер: {ticket_number}\n"
                     f"👤 Пользователь: {user.full_name or user.username}\n"
                     f"🆔 ID: `{user.id}`\n"
                     f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                     f"Для ответа используйте админ-панель: /admin",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Notify admin error: {e}")
    
    @staticmethod
    async def notify_admin_ticket_closed(update, context, ticket_number, user_id):
        """Уведомление админа о закрытии обращения"""
        try:
            from telegram import Bot
            bot = context.bot
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔒 *Обращение закрыто*\n\n"
                     f"📋 Номер: {ticket_number}\n"
                     f"👤 Пользователь ID: `{user_id}`\n"
                     f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Notify admin ticket closed error: {e}")
    
    @staticmethod
    async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка всех сообщений от пользователя"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        # Если админ пишет в личный чат - обрабатываем отдельно
        if user_id == ADMIN_ID:
            await Handlers.handle_admin_message(update, context)
            return
        
        # Проверка блокировки
        if db.is_user_banned(user_id):
            await update.message.reply_text(
                "🚫 Вы заблокированы. Обращения недоступны."
            )
            return
        
        # Проверка активного обращения
        active_ticket = db.get_user_active_ticket(user_id)
        
        if not active_ticket:
            # Предложение создать обращение
            await update.message.reply_text(
                "ℹ️ У вас нет активных обращений.\n"
                "Используйте /new для создания.",
                reply_markup=Handlers.get_main_keyboard()
            )
            return
        
        ticket_number = active_ticket['ticket_number']
        
        # Сохраняем сообщение
        message_data = Handlers.extract_message_data(update.message)
        
        if message_data:
            db.save_message(
                ticket_number=ticket_number,
                sender_id=user_id,
                sender_type="user",
                **message_data
            )
            
            # Пересылаем админу
            await Handlers.forward_to_admin(update, context, ticket_number, user)
    
    @staticmethod
    def extract_message_data(message):
        """Извлечение данных из сообщения"""
        data = {
            "message_type": "text",
            "content": None,
            "file_id": None,
            "file_name": None,
            "file_size": None,
            "mime_type": None,
            "caption": None
        }
        
        if message.text:
            data["message_type"] = "text"
            data["content"] = message.text
        elif message.photo:
            data["message_type"] = "photo"
            data["file_id"] = message.photo[-1].file_id
            data["caption"] = message.caption
        elif message.video:
            data["message_type"] = "video"
            data["file_id"] = message.video.file_id
            data["file_name"] = message.video.file_name
            data["file_size"] = message.video.file_size
            data["mime_type"] = message.video.mime_type
            data["caption"] = message.caption
        elif message.document:
            data["message_type"] = "document"
            data["file_id"] = message.document.file_id
            data["file_name"] = message.document.file_name
            data["file_size"] = message.document.file_size
            data["mime_type"] = message.document.mime_type
            data["caption"] = message.caption
        elif message.animation:
            data["message_type"] = "animation"
            data["file_id"] = message.animation.file_id
            data["file_name"] = message.animation.file_name
            data["file_size"] = message.animation.file_size
            data["mime_type"] = message.animation.mime_type
            data["caption"] = message.caption
        elif message.sticker:
            data["message_type"] = "sticker"
            data["file_id"] = message.sticker.file_id
            data["file_name"] = f"{message.sticker.emoji}.webp"
            data["file_size"] = message.sticker.file_size
        elif message.voice:
            data["message_type"] = "voice"
            data["file_id"] = message.voice.file_id
            data["file_size"] = message.voice.file_size
            data["mime_type"] = "audio/ogg"
            data["caption"] = message.caption
        elif message.video_note:
            data["message_type"] = "video_note"
            data["file_id"] = message.video_note.file_id
            data["file_size"] = message.video_note.file_size
        elif message.audio:
            data["message_type"] = "audio"
            data["file_id"] = message.audio.file_id
            data["file_name"] = message.audio.file_name
            data["file_size"] = message.audio.file_size
            data["mime_type"] = message.audio.mime_type
            data["caption"] = message.caption
        elif message.contact:
            data["message_type"] = "contact"
            data["content"] = f"📇 Контакт: {message.contact.first_name} {message.contact.last_name or ''} - {message.contact.phone_number}"
        elif message.location:
            data["message_type"] = "location"
            data["content"] = f"📍 Местоположение: {message.location.latitude}, {message.location.longitude}"
        else:
            return None
        
        return data
    
    @staticmethod
    async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_number: str, user):
        """Пересылка сообщения администратору"""
        try:
            bot = context.bot
            message = update.message
            
            # Формируем сообщение для админа
            header = (
                f"💬 *Новое сообщение*\n\n"
                f"📋 Обращение: {ticket_number}\n"
                f"👤 Пользователь: {user.full_name or user.username}\n"
                f"🆔 ID: `{user.id}`\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"{'='*20}\n\n"
            )
            
            # Отправляем в зависимости от типа
            if message.text:
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=header + message.text,
                    parse_mode='Markdown'
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=message.photo[-1].file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.video:
                await bot.send_video(
                    chat_id=ADMIN_ID,
                    video=message.video.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.document:
                await bot.send_document(
                    chat_id=ADMIN_ID,
                    document=message.document.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.animation:
                await bot.send_animation(
                    chat_id=ADMIN_ID,
                    animation=message.animation.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.sticker:
                await bot.send_sticker(
                    chat_id=ADMIN_ID,
                    sticker=message.sticker.file_id
                )
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=header,
                    parse_mode='Markdown'
                )
            elif message.voice:
                await bot.send_voice(
                    chat_id=ADMIN_ID,
                    voice=message.voice.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.video_note:
                await bot.send_video_note(
                    chat_id=ADMIN_ID,
                    video_note=message.video_note.file_id
                )
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=header,
                    parse_mode='Markdown'
                )
            elif message.audio:
                await bot.send_audio(
                    chat_id=ADMIN_ID,
                    audio=message.audio.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.contact:
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=header + f"📇 Контакт: {message.contact.first_name} {message.contact.last_name or ''}\n📞 {message.contact.phone_number}",
                    parse_mode='Markdown'
                )
            elif message.location:
                await bot.send_location(
                    chat_id=ADMIN_ID,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude
                )
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=header,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Forward to admin error: {e}")
    
    @staticmethod
    async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений от администратора"""
        user_id = update.effective_user.id
        message = update.message
        
        if user_id != ADMIN_ID:
            return
        
        # Проверяем активное обращение в контексте
        active_ticket = context.user_data.get('admin_ticket')
        
        if not active_ticket:
            await message.reply_text(
                "ℹ️ Сначала выберите обращение в админ-панели.",
                reply_markup=Handlers.get_admin_back_keyboard()
            )
            return
        
        ticket_number = active_ticket
        
        # Проверяем существует ли обращение
        ticket = db.get_ticket(ticket_number)
        if not ticket or not ticket['is_active']:
            await message.reply_text(
                "⚠️ Это обращение уже закрыто.",
                reply_markup=Handlers.get_admin_back_keyboard()
            )
            return
        
        # Сохраняем сообщение
        message_data = Handlers.extract_message_data(message)
        
        if message_data:
            db.save_message(
                ticket_number=ticket_number,
                sender_id=user_id,
                sender_type="admin",
                **message_data
            )
            
            # Отправляем пользователю
            await Handlers.forward_to_user(update, context, ticket_number)
    
    @staticmethod
    async def forward_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_number: str):
        """Отправка сообщения пользователю"""
        try:
            bot = context.bot
            message = update.message
            
            # Получаем обращение
            ticket = db.get_ticket(ticket_number)
            if not ticket:
                return
            
            user_id = ticket['user_id']
            
            # Проверяем, не заблокирован ли пользователь
            if db.is_user_banned(user_id):
                await message.reply_text("⚠️ Пользователь заблокирован. Сообщение не отправлено.")
                return
            
            # Формируем сообщение для пользователя
            header = "✉️ *Ответ администратора:*\n\n"
            
            # Отправляем в зависимости от типа
            if message.text:
                await bot.send_message(
                    chat_id=user_id,
                    text=header + message.text,
                    parse_mode='Markdown'
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.video:
                await bot.send_video(
                    chat_id=user_id,
                    video=message.video.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.document:
                await bot.send_document(
                    chat_id=user_id,
                    document=message.document.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.animation:
                await bot.send_animation(
                    chat_id=user_id,
                    animation=message.animation.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.sticker:
                await bot.send_sticker(
                    chat_id=user_id,
                    sticker=message.sticker.file_id
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=header,
                    parse_mode='Markdown'
                )
            elif message.voice:
                await bot.send_voice(
                    chat_id=user_id,
                    voice=message.voice.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.video_note:
                await bot.send_video_note(
                    chat_id=user_id,
                    video_note=message.video_note.file_id
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=header,
                    parse_mode='Markdown'
                )
            elif message.audio:
                await bot.send_audio(
                    chat_id=user_id,
                    audio=message.audio.file_id,
                    caption=header + (message.caption or ""),
                    parse_mode='Markdown'
                )
            elif message.contact:
                await bot.send_contact(
                    chat_id=user_id,
                    phone_number=message.contact.phone_number,
                    first_name=message.contact.first_name,
                    last_name=message.contact.last_name
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=header,
                    parse_mode='Markdown'
                )
            elif message.location:
                await bot.send_location(
                    chat_id=user_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=header,
                    parse_mode='Markdown'
                )
            
            await message.reply_text("✅ Сообщение отправлено пользователю.")
            
        except Exception as e:
            logger.error(f"Forward to user error: {e}")
            await message.reply_text(f"❌ Ошибка при отправке: {str(e)}")
    
    @staticmethod
    def get_admin_back_keyboard():
        from keyboards import get_back_button
        return get_back_button()
