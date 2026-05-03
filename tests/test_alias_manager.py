import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.services.alias_manager import AliasManager


class TestAliasManager(unittest.TestCase):
    def test_install_returns_structured_error_for_unsupported_platform(self):
        manager = AliasManager(
            project_root="/tmp/project",
            python_executable="/usr/bin/python3",
        )
        manager.os_type = "Plan9"

        result = manager.install()

        self.assertFalse(result.success)
        self.assertEqual(result.error_kind, "unsupported_platform")
        self.assertEqual(result.platform, "Plan9")

    def test_install_unix_returns_rc_path_without_localized_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AliasManager(
                project_root="/tmp/project",
                python_executable="/usr/bin/python3",
            )
            manager.os_type = "Darwin"
            manager.home_dir = tmpdir

            with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
                result = manager.install()

            self.assertTrue(result.success)
            self.assertTrue(result.rc_path.endswith(".zshrc"))
            self.assertIsNone(result.bin_dir)
            self.assertTrue(os.path.exists(result.rc_path))
            with open(result.rc_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("tg-msg-manager aliases", content)

    def test_get_alias_specs_returns_structured_help_entries(self):
        manager = AliasManager()

        specs = manager.get_alias_specs()

        self.assertEqual(specs[0].alias, "tg")
        self.assertEqual(specs[0].label_key, "alias_tg")
        self.assertGreaterEqual(len(specs), 6)


if __name__ == "__main__":
    unittest.main()
