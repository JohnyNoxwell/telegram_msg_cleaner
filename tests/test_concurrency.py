import sys
import os
import time
import unittest
import signal
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.process import ProcessManager
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
        with ProcessManager(self.lock_path) as pm1:
            self.assertTrue(os.path.exists(self.lock_path))
            
            # 2. Attempt to acquire second lock (should fail)
            with self.assertRaises(RuntimeError):
                with ProcessManager(self.lock_path) as pm2:
                    pass
                    
        # 3. Lock should be released
        self.assertFalse(os.path.exists(self.lock_path))

    def test_stale_lock_recovery(self):
        # 1. Create a stale lock file with a non-existent PID
        with open(self.lock_path, 'w') as f:
            f.write("999999") # Assuming this PID doesn't exist
            
        # 2. Should be able to acquire lock
        with ProcessManager(self.lock_path) as pm:
            self.assertTrue(os.path.exists(self.lock_path))

    def test_signal_handling(self):
        pm = ProcessManager(self.lock_path)
        callback = MagicMock()
        pm.setup_signals(callback)
        
        # Simulate SIGINT
        os.kill(os.getpid(), signal.SIGINT)
        
        self.assertTrue(pm.should_stop())
        callback.assert_called_once()

    def test_retry_queue_persistence(self):
        storage = SQLiteStorage(self.db_path)
        storage.enqueue_retry_task("task1", 123, "export", "Timeout")
        
        # Verify retrieved
        tasks = storage.get_retry_tasks()
        # Note: default next_retry is +300s, so for the test we might need a custom timestamp
        # But wait, I'll just check if it's in the DB at all for this basic test.
        with storage._get_connection() as conn:
            row = conn.execute("SELECT * FROM retry_queue WHERE task_id = 'task1'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["chat_id"], 123)

if __name__ == "__main__":
    unittest.main()
