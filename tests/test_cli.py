import sys
import os
import unittest
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.cli import CLIContext, get_dirty_target_ids, run_cli


class TestCLIContext(unittest.IsolatedAsyncioTestCase):
    @patch("tg_msg_manager.cli.setup_logging")
    @patch("tg_msg_manager.cli.DBExportService")
    @patch("tg_msg_manager.cli.CleanerService")
    @patch("tg_msg_manager.cli.SQLiteStorage")
    async def test_initialize_delete_context_without_client(
        self,
        mock_storage_cls,
        mock_cleaner_cls,
        mock_db_exporter_cls,
        mock_setup_logging,
    ):
        mock_storage = MagicMock()
        mock_storage.start = AsyncMock()
        mock_storage.close = AsyncMock()
        mock_storage_cls.return_value = mock_storage
        mock_db_exporter_cls.return_value = MagicMock()
        mock_cleaner_cls.return_value = MagicMock()

        with (
            patch("tg_msg_manager.cli.ProcessManager.acquire_lock", return_value=True),
            patch("tg_msg_manager.cli.ProcessManager.setup_async_signals"),
            patch("tg_msg_manager.cli.ProcessManager.release_lock"),
        ):
            ctx = CLIContext(needs_client=False)
            await ctx.initialize()

            self.assertIsNone(ctx.client)
            mock_storage.start.assert_awaited_once()
            mock_cleaner_cls.assert_called_once()

            await ctx.shutdown()
            mock_storage.close.assert_awaited_once()

    @patch("tg_msg_manager.cli.setup_logging")
    @patch("tg_msg_manager.cli.PrivateArchiveService")
    @patch("tg_msg_manager.cli.DBExportService")
    @patch("tg_msg_manager.cli.CleanerService")
    @patch("tg_msg_manager.cli.ExportService")
    @patch("tg_msg_manager.cli.TelethonClientWrapper")
    @patch("tg_msg_manager.cli.SQLiteStorage")
    async def test_initialize_live_context_wires_service_event_sinks(
        self,
        mock_storage_cls,
        mock_client_cls,
        mock_exporter_cls,
        mock_cleaner_cls,
        mock_db_exporter_cls,
        mock_private_archive_cls,
        mock_setup_logging,
    ):
        mock_storage = MagicMock()
        mock_storage.start = AsyncMock()
        mock_storage.close = AsyncMock()
        mock_storage_cls.return_value = mock_storage
        mock_db_exporter_cls.return_value = MagicMock()
        mock_exporter_cls.return_value = MagicMock()
        mock_cleaner_cls.return_value = MagicMock()
        mock_private_archive_cls.return_value = MagicMock()

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client_cls.return_value = mock_client

        with (
            patch("tg_msg_manager.cli.ProcessManager.acquire_lock", return_value=True),
            patch("tg_msg_manager.cli.ProcessManager.setup_async_signals"),
            patch("tg_msg_manager.cli.ProcessManager.release_lock"),
        ):
            ctx = CLIContext(needs_client=True)
            await ctx.initialize()

            self.assertTrue(callable(mock_exporter_cls.call_args.kwargs["event_sink"]))
            self.assertTrue(callable(mock_cleaner_cls.call_args.kwargs["event_sink"]))
            self.assertTrue(
                callable(mock_private_archive_cls.call_args.kwargs["event_sink"])
            )

            await ctx.shutdown()
            mock_client.disconnect.assert_awaited_once()

    def test_get_dirty_target_ids_filters_unchanged_users(self):
        stats = {
            1: {"name": "A", "count": 0, "dirty": False},
            2: {"name": "B", "count": 3, "dirty": True},
            3: {"name": "C", "count": 0},
            4: {"name": "D", "count": 2},
        }

        self.assertEqual(get_dirty_target_ids(stats), [2, 4])

    @patch("tg_msg_manager.cli.telemetry.log_summary")
    @patch("tg_msg_manager.cli.get_safe_user_and_chat")
    @patch("tg_msg_manager.cli.CLIContext")
    async def test_run_cli_export_logs_telemetry_summary(
        self,
        mock_ctx_cls,
        mock_get_safe_user_and_chat,
        mock_log_summary,
    ):
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()
        mock_ctx.shutdown = AsyncMock()
        mock_ctx.exporter = MagicMock()
        mock_ctx.exporter.sync_chat = AsyncMock(return_value=0)
        mock_ctx.db_exporter = MagicMock()
        mock_ctx.db_exporter.export_user_messages = AsyncMock(
            return_value="DB_EXPORTS/test.jsonl"
        )
        mock_ctx.storage = MagicMock()
        mock_ctx.storage.get_user.return_value = {
            "first_name": "Kirill",
            "last_name": "Cilantro",
        }
        mock_ctx_cls.return_value = mock_ctx

        user_ent = MagicMock(
            id=404307871, first_name="Kirill", last_name="Cilantro", username="kirill"
        )
        chat_ent = MagicMock(id=1274306614)
        mock_get_safe_user_and_chat.return_value = (user_ent, chat_ent)

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "export",
                "--user-id",
                "404307871",
                "--chat-id",
                "1274306614",
                "--depth",
                "2",
                "--json",
            ],
        ):
            await run_cli()

        mock_log_summary.assert_called_once_with("Export telemetry summary")
        self.assertTrue(
            mock_ctx.db_exporter.export_user_messages.await_args.kwargs["as_json"]
        )

    @patch("tg_msg_manager.cli.telemetry.log_summary")
    @patch("tg_msg_manager.cli.get_safe_user_and_chat")
    @patch("tg_msg_manager.cli.CLIContext")
    async def test_run_cli_export_uses_numeric_user_id_fallback_when_entity_is_unresolved(
        self,
        mock_ctx_cls,
        mock_get_safe_user_and_chat,
        mock_log_summary,
    ):
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()
        mock_ctx.shutdown = AsyncMock()
        mock_ctx.exporter = MagicMock()
        mock_ctx.exporter.sync_chat = AsyncMock(return_value=0)
        mock_ctx.exporter.sync_all_dialogs_for_user = AsyncMock(return_value=7)
        mock_ctx.db_exporter = MagicMock()
        mock_ctx.db_exporter.export_user_messages = AsyncMock(return_value="")
        mock_ctx.storage = MagicMock()
        mock_ctx.storage.get_user.return_value = None
        mock_ctx_cls.return_value = mock_ctx

        mock_get_safe_user_and_chat.return_value = (None, None)

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "export",
                "--user-id",
                "2061894541",
                "--json",
            ],
        ):
            await run_cli()

        mock_ctx.exporter.sync_all_dialogs_for_user.assert_awaited_once()
        self.assertEqual(
            mock_ctx.exporter.sync_all_dialogs_for_user.await_args.args[0], 2061894541
        )
        mock_log_summary.assert_called_once_with("Export telemetry summary")
        self.assertTrue(
            mock_ctx.db_exporter.export_user_messages.await_args.kwargs["as_json"]
        )

    @patch("tg_msg_manager.cli.telemetry.log_summary")
    @patch("tg_msg_manager.cli.get_safe_user_and_chat")
    @patch("tg_msg_manager.cli.CLIContext")
    async def test_run_cli_export_without_json_writes_txt_summary(
        self,
        mock_ctx_cls,
        mock_get_safe_user_and_chat,
        mock_log_summary,
    ):
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()
        mock_ctx.shutdown = AsyncMock()
        mock_ctx.exporter = MagicMock()
        mock_ctx.exporter.sync_all_dialogs_for_user = AsyncMock(return_value=3)
        mock_ctx.db_exporter = MagicMock()
        mock_ctx.db_exporter.export_user_messages = AsyncMock(
            return_value="DB_EXPORTS/test.txt"
        )
        mock_ctx.storage = MagicMock()
        mock_ctx.storage.get_user.return_value = None
        mock_ctx_cls.return_value = mock_ctx
        mock_get_safe_user_and_chat.return_value = (None, None)

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "export",
                "--user-id",
                "123456789",
            ],
        ):
            await run_cli()

        mock_log_summary.assert_called_once_with("Export telemetry summary")
        self.assertFalse(
            mock_ctx.db_exporter.export_user_messages.await_args.kwargs["as_json"]
        )

    @patch("tg_msg_manager.cli.CLIContext")
    async def test_run_cli_db_export_defaults_to_txt(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()
        mock_ctx.shutdown = AsyncMock()
        mock_ctx.db_exporter = MagicMock()
        mock_ctx.db_exporter.export_user_messages = AsyncMock(return_value="x.txt")
        mock_ctx_cls.return_value = mock_ctx

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "db-export",
                "--user-id",
                "123456789",
            ],
        ):
            await run_cli()

        self.assertFalse(
            mock_ctx.db_exporter.export_user_messages.await_args.kwargs["as_json"]
        )

    @patch("tg_msg_manager.cli.CLIContext")
    async def test_run_cli_db_export_json_flag_writes_json(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()
        mock_ctx.shutdown = AsyncMock()
        mock_ctx.db_exporter = MagicMock()
        mock_ctx.db_exporter.export_user_messages = AsyncMock(return_value="x.jsonl")
        mock_ctx_cls.return_value = mock_ctx

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "db-export",
                "--user-id",
                "123456789",
                "--json",
            ],
        ):
            await run_cli()

        self.assertTrue(
            mock_ctx.db_exporter.export_user_messages.await_args.kwargs["as_json"]
        )

    @patch("tg_msg_manager.cli.main_menu", new_callable=AsyncMock)
    @patch("tg_msg_manager.cli.build_cli_parser")
    async def test_run_cli_without_command_in_non_tty_prints_help(
        self,
        mock_build_parser,
        mock_main_menu,
    ):
        parser = MagicMock()
        parser.parse_args.return_value = Namespace(command=None)
        mock_build_parser.return_value = parser

        with (
            patch.object(sys.stdin, "isatty", return_value=False),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            await run_cli()

        parser.print_help.assert_called_once()
        mock_main_menu.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
