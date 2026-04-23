import sqlite3
import json
import logging
import time
import asyncio
import threading
from typing import List, Optional, Any
from datetime import datetime
from .interface import BaseStorage
from ...core.models.message import MessageData, SCHEMA_VERSION

logger = logging.getLogger(__name__)

class SQLiteStorage(BaseStorage):
    """
    High-performance SQLite implementation of BaseStorage.
    Uses WAL mode for concurrency and atomic transactions for speed.
    """

    def __init__(self, db_path: str = "messages.db", process_manager: Optional[Any] = None):
        self.db_path = db_path
        self._pm = process_manager
        self._lock = threading.Lock()
        self._conn = self._get_connection()
        self._init_db()
        
        # Async background writer
        self._write_queue = asyncio.Queue()
        self._worker_task = None
        self._shutdown_event = asyncio.Event()

    def should_stop(self) -> bool:
        """Returns True if a shutdown has been requested internally or via ProcessManager."""
        external_stop = self._pm.shutdown_requested if self._pm else False
        return self._shutdown_event.is_set() or external_stop

    async def start(self):
        """Starts the background writer task."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._background_writer())

    def request_stop(self):
        """Sets the shutdown event to signal workers to stop."""
        self._shutdown_event.set()


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
        
        # New: Normalized tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                phone TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                type TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_context_links (
                message_id INTEGER,
                context_message_id INTEGER,
                link_type TEXT,
                PRIMARY KEY (message_id, context_message_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_target_links (
                chat_id INTEGER,
                message_id INTEGER,
                target_user_id INTEGER,
                PRIMARY KEY (chat_id, message_id, target_user_id)
            )
        """)
        
        # New: Requested Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_user_chat_time ON messages (user_id, chat_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_standalone_id ON messages (message_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mt_link_target ON message_target_links (target_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_context_group ON messages (context_group_id)")

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
                user_id INTEGER,
                chat_id INTEGER,
                author_name TEXT,
                last_msg_id INTEGER DEFAULT 0,
                tail_msg_id INTEGER DEFAULT 0,
                is_complete INTEGER DEFAULT 0,
                deep_mode INTEGER DEFAULT 0,
                recursive_depth INTEGER DEFAULT 0,
                added_at INTEGER,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        
        # Migration: Add new columns if they don't exist
        for col, col_type in [("last_msg_id", "INTEGER DEFAULT 0"), 
                              ("tail_msg_id", "INTEGER DEFAULT 0"), 
                              ("is_complete", "INTEGER DEFAULT 0"),
                              ("deep_mode", "INTEGER DEFAULT 0"),
                              ("recursive_depth", "INTEGER DEFAULT 0")]:
            try:
                conn.execute(f"ALTER TABLE sync_targets ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass # Already exists
            
        # Version-based Migration Engine
        current_version = conn.execute("PRAGMA user_version").fetchone()[0]
        if current_version < 2:
            logger.info("Running Database Migration: Version 2 (Target Attribution)...")
            self.migrate_existing_links()
            conn.execute("PRAGMA user_version = 2")
            logger.info("Database migration to Version 2 successful.")
        
        if current_version < 3:
            logger.info("Running Database Migration: Version 3 (Composite PK for sync_targets)...")
            self._migrate_sync_targets_to_composite_pk()
            conn.execute("PRAGMA user_version = 3")
            logger.info("Database migration to Version 3 successful.")

        if current_version < 4:
            logger.info("Running Database Migration: Version 4 (Persistent Sync Settings)...")
            try:
                conn.execute("ALTER TABLE sync_targets ADD COLUMN deep_mode INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE sync_targets ADD COLUMN recursive_depth INTEGER DEFAULT 0")
            except Exception as e:
                logger.debug(f"Columns might already exist: {e}")
            conn.execute("PRAGMA user_version = 4")
            logger.info("Database migration to Version 4 successful.")
        else:
            logger.debug(f"Database migration skipped (already at version {current_version}).")

        conn.commit()
        logger.info(f"SQLite Storage initialized at {self.db_path} with target attribution support.")

    async def save_message(self, msg: MessageData, target_id: Optional[int] = None) -> bool:
        """Queues a single message for background saving."""
        await self._write_queue.put((msg, target_id))
        return True

    def _save_message_sync(self, msg: MessageData, target_id: Optional[int] = None) -> bool:
        try:
            with self._lock:
                with self._conn:
                    self._save_msg_internal(self._conn, msg, target_id)
            return True
        except Exception as e:
            logger.error(f"Error saving message {msg.message_id} in {msg.chat_id}: {e}")
            return False

    async def save_messages(self, msgs: List[MessageData], target_id: Optional[int] = None) -> int:
        """Queues a batch of messages for background saving."""
        for msg in msgs:
            await self._write_queue.put((msg, target_id))
        return len(msgs)

    async def _background_writer(self):
        """Background loop that commits queued messages in large batches."""
        logger.debug("SQLite Background Writer started.")
        while not self._shutdown_event.is_set() or not self._write_queue.empty():
            items = []
            try:
                # 1. Collect a batch from the queue
                timeout = 0.5 if not self._shutdown_event.is_set() else 0.05
                try:
                    # Wait for at least one item (msg, target_id)
                    item = await asyncio.wait_for(self._write_queue.get(), timeout=timeout)
                    items.append(item)
                    # Pull more items if available immediately
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
        """Helper to save items efficiently."""
        try:
            saved_count = 0
            with self._lock:
                with self._conn:
                    for msg, target_id in items:
                        self._save_msg_internal(self._conn, msg, target_id)
                        saved_count += 1
            return saved_count
        except Exception as e:
            logger.error(f"Error saving batch of messages with attribution: {e}")
            return 0

    def _save_msg_internal(self, conn, msg: MessageData, target_id: Optional[int] = None):
        """
        Helper to execute the UPSERT query.
        Implements selective update: only writes to DB if hash changed or message is new.
        Populates normalized tables: users, chats, message_target_links.
        """
        payload_hash = msg.get_payload_hash()
        
        # 3.1.1: Pre-check mechanism
        existing_hash_row = conn.execute(
            "SELECT payload_hash FROM messages WHERE chat_id = ? AND message_id = ?",
            (msg.chat_id, msg.message_id)
        ).fetchone()
        
        # Step 1: Always ensure target attribution link exists
        if target_id:
            conn.execute("""
                INSERT OR IGNORE INTO message_target_links (chat_id, message_id, target_user_id)
                VALUES (?, ?, ?)
            """, (msg.chat_id, msg.message_id, target_id))

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
        
        # --- Normalization: Users ---
        raw = data.get("raw_payload", {})
        # Note: raw is already a dict (deserialized in get_message or passed as dict in sync)
        # However, it might be a JSON string if the caller didn't deserialize. 
        # But in _save_messages_sync it comes directly from MessageData objects.
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except: raw = {}

        if data["user_id"]:
            first_name = raw.get("first_name") or ""
            last_name = raw.get("last_name") or ""
            username = raw.get("username") or ""
            phone = raw.get("phone") or ""
            
            # If name is missing from top level, try to find it in nested sender dict
            # Telethon's to_dict() nested structure varies
            sender = raw.get("sender") or raw.get("_sender") or {}
            if isinstance(sender, dict):
                first_name = first_name or sender.get("first_name", "")
                last_name = last_name or sender.get("last_name", "")
                username = username or sender.get("username", "")
                phone = phone or sender.get("phone", "")

            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, first_name, last_name, username, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (data["user_id"], first_name, last_name, username, phone))

        # --- Normalization: Chats ---
        # Chat title is usually available during sync context or in raw
        chat_title = raw.get("chat_title") or raw.get("title") or ""
        chat_type = raw.get("chat_type") or raw.get("_") or "Channel/Group"
        conn.execute("""
            INSERT OR REPLACE INTO chats (chat_id, title, type)
            VALUES (?, ?, ?)
        """, (data["chat_id"], chat_title, chat_type))

        # --- Normalization: Context Links ---
        if data.get("reply_to_id"):
            conn.execute("""
                INSERT OR REPLACE INTO message_context_links (message_id, context_message_id, link_type)
                VALUES (?, ?, ?)
            """, (data["message_id"], data["reply_to_id"], "reply"))

        # --- Main Message Save ---
        conn.execute("""
            INSERT OR REPLACE INTO messages (
                chat_id, message_id, user_id, author_name, timestamp, text, 
                media_type, reply_to_id, fwd_from_id, 
                context_group_id, raw_payload, payload_hash, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["chat_id"], data["message_id"], data["user_id"], data["author_name"],
            data["timestamp"], 
            data["text"],
            data["media_type"], data["reply_to_id"], data["fwd_from_id"],
            data["context_group_id"], json.dumps(data["raw_payload"], ensure_ascii=False, default=json_serial),
            payload_hash, SCHEMA_VERSION
        ))
        
        # 1. Update global sync state
        conn.execute("""
            INSERT INTO sync_state (chat_id, last_msg_id, last_sync_timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                last_msg_id = MAX(last_msg_id, excluded.last_msg_id),
                last_sync_timestamp = excluded.last_sync_timestamp
        """, (data["chat_id"], data["message_id"], int(time.time())))
        
        # 2. Update target-specific sync state
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

    def get_sync_status(self, chat_id: int, user_id: int) -> dict:
        """Returns complex sync status including tail, completion flag and saved settings."""
        row = self._conn.execute("""
            SELECT last_msg_id, tail_msg_id, is_complete, deep_mode, recursive_depth, author_name
            FROM sync_targets 
            WHERE user_id = ? AND chat_id = ?
        """, (user_id, chat_id)).fetchone()
        
        if row:
            return dict(row)
        return {"last_msg_id": 0, "tail_msg_id": 0, "is_complete": 0, "deep_mode": 0, "recursive_depth": 0}

    def update_sync_tail(self, chat_id: int, user_id: int, tail_id: int, is_complete: bool = False):
        """Updates the historical scan boundary for resume support."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_targets 
                SET tail_msg_id = ?, is_complete = ?, last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (tail_id, 1 if is_complete else 0, int(time.time()), user_id, chat_id))
            conn.commit()

    def update_last_msg_id(self, chat_id: int, user_id: int, last_msg_id: int):
        """Updates the latest message ID for a target."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_targets 
                SET last_msg_id = MAX(last_msg_id, ?), last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (last_msg_id, int(time.time()), user_id, chat_id))
            conn.commit()

    def update_last_sync_at(self, chat_id: int, user_id: int):
        """Simply marks the target as synced now."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_targets SET last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
            """, (int(time.time()), user_id, chat_id))
            conn.commit()

    def get_last_target_msg_id(self, chat_id: int, user_id: int) -> int:
        """Gets the highest known msg_id for a specific target user in a specific chat."""
        status = self.get_sync_status(chat_id, user_id)
        return status["last_msg_id"]

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

    def get_outdated_chats(self, threshold_seconds: int) -> List[tuple]:
        """Returns list of (chat_id, user_id) that need update (old or incomplete)."""
        cutoff = int(datetime.now().timestamp()) - threshold_seconds
        with self._get_connection() as conn:
            # 1. Look for incomplete target scans or those that haven't been synced recently
            rows = conn.execute("""
                SELECT chat_id, user_id FROM sync_targets 
                WHERE is_complete = 0 OR last_sync_at < ? OR added_at < ?
            """, (cutoff, cutoff)).fetchall()
            
            # 2. Also check whole-chat syncs
            chat_rows = conn.execute("""
                SELECT chat_id FROM sync_state 
                WHERE last_sync_timestamp < ?
            """, (cutoff,)).fetchall()
            
            results = set()
            for r in rows:
                results.add((r['chat_id'], r['user_id']))
            for r in chat_rows:
                # Whole chat scan is represented by user_id = chat_id
                results.add((r['chat_id'], r['chat_id']))
                
            return list(results)

    def get_message_count(self, chat_id: int, target_id: Optional[int] = None) -> int:
        """Returns total messages for a chat, optionally filtered by target user."""
        with self._get_connection() as conn:
            if target_id:
                # Count only messages linked to this target via attribution table
                row = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM message_target_links 
                    WHERE chat_id = ? AND target_user_id = ?
                """, (chat_id, target_id)).fetchone()
            else:
                # Count all messages in chat
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
            conn.commit()
            return res.rowcount


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
    def get_user(self, user_id: int) -> Optional[dict]:
        """Retrieves user metadata from the users table."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_user(self, user_id: int, first_name: Optional[str] = None, last_name: Optional[str] = None, username: Optional[str] = None, phone: Optional[str] = None):
        """Persists or updates user metadata in the users table."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, phone)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    last_name = COALESCE(excluded.last_name, users.last_name),
                    username = COALESCE(excluded.username, users.username),
                    phone = COALESCE(excluded.phone, users.phone)
            """, (user_id, first_name, last_name, username, phone))
            conn.commit()

    def register_target(self, user_id: int, author_name: str, chat_id: int, 
                        first_name: Optional[str] = None, 
                        last_name: Optional[str] = None, 
                        username: Optional[str] = None,
                        deep_mode: bool = False,
                        recursive_depth: int = 0):
        """Registers a primary target for sync and saves its metadata and scan settings."""
        now = int(time.time())
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sync_targets (user_id, chat_id, author_name, added_at, deep_mode, recursive_depth)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    author_name = excluded.author_name,
                    deep_mode = MAX(sync_targets.deep_mode, excluded.deep_mode),
                    recursive_depth = MAX(sync_targets.recursive_depth, excluded.recursive_depth)
            """, (user_id, chat_id, author_name, now, 1 if deep_mode else 0, recursive_depth))
            conn.commit()
            
        # Also ensure metadata is saved
        self.upsert_user(user_id, first_name, last_name, username)

    def upsert_chat(self, chat_id: int, title: str, chat_type: Optional[str] = None):
        """Persists or updates chat metadata in the chats table."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO chats (chat_id, title, type)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = COALESCE(NULLIF(excluded.title, ''), chats.title),
                    type = COALESCE(excluded.type, chats.type)
            """, (chat_id, title, chat_type))
            conn.commit()

    def _migrate_sync_targets_to_composite_pk(self):
        """Migration helper to move sync_targets to composite PRIMARY KEY."""
        # Using the existing connection to avoid locking issues
        conn = self._conn
        try:
            # 1. Get existing columns to preserve them
            cursor = conn.execute("PRAGMA table_info(sync_targets)")
            cols = [row[1] for row in cursor.fetchall()]
            
            # 2. Create temp table with NEW structure (Composite PK)
            # We MUST include all columns we know about
            col_defs = []
            for c in cols:
                if c in ("user_id", "chat_id"):
                    col_defs.append(f"{c} INTEGER")
                elif c in ("last_msg_id", "tail_msg_id", "is_complete", "deep_mode", "recursive_depth", "added_at"):
                    col_defs.append(f"{c} INTEGER DEFAULT 0")
                else:
                    col_defs.append(f"{c} TEXT")
            
            col_list = ", ".join(col_defs)
            conn.execute(f"CREATE TABLE sync_targets_new ({col_list}, PRIMARY KEY (user_id, chat_id))")
            
            # 3. Copy data
            col_names = ", ".join(cols)
            conn.execute(f"INSERT INTO sync_targets_new ({col_names}) SELECT {col_names} FROM sync_targets")
            
            # 4. Swap tables
            conn.execute("DROP TABLE sync_targets")
            conn.execute("ALTER TABLE sync_targets_new RENAME TO sync_targets")
            conn.commit()
            logger.info("Sync targets successfully migrated to composite Primary Key.")
        except Exception as e:
            logger.error(f"Migration error during PK update: {e}")
            # Try to recover
            try: conn.execute("DROP TABLE IF EXISTS sync_targets_new")
            except: pass
            raise 

    def get_primary_targets(self) -> List[dict]:
        """Returns only manually requested targets. Handles cases where the table may not exist yet."""
        try:
            with self._get_connection() as conn:
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
        """Returns True if the message is already linked to the specified target."""
        with self._get_connection() as conn:
            res = conn.execute("""
                SELECT 1 FROM message_target_links 
                WHERE chat_id = ? AND message_id = ? AND target_user_id = ?
                LIMIT 1
            """, (chat_id, message_id, target_id)).fetchone()
            return res is not None

    def get_user_messages(self, user_id: int) -> List[MessageData]:
        """
        Returns all messages explicitly linked to a sync target (Target Attribution).
        This ensures both primary messages and all gathered context are exported.
        """
        with self._get_connection() as conn:
            # We fetch all messages that have a link to this target_user_id
            rows = conn.execute("""
                SELECT m.* FROM messages m
                JOIN message_target_links l ON m.chat_id = l.chat_id AND m.message_id = l.message_id
                WHERE l.target_user_id = ?
                ORDER BY m.timestamp ASC, m.message_id ASC
            """, (user_id,)).fetchall()
            
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
        Removes all messages and tracking data for a user using Smart Cascading Deletion.
        Ensures orphans (context messages) are also purged if no other targets use them.
        """
        with self._get_connection() as conn:
            # 1. Delete all links for this target
            conn.execute("DELETE FROM message_target_links WHERE target_user_id = ?", (user_id,))
            
            # 2. Find and delete orphen messages (no links left to ANY target)
            # This is the "Garbage Collection" pass
            res = conn.execute("""
                DELETE FROM messages 
                WHERE NOT EXISTS (
                    SELECT 1 FROM message_target_links 
                    WHERE message_target_links.chat_id = messages.chat_id 
                    AND message_target_links.message_id = messages.message_id
                )
            """)
            deleted_msgs = res.rowcount
            
            # 3. Remove from sync_targets
            conn.execute("DELETE FROM sync_targets WHERE user_id = ?", (user_id,))
            
            conn.commit()
            return deleted_msgs, 0

    def migrate_existing_links(self):
        """
        Retroactively populates message_target_links for existing data.
        1. Links all messages authored by X to target X.
        2. Links all context messages to the target that authored the 'parent' in the same group.
        """
        with self._get_connection() as conn:
            # Primary links: Messages belong to their author as a target
            conn.execute("""
                INSERT OR IGNORE INTO message_target_links (chat_id, message_id, target_user_id)
                SELECT chat_id, message_id, user_id FROM messages
                WHERE user_id IN (SELECT user_id FROM sync_targets)
            """)
            
            # Context links: Linear approach
            # 1. Identify all unique (context_id, target_id) pairs
            # 2. Link all messages shared in those contexts to the target
            conn.execute("""
                INSERT OR IGNORE INTO message_target_links (chat_id, message_id, target_user_id)
                SELECT m.chat_id, m.message_id, t.target_user_id
                FROM messages m
                JOIN (
                    SELECT DISTINCT m1.context_group_id, l.target_user_id, l.chat_id
                    FROM message_target_links l
                    JOIN messages m1 ON l.chat_id = m1.chat_id AND l.message_id = m1.message_id
                    WHERE m1.context_group_id IS NOT NULL
                ) t ON m.chat_id = t.chat_id AND m.context_group_id = t.context_group_id
            """)
            conn.commit()
            logger.info("Database migration: Message attribution links populated.")

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
