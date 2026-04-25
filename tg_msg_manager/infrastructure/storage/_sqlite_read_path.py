import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional

from ...core.models.message import MessageData

logger = logging.getLogger(__name__)


class SQLiteReadPathMixin:
    def _row_to_message(self, row: sqlite3.Row) -> MessageData:
        data = dict(row)
        msg_id = data.get("message_id") if "message_id" in data else data.get("msg_id")
        return MessageData(
            message_id=msg_id,
            chat_id=data["chat_id"],
            user_id=data["user_id"],
            author_name=data.get("author_name"),
            timestamp=datetime.fromtimestamp(data["timestamp"]),
            text=data.get("text"),
            media_type=data.get("media_type"),
            reply_to_id=data.get("reply_to_id"),
            fwd_from_id=data.get("fwd_from_id"),
            context_group_id=data.get("context_group_id"),
            raw_payload=json.loads(data["raw_payload"]),
        )

    def get_message(self, chat_id: int, message_id: int) -> Optional[MessageData]:
        with self._read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id)
            ).fetchone()
            return self._row_to_message(row) if row else None

    def message_exists(self, chat_id: int, message_id: int) -> bool:
        with self._read_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM messages WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id)
            ).fetchone()
            return row is not None

    def get_last_msg_id(self, chat_id: int) -> int:
        with self._read_connection() as conn:
            row = conn.execute(
                "SELECT last_msg_id FROM sync_state WHERE chat_id = ?",
                (chat_id,)
            ).fetchone()
            return row["last_msg_id"] if row else 0

    def get_sync_status(self, chat_id: int, user_id: int) -> dict:
        with self._read_connection() as conn:
            row = conn.execute("""
                SELECT last_msg_id, tail_msg_id, is_complete, deep_mode, recursive_depth, author_name
                FROM sync_targets
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id)).fetchone()
            if row:
                return dict(row)
        return {
            "last_msg_id": 0,
            "tail_msg_id": 0,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
            "last_sync_at": 0,
        }

    def filter_existing_ids(self, chat_id: int, message_ids: List[int]) -> List[int]:
        if not message_ids:
            return []
        placeholders = ', '.join(['?'] * len(message_ids))
        with self._read_connection() as conn:
            rows = conn.execute(
                f"SELECT message_id FROM messages WHERE chat_id = ? AND message_id IN ({placeholders})",
                (chat_id, *message_ids)
            ).fetchall()
        existing = {row['message_id'] for row in rows}
        return [mid for mid in message_ids if mid not in existing]

    def get_outdated_chats(self, threshold_seconds: int) -> List[tuple]:
        cutoff = int(datetime.now().timestamp()) - threshold_seconds
        with self._read_connection() as conn:
            rows = conn.execute("""
                SELECT chat_id, user_id FROM sync_targets
                WHERE is_complete = 0 OR COALESCE(last_sync_at, 0) < ?
            """, (cutoff,)).fetchall()
            chat_rows = conn.execute("""
                SELECT chat_id FROM sync_state
                WHERE COALESCE(last_sync_timestamp, 0) < ?
            """, (cutoff,)).fetchall()

        results = {(r['chat_id'], r['user_id']) for r in rows}
        for r in chat_rows:
            results.add((r['chat_id'], r['chat_id']))
        return list(results)

    def get_message_count(self, chat_id: int, target_id: Optional[int] = None) -> int:
        with self._read_connection() as conn:
            if target_id:
                row = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM message_target_links l
                    JOIN messages m ON l.chat_id = m.chat_id AND l.message_id = m.message_id
                    WHERE l.chat_id = ? AND l.target_user_id = ?
                """, (chat_id, target_id)).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) as count FROM messages WHERE chat_id = ?",
                    (chat_id,)
                ).fetchone()
            return row['count'] if row else 0

    def get_all_message_ids_for_chat(self, chat_id: int) -> List[int]:
        with self._read_connection() as conn:
            rows = conn.execute(
                "SELECT message_id FROM messages WHERE chat_id = ? ORDER BY message_id DESC",
                (chat_id,)
            ).fetchall()
            return [row['message_id'] for row in rows]

    def get_unique_sync_users(self) -> List[dict]:
        with self._read_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT user_id, author_name
                FROM messages
                GROUP BY user_id
                ORDER BY author_name ASC
            """).fetchall()
            return [{"user_id": row["user_id"], "author_name": row["author_name"]} for row in rows]

    def get_user(self, user_id: int) -> Optional[dict]:
        with self._read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_primary_targets(self) -> List[dict]:
        try:
            with self._read_connection() as conn:
                rows = conn.execute("""
                    SELECT
                        t.*, u.username, u.first_name, u.last_name, c.title as chat_title,
                        (SELECT COUNT(*)
                         FROM message_target_links l
                         JOIN messages m ON l.chat_id = m.chat_id AND l.message_id = m.message_id
                         WHERE l.target_user_id = t.user_id AND m.user_id = t.user_id) as user_msg_count,
                        (SELECT COUNT(*)
                         FROM message_target_links l
                         JOIN messages m ON l.chat_id = m.chat_id AND l.message_id = m.message_id
                         WHERE l.target_user_id = t.user_id AND m.user_id != t.user_id) as context_msg_count
                    FROM sync_targets t
                    LEFT JOIN users u ON t.user_id = u.user_id
                    LEFT JOIN chats c ON t.chat_id = c.chat_id
                    ORDER BY t.author_name ASC
                """).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return []
            raise

    def has_target_link(self, chat_id: int, message_id: int, target_id: int) -> bool:
        with self._read_connection() as conn:
            res = conn.execute("""
                SELECT 1 FROM message_target_links
                WHERE chat_id = ? AND message_id = ? AND target_user_id = ?
                LIMIT 1
            """, (chat_id, message_id, target_id)).fetchone()
            return res is not None

    def get_user_messages(self, user_id: int) -> List[MessageData]:
        with self._read_connection() as conn:
            rows = conn.execute("""
                SELECT m.* FROM messages m
                JOIN message_target_links l ON m.chat_id = l.chat_id AND m.message_id = l.message_id
                WHERE l.target_user_id = ?
                ORDER BY m.timestamp ASC, m.message_id ASC
            """, (user_id,)).fetchall()
            return [self._row_to_message(row) for row in rows]

    def get_retry_tasks(self) -> List[dict]:
        now = int(datetime.now().timestamp())
        with self._read_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM retry_queue WHERE next_retry_timestamp <= ?",
                (now,)
            ).fetchall()
            return [dict(row) for row in rows]
