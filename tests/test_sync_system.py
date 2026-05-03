import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.service_payloads import (
    ExportDialogScanStartedPayload,
    ExportDialogSearchScanningPayload,
    ExportDialogSearchStartedPayload,
    ExportGlobalExportFinishedPayload,
    ExportTrackedUpdateStartedPayload,
)
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage
from tg_msg_manager.services.exporter import ExportService
from tg_msg_manager.core.models.sync_report import TrackedSyncRunReport


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
                "INSERT INTO sync_targets (user_id, chat_id, author_name, added_at, last_sync_at, is_complete) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, chat_id, "Test Target", old_time, old_time, 1),
            )
            conn.commit()

        # 2. Check for chats outdated by > 24 hours
        outdated = self.storage.get_outdated_chats(24 * 3600)
        self.assertIn((chat_id, chat_id), outdated)

        # 3. Check for chats outdated by > 72 hours (should be empty)
        outdated_72 = self.storage.get_outdated_chats(72 * 3600)
        self.assertEqual(len(outdated_72), 0)

    def test_recently_synced_old_target_is_not_outdated(self):
        chat_id = 456
        added_at = int((datetime.now() - timedelta(days=30)).timestamp())
        fresh_sync = int((datetime.now() - timedelta(minutes=5)).timestamp())

        with self.storage._get_connection() as conn:
            conn.execute(
                "INSERT INTO sync_targets (user_id, chat_id, author_name, added_at, last_sync_at, is_complete) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, chat_id, "Fresh Target", added_at, fresh_sync, 1),
            )
            conn.commit()

        outdated = self.storage.get_outdated_chats(24 * 3600)
        self.assertNotIn((chat_id, chat_id), outdated)

    async def test_sync_all_outdated(self):
        # Mock outdated chats
        self.storage.get_outdated_chats = MagicMock(return_value=[111])
        self.mock_client.get_entity = AsyncMock(return_value=MagicMock(id=111))

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_outdated(threshold_seconds=24 * 3600)

        service.sync_chat.assert_awaited()
        self.mock_client.get_entity.assert_awaited_with(111)

    async def test_sync_all_tracked_uses_primary_targets_and_whole_chat_mode(self):
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 200},
                {"chat_id": 300, "user_id": 999},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=[
                {"author_name": "Whole Chat", "is_complete": 1, "last_msg_id": 0},
                {"author_name": "Tracked User", "is_complete": 1, "last_msg_id": 0},
            ]
        )
        self.mock_client.get_entity = AsyncMock(
            side_effect=[MagicMock(id=200), MagicMock(id=300)]
        )

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        self.assertEqual(service.sync_chat.await_count, 2)
        first_call = service.sync_chat.await_args_list[0]
        second_call = service.sync_chat.await_args_list[1]
        self.assertIsNone(first_call.kwargs["from_user_id"])
        self.assertEqual(second_call.kwargs["from_user_id"], 999)
        self.assertFalse(first_call.kwargs["resume_history"])
        self.assertFalse(second_call.kwargs["resume_history"])

    async def test_sync_all_tracked_marks_only_changed_users_as_dirty(self):
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 200},
                {"chat_id": 300, "user_id": 999},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=[
                {"author_name": "Whole Chat"},
                {"author_name": "Tracked User"},
            ]
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(
            side_effect=[MagicMock(id=200), MagicMock(id=300)]
        )

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(side_effect=[0, 4])

        stats = await service.sync_all_tracked()

        self.assertIsInstance(stats, TrackedSyncRunReport)
        self.assertFalse(stats[200]["dirty"])
        self.assertEqual(stats[200]["count"], 0)
        self.assertTrue(stats[999]["dirty"])
        self.assertEqual(stats[999]["count"], 4)

    async def test_sync_all_tracked_reuses_chat_entity_for_same_chat(self):
        shared_entity = MagicMock(id=200)
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 111},
                {"chat_id": 200, "user_id": 222},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=[
                {"author_name": "User One"},
                {"author_name": "User Two"},
            ]
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=shared_entity)

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        self.mock_client.get_entity.assert_awaited_once_with(200)
        self.assertEqual(service.sync_chat.await_count, 2)

    async def test_sync_all_tracked_skips_user_entity_resolution(self):
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 999},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            return_value={"author_name": "Tracked User"}
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=MagicMock(id=200))

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        call = service.sync_chat.await_args_list[0]
        self.assertFalse(call.kwargs["resolve_user_entity"])

    async def test_sync_all_tracked_reuses_latest_message_probe_for_same_chat(self):
        shared_entity = MagicMock(id=200)
        latest = MagicMock(message_id=777)
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 111},
                {"chat_id": 200, "user_id": 222},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=[
                {"author_name": "User One"},
                {"author_name": "User Two"},
            ]
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=shared_entity)
        self.mock_client.get_messages = AsyncMock(return_value=[latest])

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        self.mock_client.get_messages.assert_awaited_once_with(shared_entity, limit=1)
        first_call = service.sync_chat.await_args_list[0]
        second_call = service.sync_chat.await_args_list[1]
        self.assertEqual(first_call.kwargs["current_max_hint"], 777)
        self.assertEqual(second_call.kwargs["current_max_hint"], 777)

    async def test_sync_all_tracked_reuses_shared_head_prefetch_for_same_chat_users(
        self,
    ):
        shared_entity = MagicMock(id=200)
        latest = MagicMock(message_id=777)
        prefetched = [
            MagicMock(message_id=777, user_id=111),
            MagicMock(message_id=776, user_id=222),
            MagicMock(message_id=775, user_id=333),
            MagicMock(message_id=699, user_id=111),
        ]
        expected_prefetch = prefetched[:3]

        class AsyncIterator:
            def __init__(self, items):
                self.items = list(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self.items:
                    raise StopAsyncIteration
                return self.items.pop(0)

        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 111},
                {"chat_id": 200, "user_id": 222},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=lambda chat_id, user_id: {
                "author_name": f"User {user_id}",
                "last_msg_id": 700 if user_id == 111 else 750,
            }
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=shared_entity)
        self.mock_client.get_messages = AsyncMock(return_value=[latest])
        self.mock_client.iter_messages = MagicMock(
            return_value=AsyncIterator(prefetched)
        )

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        self.mock_client.iter_messages.assert_called_once()
        first_call = service.sync_chat.await_args_list[0]
        second_call = service.sync_chat.await_args_list[1]
        self.assertEqual(first_call.kwargs["prefetched_messages"], expected_prefetch)
        self.assertEqual(second_call.kwargs["prefetched_messages"], expected_prefetch)

    async def test_sync_all_tracked_resumes_incomplete_history_even_when_head_is_current(
        self,
    ):
        shared_entity = MagicMock(id=200)
        latest = MagicMock(message_id=777)
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 999},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            return_value={
                "author_name": "Tracked User",
                "last_msg_id": 777,
                "tail_msg_id": 40,
                "is_complete": 0,
            }
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=shared_entity)
        self.mock_client.get_messages = AsyncMock(return_value=[latest])

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        service.sync_chat.assert_awaited_once()
        self.assertTrue(service.sync_chat.await_args.kwargs["resume_history"])

    async def test_sync_all_tracked_skips_up_to_date_targets_before_sync_chat(self):
        shared_entity = MagicMock(id=200)
        latest = MagicMock(message_id=777)
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 111},
                {"chat_id": 200, "user_id": 222},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            side_effect=lambda chat_id, user_id: {
                "author_name": f"User {user_id}",
                "last_msg_id": 777,
                "is_complete": 1,
            }
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=shared_entity)
        self.mock_client.get_messages = AsyncMock(return_value=[latest])

        service = ExportService(self.mock_client, self.storage)
        service.sync_chat = AsyncMock(return_value=0)

        stats = await service.sync_all_tracked()

        service.sync_chat.assert_not_awaited()
        self.assertEqual(stats[111]["count"], 0)
        self.assertFalse(stats[111]["dirty"])
        self.assertEqual(stats[222]["count"], 0)
        self.assertFalse(stats[222]["dirty"])

    async def test_sync_all_dialogs_for_user_emits_bulk_search_events(self):
        dialog_entity = type(
            "DialogEntity",
            (),
            {"id": 200, "title": "Tracked Chat", "broadcast": False},
        )()
        dialog = MagicMock(is_group=True, is_channel=False, entity=dialog_entity)
        self.mock_client.get_dialogs = AsyncMock(return_value=[dialog])
        events = []

        service = ExportService(
            self.mock_client, self.storage, event_sink=events.append
        )
        service.sync_chat = AsyncMock(return_value=3)

        processed = await service.sync_all_dialogs_for_user(999)

        self.assertEqual(processed, 3)
        self.assertEqual(
            [event.name for event in events],
            [
                "export.dialog_search_started",
                "export.dialog_search_scanning",
                "export.dialog_scan_started",
                "export.global_export_finished",
            ],
        )
        search_started = ExportDialogSearchStartedPayload.coerce(events[0].payload)
        scanning = ExportDialogSearchScanningPayload.coerce(events[1].payload)
        scan_started = ExportDialogScanStartedPayload.coerce(events[2].payload)
        finished = ExportGlobalExportFinishedPayload.coerce(events[3].payload)
        self.assertEqual(search_started.from_user_id, 999)
        self.assertEqual(scanning.dialog_count, 1)
        self.assertEqual(scan_started.dialog_title, "Tracked Chat")
        self.assertEqual(finished.total_processed, 3)

    async def test_sync_all_tracked_emits_update_started_event(self):
        self.storage.get_primary_targets = MagicMock(
            return_value=[
                {"chat_id": 200, "user_id": 999},
            ]
        )
        self.storage.get_sync_status = MagicMock(
            return_value={"author_name": "Tracked User"}
        )
        self.storage.get_user = MagicMock(return_value=None)
        self.mock_client.get_entity = AsyncMock(return_value=MagicMock(id=200))
        self.mock_client.get_messages = AsyncMock(
            return_value=[MagicMock(message_id=777)]
        )
        events = []

        service = ExportService(
            self.mock_client, self.storage, event_sink=events.append
        )
        service.sync_chat = AsyncMock(return_value=0)

        await service.sync_all_tracked()

        self.assertEqual(events[0].name, "export.tracked_update_started")
        payload = ExportTrackedUpdateStartedPayload.coerce(events[0].payload)
        self.assertEqual(payload.target_count, 1)


if __name__ == "__main__":
    unittest.main()
