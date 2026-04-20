import sqlite3
import json
import logging
import time
import asyncio
import threading
from typing import List, Optional
from datetime import datetime
from .interface import BaseStorage
from ...core.models.message import MessageData, SCHEMA_VERSION

logger = logging.getLogger(__name__)

class SQLiteStorage(BaseStorage):
    """
    High-performance SQLite implementation of BaseStorage.
    Uses WAL mode for concurrency and atomic transactions for speed.
    """

    def __init__(self, db_path: str = "messages.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = self._get_connection()
        self._init_db()
        
        # Async background writer
        self._write_queue = asyncio.Queue()
        self._worker_task = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Starts the background writer task."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._background_writer())

    async def close(self):
        """Flushes the queue and stops the background writer."""
        self._shutdown_event.set()
        if self._worker_task:
            await self._worker_task
            self._worker_task = None
        self._conn.close()

    def _get_connection(self):
        """Creates a new connection and ensures WAL mode is active."""
        # Using check_same_thread=False because we will use asyncio.to_thread
        # but we must ensure we don't concurrently access it without a lock if it was multi-threaded.
        # However, asyncio.to_thread runs in a thread pool, so we need to be careful.
        # SQLite with WAL and check_same_thread=False is generally okay for serial access.
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the database schema if it doesn't exist."""
        conn = self._conn
        # Table for storing messages
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                author_name TEXT,
                timestamp INTEGER,
                text TEXT,
                media_type TEXT,
                reply_to_id INTEGER,
                fwd_from_id INTEGER,
                context_group_id TEXT,
                raw_payload TEXT,
                payload_hash TEXT,
                schema_version INTEGER,
                PRIMARY KEY (chat_id, message_id)
            )
        """)
        
        # Table for tracking sync state per chat
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                chat_id INTEGER PRIMARY KEY,
                last_msg_id INTEGER DEFAULT 0,
                last_sync_timestamp INTEGER
            )
        """)
        
        # Table for persistent retry queue
        conn.execute("""
            CREATE TABLE IF NOT EXISTS retry_queue (
                task_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                task_type TEXT,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                next_retry_timestamp INTEGER
            )
        """)
        
        # Table for primary sync targets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_targets (
                user_id INTEGER PRIMARY KEY,
                author_name TEXT,
                chat_id INTEGER,
                last_msg_id INTEGER DEFAULT 0,
                added_at INTEGER
            )
        """)
        # Migration: Add last_msg_id to sync_targets if it doesn't exist
        try:
            conn.execute("ALTER TABLE sync_targets ADD COLUMN last_msg_id INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Already exists
            
        conn.commit()
        logger.info(f"SQLite Storage initialized at {self.db_path}")

    async def save_message(self, msg: MessageData) -> bool:
        """Queues a single message for background saving."""
        await self._write_queue.put(msg)
        return True

    def _save_message_sync(self, msg: MessageData) -> bool:
        try:
            with self._lock:
                with self._conn:
                    self._save_msg_internal(self._conn, msg)
            return True
        except Exception as e:
            logger.error(f"Error saving message {msg.message_id} in {msg.chat_id}: {e}")
            return False

    async def save_messages(self, msgs: List[MessageData]) -> int:
        """Queues a batch of messages for background saving."""
        for msg in msgs:
            await self._write_queue.put(msg)
        return len(msgs)

    async def _background_writer(self):
        """Background loop that commits queued messages in large batches."""
        logger.debug("SQLite Background Writer started.")
        while not self._shutdown_event.is_set() or not self._write_queue.empty():
            batch = []
            try:
                # 1. Collect a batch from the queue
                timeout = 0.5 if not self._shutdown_event.is_set() else 0.05
                try:
                    # Wait for at least one message
                    item = await asyncio.wait_for(self._write_queue.get(), timeout=timeout)
                    batch.append(item)
                    # Pull more messages if available immediately
                    while len(batch) < 500 and not self._write_queue.empty():
                        batch.append(self._write_queue.get_nowait())
                except (asyncio.TimeoutError, asyncio.QueueEmpty):
                    pass

                if batch:
                    await asyncio.to_thread(self._save_messages_sync, batch)
                    for _ in range(len(batch)):
                        self._write_queue.task_done()
                    logger.debug(f"Background Writer committed {len(batch)} messages.")
                
                if self._shutdown_event.is_set() and self._write_queue.empty():
                    break
                    
            except Exception as e:
                logger.error(f"Error in background writer commit: {e}")
                await asyncio.sleep(1)
        logger.debug("SQLite Background Writer stopped.")

    def _save_messages_sync(self, msgs: List[MessageData]) -> int:
        try:
            saved_count = 0
            with self._lock:
                with self._conn:
                    for msg in msgs:
                        self._save_msg_internal(self._conn, msg)
                        saved_count += 1
            return saved_count
        except Exception as e:
            logger.error(f"Error saving batch of messages: {e}")
            return 0

    def _save_msg_internal(self, conn, msg: MessageData):
        """
        Helper to execute the UPSERT query.
        Implements selective update: only writes to DB if hash changed or message is new.
        """
        payload_hash = msg.get_payload_hash()
        
        # 3.1.1: Pre-check mechanism
        existing_hash_row = conn.execute(
            "SELECT payload_hash FROM messages WHERE chat_id = ? AND message_id = ?",
            (msg.chat_id, msg.message_id)
        ).fetchone()
        
        if existing_hash_row and existing_hash_row["payload_hash"] == payload_hash:
            # 3.1.2: Skip update if content is identical
            return

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, bytes):
                return obj.hex()
            return f"<<Unserializable: {type(obj)}>>"

        data = msg.to_dict()
        conn.execute("""
            INSERT OR REPLACE INTO messages (
                chat_id, message_id, user_id, author_name, timestamp, text, 
                media_type, reply_to_id, fwd_from_id, 
                context_group_id, raw_payload, payload_hash, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["chat_id"], data["message_id"], data["user_id"], data["author_name"],
            int(data["timestamp"].timestamp()) if isinstance(data["timestamp"], datetime) else data["timestamp"], 
            data["text"],
            data["media_type"], data["reply_to_id"], data["fwd_from_id"],
            data["context_group_id"], json.dumps(data["raw_payload"], ensure_ascii=False, default=json_serial),
            payload_hash, SCHEMA_VERSION
        ))
        
        # 1. Update global sync state to track the latest msg_id in the whole chat
        conn.execute("""
            INSERT INTO sync_state (chat_id, last_msg_id, last_sync_timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                last_msg_id = MAX(last_msg_id, excluded.last_msg_id),
                last_sync_timestamp = excluded.last_sync_timestamp
        """, (data["chat_id"], data["message_id"], int(datetime.now().timestamp())))
        
        # 2. Update target-specific sync state if this message belongs to a primary target user
        conn.execute("""
            UPDATE sync_targets 
            SET last_msg_id = MAX(last_msg_id, ?)
            WHERE user_id = ? AND chat_id = ?
        """, (data["message_id"], data["user_id"], data["chat_id"]))

    def get_message(self, chat_id: int, message_id: int) -> Optional[MessageData]:
        """Retrieves a message and reconstructs the MessageData object."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id)
            ).fetchone()
            
            if not row:
                return None
            
            data = dict(row)
            return MessageData(
                message_id=data["message_id"],
                chat_id=data["chat_id"],
                user_id=data["user_id"],
                author_name=data.get("author_name"),
                timestamp=datetime.fromtimestamp(data["timestamp"]),
                text=data.get("text"),
                media_type=data.get("media_type"),
                reply_to_id=data.get("reply_to_id"),
                fwd_from_id=data.get("fwd_from_id"),
                context_group_id=data.get("context_group_id"),
                raw_payload=json.loads(data["raw_payload"])
            )

    def message_exists(self, chat_id: int, message_id: int) -> bool:
        """Quickly check for existence."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM messages WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id)
            ).fetchone()
            return row is not None

    def get_last_msg_id(self, chat_id: int) -> int:
        """Gets the highest known msg_id from the sync_state table (global chat level)."""
        row = self._conn.execute(
            "SELECT last_msg_id FROM sync_state WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
        if row:
            return row["last_msg_id"]
        return 0

    def get_last_target_msg_id(self, chat_id: int, user_id: int) -> int:
        """Gets the highest known msg_id for a specific target user in a specific chat."""
        row = self._conn.execute(
            "SELECT last_msg_id FROM sync_targets WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        ).fetchone()
        if row:
            return row["last_msg_id"]
        return 0

    def filter_existing_ids(self, chat_id: int, message_ids: List[int]) -> List[int]:
        """Returns only IDs that do NOT exist in the database."""
        if not message_ids:
            return []
        
        # Batch check for performance
        placeholders = ', '.join(['?'] * len(message_ids))
        rows = self._conn.execute(
            f"SELECT message_id FROM messages WHERE chat_id = ? AND message_id IN ({placeholders})",
            (chat_id, *message_ids)
        ).fetchall()
        
        existing = {row['message_id'] for row in rows}
        return [mid for mid in message_ids if mid not in existing]

    def get_outdated_chats(self, threshold_seconds: int) -> List[int]:
        """Returns chat_ids where last_sync_timestamp is older than threshold."""
        cutoff = int(datetime.now().timestamp()) - threshold_seconds
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT chat_id FROM sync_state WHERE last_sync_timestamp < ?",
                (cutoff,)
            ).fetchall()
            return [row["chat_id"] for row in rows]

    def get_message_count(self, chat_id: int) -> int:
        """Returns total messages for a chat."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE chat_id = ?",
                (chat_id,)
            ).fetchone()
            return row['count'] if row else 0

    def delete_messages(self, chat_id: int, message_ids: List[int]) -> int:
        if not message_ids:
            return 0
        with self._get_connection() as conn:
            placeholders = ', '.join(['?'] * len(message_ids))
            res = conn.execute(
                f"DELETE FROM messages WHERE chat_id = ? AND message_id IN ({placeholders})",
                (chat_id, *message_ids)
            )
            count = res.rowcount
            conn.commit()
            return count

    def get_all_message_ids_for_chat(self, chat_id: int) -> List[int]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT message_id FROM messages WHERE chat_id = ? ORDER BY message_id DESC",
                (chat_id,)
            ).fetchall()
            return [row['message_id'] for row in rows]

    def get_unique_sync_users(self) -> List[dict]:
        """Returns a list of all unique users found in messages (raw)."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT user_id, author_name
                FROM messages 
                GROUP BY user_id
                ORDER BY author_name ASC
            """).fetchall()
            return [{"user_id": row["user_id"], "author_name": row["author_name"]} for row in rows]

    def register_target(self, user_id: int, author_name: str, chat_id: int):
        """Registers a primary target for sync."""
        now = int(time.time())
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sync_targets (user_id, author_name, chat_id, added_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    author_name = excluded.author_name,
                    chat_id = excluded.chat_id
            """, (user_id, author_name, chat_id, now))
            conn.commit()

    def get_primary_targets(self) -> List[dict]:
        """Returns only manually requested targets."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sync_targets ORDER BY author_name ASC").fetchall()
            return [dict(row) for row in rows]

    def get_user_messages(self, user_id: int) -> List[MessageData]:
        """
        Returns all messages for a specific user AND their associated context clusters.
        This provides a complete conversation history for the export.
        """
        with self._get_connection() as conn:
            # We fetch everything in clusters where the user has at least one message
            rows = conn.execute("""
                SELECT * FROM messages 
                WHERE context_group_id IN (
                    SELECT DISTINCT context_group_id 
                    FROM messages 
                    WHERE user_id = ? AND context_group_id IS NOT NULL
                )
                OR user_id = ?
                ORDER BY timestamp ASC
            """, (user_id, user_id)).fetchall()
            
            results = []
            for row in rows:
                data = dict(row)
                results.append(MessageData(
                    message_id=data["msg_id"] if "msg_id" in data else data["message_id"],
                    chat_id=data["chat_id"],
                    user_id=data["user_id"],
                    author_name=data.get("author_name"),
                    timestamp=datetime.fromtimestamp(data["timestamp"]),
                    text=data.get("text"),
                    media_type=data.get("media_type"),
                    reply_to_id=data.get("reply_to_id"),
                    fwd_from_id=data.get("fwd_from_id"),
                    context_group_id=data.get("context_group_id"),
                    raw_payload=json.loads(data["raw_payload"])
                ))
            return results

    def delete_user_data(self, user_id: int) -> tuple[int, int]:
        """
        Removes all messages for a user and CASCADE deletes their context clusters.
        Ensures 'ghost' context messages from other users are also purged.
        """
        with self._get_connection() as conn:
            # 1. Find all clusters associated with this user
            rows = conn.execute(
                "SELECT DISTINCT context_group_id FROM messages WHERE user_id = ? AND context_group_id IS NOT NULL", 
                (user_id,)
            ).fetchall()
            cluster_ids = [row["context_group_id"] for row in rows]
            
            deleted_msgs = 0
            if cluster_ids:
                # 2. Delete all messages in these clusters (Cascade)
                placeholders = ', '.join(['?'] * len(cluster_ids))
                res = conn.execute(
                    f"DELETE FROM messages WHERE context_group_id IN ({placeholders})",
                    tuple(cluster_ids)
                )
                deleted_msgs += res.rowcount
                logger.info(f"Purged {res.rowcount} messages from {len(cluster_ids)} context clusters for user {user_id}")

            # 3. Delete messages authored by user (if any left outside clusters)
            res_user = conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            deleted_msgs += res_user.rowcount
            
            # 4. Remove from sync_targets
            conn.execute("DELETE FROM sync_targets WHERE user_id = ?", (user_id,))
            
            conn.commit()
            return deleted_msgs, 0

    def enqueue_retry_task(self, task_id: str, chat_id: int, task_type: str, error: str):
        """Adds or updates a task in the retry queue."""
        next_retry = int(time.time()) + 300  # Default 5 min delay
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO retry_queue (task_id, chat_id, task_type, last_error, next_retry_timestamp, retry_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(task_id) DO UPDATE SET
                    retry_count = retry_count + 1,
                    last_error = excluded.last_error,
                    next_retry_timestamp = excluded.next_retry_timestamp
            """, (task_id, chat_id, task_type, error, next_retry))
            conn.commit()

    def get_retry_tasks(self) -> List[dict]:
        """Returns all tasks due for retry."""
        now = int(time.time())
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM retry_queue WHERE next_retry_timestamp <= ?",
                (now,)
            ).fetchall()
            return [dict(row) for row in rows]

    def remove_retry_task(self, task_id: str):
        """Removes a task from the retry queue."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM retry_queue WHERE task_id = ?", (task_id,))
            conn.commit()
