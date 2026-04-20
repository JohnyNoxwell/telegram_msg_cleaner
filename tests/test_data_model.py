# tests/test_data_model.py
import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Step 1.1.1 verification: check package integrity"""
    try:
        import tg_msg_manager.core
        import tg_msg_manager.core.models
        print("✅ 1.1.1: Package structure is valid.")
    except ImportError as e:
        print(f"❌ 1.1.1 Error: {e}")
        sys.exit(1)

def test_message_structure():
    """Steps 1.1.2 - 1.1.5 verification"""
    try:
        from tg_msg_manager.core.models.message import MessageData
        
        # 1.1.3: Creation test
        msg = MessageData(
            message_id=1,
            chat_id=100,
            user_id=200,
            author_name="Test User",
            timestamp=datetime.now(),
            text="Test message",
            media_type=None,
            reply_to_id=None,
            fwd_from_id=None,
            context_group_id=None,
            raw_payload={"raw": "data"}
        )
        print("✅ 1.1.3: MessageData class created successfully.")
        
        # 1.1.4: Type validation test (should fail if wrong types passed)
        try:
            MessageData(message_id="wrong", chat_id=1, user_id=2, author_name="test", timestamp="not-a-date", text="test", 
                        media_type=None, reply_to_id=None, fwd_from_id=None, context_group_id=None, raw_payload={})
            print("❌ 1.1.4: Type validation failed to catch wrong types!")
        except (ValueError, TypeError):
            print("✅ 1.1.4: Type validation working.")
            
        # 1.1.5: Serialization test
        d = msg.to_dict()
        msg2 = MessageData.from_dict(d)
        if msg.message_id == msg2.message_id and msg.text == msg2.text:
            print("✅ 1.1.5: Serialization to_dict/from_dict working.")
        else:
            print("❌ 1.1.5: Serialization mismatch.")

        # 1.2.2: Key generation test
        from tg_msg_manager.core.models.message import get_message_key
        key = get_message_key(msg)
        if key == "100:1":
            print("✅ 1.2.2: get_message_key working.")
        else:
            print(f"❌ 1.2.2: get_message_key error (got {key}).")

        # 1.3.1: Schema version test
        from tg_msg_manager.core.models.message import SCHEMA_VERSION
        if SCHEMA_VERSION == 1:
            print("✅ 1.3.1: SCHEMA_VERSION defined.")
        else:
            print(f"❌ 1.3.1: SCHEMA_VERSION error (got {SCHEMA_VERSION}).")

    except ImportError as e:
        print(f"❌ Import error during 1.2/1.3 tests: {e}")

if __name__ == "__main__":
    test_imports()
    test_message_structure()
