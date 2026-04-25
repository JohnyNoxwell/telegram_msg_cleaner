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
from tg_msg_manager.services.private_archive import PrivateArchiveService

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
        self.mock_storage.save_message = AsyncMock()
        self.mock_storage.save_messages = AsyncMock()
        self.mock_storage.upsert_chat = MagicMock()
        self.mock_storage.upsert_user = MagicMock()
        self.mock_storage.register_target = MagicMock()
        self.mock_storage.update_last_sync_at = MagicMock()
        self.mock_storage.get_last_msg_id.return_value = 10
        self.mock_storage.get_message_count.return_value = 0
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 0,
            "tail_msg_id": 0,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
        }
        self.mock_storage.has_target_link.return_value = False
        self.mock_client.get_messages = AsyncMock()
        self.mock_client.get_entity = AsyncMock()
        self.mock_client.download_media = AsyncMock()

    async def test_exporter_sync(self):
        # Mock last_id in storage
        self.mock_storage.get_last_msg_id.return_value = 10
        
        # Create mock message stream
        msg1 = MessageData(message_id=15, chat_id=1, user_id=1, author_name="Exporter User",
                          timestamp=datetime.now(), 
                          text="New", media_type=None, reply_to_id=None, 
                          fwd_from_id=None, context_group_id=None, raw_payload={})
        
        self.mock_client.get_messages.return_value = [msg1]
        self.mock_client.iter_messages.return_value = AsyncIterator([msg1])
        
        service = ExportService(self.mock_client, self.mock_storage)
        count = await service.sync_chat(MagicMock(id=1), limit=10)
        
        self.assertGreaterEqual(count, 0)

    async def test_export_limit_uses_single_worker_range(self):
        msg1 = MessageData(message_id=15, chat_id=1, user_id=1, author_name="Exporter User",
                          timestamp=datetime.now(),
                          text="New", media_type=None, reply_to_id=None,
                          fwd_from_id=None, context_group_id=None, raw_payload={})

        self.mock_client.get_messages.return_value = [msg1]
        self.mock_client.iter_messages.return_value = AsyncIterator([msg1])

        service = ExportService(self.mock_client, self.mock_storage)
        await service.sync_chat(MagicMock(id=1), limit=1)

        self.assertEqual(self.mock_client.iter_messages.call_count, 1)
        self.assertEqual(self.mock_client.iter_messages.call_args.kwargs["limit"], 1)

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
        cluster_id = await engine.extract_context(MagicMock(id=1), target, window_size=1)
        
        self.assertEqual(cluster_id, "")
        # Verify storage was called with clustered messages
        self.mock_storage.save_messages.assert_awaited()

        # Check that at least one saved message has the cluster_id
        saved_batches = [call.args[0] for call in self.mock_storage.save_messages.await_args_list]
        saved_msgs = [msg for batch in saved_batches for msg in batch]
        self.assertTrue(any(msg.context_group_id for msg in saved_msgs))

    async def test_deep_mode_processed_ids_do_not_leak_between_chats(self):
        self.mock_client.iter_messages.return_value = AsyncIterator([])
        self.mock_storage.filter_existing_ids.return_value = []

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        target_chat_1 = MessageData(
            message_id=100, chat_id=1, user_id=1, author_name="Chat One",
            timestamp=datetime.now(),
            text="Target 1", media_type=None, reply_to_id=None,
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )
        target_chat_2 = MessageData(
            message_id=100, chat_id=2, user_id=1, author_name="Chat Two",
            timestamp=datetime.now(),
            text="Target 2", media_type=None, reply_to_id=None,
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )

        await engine.extract_batch_context(MagicMock(id=1), [target_chat_1], target_id=1, recursive_depth=1)
        await engine.extract_batch_context(MagicMock(id=2), [target_chat_2], target_id=1, recursive_depth=1)

        self.assertEqual(self.mock_storage.save_messages.await_count, 2)

    async def test_private_archive_downloads_media(self):
        self.mock_client.iter_messages.return_value = AsyncIterator([
            MessageData(
                message_id=5,
                chat_id=1,
                user_id=9,
                author_name="PM User",
                timestamp=datetime.now(),
                text="photo",
                media_type="Photo",
                reply_to_id=None,
                fwd_from_id=None,
                context_group_id=None,
                raw_payload={},
                media_ref=MagicMock()
            )
        ])
        self.mock_client.download_media.return_value = "/tmp/test_media.jpg"
        self.mock_storage.get_last_msg_id.return_value = 0
        self.mock_storage.register_target = MagicMock()

        service = PrivateArchiveService(self.mock_client, self.mock_storage, base_dir="/tmp/tg_pm_test")
        result_dir = await service.archive_pm(MagicMock(id=1, first_name="PM", last_name="User", username="pmuser"))

        self.assertIn("/tmp/tg_pm_test", result_dir)
        self.mock_client.download_media.assert_awaited()
        self.mock_storage.save_message.assert_awaited()
        self.assertEqual(self.mock_storage.save_message.await_args.kwargs["target_id"], 1)
        self.mock_storage.update_last_sync_at.assert_called_once_with(1, 1)

if __name__ == "__main__":
    unittest.main()
