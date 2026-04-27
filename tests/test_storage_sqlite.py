import sys
import os
import time
import unittest
from datetime import datetime
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.message import MessageData
from tg_msg_manager.infrastructure.storage.interface import (
    CleanerStorage,
    ContextStorage,
    DBExportStorage,
    ExportStorage,
    PrivateArchiveStorage,
)
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage

class TestSQLiteStorage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Use a temporary test database
        self.db_path = "test_storage.db"
        self.storage = SQLiteStorage(self.db_path)

    def tearDown(self):
        # Cleanup test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(f"{self.db_path}-wal"):
            os.remove(f"{self.db_path}-wal")
        if os.path.exists(f"{self.db_path}-shm"):
            os.remove(f"{self.db_path}-shm")

    async def test_save_and_get_message(self):
        msg = MessageData(
            message_id=1,
            chat_id=123,
            user_id=456,
            author_name="Test User",
            timestamp=datetime.now(),
            text="Hello SQLite",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={"test": "data"}
        )
        
        # Test save
        success = await self.storage.save_message(msg)
        self.assertTrue(success)
        
        # Test existence
        self.assertTrue(self.storage.message_exists(123, 1))
        
        # Test retrieval
        retrieved = self.storage.get_message(123, 1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_id, 1)
        self.assertEqual(retrieved.text, "Hello SQLite")
        self.assertEqual(retrieved.raw_payload["test"], "data")

    async def test_sqlite_storage_satisfies_service_protocols(self):
        self.assertIsInstance(self.storage, CleanerStorage)
        self.assertIsInstance(self.storage, ContextStorage)
        self.assertIsInstance(self.storage, DBExportStorage)
        self.assertIsInstance(self.storage, ExportStorage)
        self.assertIsInstance(self.storage, PrivateArchiveStorage)

    async def test_batch_save(self):
        msgs = [
            MessageData(message_id=i, chat_id=789, user_id=1, author_name="Batch User",
                        timestamp=datetime.now(), 
                        text=f"Batch {i}", media_type=None, reply_to_id=None, 
                        fwd_from_id=None, context_group_id=None, raw_payload={})
            for i in range(1, 11)
        ]
        
        count = await self.storage.save_messages(msgs)
        self.assertEqual(count, 10)
        self.assertEqual(self.storage.get_last_msg_id(789), 10)

    async def test_upsert_logic(self):
        msg = MessageData(
            message_id=1, chat_id=1, user_id=1, author_name="Orig User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )
        await self.storage.save_message(msg)
        
        # Update text for the same message_id
        updated_msg = MessageData(
            message_id=1, chat_id=1, user_id=1, author_name="Upd User",
            timestamp=datetime.now(), 
            text="Updated", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )
        await self.storage.save_message(updated_msg)
        
        retrieved = self.storage.get_message(1, 1)
        self.assertEqual(retrieved.text, "Updated")

    async def test_payload_hashing(self):
        msg = MessageData(
            message_id=55, chat_id=1, user_id=1, author_name="Hash User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={"v": 1}
        )
        await self.storage.save_message(msg)
        h1 = msg.get_payload_hash()
        
        # Test hash detection
        msg2 = MessageData(
            message_id=55, chat_id=1, user_id=1, author_name="Hash User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={"v": 2}
        )
        h2 = msg2.get_payload_hash()
        self.assertNotEqual(h1, h2)
        
        # Test that update occurs when hash changes
        await self.storage.save_message(msg2)
        retrieved = self.storage.get_message(1, 55)
        self.assertEqual(retrieved.raw_payload["v"], 2)

    async def test_target_checkpoint_uses_target_id(self):
        self.storage.register_target(999, "Target User", 321)
        self.storage.register_target(456, "Author User", 321)

        msg = MessageData(
            message_id=50,
            chat_id=321,
            user_id=456,
            author_name="Author User",
            timestamp=datetime.now(),
            text="Context message",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={}
        )

        await self.storage.save_message(msg, target_id=999)

        target_status = self.storage.get_sync_status(321, 999)
        author_status = self.storage.get_sync_status(321, 456)
        self.assertEqual(target_status["last_msg_id"], 50)
        self.assertEqual(author_status["last_msg_id"], 0)
        self.assertEqual(len(self.storage.get_user_messages(999)), 1)

    async def test_user_export_summary_and_iterator_preserve_deterministic_order(self):
        self.storage.register_target(999, "Target User", 321)
        ts = datetime.fromtimestamp(1700000000)
        msgs = [
            MessageData(
                message_id=2,
                chat_id=321,
                user_id=999,
                author_name="Target User",
                timestamp=ts,
                text="second by id",
                media_type=None,
                reply_to_id=None,
                fwd_from_id=None,
                context_group_id=None,
                raw_payload={},
            ),
            MessageData(
                message_id=1,
                chat_id=321,
                user_id=999,
                author_name="Target User",
                timestamp=ts,
                text="first by id",
                media_type=None,
                reply_to_id=None,
                fwd_from_id=None,
                context_group_id=None,
                raw_payload={},
            ),
            MessageData(
                message_id=3,
                chat_id=321,
                user_id=555,
                author_name="Context User",
                timestamp=datetime.fromtimestamp(1700000001),
                text="context",
                media_type=None,
                reply_to_id=1,
                fwd_from_id=None,
                context_group_id=None,
                raw_payload={},
            ),
        ]

        await self.storage.save_messages(msgs, target_id=999)

        summary = self.storage.get_user_export_summary(999)
        rows = list(self.storage.iter_user_export_rows(999, chunk_size=2))

        self.assertEqual(summary["message_count"], 3)
        self.assertEqual(summary["first_message_id"], 1)
        self.assertEqual(summary["last_message_id"], 3)
        self.assertEqual(summary["target_author_name"], "Target User")
        self.assertEqual([row["message_id"] for row in rows], [1, 2, 3])

    async def test_register_target_preserves_last_sync_at_on_existing_target(self):
        self.storage.register_target(999, "Target User", 321)
        with self.storage._read_connection() as conn:
            before = conn.execute(
                "SELECT last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (999, 321),
            ).fetchone()["last_sync_at"]

        time.sleep(1)
        self.storage.register_target(999, "Target User Renamed", 321)

        with self.storage._read_connection() as conn:
            row = conn.execute(
                "SELECT author_name, last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (999, 321),
            ).fetchone()

        self.assertEqual(row["author_name"], "Target User Renamed")
        self.assertEqual(row["last_sync_at"], before)

    async def test_checkpoint_updates_do_not_refresh_last_sync_at(self):
        self.storage.register_target(999, "Target User", 321)
        with self.storage._read_connection() as conn:
            before = conn.execute(
                "SELECT last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (999, 321),
            ).fetchone()["last_sync_at"]

        time.sleep(1)
        self.storage.update_last_msg_id(321, 999, 50)
        self.storage.update_sync_tail(321, 999, 10, is_complete=False)

        with self.storage._read_connection() as conn:
            row = conn.execute(
                "SELECT last_msg_id, tail_msg_id, is_complete, last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (999, 321),
            ).fetchone()

        self.assertEqual(row["last_msg_id"], 50)
        self.assertEqual(row["tail_msg_id"], 10)
        self.assertEqual(row["is_complete"], 0)
        self.assertEqual(row["last_sync_at"], before)

    async def test_repair_terminal_incomplete_targets_marks_only_tail_threshold_rows_complete(self):
        self.storage.register_target(999, "Tail One", 321)
        self.storage.register_target(888, "Still Incomplete", 321)

        with self.storage._write_transaction() as conn:
            conn.execute(
                """
                UPDATE sync_targets
                SET last_msg_id = ?, tail_msg_id = ?, is_complete = ?, last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
                """,
                (50, 1, 0, 1234567890, 999, 321),
            )
            conn.execute(
                """
                UPDATE sync_targets
                SET last_msg_id = ?, tail_msg_id = ?, is_complete = ?, last_sync_at = ?
                WHERE user_id = ? AND chat_id = ?
                """,
                (60, 5, 0, 1234567891, 888, 321),
            )

        repaired = self.storage.repair_terminal_incomplete_targets()

        self.assertEqual(len(repaired), 1)
        self.assertEqual(repaired[0]["user_id"], 999)

        with self.storage._read_connection() as conn:
            repaired_row = conn.execute(
                "SELECT tail_msg_id, is_complete, last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (999, 321),
            ).fetchone()
            pending_row = conn.execute(
                "SELECT tail_msg_id, is_complete, last_sync_at FROM sync_targets WHERE user_id = ? AND chat_id = ?",
                (888, 321),
            ).fetchone()

        self.assertEqual(repaired_row["tail_msg_id"], 0)
        self.assertEqual(repaired_row["is_complete"], 1)
        self.assertEqual(repaired_row["last_sync_at"], 1234567890)
        self.assertEqual(pending_row["tail_msg_id"], 5)
        self.assertEqual(pending_row["is_complete"], 0)
        self.assertEqual(pending_row["last_sync_at"], 1234567891)


    async def test_get_all_message_ids(self):
        msg = MessageData(1, 100, 1, "Test User", datetime.now(), "Test", None, None, None, None, {})
        await self.storage.save_message(msg)
        ids = self.storage.get_all_message_ids_for_chat(100)
        self.assertEqual(ids, [1])

    async def test_delete_messages_cleans_target_links(self):
        self.storage.register_target(1, "Target User", 777)
        msg = MessageData(
            message_id=1,
            chat_id=777,
            user_id=1,
            author_name="Target User",
            timestamp=datetime.now(),
            text="Delete me",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={}
        )

        await self.storage.save_message(msg, target_id=1)
        self.assertEqual(self.storage.get_message_count(777, target_id=1), 1)

        deleted = self.storage.delete_messages(777, [1])
        self.assertEqual(deleted, 1)
        self.assertEqual(self.storage.get_message_count(777, target_id=1), 0)

        with self.storage._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM message_target_links WHERE chat_id = ? AND message_id = ? AND target_user_id = ?",
                (777, 1, 1)
            ).fetchone()
            self.assertEqual(row["count"], 0)

    async def test_filter_missing_target_links_batches_existing_ids(self):
        self.storage.register_target(1, "Target User", 777)
        msg = MessageData(
            message_id=1,
            chat_id=777,
            user_id=1,
            author_name="Target User",
            timestamp=datetime.now(),
            text="Keep me",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={}
        )

        await self.storage.save_message(msg, target_id=1)
        missing = self.storage.filter_missing_target_links(777, 1, [1, 2, 3])
        self.assertEqual(missing, [2, 3])

    async def test_get_target_message_breakdown_counts_own_and_context(self):
        self.storage.register_target(1, "Target User", 777)
        own_msg = MessageData(
            message_id=1,
            chat_id=777,
            user_id=1,
            author_name="Target User",
            timestamp=datetime.now(),
            text="Mine",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={}
        )
        context_msg = MessageData(
            message_id=2,
            chat_id=777,
            user_id=2,
            author_name="Other User",
            timestamp=datetime.now(),
            text="Context",
            media_type=None,
            reply_to_id=1,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={}
        )

        await self.storage.save_message(own_msg, target_id=1)
        await self.storage.save_message(context_msg, target_id=1)
        breakdown = self.storage.get_target_message_breakdown(777, 1)
        self.assertEqual(breakdown["own_messages"], 1)
        self.assertEqual(breakdown["with_context"], 2)

    async def asyncTearDown(self):
        await self.storage.close()
