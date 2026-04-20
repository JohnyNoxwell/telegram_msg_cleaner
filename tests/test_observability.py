import sys
import os
import io
import json
import unittest
import logging
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.logging import JSONFormatter
from tg_msg_manager.core.context import set_chat_id, ctx_chat_id
from tg_msg_manager.core.telemetry import telemetry

class TestObservability(unittest.TestCase):
    def test_json_formatter(self):
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(JSONFormatter())
        
        logger = logging.getLogger("test_json")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.propagate = False
        
        # Set context
        set_chat_id(999)
        logger.info("Test message")
        
        output = log_capture.getvalue().strip()
        data = json.loads(output)
        
        self.assertEqual(data["message"], "Test message")
        self.assertEqual(data["chat_id"], 999)
        self.assertIn("timestamp", data)

    def test_telemetry_counters(self):
        # Reset telemetry for test (singleton)
        telemetry.data.api_requests_total = 0
        
        telemetry.track_request()
        telemetry.track_request()
        
        self.assertEqual(telemetry.get_summary()["api_requests"], 2)

if __name__ == "__main__":
    unittest.main()
