import sys
from typing import Any, Callable, Optional

from .core.models.service_payloads import (
    CleanerDialogMessagesFoundPayload,
    CleanerDialogScanStartedPayload,
    ExportDialogScanStartedPayload,
    ExportDialogSearchScanningPayload,
    ExportDialogSearchStartedPayload,
    ExportGlobalExportFinishedPayload,
    ExportSyncFinishedPayload,
    ExportSyncProgressPayload,
    ExportSyncStartedPayload,
    ExportSyncSummaryPayload,
    ExportTargetedDialogSearchStartedPayload,
    ExportTrackedUpdateStartedPayload,
    PrivateArchiveCompletedPayload,
    PrivateArchiveMediaStats,
    PrivateArchiveMediaSavedPayload,
    PrivateArchiveProgressPayload,
    PrivateArchiveStartedPayload,
    PrivateArchiveTransferStats,
)
from .core.models.sync_report import TrackedSyncRunReport
from .core.service_events import (
    CleanerEvents,
    ExportEvents,
    PrivateArchiveEvents,
    ServiceEvent,
)
from .infrastructure.storage.records import PrimaryTarget
from .i18n import _
from .utils.ui import UI

try:
    import tty
    import termios
except ImportError:
    tty = None
    termios = None


class TerminalInput:
    """Helper to read raw input including Escape key on Unix systems."""

    @staticmethod
    def get_char():
        if not tty or not termios:
            return sys.stdin.read(1)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)
        return ch

    @staticmethod
    def prompt_with_esc(prompt: str = "") -> Optional[str]:
        """Equivalent to input() but returns None if ESC is pressed."""
        sys.stdout.write(prompt)
        sys.stdout.flush()
        input_str = ""
        while True:
            char = TerminalInput.get_char()
            if char == "\x1b":
                sys.stdout.write("\n")
                return None
            if char == "\r" or char == "\n":
                sys.stdout.write("\n")
                return input_str
            if char == "\x7f" or char == "\x08":
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if char.isprintable():
                input_str += char
                sys.stdout.write(char)
                sys.stdout.flush()


def _archive_media_summary(stats: PrivateArchiveMediaStats) -> str:
    return f"P:{stats.photo} V:{stats.video} S:{stats.voice} D:{stats.document}"


def _archive_progress_summary(archive_stats: PrivateArchiveTransferStats) -> str:
    return (
        f"{_('label_downloaded')}={archive_stats.downloaded} "
        f"{_('label_skipped')}={archive_stats.skipped}"
    )


def _render_export_sync_chat_started(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = ExportSyncStartedPayload.coerce(payload)
    colored_title = UI.paint(typed.chat_title, UI.CLR_CHAT, bold=True)
    mode_label = f"DEEP (Depth {typed.depth})" if typed.deep_mode else "FLAT"
    mode_badge = UI.paint(mode_label, UI.CLR_STATS, bold=True)
    status_badge = ""
    if typed.status_kind == "resuming_history":
        status_badge = UI.muted(_("text_resuming_history"))
    elif typed.status_kind == "updating":
        status_badge = UI.muted(_("text_updating"))
    header = f"{UI.section(_('section_sync'), icon='◆')}  {colored_title}"
    if typed.user_label:
        header = f"{header}  {UI.muted(_('label_user'))} {UI.paint(typed.user_label, UI.CLR_USER, bold=True)}"
    header = f"{header}  {UI.muted(_('label_mode'))} {mode_badge}"
    if status_badge:
        header = f"{header}  {status_badge}"
    print(f"\n{header}")


def _render_export_sync_progress(payload: dict[str, Any]) -> None:
    typed = ExportSyncProgressPayload.coerce(payload)
    suffix = f"💬 {typed.db_total}"
    if typed.extra:
        suffix = f"{suffix} {typed.extra}"
    UI.print_status("Syncing", "", extra=suffix)


def _render_export_sync_finished(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = ExportSyncFinishedPayload.coerce(payload)
    UI.print_status("Finished", "", extra=f"💬 {typed.db_count}")
    sys.stdout.write("\n")
    sys.stdout.flush()


def _render_export_sync_summary(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = ExportSyncSummaryPayload.coerce(payload)
    UI.print_final_summary(
        "sync_summary_title",
        [
            {
                "title": typed.title,
                "lines": [
                    ("user_messages", typed.own_messages),
                    ("with_context", typed.with_context),
                ],
            }
        ],
    )


def _render_export_history_fully_synced(payload: dict[str, Any]) -> None:
    del payload
    if sys.stdout.isatty():
        print(
            f"\n{UI.paint('✓', UI.CLR_SUCCESS, bold=True)} {UI.paint(_('text_history_fully_synced'), UI.CLR_SUCCESS)}"
        )


def _render_export_targeted_dialog_search_started(payload: dict[str, Any]) -> None:
    if sys.stdout.isatty():
        typed = ExportTargetedDialogSearchStartedPayload.coerce(payload)
        print(
            f"\n{UI.section(_('section_targeted_search'), icon='◆')}  {UI.key_value(_('label_user'), typed.from_user_id, icon='◌')}  {UI.key_value(_('label_dialogs'), typed.dialog_count, icon='◌')}"
        )


def _render_export_dialog_search_started(payload: dict[str, Any]) -> None:
    if sys.stdout.isatty():
        typed = ExportDialogSearchStartedPayload.coerce(payload)
        print(
            f"\n{UI.section(_('section_dialog_search'), icon='◆')}  {UI.key_value(_('label_user'), typed.from_user_id, icon='◌')}"
        )


def _render_export_dialog_search_scanning(payload: dict[str, Any]) -> None:
    if sys.stdout.isatty():
        typed = ExportDialogSearchScanningPayload.coerce(payload)
        print(
            f"   {UI.muted(_('label_scanning'))} {UI.paint(typed.dialog_count, UI.CLR_STATS, bold=True)} {UI.muted(_('label_dialogs'))}"
        )


def _render_export_dialog_scan_started(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = ExportDialogScanStartedPayload.coerce(payload)
    progress_label = f"{typed.index}/{typed.total}"
    print(
        f"\n   {UI.paint(progress_label, UI.CLR_MUTED)}  {UI.paint(typed.dialog_title, UI.CLR_CHAT, bold=True)}"
    )


def _render_export_global_export_finished(payload: dict[str, Any]) -> None:
    if UI.is_tty():
        typed = ExportGlobalExportFinishedPayload.coerce(payload)
        print(
            f"\n{UI.paint('✓', UI.CLR_SUCCESS, bold=True)} {UI.paint(_('text_global_export_finished'), UI.CLR_SUCCESS)}  {UI.key_value(_('label_processed'), typed.total_processed, icon='✉')}"
        )


def _render_export_tracked_update_started(payload: dict[str, Any]) -> None:
    if UI.is_tty():
        typed = ExportTrackedUpdateStartedPayload.coerce(payload)
        print(
            f"\n{UI.section(_('section_update'), icon='◆')}  {UI.key_value(_('label_targets'), typed.target_count, icon='◌')}"
        )


def _render_cleaner_dialog_scan_started(payload: dict[str, Any]) -> None:
    typed = CleanerDialogScanStartedPayload.coerce(payload)
    UI.print_status("Cleaning", f"[{typed.index}/{typed.total}] {typed.name}")


def _render_cleaner_dialog_messages_found(payload: dict[str, Any]) -> None:
    typed = CleanerDialogMessagesFoundPayload.coerce(payload)
    UI.print_status("Found", typed.count, extra=f"messages in {typed.name}")
    sys.stdout.write("\n")
    sys.stdout.flush()


def _render_private_archive_started(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = PrivateArchiveStartedPayload.coerce(payload)
    print(
        f"\n{UI.section(_('section_pm_archive'), icon='◆')}  {UI.paint(typed.target_name, UI.CLR_USER, bold=True)}  {UI.muted(_('label_id'))} {UI.paint(typed.user_id, UI.CLR_ID)}"
    )
    print(f"   {UI.muted(_('label_path'))} {UI.paint(typed.user_dir, UI.CLR_CHAT)}")


def _render_private_archive_progress(payload: dict[str, Any]) -> None:
    typed = PrivateArchiveProgressPayload.coerce(payload)
    UI.print_status(
        "Archiving",
        typed.count,
        extra=f"{_('label_messages')} | {_archive_progress_summary(typed.archive_stats)} | {_('label_media')}: {_archive_media_summary(typed.stats)}",
    )


def _render_private_archive_media_saved(payload: dict[str, Any]) -> None:
    if UI.is_tty():
        typed = PrivateArchiveMediaSavedPayload.coerce(payload)
        print(
            f"   {UI.paint('↳', UI.CLR_MUTED)} {UI.muted(_('label_saved_media'))} {UI.paint(typed.filename, UI.CLR_STATS)}"
        )


def _render_private_archive_completed(payload: dict[str, Any]) -> None:
    if not UI.is_tty():
        return
    typed = PrivateArchiveCompletedPayload.coerce(payload)
    UI.print_status(
        "Complete",
        typed.count,
        extra=f"{_('label_messages')} | {_archive_progress_summary(typed.archive_stats)} | {_('label_media')}: {_archive_media_summary(typed.stats)}",
    )
    UI.print_final_summary(
        "sync_summary_title",
        [
            {
                "title": typed.target_name,
                "lines": [
                    ("messages", typed.count),
                    ("downloaded", typed.archive_stats.downloaded),
                    ("skipped", typed.archive_stats.skipped),
                    ("media", typed.stats.total),
                ],
            }
        ],
    )
    sys.stdout.write("\n")
    sys.stdout.flush()


_EVENT_RENDERERS: dict[str, Callable[[dict[str, Any]], None]] = {
    ExportEvents.SYNC_CHAT_STARTED: _render_export_sync_chat_started,
    ExportEvents.SYNC_PROGRESS: _render_export_sync_progress,
    ExportEvents.SYNC_FINISHED: _render_export_sync_finished,
    ExportEvents.SYNC_SUMMARY: _render_export_sync_summary,
    ExportEvents.HISTORY_FULLY_SYNCED: _render_export_history_fully_synced,
    ExportEvents.TARGETED_DIALOG_SEARCH_STARTED: _render_export_targeted_dialog_search_started,
    ExportEvents.DIALOG_SEARCH_STARTED: _render_export_dialog_search_started,
    ExportEvents.DIALOG_SEARCH_SCANNING: _render_export_dialog_search_scanning,
    ExportEvents.DIALOG_SCAN_STARTED: _render_export_dialog_scan_started,
    ExportEvents.GLOBAL_EXPORT_FINISHED: _render_export_global_export_finished,
    ExportEvents.TRACKED_UPDATE_STARTED: _render_export_tracked_update_started,
    CleanerEvents.DIALOG_SCAN_STARTED: _render_cleaner_dialog_scan_started,
    CleanerEvents.DIALOG_MESSAGES_FOUND: _render_cleaner_dialog_messages_found,
    PrivateArchiveEvents.STARTED: _render_private_archive_started,
    PrivateArchiveEvents.PROGRESS: _render_private_archive_progress,
    PrivateArchiveEvents.MEDIA_SAVED: _render_private_archive_media_saved,
    PrivateArchiveEvents.COMPLETED: _render_private_archive_completed,
}


def render_service_event(event: ServiceEvent) -> None:
    renderer = _EVENT_RENDERERS.get(event.name)
    if renderer is not None:
        renderer(event.payload)


def print_target_list(targets: list[PrimaryTarget]) -> None:
    """Prints a formatted, color-coded list of primary targets."""
    for i, item in enumerate(targets):
        u = PrimaryTarget.coerce(item)
        display_name = UI.paint(u.author_name, UI.CLR_USER, bold=True)
        user_id_str = UI.paint(u.user_id, UI.CLR_ID)
        chat_info = (
            f"  {UI.paint('•', UI.CLR_BORDER)}  {UI.paint(u.chat_title, UI.CLR_CHAT)}"
            if u.chat_title
            else ""
        )
        own_count = UI.key_value(_("label_msg_short"), u.user_msg_count, icon="✉")
        context_count = UI.key_value(
            _("label_ctx_short"), u.context_msg_count, icon="◌"
        )
        is_complete = u.is_complete
        status_color = UI.CLR_SUCCESS if is_complete else UI.CLR_WARN
        status_label = _("status_complete") if is_complete else _("status_incomplete")
        status = UI.paint(status_label, status_color, bold=True)
        idx_str = UI.paint(f"{i + 1:02}.", UI.CLR_MUTED)
        print(
            f" {idx_str}  {display_name}  {UI.muted(_('label_id'))} {user_id_str}  {own_count}  {context_count}  {status}{chat_info}"
        )


def print_update_summary(stats: Any, *, title: str) -> None:
    try:
        report = TrackedSyncRunReport.coerce(stats)
    except TypeError:
        report = TrackedSyncRunReport()

    UI.print_final_summary(
        "sync_summary_title",
        [
            {
                "title": title,
                "lines": [
                    ("processed", report.total_processed),
                    ("targets", len(report)),
                ],
            }
        ],
    )


def pause_for_enter() -> None:
    sys.stdout.write("\n" + _("press_enter"))
    sys.stdout.flush()
    TerminalInput.get_char()


def render_main_menu(me_id: Any) -> None:
    UI.clear_screen()
    UI.print_gradient_banner()
    print(UI.rule(105))
    print(
        f" {UI.section(_('section_control_center'), icon='◆')}  {UI.key_value(_('label_account'), me_id, icon='◌')}"
    )
    print(f" {UI.muted('ESC — back/cancel   ·   0 — exit')}")
    print(UI.rule(105))
    for i in range(1, 10):
        print(
            f" {UI.paint(f'[{i}]', UI.CLR_ACCENT, bold=True)} {UI.paint(_('menu_' + str(i)), UI.CLR_TEXT)}  {UI.muted(_('menu_' + str(i) + '_desc'))}"
        )
    print(
        f" {UI.paint('[L]', UI.CLR_ACCENT, bold=True)} {UI.paint(_('menu_lang'), UI.CLR_TEXT)}"
    )
    print(
        f" {UI.paint('[0]', UI.CLR_ACCENT, bold=True)} {UI.paint(_('menu_exit'), UI.CLR_TEXT)}"
    )
