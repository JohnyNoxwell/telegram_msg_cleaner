import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Optional

from ...core.models.message import MessageData, SCHEMA_VERSION

logger = logging.getLogger(__name__)


class SQLiteWritePathMixin:
    async def save_message(self, msg: MessageData, target_id: Optional[int] = None) -> bool:
        """Queues a single message for background saving."""
        await self._ensure_worker_started()
        await self._write_queue.put((msg, target_id))
        await self.flush()
        return True

    async def save_messages(self, msgs: List[MessageData], target_id: Optional[int] = None) -> int:
        """Queues a batch of messages for background saving."""
        await self._ensure_worker_started()
        for msg in msgs:
            await self._write_queue.put((msg, target_id))
        await self.flush()
        return len(msgs)

    def _save_message_sync(self, msg: MessageData, target_id: Optional[int] = None) -> bool:
        try:
            with self._write_transaction() as conn:
                self._save_msg_internal(conn, msg, target_id)
            return True
        except Exception as e:
            logger.error(f"Error saving message {msg.message_id} in {msg.chat_id}: {e}")
            return False

    async def _background_writer(self):
        """Background loop that commits queued messages in large batches."""
        logger.debug("SQLite Background Writer started.")
        while not self._shutdown_event.is_set() or not self._write_queue.empty():
            items = []
            try:
                timeout = 0.5 if not self._shutdown_event.is_set() else 0.05
                try:
                    item = await asyncio.wait_for(self._write_queue.get(), timeout=timeout)
                    items.append(item)
                    while len(items) < 500 and not self._write_queue.empty():
                        items.append(self._write_queue.get_nowait())
                except (asyncio.TimeoutError, asyncio.QueueEmpty):
                    pass

                if items:
                    await asyncio.to_thread(self._save_batches_by_target, items)
                    for _ in range(len(items)):
                        self._write_queue.task_done()
                    logger.debug(f"Background Writer committed {len(items)} items.")

                if self._shutdown_event.is_set() and self._write_queue.empty():
                    break

            except Exception as e:
                logger.error(f"Error in background writer commit: {e}")
                await asyncio.sleep(1)
        logger.debug("SQLite Background Writer stopped.")

    def _save_batches_by_target(self, items: List[tuple[MessageData, Optional[int]]]) -> int:
        """Saves queued items efficiently in one transaction."""
        try:
            saved_count = 0
            with self._write_transaction() as conn:
                for msg, target_id in items:
                    self._save_msg_internal(conn, msg, target_id)
                    saved_count += 1
            return saved_count
        except Exception as e:
            logger.error(f"Error saving batch of messages with attribution: {e}")
            return 0

    def _save_msg_internal(self, conn, msg: MessageData, target_id: Optional[int] = None):
        """Executes normalized UPSERTs for a message and sync state."""
        payload_hash = msg.get_payload_hash()
        existing_hash_row = conn.execute(
            "SELECT payload_hash FROM messages WHERE chat_id = ? AND message_id = ?",
            (msg.chat_id, msg.message_id)
        ).fetchone()

        if target_id is not None:
            self._ensure_target_link_in_conn(conn, msg.chat_id, msg.message_id, target_id)

        if existing_hash_row and existing_hash_row["payload_hash"] == payload_hash:
            return

        data = msg.to_dict()
        raw = self._normalize_raw_payload(data.get("raw_payload", {}))

        if data["user_id"]:
            self._upsert_user_from_payload_in_conn(conn, data["user_id"], raw)

        self._upsert_chat_from_payload_in_conn(conn, data["chat_id"], raw)
        self._upsert_context_link_in_conn(conn, data["message_id"], data.get("reply_to_id"))
        self._upsert_message_row_in_conn(conn, data, payload_hash)
        self._update_sync_state_for_message_in_conn(conn, data["chat_id"], data["message_id"], target_id)

    def _normalize_raw_payload(self, raw):
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return raw

    def _json_serial(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.hex()
        return f"<<Unserializable: {type(obj)}>>"

    def _ensure_target_link_in_conn(self, conn, chat_id: int, message_id: int, target_id: int):
        conn.execute("""
            INSERT OR IGNORE INTO message_target_links (chat_id, message_id, target_user_id)
            VALUES (?, ?, ?)
        """, (chat_id, message_id, target_id))

    def _upsert_user_from_payload_in_conn(self, conn, user_id: int, raw: dict):
        first_name = raw.get("first_name") or ""
        last_name = raw.get("last_name") or ""
        username = raw.get("username") or ""
        phone = raw.get("phone") or ""

        sender = raw.get("sender") or raw.get("_sender") or {}
        if isinstance(sender, dict):
            first_name = first_name or sender.get("first_name", "")
            last_name = last_name or sender.get("last_name", "")
            username = username or sender.get("username", "")
            phone = phone or sender.get("phone", "")

        self._upsert_user_in_conn(conn, user_id, first_name, last_name, username, phone)

    def _upsert_chat_from_payload_in_conn(self, conn, chat_id: int, raw: dict):
        chat_title = raw.get("chat_title") or raw.get("title") or ""
        chat_type = raw.get("chat_type") or raw.get("_") or "Channel/Group"
        self._upsert_chat_in_conn(conn, chat_id, chat_title, chat_type)

    def _upsert_context_link_in_conn(self, conn, message_id: int, reply_to_id: Optional[int]):
        if reply_to_id:
            conn.execute("""
                INSERT OR REPLACE INTO message_context_links (message_id, context_message_id, link_type)
                VALUES (?, ?, ?)
            """, (message_id, reply_to_id, "reply"))

    def _upsert_message_row_in_conn(self, conn, data: dict, payload_hash: str):
        conn.execute("""
            INSERT OR REPLACE INTO messages (
                chat_id, message_id, user_id, author_name, timestamp, text,
                media_type, reply_to_id, fwd_from_id,
                context_group_id, raw_payload, payload_hash, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["chat_id"], data["message_id"], data["user_id"], data["author_name"],
            data["timestamp"], data["text"],
            data["media_type"], data["reply_to_id"], data["fwd_from_id"],
            data["context_group_id"],
            json.dumps(data["raw_payload"], ensure_ascii=False, default=self._json_serial),
            payload_hash,
            SCHEMA_VERSION,
        ))

    def _update_sync_state_for_message_in_conn(self, conn, chat_id: int, message_id: int, target_id: Optional[int]):
        now = int(time.time())
        conn.execute("""
            INSERT INTO sync_state (chat_id, last_msg_id, last_sync_timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                last_msg_id = MAX(last_msg_id, excluded.last_msg_id),
                last_sync_timestamp = excluded.last_sync_timestamp
        """, (chat_id, message_id, now))

        if target_id is not None:
            conn.execute("""
                UPDATE sync_targets
                SET last_msg_id = MAX(last_msg_id, ?)
                WHERE user_id = ? AND chat_id = ?
            """, (message_id, target_id, chat_id))
