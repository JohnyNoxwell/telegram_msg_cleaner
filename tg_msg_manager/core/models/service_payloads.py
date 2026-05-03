from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ExportSyncStartedPayload:
    chat_title: str
    user_label: str = ""
    deep_mode: bool = False
    depth: int = 0
    status_kind: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chat_title": self.chat_title,
            "user_label": self.user_label,
            "deep_mode": self.deep_mode,
            "depth": self.depth,
            "status_kind": self.status_kind,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportSyncStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                chat_title=str(value.get("chat_title") or ""),
                user_label=str(value.get("user_label") or ""),
                deep_mode=bool(value.get("deep_mode", False)),
                depth=int(value.get("depth", 0) or 0),
                status_kind=value.get("status_kind"),
            )
        raise TypeError(f"Unsupported export sync started payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportSyncSummaryPayload:
    title: str
    own_messages: int
    with_context: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "own_messages": self.own_messages,
            "with_context": self.with_context,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportSyncSummaryPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                title=str(value.get("title") or ""),
                own_messages=int(value.get("own_messages", 0) or 0),
                with_context=int(value.get("with_context", 0) or 0),
            )
        raise TypeError(f"Unsupported export sync summary payload: {type(value)!r}")


@dataclass(frozen=True)
class PrivateArchiveStartedPayload:
    target_name: str
    user_id: int
    user_dir: str
    last_id: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "user_id": self.user_id,
            "user_dir": self.user_dir,
            "last_id": self.last_id,
        }

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                target_name=str(value.get("target_name") or ""),
                user_id=int(value.get("user_id", 0) or 0),
                user_dir=str(value.get("user_dir") or ""),
                last_id=int(value.get("last_id", 0) or 0),
            )
        raise TypeError(f"Unsupported private archive started payload: {type(value)!r}")


@dataclass()
class PrivateArchiveMediaStats:
    photo: int = 0
    video: int = 0
    voice: int = 0
    document: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveMediaStats":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                photo=int(value.get("photo", value.get("Photo", 0)) or 0),
                video=int(value.get("video", value.get("Video", 0)) or 0),
                voice=int(value.get("voice", value.get("Voice", 0)) or 0),
                document=int(value.get("document", value.get("Document", 0)) or 0),
            )
        raise TypeError(f"Unsupported private archive media stats: {type(value)!r}")

    @property
    def total(self) -> int:
        return self.photo + self.video + self.voice + self.document

    def increment(self, media_type: Optional[str]) -> None:
        if not media_type:
            return
        if media_type == "Photo":
            self.photo += 1
        elif media_type == "Video":
            self.video += 1
        elif media_type == "Voice":
            self.voice += 1
        else:
            self.document += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "Photo": self.photo,
            "Video": self.video,
            "Voice": self.voice,
            "Document": self.document,
        }

    def __getitem__(self, key: str) -> int:
        if key == "Photo":
            return self.photo
        if key == "Video":
            return self.video
        if key == "Voice":
            return self.voice
        if key == "Document":
            return self.document
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def values(self):
        return self.as_dict().values()


@dataclass()
class PrivateArchiveTransferStats:
    downloaded: int = 0
    skipped: int = 0

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveTransferStats":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                downloaded=int(value.get("downloaded", 0) or 0),
                skipped=int(value.get("skipped", 0) or 0),
            )
        raise TypeError(f"Unsupported private archive transfer stats: {type(value)!r}")

    def as_dict(self) -> dict[str, int]:
        return {
            "downloaded": self.downloaded,
            "skipped": self.skipped,
        }

    def __getitem__(self, key: str) -> int:
        if key == "downloaded":
            return self.downloaded
        if key == "skipped":
            return self.skipped
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass(frozen=True)
class PrivateArchiveProgressPayload:
    count: int
    stats: PrivateArchiveMediaStats
    archive_stats: PrivateArchiveTransferStats

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "stats": self.stats.as_dict(),
            "archive_stats": self.archive_stats.as_dict(),
        }

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveProgressPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                count=int(value.get("count", 0) or 0),
                stats=PrivateArchiveMediaStats.coerce(value.get("stats") or {}),
                archive_stats=PrivateArchiveTransferStats.coerce(
                    value.get("archive_stats") or {}
                ),
            )
        raise TypeError(
            f"Unsupported private archive progress payload: {type(value)!r}"
        )


@dataclass(frozen=True)
class PrivateArchiveMediaSavedPayload:
    filename: str
    path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "path": self.path,
        }

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveMediaSavedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                filename=str(value.get("filename") or ""),
                path=str(value.get("path") or ""),
            )
        raise TypeError(
            f"Unsupported private archive media-saved payload: {type(value)!r}"
        )


@dataclass(frozen=True)
class PrivateArchiveCompletedPayload:
    target_name: str
    count: int
    stats: PrivateArchiveMediaStats
    archive_stats: PrivateArchiveTransferStats

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "count": self.count,
            "stats": self.stats.as_dict(),
            "archive_stats": self.archive_stats.as_dict(),
        }

    @classmethod
    def coerce(cls, value: Any) -> "PrivateArchiveCompletedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                target_name=str(value.get("target_name") or ""),
                count=int(value.get("count", 0) or 0),
                stats=PrivateArchiveMediaStats.coerce(value.get("stats") or {}),
                archive_stats=PrivateArchiveTransferStats.coerce(
                    value.get("archive_stats") or {}
                ),
            )
        raise TypeError(
            f"Unsupported private archive completed payload: {type(value)!r}"
        )


@dataclass(frozen=True)
class ExportSyncProgressPayload:
    db_total: int
    extra: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "db_total": self.db_total,
            "extra": self.extra,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportSyncProgressPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                db_total=int(value.get("db_total", 0) or 0),
                extra=str(value.get("extra") or ""),
            )
        raise TypeError(f"Unsupported export sync progress payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportSyncFinishedPayload:
    db_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "db_count": self.db_count,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportSyncFinishedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(db_count=int(value.get("db_count", 0) or 0))
        raise TypeError(f"Unsupported export sync finished payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportTargetedDialogSearchStartedPayload:
    from_user_id: int
    dialog_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_user_id": self.from_user_id,
            "dialog_count": self.dialog_count,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportTargetedDialogSearchStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                from_user_id=int(value.get("from_user_id", 0) or 0),
                dialog_count=int(value.get("dialog_count", 0) or 0),
            )
        raise TypeError(
            f"Unsupported targeted dialog search started payload: {type(value)!r}"
        )


@dataclass(frozen=True)
class ExportDialogSearchStartedPayload:
    from_user_id: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_user_id": self.from_user_id,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportDialogSearchStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(from_user_id=int(value.get("from_user_id", 0) or 0))
        raise TypeError(f"Unsupported dialog search started payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportDialogSearchScanningPayload:
    dialog_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "dialog_count": self.dialog_count,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportDialogSearchScanningPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(dialog_count=int(value.get("dialog_count", 0) or 0))
        raise TypeError(f"Unsupported dialog search scanning payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportDialogScanStartedPayload:
    index: int
    total: int
    dialog_title: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "total": self.total,
            "dialog_title": self.dialog_title,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportDialogScanStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                index=int(value.get("index", 0) or 0),
                total=int(value.get("total", 0) or 0),
                dialog_title=str(value.get("dialog_title") or ""),
            )
        raise TypeError(f"Unsupported dialog scan started payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportGlobalExportFinishedPayload:
    total_processed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_processed": self.total_processed,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportGlobalExportFinishedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(total_processed=int(value.get("total_processed", 0) or 0))
        raise TypeError(f"Unsupported global export finished payload: {type(value)!r}")


@dataclass(frozen=True)
class ExportTrackedUpdateStartedPayload:
    target_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_count": self.target_count,
        }

    @classmethod
    def coerce(cls, value: Any) -> "ExportTrackedUpdateStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(target_count=int(value.get("target_count", 0) or 0))
        raise TypeError(f"Unsupported tracked update started payload: {type(value)!r}")


@dataclass(frozen=True)
class CleanerDialogScanStartedPayload:
    index: int
    total: int
    name: str
    chat_id: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "total": self.total,
            "name": self.name,
            "chat_id": self.chat_id,
        }

    @classmethod
    def coerce(cls, value: Any) -> "CleanerDialogScanStartedPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                index=int(value.get("index", 0) or 0),
                total=int(value.get("total", 0) or 0),
                name=str(value.get("name") or ""),
                chat_id=int(value.get("chat_id", 0) or 0),
            )
        raise TypeError(
            f"Unsupported cleaner dialog scan started payload: {type(value)!r}"
        )


@dataclass(frozen=True)
class CleanerDialogMessagesFoundPayload:
    name: str
    chat_id: int
    count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "chat_id": self.chat_id,
            "count": self.count,
        }

    @classmethod
    def coerce(cls, value: Any) -> "CleanerDialogMessagesFoundPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                name=str(value.get("name") or ""),
                chat_id=int(value.get("chat_id", 0) or 0),
                count=int(value.get("count", 0) or 0),
            )
        raise TypeError(
            f"Unsupported cleaner dialog messages found payload: {type(value)!r}"
        )
