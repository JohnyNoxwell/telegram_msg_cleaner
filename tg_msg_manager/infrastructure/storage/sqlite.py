import asyncio
import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Optional

from .interface import BaseStorage
from ._sqlite_read_path import SQLiteReadPathMixin
from ._sqlite_schema import SQLiteSchemaMixin
from ._sqlite_sync_state import SQLiteSyncStateMixin
from ._sqlite_write_path import SQLiteWritePathMixin

logger = logging.getLogger(__name__)


class SQLiteStorage(
    SQLiteSchemaMixin,
    SQLiteWritePathMixin,
    SQLiteReadPathMixin,
    SQLiteSyncStateMixin,
    BaseStorage,
):
    """
    SQLite storage with separated schema, write-path, read-path, and sync-state concerns.
    """

    def __init__(self, db_path: str = "messages.db", process_manager: Optional[Any] = None):
        self.db_path = db_path
        self._pm = process_manager
        self._lock = threading.Lock()
        self._conn = self._create_connection()
        self._init_db()

        self._write_queue = asyncio.Queue()
        self._worker_task = None
        self._shutdown_event = asyncio.Event()

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _get_connection(self) -> sqlite3.Connection:
        return self._create_connection()

    def _read_connection(self) -> sqlite3.Connection:
        return self._get_connection()

    @contextmanager
    def _write_transaction(self):
        with self._lock:
            with self._conn:
                yield self._conn

    def should_stop(self) -> bool:
        """Returns True if a shutdown has been requested internally or via ProcessManager."""
        external_stop = self._pm.shutdown_requested if self._pm else False
        return self._shutdown_event.is_set() or external_stop

    async def start(self):
        """Starts the background writer task."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._background_writer())

    async def _ensure_worker_started(self):
        """Lazily starts the writer so async save calls work even without explicit start()."""
        if not self._worker_task:
            await self.start()

    async def flush(self):
        """Waits until queued writes are persisted."""
        await self._ensure_worker_started()
        await self._write_queue.join()

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
