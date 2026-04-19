from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class MessageData:
    date: datetime
    author_name: str
    author_id: int
    author_username: Optional[str]
    text: str
    msg_id: int = 0
    chat_id: int = 0
    chat_title: str = ""
    is_reply: bool = False
    reply_to_msg_id: Optional[int] = None
    is_forward: bool = False
    fwd_from_id: Optional[int] = None
    fwd_from_name: Optional[str] = None
    media_type: Optional[str] = None
    edit_date: Optional[datetime] = None
    reactions: List[str] = field(default_factory=list)
    original_msg: Optional[Dict[str, Any]] = None
    schema_version: int = 1

    def to_dict(self):
        d = asdict(self)
        d['date'] = self.date.isoformat() if self.date else None
        d['edit_date'] = self.edit_date.isoformat() if self.edit_date else None
        d['schema_version'] = self.schema_version
        if self.original_msg and hasattr(self.original_msg, 'to_dict'):
            d['original_msg'] = self.original_msg.to_dict()
        return d
