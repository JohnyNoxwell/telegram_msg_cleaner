import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage
from tg_msg_manager.services.exporter import ExportService

class TestSyncSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = "test_sync.db"
        self.storage = SQLiteStorage(self.db_path)
        self.mock_client = AsyncMock()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_outdated_filtering(self):
        # 1. Add a chat with an old sync timestamp (48 hours ago)
        chat_id = 123
        old_time = int((datetime.now() - timedelta(hours=48)).timestamp())
        
        with self.storage._get_connection() as conn:
            conn.execute(
                "INSERT INTO sync_state (chat_id, last_msg_id, last_sync_timestamp) VALUES (?, ?, ?)",
                (chat_id, 0, old_time)
            )
            conn.commit()
            
        # 2. Check for chats outdated by > 24 hours
        outdated = self.storage.get_outdated_chats(24 * 3600)
        self.assertIn(chat_id, outdated)
        
        # 3. Check for chats outdated by > 72 hours (should be empty)
        outdated_72 = self.storage.get_outdated_chats(72 * 3600)
        self.assertEqual(len(outdated_72), 0)

    async def test_sync_all_outdated(self):
        # Mock outdated chats
        self.storage.get_outdated_chats = MagicMock(return_value=[111])
        self.mock_client.get_entity = AsyncMock(return_value=MagicMock(id=111))
        
        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock()
        
        await service.sync_all_outdated(threshold_hours=24)
        
        service.sync_chat.assert_awaited()
        self.mock_client.get_entity.assert_awaited_with(111)

if __name__ == "__main__":
    unittest.main()
