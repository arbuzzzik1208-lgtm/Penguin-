# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Главная клавиатура пользователя"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 Создать обращение")],
        [KeyboardButton("❓ Помощь")]
    ], resize_keyboard=True, one_time_keyboard=False)

def get_admin_keyboard():
    """Главная клавиатура администратора"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 Активные обращения")],
        [KeyboardButton("👥 Заблокированные пользователи")],
        [KeyboardButton("📊 Статистика")],
        [KeyboardButton("❓ Помощь админа")]
    ], resize_keyboard=True, one_time_keyboard=False)

def get_ticket_buttons(ticket_number: str, is_active: bool = True):
    """Кнопки для обращения"""
    buttons = []
    
    if is_active:
        buttons.append([InlineKeyboardButton("📩 Ответить", callback_data=f"reply_{ticket_number}")])
        buttons.append([InlineKeyboardButton("🔒 Закрыть обращение", callback_data=f"close_{ticket_number}")])
    else:
        buttons.append([InlineKeyboardButton("📖 Только чтение", callback_data="readonly")])
    
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{ticket_number}")])
    buttons.append([InlineKeyboardButton("🔙 Назад к обращениям", callback_data="back_to_tickets")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_tickets_list(tickets: list, page: int = 0):
    """Список обращений для админа с пагинацией"""
    buttons = []
    per_page = 8
    
    start = page * per_page
    end = start + per_page
    page_tickets = tickets[start:end]
    
    for ticket in page_tickets:
        status = "🟢" if ticket['is_active'] else "🔴"
        username = ticket['username'] or "без username"
        date = ticket['created_at'][:16]
        ticket_number = ticket['ticket_number']
        
        buttons.append([InlineKeyboardButton(
            f"{status} {ticket_number} | {username} | {date}",
            callback_data=f"open_{ticket_number}"
        )])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"tickets_page_{page-1}"))
    if end < len(tickets):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"tickets_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tickets")])
    
    return InlineKeyboardMarkup(buttons)

def get_ban_buttons(user_id: int):
    """Кнопки управления блокировкой"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Заблокировать", callback_data=f"ban_{user_id}")],
        [InlineKeyboardButton("🔓 Разблокировать", callback_data=f"unban_{user_id}")]
    ])

def get_back_button():
    """Кнопка возврата"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]
    ])
