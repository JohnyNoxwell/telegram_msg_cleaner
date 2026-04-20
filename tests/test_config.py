import sys
import os
import unittest
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.config import Settings

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
        settings = Settings(api_id=1, api_hash="h", whitelist=["123", "user1"])
        self.assertIn("123", settings.whitelist)
        self.assertIn("user1", settings.whitelist)

if __name__ == "__main__":
    unittest.main()
