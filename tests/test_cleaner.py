import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.service_payloads import (
    CleanerDialogMessagesFoundPayload,
    CleanerDialogScanStartedPayload,
)
from tg_msg_manager.services.cleaner import CleanerService
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage


class AsyncIterator:
    def __init__(self, items):
        self.items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


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

    async def test_whitelist_protection_accepts_full_telegram_chat_id(self):
        whitelist = {-1001700453512}
        cleaner = CleanerService(self.mock_client, self.storage, whitelist)

        entity = MagicMock(id=1700453512)
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
                (
                    777,
                    1,
                    1,
                    "CleanerUser",
                    int(datetime.now().timestamp()),
                    "Delete me",
                ),
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

    async def test_global_self_cleanup_filters_whitelist_and_skips_service_messages(
        self,
    ):
        allowed_entity = MagicMock(id=777, username="allowed_group")
        blocked_entity = MagicMock(id=123, username="blocked_group")
        pm_entity = MagicMock(id=999, username="pm_user")

        allowed_dialog = MagicMock(
            id=777,
            entity=allowed_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )
        allowed_dialog.name = "Allowed Group"
        blocked_dialog = MagicMock(
            id=123,
            name="Blocked Group",
            entity=blocked_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )
        pm_dialog = MagicMock(
            id=999,
            name="PM User",
            entity=pm_entity,
            is_group=False,
            is_channel=False,
            is_user=True,
        )

        service_msg = MagicMock(message_id=1, is_service=True)
        own_msg_1 = MagicMock(message_id=11, is_service=False)
        own_msg_2 = MagicMock(message_id=12, is_service=False)

        self.mock_client.get_dialogs = AsyncMock(
            return_value=[allowed_dialog, blocked_dialog, pm_dialog]
        )
        self.mock_client.iter_messages = MagicMock(
            side_effect=lambda entity, **kwargs: AsyncIterator(
                [service_msg, own_msg_1, own_msg_2] if entity.id == 777 else []
            )
        )

        cleaner = CleanerService(self.mock_client, self.storage, whitelist={123})
        cleaner.delete_chat_messages = AsyncMock(return_value=2)

        deleted = await cleaner.global_self_cleanup(dry_run=False, include_pms=False)

        self.assertEqual(deleted, 2)
        cleaner.delete_chat_messages.assert_awaited_once()
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[1], [11, 12])
        self.assertEqual(self.mock_client.iter_messages.call_count, 1)
        self.assertEqual(self.mock_client.iter_messages.call_args.args[0].id, 777)

    async def test_global_self_cleanup_emits_service_events(self):
        allowed_entity = MagicMock(id=777, username="allowed_group")
        allowed_dialog = MagicMock(
            id=777,
            entity=allowed_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )
        allowed_dialog.name = "Allowed Group"
        own_msg = MagicMock(message_id=11, is_service=False)

        events = []
        self.mock_client.get_dialogs = AsyncMock(return_value=[allowed_dialog])
        self.mock_client.iter_messages = MagicMock(
            return_value=AsyncIterator([own_msg])
        )

        cleaner = CleanerService(
            self.mock_client, self.storage, event_sink=events.append
        )
        cleaner.delete_chat_messages = AsyncMock(return_value=1)

        deleted = await cleaner.global_self_cleanup(dry_run=False, include_pms=False)

        self.assertEqual(deleted, 1)
        self.assertEqual(
            [event.name for event in events],
            [
                "cleaner.dialog_scan_started",
                "cleaner.dialog_messages_found",
            ],
        )
        started_payload = CleanerDialogScanStartedPayload.coerce(events[0].payload)
        found_payload = CleanerDialogMessagesFoundPayload.coerce(events[1].payload)
        self.assertEqual(started_payload.name, "Allowed Group")
        self.assertEqual(found_payload.count, 1)

    async def test_global_self_cleanup_skips_whitelisted_full_telegram_chat_id(self):
        channel_id = 1700453512
        full_chat_id = -1001700453512

        blocked_entity = MagicMock(id=channel_id, username="blocked_group")
        allowed_entity = MagicMock(id=777, username="allowed_group")

        blocked_dialog = MagicMock(
            id=channel_id,
            name="Blocked Group",
            entity=blocked_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )
        allowed_dialog = MagicMock(
            id=777,
            name="Allowed Group",
            entity=allowed_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )

        own_msg = MagicMock(message_id=31, is_service=False)
        self.mock_client.get_dialogs = AsyncMock(
            return_value=[blocked_dialog, allowed_dialog]
        )
        self.mock_client.iter_messages = MagicMock(
            side_effect=lambda entity, **kwargs: AsyncIterator(
                [own_msg] if entity.id == 777 else []
            )
        )

        cleaner = CleanerService(
            self.mock_client, self.storage, whitelist={full_chat_id}
        )
        cleaner.delete_chat_messages = AsyncMock(return_value=1)

        deleted = await cleaner.global_self_cleanup(dry_run=False, include_pms=False)

        self.assertEqual(deleted, 1)
        cleaner.delete_chat_messages.assert_awaited_once()
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[0].id, 777)
        self.assertEqual(self.mock_client.iter_messages.call_count, 1)
        self.assertEqual(self.mock_client.iter_messages.call_args.args[0].id, 777)

    async def test_global_self_cleanup_include_list_matches_username_for_pm(self):
        pm_entity = MagicMock(id=777, username="allowed_pm")
        other_entity = MagicMock(id=888, username="other_pm")
        pm_dialog = MagicMock(
            id=777,
            name="Allowed PM",
            entity=pm_entity,
            is_group=False,
            is_channel=False,
            is_user=True,
        )
        other_dialog = MagicMock(
            id=888,
            name="Other PM",
            entity=other_entity,
            is_group=False,
            is_channel=False,
            is_user=True,
        )
        own_msg = MagicMock(message_id=21, is_service=False)

        self.mock_client.get_dialogs = AsyncMock(return_value=[pm_dialog, other_dialog])
        self.mock_client.iter_messages = MagicMock(
            side_effect=lambda entity, **kwargs: AsyncIterator(
                [own_msg] if entity.id == 777 else []
            )
        )

        cleaner = CleanerService(
            self.mock_client, self.storage, include_list={"allowed_pm"}
        )
        cleaner.delete_chat_messages = AsyncMock(return_value=1)

        deleted = await cleaner.global_self_cleanup(dry_run=False, include_pms=True)

        self.assertEqual(deleted, 1)
        cleaner.delete_chat_messages.assert_awaited_once()
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[0].id, 777)
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[1], [21])
        self.assertEqual(self.mock_client.iter_messages.call_count, 1)

    async def test_global_self_cleanup_include_list_matches_full_telegram_chat_id(self):
        channel_id = 1700453512
        full_chat_id = -1001700453512
        included_entity = MagicMock(id=channel_id, username="included_group")
        other_entity = MagicMock(id=888, username="other_group")

        included_dialog = MagicMock(
            id=channel_id,
            name="Included Group",
            entity=included_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )
        other_dialog = MagicMock(
            id=888,
            name="Other Group",
            entity=other_entity,
            is_group=True,
            is_channel=False,
            is_user=False,
        )

        own_msg = MagicMock(message_id=41, is_service=False)
        self.mock_client.get_dialogs = AsyncMock(
            return_value=[included_dialog, other_dialog]
        )
        self.mock_client.iter_messages = MagicMock(
            side_effect=lambda entity, **kwargs: AsyncIterator(
                [own_msg] if entity.id == channel_id else []
            )
        )

        cleaner = CleanerService(
            self.mock_client, self.storage, include_list={full_chat_id}
        )
        cleaner.delete_chat_messages = AsyncMock(return_value=1)

        deleted = await cleaner.global_self_cleanup(dry_run=False, include_pms=False)

        self.assertEqual(deleted, 1)
        cleaner.delete_chat_messages.assert_awaited_once()
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[0].id, channel_id)
        self.assertEqual(cleaner.delete_chat_messages.await_args.args[1], [41])
        self.assertEqual(self.mock_client.iter_messages.call_count, 1)
        self.assertEqual(
            self.mock_client.iter_messages.call_args.args[0].id, channel_id
        )


if __name__ == "__main__":
    unittest.main()
