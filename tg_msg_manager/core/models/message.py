from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import json

SCHEMA_VERSION = 1

@dataclass(frozen=True)
class MessageData:
    message_id: int
    chat_id: int
    user_id: int
    author_name: Optional[str]
    timestamp: datetime
    text: Optional[str]
    media_type: Optional[str]
    reply_to_id: Optional[int]
    fwd_from_id: Optional[int]
    context_group_id: Optional[str]
    raw_payload: Dict[str, Any]

    def __post_init__(self):
        # Strict type validation
        if not isinstance(self.message_id, int):
            raise TypeError(f"message_id must be int, not {type(self.message_id)}")
        if not isinstance(self.chat_id, int):
            raise TypeError(f"chat_id must be int, not {type(self.chat_id)}")
        if not isinstance(self.user_id, int):
            raise TypeError(f"user_id must be int, not {type(self.user_id)}")
        if not isinstance(self.timestamp, datetime):
            raise TypeError(f"timestamp must be datetime, not {type(self.timestamp)}")
        if not isinstance(self.raw_payload, dict):
            raise TypeError(f"raw_payload must be dict, not {type(self.raw_payload)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "author_name": self.author_name,
            "timestamp": int(self.timestamp.timestamp()),
            "text": self.text,
            "media_type": self.media_type,
            "reply_to_id": self.reply_to_id,
            "fwd_from_id": self.fwd_from_id,
            "context_group_id": self.context_group_id,
            "raw_payload": self.raw_payload
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageData':
        return cls(
            message_id=data["message_id"],
            chat_id=data["chat_id"],
            user_id=data["user_id"],
            author_name=data.get("author_name"),
            timestamp=datetime.fromtimestamp(data["timestamp"]),
            text=data.get("text"),
            media_type=data.get("media_type"),
            reply_to_id=data.get("reply_to_id"),
            fwd_from_id=data.get("fwd_from_id"),
            context_group_id=data.get("context_group_id"),
            raw_payload=data.get("raw_payload", {})
        )

    def get_payload_hash(self) -> str:
        """Deterministic SHA256 of core fields and raw_payload."""
        hash_data = {
            "text": self.text,
            "media_type": self.media_type,
            "raw_payload": self.raw_payload
        }

        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, bytes):
                return obj.hex()
            return f"<<Unserializable: {type(obj)}>>"

        data_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False, default=json_serial)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

def get_message_key(msg: MessageData) -> str:
    """Unique key format: chat_id:message_id"""
    return f"{msg.chat_id}:{msg.message_id}"
