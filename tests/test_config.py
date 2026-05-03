import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.config import Settings, load_settings
from tg_msg_manager.core.runtime import build_app_runtime


class TestConfig(unittest.TestCase):
    def test_missing_required_fields(self):
        # Should fail if api_id is missing
        with self.assertRaises(Exception):
            Settings(api_hash="hash")

    def test_env_override(self):
        with patch.dict(os.environ, {"TG_API_ID": "12345", "TG_API_HASH": "abcde"}):
            settings = Settings()
            self.assertEqual(settings.api_id, 12345)
            self.assertEqual(settings.api_hash, "abcde")

    def test_whitelist_casting(self):
        # Verify it handles set of strings
        settings = Settings(api_id=1, api_hash="h", whitelist_chats=["123", "user1"])
        self.assertIn(123, settings.whitelist_chats)
        self.assertIn("user1", settings.whitelist_chats)

    def test_language_aliases_normalize_and_fallback(self):
        settings = Settings(api_id=1, api_hash="h", language="EN")
        self.assertEqual(settings.lang, "en")

        fallback = Settings(api_id=1, api_hash="h", ui_language="de")
        self.assertEqual(fallback.lang, "ru")

    def test_load_settings_maps_legacy_exclude_chats_alias_from_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "api_id": 1,
                        "api_hash": "h",
                        "exclude_chats": [-1001700453512],
                    },
                    fh,
                )

            settings = load_settings(config_path)

        self.assertEqual(settings.whitelist_chats, {-1001700453512})

    @patch("tg_msg_manager.core.runtime.load_settings")
    def test_build_app_runtime_resolves_project_relative_paths(
        self, mock_load_settings
    ):
        mock_load_settings.return_value = Settings(
            api_id=1,
            api_hash="h",
            db_path="data/messages.db",
        )

        runtime = build_app_runtime(
            project_root="/tmp/tg-msg-manager",
            python_executable="/usr/bin/python3",
        )

        self.assertEqual(runtime.paths.project_root, "/tmp/tg-msg-manager")
        self.assertEqual(runtime.paths.db_path, "/tmp/tg-msg-manager/data/messages.db")
        self.assertEqual(runtime.paths.db_exports_dir, "/tmp/tg-msg-manager/DB_EXPORTS")
        self.assertEqual(runtime.python_executable, "/usr/bin/python3")
        mock_load_settings.assert_called_once_with("/tmp/tg-msg-manager/config.json")


if __name__ == "__main__":
    unittest.main()
