import sys
import os
import shutil
import tempfile
import unittest
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.services.file_writer import FileRotateWriter


class TestFileRotateWriter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="tg_writer_test_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    async def test_txt_resume_uses_persisted_state(self):
        base_path = os.path.join(self.tmpdir, "chat_log.txt")

        writer = FileRotateWriter(base_path, as_json=False, max_msgs=2, overwrite=True)
        await writer.write_block("first\n", 1)

        resumed = FileRotateWriter(base_path, as_json=False, max_msgs=2, overwrite=False)
        await resumed.write_block("second\n", 1)
        await resumed.write_block("third\n", 1)

        self.assertTrue(os.path.exists(base_path))
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "chat_log_part2.txt")))

    async def test_overwrite_cleans_state(self):
        base_path = os.path.join(self.tmpdir, "chat_log.txt")

        writer = FileRotateWriter(base_path, as_json=False, max_msgs=2, overwrite=True)
        await writer.write_block("first\n", 1)
        state_path = os.path.join(self.tmpdir, ".chat_log.writer_state.json")
        self.assertTrue(os.path.exists(state_path))

        FileRotateWriter(base_path, as_json=False, max_msgs=2, overwrite=True)
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertEqual(state["current_part"], 1)
        self.assertEqual(state["current_count"], 0)


if __name__ == "__main__":
    unittest.main()
