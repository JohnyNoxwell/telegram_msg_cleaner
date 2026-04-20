import sys
import os
import unittest
from datetime import datetime
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.message import MessageData
from tg_msg_manager.infrastructure.storage.sqlite import SQLiteStorage

class TestSQLiteStorage(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.db_path = "test_storage.db"
        self.storage = SQLiteStorage(self.db_path)

    def tearDown(self):
        # Cleanup test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(f"{self.db_path}-wal"):
            os.remove(f"{self.db_path}-wal")
        if os.path.exists(f"{self.db_path}-shm"):
            os.remove(f"{self.db_path}-shm")

    def test_save_and_get_message(self):
        msg = MessageData(
            message_id=1,
            chat_id=123,
            user_id=456,
            author_name="Test User",
            timestamp=datetime.now(),
            text="Hello SQLite",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={"test": "data"}
        )
        
        # Test save
        success = self.storage.save_message(msg)
        self.assertTrue(success)
        
        # Test existence
        self.assertTrue(self.storage.message_exists(123, 1))
        
        # Test retrieval
        retrieved = self.storage.get_message(123, 1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_id, 1)
        self.assertEqual(retrieved.text, "Hello SQLite")
        self.assertEqual(retrieved.raw_payload["test"], "data")

    def test_batch_save(self):
        msgs = [
            MessageData(message_id=i, chat_id=789, user_id=1, author_name="Batch User",
                        timestamp=datetime.now(), 
                        text=f"Batch {i}", media_type=None, reply_to_id=None, 
                        fwd_from_id=None, context_group_id=None, raw_payload={})
            for i in range(1, 11)
        ]
        
        count = self.storage.save_messages(msgs)
        self.assertEqual(count, 10)
        self.assertEqual(self.storage.get_last_msg_id(789), 10)

    def test_upsert_logic(self):
        msg = MessageData(
            message_id=1, chat_id=1, user_id=1, author_name="Orig User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )
        self.storage.save_message(msg)
        
        # Update text for the same message_id
        updated_msg = MessageData(
            message_id=1, chat_id=1, user_id=1, author_name="Upd User",
            timestamp=datetime.now(), 
            text="Updated", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={}
        )
        self.storage.save_message(updated_msg)
        
        retrieved = self.storage.get_message(1, 1)
        self.assertEqual(retrieved.text, "Updated")

    def test_payload_hashing(self):
        msg = MessageData(
            message_id=55, chat_id=1, user_id=1, author_name="Hash User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={"v": 1}
        )
        self.storage.save_message(msg)
        h1 = msg.get_payload_hash()
        
        # Test hash detection
        msg2 = MessageData(
            message_id=55, chat_id=1, user_id=1, author_name="Hash User",
            timestamp=datetime.now(), 
            text="Original", media_type=None, reply_to_id=None, 
            fwd_from_id=None, context_group_id=None, raw_payload={"v": 2}
        )
        h2 = msg2.get_payload_hash()
        self.assertNotEqual(h1, h2)
        
        # Test that update occurs when hash changes
        self.storage.save_message(msg2)
        retrieved = self.storage.get_message(1, 55)
        self.assertEqual(retrieved.raw_payload["v"], 2)


    def test_get_all_message_ids(self):
        msg = MessageData(1, 100, 1, "Test User", datetime.now(), "Test", None, None, None, None, {})
        self.storage.save_message(msg)
        ids = self.storage.get_all_message_ids_for_chat(100)
        self.assertEqual(ids, [1])

if __name__ == "__main__":
    unittest.main()
