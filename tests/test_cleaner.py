import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.services.cleaner import CleanerService
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage

class TestCleaner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_client = AsyncMock()
        self.db_path = "test_cleaner.db"
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    async def test_whitelist_protection(self):
        whitelist = {123}
        cleaner = CleanerService(self.mock_client, self.storage, whitelist)
        
        # Protected chat
        entity = MagicMock(id=123)
        count = await cleaner.delete_chat_messages(entity, [1, 2, 3], dry_run=False)
        
        self.assertEqual(count, 0)
        self.mock_client.delete_messages.assert_not_called()

    async def test_dry_run_no_calls(self):
        cleaner = CleanerService(self.mock_client, self.storage)
        entity = MagicMock(id=456)
        
        count = await cleaner.delete_chat_messages(entity, [1, 2], dry_run=True)
        
        self.assertEqual(count, 0)
        self.mock_client.delete_messages.assert_not_called()

    async def test_live_deletion_and_purge(self):
        # 1. Setup DB with a message
        with self.storage._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (chat_id, message_id, user_id, author_name, timestamp, text) VALUES (?, ?, ?, ?, ?, ?)",
                (777, 1, 1, "CleanerUser", int(datetime.now().timestamp()), "Delete me")
            )
            conn.commit()
            
        cleaner = CleanerService(self.mock_client, self.storage)
        self.mock_client.delete_messages.return_value = 1
        
        entity = MagicMock(id=777)
        count = await cleaner.delete_chat_messages(entity, [1], dry_run=False)
        
        self.assertEqual(count, 1)
        self.mock_client.delete_messages.assert_called_once()
        
        # Verify purged from DB
        self.assertEqual(self.storage.get_message_count(777), 0)

if __name__ == "__main__":
    unittest.main()
