# database.py
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "support_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация всех таблиц"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица обращений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_number TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    created_at TEXT NOT NULL,
                    closed_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    messages_count INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_number TEXT NOT NULL,
                    sender_id INTEGER NOT NULL,
                    sender_type TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT,
                    file_id TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    caption TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ticket_number) REFERENCES tickets(ticket_number)
                )
            ''')
            
            # Таблица заблокированных пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id INTEGER PRIMARY KEY,
                    banned_at TEXT NOT NULL,
                    reason TEXT,
                    banned_by INTEGER
                )
            ''')
            
            # Таблица настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database init error: {e}")
    
    # ============ TICKETS ============
    
    def create_ticket(self, user_id: int, username: str = None, full_name: str = None) -> str:
        """Создание нового обращения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Генерация номера
            from random import randint
            ticket_number = f"№{randint(1000000000, 9999999999)}"
            
            cursor.execute('''
                INSERT INTO tickets (ticket_number, user_id, username, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_number, user_id, username, full_name, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logger.info(f"Ticket created: {ticket_number} by user {user_id}")
            return ticket_number
        except Exception as e:
            logger.error(f"Create ticket error: {e}")
            return None
    
    def get_ticket(self, ticket_number: str) -> Optional[Dict]:
        """Получение информации об обращении"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tickets WHERE ticket_number = ?', (ticket_number,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get ticket error: {e}")
            return None
    
    def get_user_active_ticket(self, user_id: int) -> Optional[Dict]:
        """Получение активного обращения пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get user active ticket error: {e}")
            return None
    
    def get_all_active_tickets(self) -> List[Dict]:
        """Получение всех активных обращений"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE is_active = 1
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get all active tickets error: {e}")
            return []
    
    def close_ticket(self, ticket_number: str) -> bool:
        """Закрытие обращения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tickets 
                SET is_active = 0, closed_at = ?
                WHERE ticket_number = ?
            ''', (datetime.now().isoformat(), ticket_number))
            conn.commit()
            conn.close()
            logger.info(f"Ticket closed: {ticket_number}")
            return True
        except Exception as e:
            logger.error(f"Close ticket error: {e}")
            return False
    
    # ============ MESSAGES ============
    
    def save_message(self, ticket_number: str, sender_id: int, sender_type: str,
                     message_type: str, content: str = None, file_id: str = None,
                     file_name: str = None, file_size: int = None,
                     mime_type: str = None, caption: str = None) -> bool:
        """Сохранение сообщения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (
                    ticket_number, sender_id, sender_type, message_type,
                    content, file_id, file_name, file_size, mime_type,
                    caption, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticket_number, sender_id, sender_type, message_type,
                content, file_id, file_name, file_size, mime_type,
                caption, datetime.now().isoformat()
            ))
            
            # Обновляем счетчик сообщений
            cursor.execute('''
                UPDATE tickets SET messages_count = messages_count + 1
                WHERE ticket_number = ?
            ''', (ticket_number,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Save message error: {e}")
            return False
    
    def get_ticket_messages(self, ticket_number: str) -> List[Dict]:
        """Получение всех сообщений обращения"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM messages 
                WHERE ticket_number = ?
                ORDER BY created_at ASC
            ''', (ticket_number,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get ticket messages error: {e}")
            return []
    
    # ============ BANS ============
    
    def ban_user(self, user_id: int, reason: str = None, banned_by: int = None) -> bool:
        """Блокировка пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO banned_users (user_id, banned_at, reason, banned_by)
                VALUES (?, ?, ?, ?)
            ''', (user_id, datetime.now().isoformat(), reason, banned_by))
            conn.commit()
            conn.close()
            logger.info(f"User banned: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ban user error: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """Разблокировка пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            logger.info(f"User unbanned: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Unban user error: {e}")
            return False
    
    def is_user_banned(self, user_id: int) -> bool:
        """Проверка блокировки пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM banned_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Check ban error: {e}")
            return False
    
    def get_banned_users(self) -> List[Dict]:
        """Получение списка заблокированных пользователей"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM banned_users ORDER BY banned_at DESC')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get banned users error: {e}")
            return []
