from dataclasses import dataclass, fields
from typing import Any, Iterator, Mapping, Optional


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(_coerce_int(value, 0))


class StorageRecord(Mapping[str, Any]):
    """Typed storage DTO with a small dict-compatibility surface for migration."""

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        for field in fields(self):
            yield field.name

    def __len__(self) -> int:
        return len(fields(self))

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class SyncUser(StorageRecord):
    user_id: int
    author_name: Optional[str] = None

    @classmethod
    def coerce(cls, value: Any) -> "SyncUser":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                user_id=_coerce_int(value.get("user_id")),
                author_name=value.get("author_name"),
            )
        return cls(user_id=0)


@dataclass(frozen=True)
class StoredUser(StorageRecord):
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None

    @property
    def id(self) -> int:
        return self.user_id

    @classmethod
    def coerce(cls, value: Any) -> Optional["StoredUser"]:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                user_id=_coerce_int(value.get("user_id")),
                first_name=value.get("first_name"),
                last_name=value.get("last_name"),
                username=value.get("username"),
                phone=value.get("phone"),
            )
        raise TypeError(f"Unsupported stored user payload: {type(value)!r}")


@dataclass(frozen=True)
class SyncStatus(StorageRecord):
    last_msg_id: int = 0
    tail_msg_id: int = 0
    is_complete: bool = False
    deep_mode: bool = False
    recursive_depth: int = 0
    last_sync_at: int = 0
    author_name: Optional[str] = None

    @classmethod
    def coerce(cls, value: Any) -> "SyncStatus":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                last_msg_id=_coerce_int(value.get("last_msg_id")),
                tail_msg_id=_coerce_int(value.get("tail_msg_id")),
                is_complete=_coerce_bool(value.get("is_complete")),
                deep_mode=_coerce_bool(value.get("deep_mode")),
                recursive_depth=_coerce_int(value.get("recursive_depth")),
                last_sync_at=_coerce_int(value.get("last_sync_at")),
                author_name=value.get("author_name"),
            )
        return cls()


@dataclass(frozen=True)
class PrimaryTarget(StorageRecord):
    user_id: int
    chat_id: int
    author_name: Optional[str] = None
    added_at: int = 0
    last_sync_at: int = 0
    last_msg_id: int = 0
    tail_msg_id: int = 0
    is_complete: bool = False
    deep_mode: bool = False
    recursive_depth: int = 0
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    chat_title: Optional[str] = None
    user_msg_count: int = 0
    context_msg_count: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "PrimaryTarget":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                user_id=_coerce_int(value.get("user_id")),
                chat_id=_coerce_int(value.get("chat_id")),
                author_name=value.get("author_name"),
                added_at=_coerce_int(value.get("added_at")),
                last_sync_at=_coerce_int(value.get("last_sync_at")),
                last_msg_id=_coerce_int(value.get("last_msg_id")),
                tail_msg_id=_coerce_int(value.get("tail_msg_id")),
                is_complete=_coerce_bool(value.get("is_complete")),
                deep_mode=_coerce_bool(value.get("deep_mode")),
                recursive_depth=_coerce_int(value.get("recursive_depth")),
                username=value.get("username"),
                first_name=value.get("first_name"),
                last_name=value.get("last_name"),
                chat_title=value.get("chat_title"),
                user_msg_count=_coerce_int(value.get("user_msg_count")),
                context_msg_count=_coerce_int(value.get("context_msg_count")),
            )
        return cls(user_id=0, chat_id=0)


@dataclass(frozen=True)
class UserExportSummary(StorageRecord):
    message_count: int
    first_message_id: int
    last_message_id: int
    first_timestamp: int
    last_timestamp: int
    target_author_name: Optional[str] = None

    @classmethod
    def coerce(cls, value: Any) -> Optional["UserExportSummary"]:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                message_count=_coerce_int(value.get("message_count")),
                first_message_id=_coerce_int(value.get("first_message_id")),
                last_message_id=_coerce_int(value.get("last_message_id")),
                first_timestamp=_coerce_int(value.get("first_timestamp")),
                last_timestamp=_coerce_int(value.get("last_timestamp")),
                target_author_name=value.get("target_author_name"),
            )
        raise TypeError(f"Unsupported export summary payload: {type(value)!r}")


@dataclass(frozen=True)
class UserExportRow(StorageRecord):
    message_id: int
    chat_id: int
    user_id: int
    author_name: Optional[str] = None
    timestamp: int = 0
    text: Optional[str] = None
    media_type: Optional[str] = None
    reply_to_id: Optional[int] = None
    fwd_from_id: Optional[int] = None
    context_group_id: Optional[int] = None
    raw_payload: Any = None
    is_service: bool = False

    @classmethod
    def coerce(cls, value: Any) -> "UserExportRow":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                message_id=_coerce_int(value.get("message_id")),
                chat_id=_coerce_int(value.get("chat_id")),
                user_id=_coerce_int(value.get("user_id")),
                author_name=value.get("author_name"),
                timestamp=_coerce_int(value.get("timestamp")),
                text=value.get("text"),
                media_type=value.get("media_type"),
                reply_to_id=value.get("reply_to_id"),
                fwd_from_id=value.get("fwd_from_id"),
                context_group_id=value.get("context_group_id"),
                raw_payload=value.get("raw_payload"),
                is_service=_coerce_bool(value.get("is_service")),
            )
        raise TypeError(f"Unsupported export row payload: {type(value)!r}")


@dataclass(frozen=True)
class TargetMessageBreakdown(StorageRecord):
    own_messages: int = 0
    with_context: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "TargetMessageBreakdown":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                own_messages=_coerce_int(value.get("own_messages")),
                with_context=_coerce_int(value.get("with_context")),
            )
        return cls()


@dataclass(frozen=True)
class DeleteUserDataResult(StorageRecord):
    deleted_messages: int = 0
    deleted_targets: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "DeleteUserDataResult":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                deleted_messages=_coerce_int(
                    value.get("deleted_messages", value.get("message_count"))
                ),
                deleted_targets=_coerce_int(
                    value.get("deleted_targets", value.get("target_count"))
                ),
            )
        if isinstance(value, (tuple, list)):
            deleted_messages = value[0] if len(value) > 0 else 0
            deleted_targets = value[1] if len(value) > 1 else 0
            return cls(
                deleted_messages=_coerce_int(deleted_messages),
                deleted_targets=_coerce_int(deleted_targets),
            )
        return cls()


@dataclass(frozen=True)
class TerminalRepairCandidate(StorageRecord):
    user_id: int = 0
    chat_id: int = 0
    author_name: Optional[str] = None
    last_msg_id: int = 0
    tail_msg_id: int = 0
    is_complete: bool = False
    last_sync_at: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "TerminalRepairCandidate":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                user_id=_coerce_int(value.get("user_id")),
                chat_id=_coerce_int(value.get("chat_id")),
                author_name=value.get("author_name"),
                last_msg_id=_coerce_int(value.get("last_msg_id")),
                tail_msg_id=_coerce_int(value.get("tail_msg_id")),
                is_complete=_coerce_bool(value.get("is_complete")),
                last_sync_at=_coerce_int(value.get("last_sync_at")),
            )
        return cls()


@dataclass(frozen=True)
class RetryTaskRecord(StorageRecord):
    task_id: str = ""
    chat_id: int = 0
    task_type: str = ""
    last_error: Optional[str] = None
    next_retry_timestamp: int = 0
    retry_count: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "RetryTaskRecord":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                task_id=str(value.get("task_id") or ""),
                chat_id=_coerce_int(value.get("chat_id")),
                task_type=str(value.get("task_type") or ""),
                last_error=value.get("last_error"),
                next_retry_timestamp=_coerce_int(value.get("next_retry_timestamp")),
                retry_count=_coerce_int(value.get("retry_count")),
            )
        return cls()
