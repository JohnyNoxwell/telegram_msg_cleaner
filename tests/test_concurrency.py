import sys
import os
import unittest
import signal
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.process import ProcessManager
from tg_msg_manager.infrastructure.storage.records import RetryTaskRecord
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage


class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.lock_path = "test.lock"
        self.db_path = "test_concurrency.db"
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)

    def tearDown(self):
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_lock_exclusion(self):
        # 1. Acquire first lock
        with ProcessManager(self.lock_path):
            self.assertTrue(os.path.exists(self.lock_path))

            # 2. Attempt to acquire second lock (should fail)
            with self.assertRaises(RuntimeError):
                with ProcessManager(self.lock_path):
                    pass

        # 3. Lock should be released
        self.assertFalse(os.path.exists(self.lock_path))

    def test_stale_lock_recovery(self):
        # 1. Create a stale lock file with a non-existent PID
        with open(self.lock_path, "w") as f:
            f.write("999999")  # Assuming this PID doesn't exist

        # 2. Should be able to acquire lock
        with ProcessManager(self.lock_path):
            self.assertTrue(os.path.exists(self.lock_path))

    def test_signal_handling(self):
        pm = ProcessManager(self.lock_path)
        callback = MagicMock()
        with self.assertRaises(KeyboardInterrupt):
            pm._handle_sync_signal(signal.SIGINT, loop_stop_callback=callback)

        self.assertTrue(pm.should_stop())
        callback.assert_called_once()

    def test_signal_second_interrupt_forces_exit(self):
        pm = ProcessManager(self.lock_path)
        forced = []

        pm.shutdown_requested = True
        pm._sig_count = 1
        pm._handle_sync_signal(
            signal.SIGTERM, force_exit=lambda code: forced.append(code)
        )

        self.assertEqual(forced, [1])

    def test_retry_queue_persistence(self):
        storage = SQLiteStorage(self.db_path)
        storage.enqueue_retry_task("task1", 123, "export", "Timeout")
        with storage._write_transaction() as conn:
            conn.execute(
                "UPDATE retry_queue SET next_retry_timestamp = 0 WHERE task_id = ?",
                ("task1",),
            )

        # Verify retrieved
        tasks = storage.get_retry_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertIsInstance(tasks[0], RetryTaskRecord)
        self.assertEqual(tasks[0].chat_id, 123)
        with storage._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM retry_queue WHERE task_id = 'task1'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["chat_id"], 123)


if __name__ == "__main__":
    unittest.main()
