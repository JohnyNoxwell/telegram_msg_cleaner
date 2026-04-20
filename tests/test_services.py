import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.message import MessageData
from tg_msg_manager.services.exporter import ExportService
from tg_msg_manager.services.context_engine import DeepModeEngine

class AsyncIterator:
    def __init__(self, items):
        self.items = items
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

class TestServices(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_storage = MagicMock()
        self.mock_storage.get_message_count.return_value = 0
        
    async def test_exporter_sync(self):
        # Mock last_id in storage
        self.mock_storage.get_last_msg_id.return_value = 10
        
        # Create mock message stream
        msg1 = MessageData(message_id=15, chat_id=1, user_id=1, author_name="Exporter User",
                          timestamp=datetime.now(), 
                          text="New", media_type=None, reply_to_id=None, 
                          fwd_from_id=None, context_group_id=None, raw_payload={})
        
        self.mock_client.iter_messages.return_value = AsyncIterator([msg1])
        
        service = ExportService(self.mock_client, self.mock_storage)
        count = await service.sync_chat(MagicMock(id=1), limit=10)
        
        self.assertEqual(count, 1)
        self.mock_storage.save_messages.assert_called()

    async def test_deep_mode_clustering(self):
        target = MessageData(message_id=100, chat_id=1, user_id=1, author_name="Deep User",
                            timestamp=datetime.now(), 
                            text="Target", media_type=None, reply_to_id=None, 
                            fwd_from_id=None, context_group_id=None, raw_payload={})
        
        # Mock surrounding messages
        m1 = MessageData(message_id=99, chat_id=1, user_id=2, author_name="Context User",
                        timestamp=datetime.now(), 
                        text="Context", media_type=None, reply_to_id=None, 
                        fwd_from_id=None, context_group_id=None, raw_payload={})
        
        self.mock_client.iter_messages.return_value = AsyncIterator([m1])
        
        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        cluster_id = await engine.extract_context(MagicMock(id=1), target, window_before=1, window_after=1)
        
        self.assertIsNotNone(cluster_id)
        # Verify storage was called with clustered messages
        self.mock_storage.save_message.assert_called()
        self.mock_storage.save_messages.assert_called()
        
        # Check that saved message has the cluster_id
        saved_msg = self.mock_storage.save_messages.call_args[0][0][0]
        self.assertEqual(saved_msg.context_group_id, cluster_id)

if __name__ == "__main__":
    unittest.main()
