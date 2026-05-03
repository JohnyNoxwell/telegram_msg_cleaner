from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


class ExportEvents:
    SYNC_CHAT_STARTED = "export.sync_chat_started"
    SYNC_PROGRESS = "export.sync_progress"
    SYNC_FINISHED = "export.sync_finished"
    SYNC_SUMMARY = "export.sync_summary"
    HISTORY_FULLY_SYNCED = "export.history_fully_synced"
    TARGETED_DIALOG_SEARCH_STARTED = "export.targeted_dialog_search_started"
    DIALOG_SEARCH_STARTED = "export.dialog_search_started"
    DIALOG_SEARCH_SCANNING = "export.dialog_search_scanning"
    DIALOG_SCAN_STARTED = "export.dialog_scan_started"
    GLOBAL_EXPORT_FINISHED = "export.global_export_finished"
    TRACKED_UPDATE_STARTED = "export.tracked_update_started"


class CleanerEvents:
    DIALOG_SCAN_STARTED = "cleaner.dialog_scan_started"
    DIALOG_MESSAGES_FOUND = "cleaner.dialog_messages_found"


class PrivateArchiveEvents:
    STARTED = "private_archive.started"
    PROGRESS = "private_archive.progress"
    MEDIA_SAVED = "private_archive.media_saved"
    COMPLETED = "private_archive.completed"


@dataclass(frozen=True)
class ServiceEvent:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)


ServiceEventSink = Optional[Callable[[ServiceEvent], None]]


def emit_service_event(sink: ServiceEventSink, event_name: str, **payload: Any) -> None:
    if sink is None:
        return
    sink(ServiceEvent(name=event_name, payload=payload))
