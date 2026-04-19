import sqlite3
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import MessageData


class BaseStorage(ABC):
    @abstractmethod
    def save_message(self, msg: MessageData) -> bool:
        """Сохранить сообщение в хранилище. Возвращает True, если сохранено успешно."""
        pass

    @abstractmethod
    def get_last_msg_id(self, user_id: int, chat_id: int) -> int:
        """Получить ID последнего сохраненного сообщения пользователя в конкретном чате."""
        pass

    @abstractmethod
    def message_exists(self, chat_id: int, msg_id: int) -> bool:
        """Проверить, существует ли сообщение в базе данных."""
        pass

    @abstractmethod
    def close(self):
        """Закрыть соединение с хранилищем."""
        pass


class SQLiteStorage(BaseStorage):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id INTEGER,
                    msg_id INTEGER,
                    user_id INTEGER,
                    date TEXT,
                    author_name TEXT,
                    author_username TEXT,
                    text TEXT,
                    media_type TEXT,
                    is_reply INTEGER,
                    reply_to_msg_id INTEGER,
                    is_forward INTEGER,
                    fwd_from_id INTEGER,
                    fwd_from_name TEXT,
                    edit_date TEXT,
                    reactions TEXT,
                    original_msg_json TEXT,
                    chat_title TEXT,
                    schema_version INTEGER,
                    PRIMARY KEY (chat_id, msg_id)
                )
            """)
            
            # Таблица активных целей для синхронизации
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_targets (
                    user_id INTEGER,
                    chat_id INTEGER,
                    author_name TEXT,
                    chat_title TEXT,
                    is_active INTEGER DEFAULT 1,
                    export_mode TEXT DEFAULT 'normal',
                    window_size INTEGER DEFAULT 0,
                    max_cluster INTEGER DEFAULT 15,
                    last_synced_at TEXT,
                    added_at TEXT,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            # Migration check: ensure original_msg_json column exists if DB was created with older version
            cursor = conn.execute("PRAGMA table_info(messages)")
            columns = [info[1] for info in cursor.fetchall()]
            if "original_msg_json" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN original_msg_json TEXT")
            if "chat_title" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN chat_title TEXT")
            
            # Проверка колонок в sync_targets
            cursor = conn.execute("PRAGMA table_info(sync_targets)")
            target_columns = [info[1] for info in cursor.fetchall()]
            if "export_mode" not in target_columns:
                conn.execute("ALTER TABLE sync_targets ADD COLUMN export_mode TEXT DEFAULT 'normal'")
            if "window_size" not in target_columns:
                conn.execute("ALTER TABLE sync_targets ADD COLUMN window_size INTEGER DEFAULT 0")
            if "max_cluster" not in target_columns:
                conn.execute("ALTER TABLE sync_targets ADD COLUMN max_cluster INTEGER DEFAULT 15")
            
            # Индекс для быстрого получения последнего ID
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_chat ON messages(user_id, chat_id, msg_id)")
            conn.commit()

    def save_message(self, msg: MessageData) -> bool:
        """Сохраняет сообщение. Использует INSERT OR REPLACE для обработки дубликатов/обновлений."""
        try:
            with self._get_connection() as conn:
                # В SQLite нет прямого BOOLEAN, используем 0/1
                conn.execute("""
                    INSERT OR REPLACE INTO messages (
                        chat_id, msg_id, user_id, date, author_name, author_username,
                    text, media_type, is_reply, reply_to_msg_id, is_forward,
                        fwd_from_id, fwd_from_name, edit_date, reactions, 
                        original_msg_json, chat_title, schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.chat_id,
                    msg.msg_id,
                    msg.author_id,
                    msg.date.isoformat() if msg.date else None,
                    msg.author_name,
                    msg.author_username,
                    msg.text,
                    msg.media_type,
                    1 if msg.is_reply else 0,
                    msg.reply_to_msg_id,
                    1 if msg.is_forward else 0,
                    msg.fwd_from_id,
                    msg.fwd_from_name,
                    msg.edit_date.isoformat() if msg.edit_date else None,
                    json.dumps(msg.reactions) if msg.reactions else None,
                    json.dumps(msg.original_msg.to_dict() if hasattr(msg.original_msg, 'to_dict') else msg.original_msg) if msg.original_msg else None,
                    msg.chat_title,
                    msg.schema_version
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении в БД: {e}")
            return False

    def get_last_msg_id(self, user_id: int, chat_id: int) -> int:
        """Возвращает максимальный msg_id для данного пользователя в данном чате."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT MAX(msg_id) as last_id FROM messages WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            ).fetchone()
            return row['last_id'] if row and row['last_id'] else 0

    def message_exists(self, chat_id: int, msg_id: int) -> bool:
        """Проверяет наличие сообщения по его уникальному ключу (chat_id, msg_id)."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM messages WHERE chat_id = ? AND msg_id = ?",
                (chat_id, msg_id)
            ).fetchone()
            return row is not None

    def get_all_targets(self) -> List[Dict[str, Any]]:
        """Возвращает список всех уникальных пар (user_id, chat_id) с метаданными."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT user_id, chat_id, author_name, author_username, chat_title 
                FROM messages
                GROUP BY user_id, chat_id
            """).fetchall()
            return [dict(row) for row in rows]
            
    def get_author_chats(self, user_id: int) -> List[int]:
        """Получить список ID всех чатов, где есть сообщения этого пользователя."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT chat_id FROM messages WHERE user_id = ?", 
                (user_id,)
            ).fetchall()
            return [row['chat_id'] for row in rows]

    # --- Методы для управления целями синхронизации (Tracking Targets) ---

    def add_sync_target(self, user_id: int, chat_id: int, author_name: str, chat_title: str, mode: str = 'normal', window: int = 0, max_cluster: int = 15):
        """Добавляет пользователя/чат в список активного отслеживания с параметрами."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_targets (user_id, chat_id, author_name, chat_title, export_mode, window_size, max_cluster, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, author_name, chat_title, mode, window, max_cluster, datetime.now().isoformat()))
            conn.commit()

    def get_active_sync_targets(self) -> List[Dict[str, Any]]:
        """Возвращает список всех целей, отмеченных для синхронизации."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sync_targets WHERE is_active = 1").fetchall()
            return [dict(row) for row in rows]

    def get_unique_sync_users(self) -> List[Dict[str, Any]]:
        """Возвращает список уникальных пользователей из целей синхронизации."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT user_id, author_name 
                FROM sync_targets 
                WHERE is_active = 1
                ORDER BY author_name ASC
            """).fetchall()
            return [dict(row) for row in rows]

    def remove_sync_target(self, user_id: int, chat_id: int):
        """Полностью удаляет цель из синхронизации (данные в 'messages' остаются)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sync_targets WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
            conn.commit()

    def update_sync_timestamp(self, user_id: int, chat_id: int):
        """Обновляет время последней синхронизации."""
        with self._get_connection() as conn:
            conn.execute("UPDATE sync_targets SET last_synced_at = ? WHERE user_id = ? AND chat_id = ?", (datetime.now().isoformat(), user_id, chat_id))
            conn.commit()

    def delete_user_data(self, user_id: int):
        """Полностью удаляет все данные пользователя из БД (сообщения и цели синхронизации)."""
        with self._get_connection() as conn:
            # Удаляем сообщения
            res_msgs = conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            msg_count = res_msgs.rowcount
            # Удаляем цели синхронизации
            res_targets = conn.execute("DELETE FROM sync_targets WHERE user_id = ?", (user_id,))
            target_count = res_targets.rowcount
            conn.commit()
            return msg_count, target_count

    def close(self):
        # В этой реализации соединение открывается/закрывается при каждом вызове (через контекстный менеджер),
        # но мы оставляем метод для совместимости с интерфейсом.
        pass
