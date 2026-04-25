import logging
import sqlite3

logger = logging.getLogger(__name__)


class SQLiteSchemaMixin:
    def _init_db(self):
        """Initializes database schema and applies migrations."""
        conn = self._conn
        self._create_tables(conn)
        self._create_indexes(conn)
        self._ensure_sync_target_columns(conn)
        self._run_migrations(conn)
        conn.commit()
        logger.info(f"SQLite Storage initialized at {self.db_path} with target attribution support.")

    def _create_tables(self, conn: sqlite3.Connection):
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                chat_id INTEGER PRIMARY KEY,
                last_msg_id INTEGER DEFAULT 0,
                last_sync_timestamp INTEGER
            )
        """)
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
                last_sync_at INTEGER,
                PRIMARY KEY (user_id, chat_id)
            )
        """)

    def _create_indexes(self, conn: sqlite3.Connection):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_user_chat_time ON messages (user_id, chat_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_standalone_id ON messages (message_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mt_link_target ON message_target_links (target_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_context_group ON messages (context_group_id)")

    def _ensure_sync_target_columns(self, conn: sqlite3.Connection):
        for col, col_type in [
            ("last_msg_id", "INTEGER DEFAULT 0"),
            ("tail_msg_id", "INTEGER DEFAULT 0"),
            ("is_complete", "INTEGER DEFAULT 0"),
            ("deep_mode", "INTEGER DEFAULT 0"),
            ("recursive_depth", "INTEGER DEFAULT 0"),
            ("last_sync_at", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE sync_targets ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

    def _run_migrations(self, conn: sqlite3.Connection):
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
                conn.execute("ALTER TABLE sync_targets ADD COLUMN last_sync_at INTEGER")
            except Exception as e:
                logger.debug(f"Columns might already exist: {e}")
            conn.execute("PRAGMA user_version = 4")
            logger.info("Database migration to Version 4 successful.")
        else:
            logger.debug(f"Database migration skipped (already at version {current_version}).")

    def _migrate_sync_targets_to_composite_pk(self):
        """Migration helper to move sync_targets to composite PRIMARY KEY."""
        conn = self._conn
        try:
            cursor = conn.execute("PRAGMA table_info(sync_targets)")
            cols = [row[1] for row in cursor.fetchall()]

            col_defs = []
            for c in cols:
                if c in ("user_id", "chat_id"):
                    col_defs.append(f"{c} INTEGER")
                elif c in ("last_msg_id", "tail_msg_id", "is_complete", "deep_mode", "recursive_depth", "added_at", "last_sync_at"):
                    col_defs.append(f"{c} INTEGER DEFAULT 0")
                else:
                    col_defs.append(f"{c} TEXT")

            col_list = ", ".join(col_defs)
            conn.execute(f"CREATE TABLE sync_targets_new ({col_list}, PRIMARY KEY (user_id, chat_id))")

            col_names = ", ".join(cols)
            conn.execute(f"INSERT INTO sync_targets_new ({col_names}) SELECT {col_names} FROM sync_targets")

            conn.execute("DROP TABLE sync_targets")
            conn.execute("ALTER TABLE sync_targets_new RENAME TO sync_targets")
            conn.commit()
            logger.info("Sync targets successfully migrated to composite Primary Key.")
        except Exception as e:
            logger.error(f"Migration error during PK update: {e}")
            try:
                conn.execute("DROP TABLE IF EXISTS sync_targets_new")
            except Exception:
                pass
            raise

    def migrate_existing_links(self):
        """
        Retroactively populates message_target_links for existing data.
        """
        with self._write_transaction() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO message_target_links (chat_id, message_id, target_user_id)
                SELECT chat_id, message_id, user_id FROM messages
                WHERE user_id IN (SELECT user_id FROM sync_targets)
            """)
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
        logger.info("Database migration: Message attribution links populated.")
