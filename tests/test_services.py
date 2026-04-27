import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.message import MessageData
from tg_msg_manager.core.telemetry import telemetry
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
        self.mock_storage.should_stop = MagicMock(return_value=False)
        self.mock_storage.flush = AsyncMock()
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
        self.mock_storage.get_message.return_value = None
        self.mock_client.get_messages = AsyncMock(return_value=[])
        self.mock_client.get_entity = AsyncMock()
        self.mock_client.download_media = AsyncMock()

    def _message(
        self,
        message_id,
        *,
        chat_id=1,
        user_id=1,
        author_name="User",
        text="msg",
        timestamp=None,
        reply_to_id=None,
        raw_payload=None,
        is_service=False,
    ):
        return MessageData(
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            author_name=author_name,
            timestamp=timestamp or datetime.now(),
            text=text,
            media_type=None,
            reply_to_id=reply_to_id,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload=raw_payload or {},
            is_service=is_service,
        )

    def _saved_message_ids(self):
        saved_batches = [call.args[0] for call in self.mock_storage.save_messages.await_args_list]
        return [msg.message_id for batch in saved_batches for msg in batch]

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
        self.mock_storage.flush.assert_awaited()

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
        self.assertEqual(self.mock_client.iter_messages.call_args.kwargs["offset_id"], 16)

    def test_build_scan_ranges_first_full_sync_has_no_overlap(self):
        service = ExportService(self.mock_client, self.mock_storage)
        ranges = service._build_scan_ranges(
            current_max=100,
            head_id=0,
            tail_id=0,
            is_complete=False,
            limit=None,
        )

        self.assertTrue(ranges)
        self.assertTrue(all(item["role"] == "TAIL" for item in ranges))

        covered = set()
        for item in ranges:
            chunk = set(range(item["lower"], item["upper"] + 1))
            self.assertTrue(covered.isdisjoint(chunk))
            covered.update(chunk)

        self.assertEqual(covered, set(range(1, 101)))

    def test_build_scan_ranges_resume_separates_head_and_history(self):
        service = ExportService(self.mock_client, self.mock_storage)
        ranges = service._build_scan_ranges(
            current_max=120,
            head_id=100,
            tail_id=40,
            is_complete=False,
            limit=None,
        )

        head_ranges = [item for item in ranges if item["role"] == "HEAD"]
        tail_ranges = [item for item in ranges if item["role"] == "TAIL"]

        self.assertEqual(head_ranges, [{"upper": 120, "lower": 101, "role": "HEAD"}])
        self.assertTrue(tail_ranges)

        covered = set()
        for item in ranges:
            chunk = set(range(item["lower"], item["upper"] + 1))
            self.assertTrue(covered.isdisjoint(chunk))
            covered.update(chunk)

        self.assertEqual(covered, set(range(1, 40)) | set(range(101, 121)))

    def test_build_scan_ranges_update_mode_skips_history_resume(self):
        service = ExportService(self.mock_client, self.mock_storage)
        ranges = service._build_scan_ranges(
            current_max=120,
            head_id=100,
            tail_id=40,
            is_complete=False,
            limit=None,
            allow_history=False,
        )

        self.assertEqual(ranges, [{"upper": 120, "lower": 101, "role": "HEAD"}])

    def test_resolve_tail_progress_checkpoint_uses_highest_contiguous_prefix_only(self):
        service = ExportService(self.mock_client, self.mock_storage)
        checkpoint = service._resolve_tail_progress_checkpoint([
            {"upper": 120, "lower": 91, "tail_scan_complete": True, "tail": 91},
            {"upper": 90, "lower": 61, "tail_scan_complete": False, "tail": 74},
            {"upper": 60, "lower": 31, "tail_scan_complete": True, "tail": 31},
        ])

        self.assertEqual(checkpoint, 74)

    def test_resolve_tail_progress_checkpoint_stops_when_top_range_has_no_progress(self):
        service = ExportService(self.mock_client, self.mock_storage)
        checkpoint = service._resolve_tail_progress_checkpoint([
            {"upper": 120, "lower": 91, "tail_scan_complete": False, "tail": None},
            {"upper": 90, "lower": 61, "tail_scan_complete": True, "tail": 61},
        ])

        self.assertIsNone(checkpoint)

    async def test_sync_chat_update_mode_returns_fast_when_only_history_remains(self):
        latest = self._message(120, chat_id=1, user_id=1, author_name="Exporter User")
        self.mock_client.get_messages.return_value = [latest]
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([]))
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 120,
            "tail_msg_id": 40,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(MagicMock(id=1), resume_history=False)

        self.assertEqual(processed, 0)
        self.assertFalse(self.mock_client.iter_messages.called)

    async def test_sync_chat_marks_terminal_history_complete_when_tail_reaches_one(self):
        latest = self._message(120, chat_id=1, user_id=999, author_name="Tracked User")
        self.mock_client.get_messages.return_value = [latest]
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 120,
            "tail_msg_id": 1,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            current_max_hint=120,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 0)
        self.mock_client.iter_messages.assert_not_called()
        self.mock_storage.update_sync_tail.assert_any_call(1, 999, 0, is_complete=True)
        self.mock_storage.update_last_sync_at.assert_called_once_with(1, 999)

    async def test_sync_chat_advances_head_cursor_after_empty_head_scan(self):
        stale = self._message(105, chat_id=1, user_id=999, author_name="Tracked User")
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([stale]))
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 100,
            "tail_msg_id": 0,
            "is_complete": 1,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }
        self.mock_storage.filter_missing_target_links.return_value = []

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            resume_history=False,
            current_max_hint=120,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 0)
        self.mock_storage.update_last_msg_id.assert_any_call(1, 999, 120)

    async def test_sync_chat_advances_tail_cursor_after_empty_history_scan(self):
        latest = self._message(120, chat_id=1, user_id=999, author_name="Tracked User")
        self.mock_client.get_messages.return_value = [latest]
        self.mock_client.iter_messages = MagicMock(side_effect=[
            AsyncIterator([]),
            AsyncIterator([]),
            AsyncIterator([]),
            AsyncIterator([]),
        ])
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 120,
            "tail_msg_id": 40,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 0)
        self.mock_storage.update_sync_tail.assert_any_call(1, 999, 0, is_complete=True)

    async def test_sync_chat_uses_prefetched_head_messages_without_network_iter(self):
        prefetched = [
            self._message(120, chat_id=1, user_id=222, author_name="Noise User"),
            self._message(118, chat_id=1, user_id=999, author_name="Tracked User"),
            self._message(114, chat_id=1, user_id=999, author_name="Tracked User"),
            self._message(109, chat_id=1, user_id=777, author_name="Other User"),
        ]
        self.mock_client.iter_messages = MagicMock(side_effect=AssertionError("network iter should not run"))
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 110,
            "tail_msg_id": 0,
            "is_complete": 1,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }
        self.mock_storage.filter_missing_target_links.return_value = [118, 114]

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            resume_history=False,
            current_max_hint=120,
            prefetched_messages=prefetched,
            prefetched_head_complete=True,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 2)
        saved_ids = self._saved_message_ids()
        self.assertEqual(saved_ids, [118, 114])
        self.mock_storage.update_last_msg_id.assert_any_call(1, 999, 120)

    async def test_sync_chat_falls_back_to_client_side_sender_filter_when_user_is_unresolved(self):
        self.mock_client.get_entity = AsyncMock(side_effect=Exception("unresolved"))
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([
            self._message(105, chat_id=1, user_id=111, author_name="Noise User"),
            self._message(104, chat_id=1, user_id=999, author_name="Tracked User"),
            self._message(103, chat_id=1, user_id=222, author_name="Noise User"),
        ]))
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 100,
            "tail_msg_id": 0,
            "is_complete": 1,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            resume_history=False,
            current_max_hint=105,
        )

        self.assertEqual(processed, 1)
        self.assertIsNone(self.mock_client.iter_messages.call_args.kwargs["from_user"])
        saved_ids = self._saved_message_ids()
        self.assertEqual(saved_ids, [104])

    async def test_sync_chat_does_not_auto_complete_based_on_low_tail_checkpoint(self):
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([]))
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 120,
            "tail_msg_id": 5,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            current_max_hint=120,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 0)
        self.mock_client.iter_messages.assert_called()
        self.assertTrue(any(
            call.args == (1, 999, 0) and call.kwargs == {"is_complete": True}
            for call in self.mock_storage.update_sync_tail.call_args_list
        ))

    async def test_sync_chat_does_not_mark_history_complete_when_stop_is_requested(self):
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([]))
        self.mock_storage.should_stop = MagicMock(return_value=True)
        self.mock_storage.get_sync_status.return_value = {
            "last_msg_id": 120,
            "tail_msg_id": 5,
            "is_complete": 0,
            "deep_mode": 0,
            "recursive_depth": 0,
            "author_name": "Tracked User",
        }

        service = ExportService(self.mock_client, self.mock_storage)
        processed = await service.sync_chat(
            MagicMock(id=1),
            from_user_id=999,
            current_max_hint=120,
            resolve_user_entity=False,
        )

        self.assertEqual(processed, 0)
        self.assertFalse(any(
            call.args == (1, 999, 0) and call.kwargs == {"is_complete": True}
            for call in self.mock_storage.update_sync_tail.call_args_list
        ))
        self.mock_storage.update_last_sync_at.assert_not_called()

    async def test_deep_mode_clustering(self):
        target = self._message(100, user_id=1, author_name="Deep User", text="Target")
        direct_reply = self._message(
            101,
            user_id=2,
            author_name="Reply User",
            text="Reply",
            reply_to_id=100,
            timestamp=target.timestamp + timedelta(seconds=30),
            raw_payload={"reply_to": {"reply_to_msg_id": 100}},
        )
        unrelated = self._message(
            99,
            user_id=3,
            author_name="Noise User",
            text="Noise",
            timestamp=target.timestamp - timedelta(seconds=30),
        )

        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([direct_reply, unrelated, target])
        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        cluster_id = await engine.extract_context(MagicMock(id=1), target, window_size=1)

        self.assertTrue(cluster_id)
        self.mock_storage.save_messages.assert_awaited()
        saved_ids = self._saved_message_ids()
        self.assertIn(100, saved_ids)
        self.assertIn(101, saved_ids)
        self.assertNotIn(99, saved_ids)

    async def test_deep_mode_includes_parent_message(self):
        parent = self._message(50, user_id=2, author_name="Parent", text="Parent")
        target = self._message(
            100,
            user_id=1,
            author_name="Deep User",
            text="Target",
            reply_to_id=50,
            raw_payload={"reply_to": {"reply_to_msg_id": 50}},
        )

        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([target])
        self.mock_client.get_messages.return_value = [parent]

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=1)

        saved_ids = self._saved_message_ids()
        self.assertIn(50, saved_ids)

    async def test_deep_mode_includes_parent_message_from_batched_storage_lookup(self):
        parent = self._message(50, user_id=2, author_name="Parent", text="Parent")
        target = self._message(
            100,
            user_id=1,
            author_name="Deep User",
            text="Target",
            reply_to_id=50,
            raw_payload={"reply_to": {"reply_to_msg_id": 50}},
        )

        self.mock_storage.get_messages_by_ids.return_value = [parent]
        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([target])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=1)

        saved_ids = self._saved_message_ids()
        self.assertIn(50, saved_ids)
        self.mock_client.get_messages.assert_not_awaited()

    async def test_deep_mode_uses_local_range_without_live_fetch_when_range_is_complete(self):
        telemetry.reset()
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)
        stored_reply = self._message(
            101,
            user_id=2,
            author_name="Stored Reply",
            text="Reply",
            timestamp=base_time + timedelta(seconds=15),
            reply_to_id=100,
            raw_payload={"reply_to": {"reply_to_msg_id": 100}},
        )

        stored_range = []
        for message_id in range(92, 161):
            if message_id == 100:
                stored_range.append(target)
            elif message_id == 101:
                stored_range.append(stored_reply)
            else:
                stored_range.append(
                    self._message(
                        message_id,
                        user_id=9,
                        author_name="Noise",
                        text=f"Noise {message_id}",
                        timestamp=base_time + timedelta(seconds=message_id - 100),
                    )
                )

        self.mock_storage.get_messages_in_id_range.return_value = stored_range
        self.mock_storage.get_messages_replying_to.return_value = []
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([]))

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(
            MagicMock(id=1),
            [target],
            target_id=1,
            window_size=1,
            max_cluster=2,
            recursive_depth=1,
        )

        saved_ids = self._saved_message_ids()
        self.assertIn(101, saved_ids)
        self.assertFalse(self.mock_client.iter_messages.called)
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["deep.fetch_range.local_only.calls"], 1)
        self.assertEqual(summary["counters"]["deep.fetch_range.range_width"], 69)
        self.assertEqual(summary["counters"]["deep.fetch_range.stored_hits"], 69)
        self.assertEqual(summary["counters"]["deep.fetch_range.missing_ids"], 0)
        self.assertEqual(summary["counters"]["deep.fetch_range.coverage_100.calls"], 1)

    async def test_deep_mode_prefers_selective_fill_when_replies_exist_and_coverage_is_good(self):
        telemetry.reset()
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)
        stored_reply = self._message(
            101,
            user_id=2,
            author_name="Stored Reply",
            text="Stored reply",
            timestamp=base_time + timedelta(seconds=15),
            reply_to_id=100,
            raw_payload={"reply_to": {"reply_to_msg_id": 100}},
        )

        stored_range = []
        for message_id in range(92, 161):
            if message_id % 2 == 0:
                payload = {"reply_to": {"reply_to_msg_id": 100}} if message_id == 100 else {}
                stored_range.append(
                    self._message(
                        message_id,
                        user_id=9,
                        author_name="Cached",
                        text=f"Cached {message_id}",
                        timestamp=base_time + timedelta(seconds=message_id - 100),
                        reply_to_id=100 if message_id == 100 else None,
                        raw_payload=payload,
                    )
                )

        self.mock_storage.get_messages_in_id_range.return_value = stored_range
        self.mock_storage.get_messages_replying_to.return_value = [stored_reply]
        self.mock_client.get_messages = AsyncMock(return_value=[])
        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([]))

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(
            MagicMock(id=1),
            [target],
            target_id=1,
            window_size=1,
            max_cluster=2,
            recursive_depth=1,
        )

        self.mock_client.get_messages.assert_awaited()
        self.assertFalse(self.mock_client.iter_messages.called)
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["deep.fetch_range.selective_fill.calls"], 1)

    async def test_deep_mode_uses_compact_fill_before_full_scan_for_fragmented_holes(self):
        telemetry.reset()
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)

        stored_range = []
        stored_ids = set(range(92, 161)) - {
            98, 99, 100, 101, 102, 103, 104,
            115, 116, 117, 118, 119, 120, 121,
            132, 133, 134, 135, 136, 137, 138,
            149, 150, 151, 152, 153, 154, 155,
        }
        for message_id in sorted(stored_ids):
            raw_payload = {"reply_to": {"reply_to_msg_id": 100}} if message_id == 100 else {}
            stored_range.append(
                self._message(
                    message_id,
                    user_id=9,
                    author_name="Cached",
                    text=f"Cached {message_id}",
                    timestamp=base_time + timedelta(seconds=message_id - 100),
                    reply_to_id=100 if message_id == 100 else None,
                    raw_payload=raw_payload,
                )
            )

        live_fill = [
            [self._message(98, user_id=2, author_name="Live", text="Live 98", timestamp=base_time - timedelta(seconds=2))],
            [self._message(118, user_id=2, author_name="Live", text="Live 118", timestamp=base_time + timedelta(seconds=18))],
            [self._message(135, user_id=2, author_name="Live", text="Live 135", timestamp=base_time + timedelta(seconds=35), reply_to_id=100, raw_payload={"reply_to": {"reply_to_msg_id": 100}})],
            [self._message(152, user_id=2, author_name="Live", text="Live 152", timestamp=base_time + timedelta(seconds=52))],
        ]

        self.mock_storage.get_messages_in_id_range.return_value = stored_range
        self.mock_storage.get_messages_replying_to.return_value = []
        self.mock_client.get_messages = AsyncMock(return_value=[])
        self.mock_client.iter_messages = MagicMock(side_effect=[AsyncIterator(batch) for batch in live_fill])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(
            MagicMock(id=1),
            [target],
            target_id=1,
            window_size=1,
            max_cluster=3,
            recursive_depth=1,
        )

        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["deep.fetch_range.compact_fill.calls"], 1)
        self.assertEqual(summary["counters"]["deep.fetch_range.compact_fill.ranges"], 4)
        self.assertNotIn("deep.fetch_range.full_scan.calls", summary["counters"])
        self.assertEqual(self.mock_client.iter_messages.call_count, 4)

    async def test_deep_mode_same_topic_requires_topic_match(self):
        target = self._message(
            100,
            user_id=1,
            author_name="Deep User",
            text="Topic target",
            raw_payload={"reply_to": {"reply_to_top_id": 900}},
        )
        same_topic = self._message(
            104,
            user_id=2,
            author_name="Topic User",
            text="Same topic",
            raw_payload={"reply_to": {"reply_to_top_id": 900}},
            timestamp=target.timestamp + timedelta(seconds=20),
        )
        other_topic = self._message(
            105,
            user_id=3,
            author_name="Other Topic",
            text="Other topic",
            raw_payload={"reply_to": {"reply_to_top_id": 901}},
            timestamp=target.timestamp + timedelta(seconds=25),
        )

        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([other_topic, same_topic, target])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=2)

        saved_ids = self._saved_message_ids()
        self.assertIn(104, saved_ids)
        self.assertNotIn(105, saved_ids)

    async def test_deep_mode_skips_redundant_round_two_for_non_topic_without_structure(self):
        telemetry.reset()
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)
        noise = self._message(
            101,
            user_id=2,
            author_name="Noise",
            text="Noise",
            timestamp=base_time + timedelta(seconds=15),
        )

        self.mock_client.iter_messages = MagicMock(return_value=AsyncIterator([noise, target]))

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=2)

        self.assertEqual(self.mock_client.iter_messages.call_count, 1)
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["deep.round_2.skipped_empty_clusters"], 1)
        self.assertNotIn("deep.round_2.clusters", summary["counters"])

    def test_candidate_index_routes_reply_to_matching_cluster_only(self):
        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        target_a = self._message(100, user_id=1, author_name="A", text="Target A")
        target_b = self._message(200, user_id=2, author_name="B", text="Target B")
        reply_b = self._message(
            201,
            user_id=3,
            author_name="Reply",
            text="Reply to B",
            reply_to_id=200,
            raw_payload={"reply_to": {"reply_to_msg_id": 200}},
        )

        clusters = engine._initialize_clusters([target_a, target_b])
        candidate = engine._normalize_message(reply_b)
        additions = engine._associate_candidates(clusters, [candidate], round_number=1, max_cluster=10)

        self.assertEqual(len(additions), 1)
        self.assertEqual(additions[0].context_group_id, clusters[1].cluster_id)
        self.assertNotIn(candidate.key, clusters[0].messages)
        self.assertIn(candidate.key, clusters[1].messages)

    async def test_deep_mode_time_fallback_requires_missing_structural_metadata(self):
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)
        prev_msg = self._message(
            99,
            user_id=2,
            author_name="Before",
            text="Before",
            timestamp=base_time - timedelta(seconds=45),
        )
        next_msg = self._message(
            101,
            user_id=3,
            author_name="After",
            text="After",
            timestamp=base_time + timedelta(seconds=50),
        )

        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([next_msg, target, prev_msg])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=3)

        saved_ids = self._saved_message_ids()
        self.assertIn(99, saved_ids)
        self.assertIn(101, saved_ids)

        self.mock_storage.save_messages.reset_mock()
        parent = self._message(50, user_id=9, author_name="Parent", text="Parent")
        structural_target = self._message(
            200,
            user_id=1,
            author_name="Deep User",
            text="Reply target",
            timestamp=base_time,
            reply_to_id=50,
            raw_payload={"reply_to": {"reply_to_msg_id": 50}},
        )
        noise = self._message(
            201,
            user_id=8,
            author_name="Noise",
            text="Noise",
            timestamp=base_time + timedelta(seconds=30),
        )
        self.mock_client.get_messages.return_value = [parent]
        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([noise, structural_target])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [structural_target], target_id=1, recursive_depth=3)

        saved_ids = self._saved_message_ids()
        self.assertIn(50, saved_ids)
        self.assertNotIn(201, saved_ids)

    async def test_deep_mode_skips_service_messages(self):
        base_time = datetime.now()
        target = self._message(100, user_id=1, author_name="Deep User", text="Target", timestamp=base_time)
        service = self._message(
            101,
            user_id=2,
            author_name="Service",
            text="joined",
            timestamp=base_time + timedelta(seconds=20),
            is_service=True,
        )

        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([service, target])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=3)

        saved_ids = self._saved_message_ids()
        self.assertIn(100, saved_ids)
        self.assertNotIn(101, saved_ids)

    async def test_deep_mode_handles_mixed_storage_and_live_timestamps(self):
        base_time = datetime.now(timezone.utc)
        stored_parent = self._message(
            50,
            user_id=9,
            author_name="Stored Parent",
            text="Parent",
            timestamp=base_time - timedelta(minutes=1),
        )
        target = self._message(
            100,
            user_id=1,
            author_name="Deep User",
            text="Target",
            timestamp=base_time,
            reply_to_id=50,
            raw_payload={"reply_to": {"reply_to_msg_id": 50}},
        )
        live_reply = self._message(
            101,
            user_id=2,
            author_name="Live Reply",
            text="Reply",
            timestamp=base_time + timedelta(seconds=30),
            reply_to_id=100,
            raw_payload={"reply_to": {"reply_to_msg_id": 100}},
        )

        self.mock_storage.get_message.return_value = MessageData.from_dict(stored_parent.to_dict())
        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([live_reply, target])

        engine = DeepModeEngine(self.mock_client, self.mock_storage)
        await engine.extract_batch_context(MagicMock(id=1), [target], target_id=1, recursive_depth=3)

        saved_ids = self._saved_message_ids()
        self.assertIn(50, saved_ids)
        self.assertIn(101, saved_ids)

    async def test_deep_mode_processed_ids_do_not_leak_between_chats(self):
        self.mock_client.iter_messages.side_effect = lambda *args, **kwargs: AsyncIterator([])

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

    async def test_private_archive_stops_at_last_synced_message(self):
        new_message = MessageData(
            message_id=6,
            chat_id=1,
            user_id=9,
            author_name="PM User",
            timestamp=datetime.now(),
            text="new",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={},
        )
        stale_message = MessageData(
            message_id=5,
            chat_id=1,
            user_id=9,
            author_name="PM User",
            timestamp=datetime.now(),
            text="old photo",
            media_type="Photo",
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={},
            media_ref=MagicMock(),
        )

        self.mock_client.iter_messages.return_value = AsyncIterator([new_message, stale_message])
        self.mock_storage.get_last_msg_id.return_value = 5
        self.mock_storage.register_target = MagicMock()

        service = PrivateArchiveService(self.mock_client, self.mock_storage, base_dir="/tmp/tg_pm_test")
        await service.archive_pm(MagicMock(id=1, first_name="PM", last_name="User", username="pmuser"))

        self.assertEqual(self.mock_storage.save_message.await_count, 1)
        self.assertEqual(self.mock_storage.save_message.await_args.args[0].message_id, 6)
        self.mock_client.download_media.assert_not_awaited()
        self.mock_storage.update_last_sync_at.assert_called_once_with(1, 1)

    async def test_private_archive_emits_service_events(self):
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
                media_ref=MagicMock(),
            )
        ])
        self.mock_client.download_media.return_value = "/tmp/test_media.jpg"
        self.mock_storage.get_last_msg_id.return_value = 0
        self.mock_storage.register_target = MagicMock()
        events = []

        service = PrivateArchiveService(
            self.mock_client,
            self.mock_storage,
            base_dir="/tmp/tg_pm_test",
            event_sink=events.append,
        )
        await service.archive_pm(MagicMock(id=1, first_name="PM", last_name="User", username="pmuser"))

        self.assertEqual(
            [event.name for event in events],
            [
                "private_archive.started",
                "private_archive.media_saved",
                "private_archive.completed",
            ],
        )
        self.assertEqual(events[0].payload["user_id"], 1)
        self.assertEqual(events[1].payload["filename"], "test_media.jpg")
        self.assertEqual(events[2].payload["count"], 1)

if __name__ == "__main__":
    unittest.main()
