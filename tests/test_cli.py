import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.cli import CLIContext


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

        with patch("tg_msg_manager.cli.ProcessManager.acquire_lock", return_value=True), \
             patch("tg_msg_manager.cli.ProcessManager.setup_async_signals"), \
             patch("tg_msg_manager.cli.ProcessManager.release_lock"):
            ctx = CLIContext(needs_client=False)
            await ctx.initialize()

            self.assertIsNone(ctx.client)
            mock_storage.start.assert_awaited_once()
            mock_cleaner_cls.assert_called_once()

            await ctx.shutdown()
            mock_storage.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
