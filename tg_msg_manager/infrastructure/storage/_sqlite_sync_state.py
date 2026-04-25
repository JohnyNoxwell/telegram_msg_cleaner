import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class SQLiteSyncStateMixin:
    def update_sync_tail(self, chat_id: int, user_id: int, tail_id: int, is_complete: bool = False):
        with self._write_transaction() as conn:
            conn.execute("""
                UPDATE sync_targets
                SET tail_msg_id = ?, is_complete = ?, last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (tail_id, 1 if is_complete else 0, int(time.time()), user_id, chat_id))

    def update_last_msg_id(self, chat_id: int, user_id: int, last_msg_id: int):
        with self._write_transaction() as conn:
            conn.execute("""
                UPDATE sync_targets
                SET last_msg_id = MAX(last_msg_id, ?), last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (last_msg_id, int(time.time()), user_id, chat_id))

    def update_last_sync_at(self, chat_id: int, user_id: int):
        with self._write_transaction() as conn:
            conn.execute("""
                UPDATE sync_targets SET last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (int(time.time()), user_id, chat_id))

    def get_last_target_msg_id(self, chat_id: int, user_id: int) -> int:
        status = self.get_sync_status(chat_id, user_id)
        return status["last_msg_id"]

    def upsert_user(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        phone: Optional[str] = None,
    ):
        with self._write_transaction() as conn:
            self._upsert_user_in_conn(conn, user_id, first_name, last_name, username, phone)

    def _upsert_user_in_conn(
        self,
        conn,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        phone: Optional[str] = None,
    ):
        conn.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, phone)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                username = COALESCE(excluded.username, users.username),
                phone = COALESCE(excluded.phone, users.phone)
        """, (user_id, first_name, last_name, username, phone))

    def register_target(
        self,
        user_id: int,
        author_name: str,
        chat_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        deep_mode: bool = False,
        recursive_depth: int = 0,
    ):
        now = int(time.time())
        with self._write_transaction() as conn:
            conn.execute("""
                INSERT INTO sync_targets (user_id, chat_id, author_name, added_at, last_sync_at, deep_mode, recursive_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    author_name = excluded.author_name,
                    deep_mode = MAX(sync_targets.deep_mode, excluded.deep_mode),
                    recursive_depth = MAX(sync_targets.recursive_depth, excluded.recursive_depth),
                    last_sync_at = COALESCE(excluded.last_sync_at, sync_targets.last_sync_at)
            """, (user_id, chat_id, author_name, now, now, 1 if deep_mode else 0, recursive_depth))
            self._upsert_user_in_conn(conn, user_id, first_name, last_name, username)

    def upsert_chat(self, chat_id: int, title: str, chat_type: Optional[str] = None):
        with self._write_transaction() as conn:
            self._upsert_chat_in_conn(conn, chat_id, title, chat_type)

    def _upsert_chat_in_conn(self, conn, chat_id: int, title: str, chat_type: Optional[str] = None):
        conn.execute("""
            INSERT INTO chats (chat_id, title, type)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = COALESCE(NULLIF(excluded.title, ''), chats.title),
                type = COALESCE(excluded.type, chats.type)
        """, (chat_id, title, chat_type))

    def delete_messages(self, chat_id: int, message_ids: List[int]) -> int:
        if not message_ids:
            return 0
        placeholders = ', '.join(['?'] * len(message_ids))
        with self._write_transaction() as conn:
            conn.execute(
                f"DELETE FROM message_target_links WHERE chat_id = ? AND message_id IN ({placeholders})",
                (chat_id, *message_ids)
            )
            res = conn.execute(
                f"DELETE FROM messages WHERE chat_id = ? AND message_id IN ({placeholders})",
                (chat_id, *message_ids)
            )
            return res.rowcount

    def delete_user_data(self, user_id: int) -> tuple[int, int]:
        with self._write_transaction() as conn:
            conn.execute("DELETE FROM message_target_links WHERE target_user_id = ?", (user_id,))
            res = conn.execute("""
                DELETE FROM messages
                WHERE NOT EXISTS (
                    SELECT 1 FROM message_target_links
                    WHERE message_target_links.chat_id = messages.chat_id
                    AND message_target_links.message_id = messages.message_id
                )
            """)
            deleted_msgs = res.rowcount
            conn.execute("DELETE FROM sync_targets WHERE user_id = ?", (user_id,))
            return deleted_msgs, 0

    def enqueue_retry_task(self, task_id: str, chat_id: int, task_type: str, error: str):
        next_retry = int(time.time()) + 300
        with self._write_transaction() as conn:
            conn.execute("""
                INSERT INTO retry_queue (task_id, chat_id, task_type, last_error, next_retry_timestamp, retry_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(task_id) DO UPDATE SET
                    retry_count = retry_count + 1,
                    last_error = excluded.last_error,
                    next_retry_timestamp = excluded.next_retry_timestamp
            """, (task_id, chat_id, task_type, error, next_retry))

    def remove_retry_task(self, task_id: str):
        with self._write_transaction() as conn:
            conn.execute("DELETE FROM retry_queue WHERE task_id = ?", (task_id,))
