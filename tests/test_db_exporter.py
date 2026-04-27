import sys
import os
import json
import asyncio
import unittest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.message import MessageData
from tg_msg_manager.core.telemetry import telemetry
from tg_msg_manager.services.db_exporter import DBExportService


class TestDBExporter(unittest.TestCase):
    def setUp(self):
        self.storage = MagicMock()
        self.storage.get_user_export_summary.return_value = None
        self.storage.get_user_export_rows.return_value = None
        self.storage.iter_user_export_rows.return_value = iter(())
        self.service = DBExportService(self.storage)
        self.tmpdir = tempfile.mkdtemp(prefix="tg_db_export_test_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_ai_json_profile_is_default_and_keeps_graph_fields(self):
        msg = MessageData(
            message_id=101,
            chat_id=202,
            user_id=303,
            author_name="Graph User",
            timestamp=datetime.fromtimestamp(1700000000),
            text="hello",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id="cluster-1",
            raw_payload={
                "reply_to": {
                    "reply_to_msg_id": 77,
                    "reply_to_top_id": 55,
                    "forum_topic": True,
                },
                "edit_date": "2025-01-01T12:00:00+00:00",
                "reactions": {
                    "results": [
                        {
                            "reaction": {"_": "ReactionEmoji", "emoticon": "👍"},
                            "count": 3,
                        }
                    ]
                },
            },
        )

        payload = json.loads(self.service.format_message(msg, as_json=True))

        self.assertNotIn("raw_payload", payload)
        self.assertEqual(payload["reply_to_id"], 77)
        self.assertEqual(payload["reply_to_top_id"], 55)
        self.assertTrue(payload["forum_topic"])
        self.assertEqual(payload["context_group_id"], "cluster-1")
        self.assertEqual(payload["reactions"], [{"emoji": "👍", "count": 3}])
        self.assertEqual(payload["edit_date"], "2025-01-01T12:00:00+00:00")
        rendered = self.service.format_message(msg, as_json=True)
        self.assertTrue(rendered.startswith('{"edit_date":"2025-01-01T12:00:00+00:00"'))

    def test_full_json_profile_keeps_raw_payload(self):
        msg = MessageData(
            message_id=1,
            chat_id=2,
            user_id=3,
            author_name="Full User",
            timestamp=datetime.fromtimestamp(1700000000),
            text="full",
            media_type=None,
            reply_to_id=9,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={"reply_to": {"reply_to_msg_id": 9}},
        )

        payload = json.loads(self.service.format_message(msg, as_json=True, json_profile="full"))

        self.assertIn("raw_payload", payload)
        self.assertEqual(payload["reply_to_id"], 9)

    def test_resolve_export_author_name_prefers_message_author_when_user_card_is_empty(self):
        self.storage.get_user.return_value = {
            "user_id": 2142333070,
            "first_name": "",
            "last_name": "",
            "username": "",
        }
        msg = MessageData(
            message_id=1,
            chat_id=2,
            user_id=2142333070,
            author_name="Никто",
            timestamp=datetime.fromtimestamp(1700000000),
            text="hello",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={},
        )

        name = self.service._resolve_export_author_name(2142333070, [msg])

        self.assertEqual(name, "Никто")

    def test_write_batch_size_prefers_larger_batches_for_ai_json(self):
        self.assertEqual(self.service._write_batch_size(as_json=False, json_profile="ai"), 100)
        self.assertEqual(self.service._write_batch_size(as_json=True, json_profile="full"), 500)
        self.assertEqual(self.service._write_batch_size(as_json=True, json_profile="ai"), 1000)

    def test_export_user_messages_skips_full_rewrite_when_fingerprint_is_unchanged(self):
        telemetry.reset()
        message = MessageData(
            message_id=1,
            chat_id=2,
            user_id=3,
            author_name="Stable User",
            timestamp=datetime.fromtimestamp(1700000000),
            text="hello",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={},
        )
        self.storage.get_user_messages.return_value = [message]
        self.storage.get_user.return_value = {
            "user_id": 3,
            "first_name": "Stable",
            "last_name": "User",
            "username": "stable",
        }

        first_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))
        with open(first_path, "r", encoding="utf-8") as f:
            first_content = f.read()

        second_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))
        with open(second_path, "r", encoding="utf-8") as f:
            second_content = f.read()

        self.assertEqual(first_path, second_path)
        self.assertEqual(first_content, second_content)
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["db_export.skipped_unchanged"], 1)

    def test_export_user_messages_skips_multipart_rewrite_when_parts_are_unchanged(self):
        telemetry.reset()
        messages = []
        base_ts = 1700000000
        for idx in range(5001):
            messages.append(
                MessageData(
                    message_id=idx + 1,
                    chat_id=2,
                    user_id=3,
                    author_name="Stable User",
                    timestamp=datetime.fromtimestamp(base_ts + idx),
                    text=f"hello {idx}",
                    media_type=None,
                    reply_to_id=None,
                    fwd_from_id=None,
                    context_group_id=None,
                    raw_payload={},
                )
            )
        self.storage.get_user_messages.return_value = messages
        self.storage.get_user.return_value = {
            "user_id": 3,
            "first_name": "Stable",
            "last_name": "User",
            "username": "stable",
        }

        first_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))
        second_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))

        self.assertEqual(first_path, second_path)
        self.assertTrue(os.path.exists(first_path))
        self.assertTrue(os.path.exists(first_path.replace(".jsonl", "_part2.jsonl")))
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["db_export.skipped_unchanged"], 1)

    def test_export_user_messages_uses_streaming_row_fast_path_for_ai_json(self):
        row = {
            "message_id": 1,
            "chat_id": 2,
            "user_id": 3,
            "author_name": "Fast User",
            "timestamp": 1700000000,
            "text": "hello",
            "media_type": None,
            "reply_to_id": None,
            "fwd_from_id": None,
            "context_group_id": None,
            "raw_payload": "{}",
            "is_service": 0,
        }
        self.storage.get_user_export_summary.return_value = {
            "message_count": 1,
            "first_message_id": 1,
            "last_message_id": 1,
            "first_timestamp": 1700000000,
            "last_timestamp": 1700000000,
            "target_author_name": "Fast User",
        }
        self.storage.iter_user_export_rows.side_effect = lambda user_id: iter([row])
        self.storage.get_user.return_value = {
            "user_id": 3,
            "first_name": "Fast",
            "last_name": "User",
            "username": "fast",
        }

        output_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))

        self.storage.get_user_messages.assert_not_called()
        self.storage.get_user_export_rows.assert_not_called()
        self.assertTrue(os.path.exists(output_path))

    def test_export_user_messages_streaming_row_fast_path_skips_unchanged_without_len_none_crash(self):
        telemetry.reset()
        row = {
            "message_id": 1,
            "chat_id": 2,
            "user_id": 3,
            "author_name": "Fast User",
            "timestamp": 1700000000,
            "text": "hello",
            "media_type": None,
            "reply_to_id": None,
            "fwd_from_id": None,
            "context_group_id": None,
            "raw_payload": "{}",
            "is_service": 0,
        }
        self.storage.get_user_export_summary.return_value = {
            "message_count": 1,
            "first_message_id": 1,
            "last_message_id": 1,
            "first_timestamp": 1700000000,
            "last_timestamp": 1700000000,
            "target_author_name": "Fast User",
        }
        self.storage.iter_user_export_rows.side_effect = lambda user_id: iter([row])
        self.storage.get_user.return_value = {
            "user_id": 3,
            "first_name": "Fast",
            "last_name": "User",
            "username": "fast",
        }

        first_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))
        second_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))

        self.assertEqual(first_path, second_path)
        self.storage.get_user_messages.assert_not_called()
        summary = telemetry.get_summary()
        self.assertEqual(summary["counters"]["db_export.skipped_unchanged"], 1)

    def test_export_user_messages_falls_back_to_materialized_rows_when_streaming_helpers_are_unavailable(self):
        row = {
            "message_id": 1,
            "chat_id": 2,
            "user_id": 3,
            "author_name": "Legacy Fast User",
            "timestamp": 1700000000,
            "text": "hello",
            "media_type": None,
            "reply_to_id": None,
            "fwd_from_id": None,
            "context_group_id": None,
            "raw_payload": "{}",
            "is_service": 0,
        }
        self.storage.get_user_export_rows.return_value = [row]
        self.storage.get_user.return_value = {
            "user_id": 3,
            "first_name": "Legacy",
            "last_name": "User",
            "username": "legacy",
        }

        output_path = asyncio.run(self.service.export_user_messages(3, output_dir=self.tmpdir, as_json=True))

        self.storage.get_user_messages.assert_not_called()
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "r", encoding="utf-8") as f:
            payload = json.loads(f.readline())
        self.assertEqual(payload["author_name"], "Legacy Fast User")


if __name__ == "__main__":
    unittest.main()
