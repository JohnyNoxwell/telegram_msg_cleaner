import asyncio
import logging
import sys
import argparse
from typing import Optional, Any

from .core.config import settings
from .core.logging import setup_logging
from .core.process import ProcessManager
from .core.service_events import ServiceEvent
from .core.telemetry import telemetry
from .core.telegram.client import TelethonClientWrapper
from .i18n import _, set_lang, get_lang
from .infrastructure.storage.sqlite import SQLiteStorage
from .services.alias_manager import AliasManager
from .services.cleaner import CleanerService
from .services.db_exporter import DBExportService
from .services.exporter import ExportService
from .services.private_archive import PrivateArchiveService
from .services.scheduler import setup_scheduler
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
            # Use TCSANOW for immediate restoration
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
            if char == "\x1b":  # ESC
                sys.stdout.write("\n")
                return None
            if char == "\r" or char == "\n":  # Enter
                sys.stdout.write("\n")
                return input_str
            if char == "\x7f" or char == "\x08":  # Backspace
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if char.isprintable():  # Regular printable chars
                input_str += char
                sys.stdout.write(char)
                sys.stdout.flush()


logger = logging.getLogger(__name__)


def _archive_media_summary(stats: dict) -> str:
    return f"P:{stats['Photo']} V:{stats['Video']} S:{stats['Voice']} D:{stats['Document']}"


def _archive_progress_summary(archive_stats: dict) -> str:
    return f"{_('label_downloaded')}={archive_stats['downloaded']} {_('label_skipped')}={archive_stats['skipped']}"


def _render_service_event(event: ServiceEvent) -> None:
    payload = event.payload

    if event.name == "export.sync_chat_started":
        if UI.is_tty():
            colored_title = UI.paint(payload["chat_title"], UI.CLR_CHAT, bold=True)
            mode_badge = UI.paint(payload["mode_str"], UI.CLR_STATS, bold=True)
            status_badge = (
                UI.muted(payload["status_str"]) if payload["status_str"] else ""
            )
            header = f"{UI.section(_('section_sync'), icon='◆')}  {colored_title}"
            if payload["user_label"]:
                header = f"{header}  {UI.muted(_('label_user'))} {UI.paint(payload['user_label'], UI.CLR_USER, bold=True)}"
            header = f"{header}  {UI.muted(_('label_mode'))} {mode_badge}"
            if status_badge:
                header = f"{header}  {status_badge}"
            print(f"\n{header}")
        return

    if event.name == "export.sync_progress":
        suffix = f"💬 {payload['db_total']}"
        if payload["extra"]:
            suffix = f"{suffix} {payload['extra']}"
        UI.print_status("Syncing", "", extra=suffix)
        return

    if event.name == "export.sync_finished":
        if UI.is_tty():
            UI.print_status("Finished", "", extra=f"💬 {payload['db_count']}")
            sys.stdout.write("\n")
            sys.stdout.flush()
        return

    if event.name == "export.sync_summary":
        if UI.is_tty():
            UI.print_final_summary(
                "sync_summary_title",
                [
                    {
                        "title": payload["title"],
                        "lines": [
                            ("user_messages", payload["own_messages"]),
                            ("with_context", payload["with_context"]),
                        ],
                    }
                ],
            )
        return

    if event.name == "export.history_fully_synced":
        if sys.stdout.isatty():
            print(
                f"\n{UI.paint('✓', UI.CLR_SUCCESS, bold=True)} {UI.paint(_('text_history_fully_synced'), UI.CLR_SUCCESS)}"
            )
        return

    if event.name == "export.targeted_dialog_search_started":
        if sys.stdout.isatty():
            print(
                f"\n{UI.section(_('section_targeted_search'), icon='◆')}  {UI.key_value(_('label_user'), payload['from_user_id'], icon='◌')}  {UI.key_value(_('label_dialogs'), payload['dialog_count'], icon='◌')}"
            )
        return

    if event.name == "export.dialog_search_started":
        if sys.stdout.isatty():
            print(
                f"\n{UI.section(_('section_dialog_search'), icon='◆')}  {UI.key_value(_('label_user'), payload['from_user_id'], icon='◌')}"
            )
        return

    if event.name == "export.dialog_search_scanning":
        if sys.stdout.isatty():
            print(
                f"   {UI.muted(_('label_scanning'))} {UI.paint(payload['dialog_count'], UI.CLR_STATS, bold=True)} {UI.muted(_('label_dialogs'))}"
            )
        return

    if event.name == "export.dialog_scan_started":
        if UI.is_tty():
            progress_label = f"{payload['index']}/{payload['total']}"
            print(
                f"\n   {UI.paint(progress_label, UI.CLR_MUTED)}  {UI.paint(payload['dialog_title'], UI.CLR_CHAT, bold=True)}"
            )
        return

    if event.name == "export.global_export_finished":
        if UI.is_tty():
            print(
                f"\n{UI.paint('✓', UI.CLR_SUCCESS, bold=True)} {UI.paint(_('text_global_export_finished'), UI.CLR_SUCCESS)}  {UI.key_value(_('label_processed'), payload['total_processed'], icon='✉')}"
            )
        return

    if event.name == "export.tracked_update_started":
        if UI.is_tty():
            print(
                f"\n{UI.section(_('section_update'), icon='◆')}  {UI.key_value(_('label_targets'), payload['target_count'], icon='◌')}"
            )
        return

    if event.name == "cleaner.dialog_scan_started":
        UI.print_status(
            "Cleaning", f"[{payload['index']}/{payload['total']}] {payload['name']}"
        )
        return

    if event.name == "cleaner.dialog_messages_found":
        UI.print_status(
            "Found", payload["count"], extra=f"messages in {payload['name']}"
        )
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    if event.name == "private_archive.started":
        if UI.is_tty():
            print(
                f"\n{UI.section(_('section_pm_archive'), icon='◆')}  {UI.paint(payload['target_name'], UI.CLR_USER, bold=True)}  {UI.muted(_('label_id'))} {UI.paint(payload['user_id'], UI.CLR_ID)}"
            )
            print(
                f"   {UI.muted(_('label_path'))} {UI.paint(payload['user_dir'], UI.CLR_CHAT)}"
            )
        return

    if event.name == "private_archive.progress":
        UI.print_status(
            "Archiving",
            payload["count"],
            extra=f"{_('label_messages')} | {_archive_progress_summary(payload['archive_stats'])} | {_('label_media')}: {_archive_media_summary(payload['stats'])}",
        )
        return

    if event.name == "private_archive.media_saved":
        if UI.is_tty():
            print(
                f"   {UI.paint('↳', UI.CLR_MUTED)} {UI.muted(_('label_saved_media'))} {UI.paint(payload['filename'], UI.CLR_STATS)}"
            )
        return

    if event.name == "private_archive.completed":
        if not UI.is_tty():
            return
        UI.print_status(
            "Complete",
            payload["count"],
            extra=f"{_('label_messages')} | {_archive_progress_summary(payload['archive_stats'])} | {_('label_media')}: {_archive_media_summary(payload['stats'])}",
        )
        UI.print_final_summary(
            "sync_summary_title",
            [
                {
                    "title": payload["target_name"],
                    "lines": [
                        ("messages", payload["count"]),
                        ("downloaded", payload["archive_stats"]["downloaded"]),
                        ("skipped", payload["archive_stats"]["skipped"]),
                        ("media", sum(payload["stats"].values())),
                    ],
                }
            ],
        )
        sys.stdout.write("\n")
        sys.stdout.flush()
        return


def resolve_id(id_str: str) -> Any:
    """Helper to convert string IDs to int if they look like numbers."""
    try:
        return int(id_str)
    except (ValueError, TypeError):
        return id_str


async def get_safe_user_and_chat(
    client: TelethonClientWrapper,
    user_id_str: str,
    chat_id_str: Optional[str] = None,
):
    """Safely resolves user and chat entities."""
    user_id = resolve_id(user_id_str)
    chat_id = resolve_id(chat_id_str) if chat_id_str else None

    chat_entity = None
    if chat_id:
        try:
            chat_entity = await client.get_entity(chat_id)
        except Exception as e:
            logger.warning(f"Could not resolve chat {chat_id}: {e}")

    user_entity = None
    try:
        user_entity = await client.get_entity(user_id)
    except Exception as e:
        logger.warning(f"Could not resolve user {user_id} directly: {e}")

    return user_entity, chat_entity


class CLIContext:
    """
    Centralized context for CLI resource management.
    Ensures single initialization of services and graceful shutdown.
    """

    def __init__(self, needs_client: bool = True):
        self.pm = ProcessManager()
        self.storage: Optional[SQLiteStorage] = None
        self.client: Optional[TelethonClientWrapper] = None
        self.needs_client = needs_client

        # Services
        self.exporter: Optional[ExportService] = None
        self.cleaner: Optional[CleanerService] = None
        self.db_exporter: Optional[DBExportService] = None
        self.private_archive: Optional[PrivateArchiveService] = None
        self.alias_manager = AliasManager()

        self.active_uid = None

    async def initialize(self):
        setup_logging()
        telemetry.reset()
        if not self.pm.acquire_lock():
            print(_("error_locked"))
            sys.exit(1)

        # Setup async signals early
        self.pm.setup_async_signals(asyncio.get_running_loop(), self.emergency_callback)

        self.storage = SQLiteStorage(settings.db_path, process_manager=self.pm)
        await self.storage.start()

        self.db_exporter = DBExportService(self.storage)

        if self.needs_client:
            self.client = TelethonClientWrapper(
                settings.session_name, settings.api_id, settings.api_hash
            )
            await self.client.connect()
            self.exporter = ExportService(
                self.client, self.storage, event_sink=_render_service_event
            )
            self.private_archive = PrivateArchiveService(
                self.client, self.storage, event_sink=_render_service_event
            )

        self.cleaner = CleanerService(
            self.client,
            self.storage,
            whitelist=settings.whitelist_chats,
            include_list=settings.include_chats,
            event_sink=_render_service_event,
        )

    async def shutdown(self):
        if self.client:
            await self.client.disconnect()
        if self.storage:
            await self.storage.close()
        if self.pm:
            self.pm.release_lock()

    async def emergency_callback(self):
        """Async callback for signal handling."""
        if self.active_uid and self.db_exporter:
            sys.stdout.write(
                f"\n⚠️ Performing emergency JSON export for User ID: {self.active_uid}...\n"
            )
            path = await self.db_exporter.export_user_messages(
                self.active_uid,
                as_json=True,
                include_date=False,
            )
            if path:
                sys.stdout.write(f"✅ Emergency dump saved to: {path}\n")
            sys.stdout.flush()


def print_target_list(targets: list):
    """Prints a formatted, color-coded list of primary targets."""
    for i, u in enumerate(targets):
        display_name = UI.paint(u["author_name"], UI.CLR_USER, bold=True)
        user_id_str = UI.paint(u["user_id"], UI.CLR_ID)
        chat_info = (
            f"  {UI.paint('•', UI.CLR_BORDER)}  {UI.paint(u['chat_title'], UI.CLR_CHAT)}"
            if u.get("chat_title")
            else ""
        )
        own_count = UI.key_value(_("label_msg_short"), u["user_msg_count"], icon="✉")
        context_count = UI.key_value(
            _("label_ctx_short"), u["context_msg_count"], icon="◌"
        )
        is_complete = bool(u.get("is_complete", 0))
        status_color = UI.CLR_SUCCESS if is_complete else UI.CLR_WARN
        status_label = _("status_complete") if is_complete else _("status_incomplete")
        status = UI.paint(status_label, status_color, bold=True)
        idx_str = UI.paint(f"{i + 1:02}.", UI.CLR_MUTED)
        print(
            f" {idx_str}  {display_name}  {UI.muted(_('label_id'))} {user_id_str}  {own_count}  {context_count}  {status}{chat_info}"
        )


def get_dirty_target_ids(stats: dict) -> list:
    """Returns only targets that actually received new messages during update."""
    dirty_ids = []
    for uid, item in stats.items():
        if not isinstance(item, dict):
            continue
        if item.get("dirty") or item.get("count", 0) > 0:
            dirty_ids.append(uid)
    return dirty_ids


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TG_MSG_MNGR CLI")
    subparsers = parser.add_subparsers(dest="command")

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--user-id", required=True)
    export_parser.add_argument("--chat-id", default=None)
    export_parser.add_argument("--deep", action="store_true", default=True)
    export_parser.add_argument("--flat", action="store_false", dest="deep")
    export_parser.add_argument("--force-resync", action="store_true")
    export_parser.add_argument("--context-window", type=int, default=3)
    export_parser.add_argument("--max-cluster", type=int, default=10)
    export_parser.add_argument("--depth", type=int, default=2)
    export_parser.add_argument("--limit", type=int, default=None)
    export_parser.add_argument("--json", action="store_true")

    subparsers.add_parser("update")

    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("--dry-run", action="store_true", default=None)
    clean_parser.add_argument("--apply", action="store_true")
    clean_parser.add_argument("--yes", "-y", action="store_true")

    subparsers.add_parser("export-pm").add_argument("--user-id", required=True)
    subparsers.add_parser("delete").add_argument("--user-id", required=True)
    subparsers.add_parser("schedule")
    subparsers.add_parser("setup")

    db_parser = subparsers.add_parser("db-export")
    db_parser.add_argument("--user-id", required=True)
    db_parser.add_argument("--json", action="store_true", default=False)
    return parser


def _command_needs_client(command: str) -> bool:
    return command not in ("setup", "schedule", "db-export")


def _store_resolved_user(ctx: CLIContext, user_ent: Any) -> None:
    if not user_ent:
        return
    ctx.active_uid = user_ent.id
    ctx.storage.upsert_user(
        user_id=user_ent.id,
        first_name=getattr(user_ent, "first_name", None),
        last_name=getattr(user_ent, "last_name", None),
        username=getattr(user_ent, "username", None),
    )


async def _run_export_sync(
    ctx: CLIContext,
    *,
    final_uid: Any,
    user_ent: Any,
    chat_ent: Any,
    deep_mode: bool,
    recursive_depth: int,
    force_resync: bool = False,
    context_window: int = 3,
    max_cluster: int = 10,
    limit: Optional[int] = None,
) -> int:
    if chat_ent:
        return await ctx.exporter.sync_chat(
            chat_ent,
            from_user_id=final_uid,
            deep_mode=deep_mode,
            force_resync=force_resync,
            context_window=context_window,
            max_cluster=max_cluster,
            recursive_depth=recursive_depth,
            limit=limit,
        )
    if user_ent or isinstance(final_uid, int):
        return await ctx.exporter.sync_all_dialogs_for_user(
            final_uid,
            target_chat_ids=settings.chats_to_search_user_msgs,
            deep_mode=deep_mode,
            force_resync=force_resync,
            context_window=context_window,
            max_cluster=max_cluster,
            recursive_depth=recursive_depth,
            limit=limit,
        )
    print(
        f"{UI.paint('✖', UI.CLR_ERROR, bold=True)} {UI.paint(_('text_could_not_resolve_target', target=final_uid), UI.CLR_ERROR)}"
    )
    return 0


async def _emit_export_summary(
    ctx: CLIContext,
    *,
    final_uid: Any,
    processed: int,
    as_json: bool,
    show_finalize_section: bool,
    show_saved_path: bool,
) -> None:
    if show_finalize_section:
        print(f"\n{UI.section(_('section_finalizing_export'), icon='⬢')}")

    path = await ctx.db_exporter.export_user_messages(
        final_uid, as_json=as_json, include_date=False
    )
    if show_saved_path and path:
        print(
            f"{UI.paint('✓', UI.CLR_SUCCESS, bold=True)} {UI.paint(_('text_export_saved'), UI.CLR_SUCCESS)}  {UI.muted(path)}"
        )

    telemetry.log_summary("Export telemetry summary")
    user_info = ctx.storage.get_user(final_uid)
    target_name = UI.format_name(user_info) if user_info else f"ID:{final_uid}"
    UI.print_final_summary(
        "sync_summary_title",
        [
            {
                "title": f"{_('label_export')}: {target_name}",
                "lines": [("processed", processed)],
            }
        ],
    )


async def _sync_and_export_dirty_targets(
    ctx: CLIContext, *, emit_telemetry_summary: bool
) -> dict:
    stats = await ctx.exporter.sync_all_tracked()
    for uid in get_dirty_target_ids(stats):
        await ctx.db_exporter.export_user_messages(
            uid, as_json=True, include_date=False
        )
    if emit_telemetry_summary:
        telemetry.log_summary("Update telemetry summary")
    return stats


def _print_update_summary(stats: dict, *, title: str) -> None:
    total_processed = sum(
        item["count"] for item in stats.values() if isinstance(item, dict)
    )
    UI.print_final_summary(
        "sync_summary_title",
        [
            {
                "title": title,
                "lines": [
                    ("processed", total_processed),
                    ("targets", len(stats)),
                ],
            }
        ],
    )


def _print_alias_install_result(ctx: CLIContext, *, paint_errors: bool) -> None:
    res = ctx.alias_manager.install()
    if "success" in res:
        print(res["message"])
        if "activate_cmd" in res:
            print(res["activate_cmd"])
        print("\n" + _("alias_header"))
        for line in ctx.alias_manager.get_alias_help()[1:]:
            print(line)
        return

    error_message = res.get(
        "error", "Error during setup." if paint_errors else "Error during setup"
    )
    if paint_errors:
        print(UI.paint(error_message, UI.CLR_ERROR))
    else:
        print(error_message)


def _pause_for_enter() -> None:
    sys.stdout.write("\n" + _("press_enter"))
    sys.stdout.flush()
    TerminalInput.get_char()


def _render_main_menu(me_id: Any) -> None:
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


async def _handle_setup_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    _print_alias_install_result(ctx, paint_errors=False)


async def _handle_schedule_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    await setup_scheduler()


async def _handle_delete_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    uid = resolve_id(args.user_id)
    await ctx.cleaner.purge_user_data(uid)


async def _handle_db_export_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    uid = resolve_id(args.user_id)
    await ctx.db_exporter.export_user_messages(uid, as_json=args.json)


async def _handle_export_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    ctx.active_uid = resolve_id(args.user_id)
    user_ent, chat_ent = await get_safe_user_and_chat(
        ctx.client, args.user_id, args.chat_id
    )
    _store_resolved_user(ctx, user_ent)

    processed = 0
    try:
        processed = await _run_export_sync(
            ctx,
            final_uid=ctx.active_uid,
            user_ent=user_ent,
            chat_ent=chat_ent,
            deep_mode=args.deep,
            recursive_depth=args.depth,
            force_resync=args.force_resync,
            context_window=args.context_window,
            max_cluster=args.max_cluster,
            limit=args.limit,
        )
        await _emit_export_summary(
            ctx,
            final_uid=ctx.active_uid,
            processed=processed,
            as_json=args.json,
            show_finalize_section=True,
            show_saved_path=True,
        )
    except Exception as e:
        if not ctx.pm.should_stop():
            logger.error(f"Error during export: {e}")


async def _handle_update_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    stats = await _sync_and_export_dirty_targets(ctx, emit_telemetry_summary=True)
    _print_update_summary(stats, title=_("label_update"))


async def _handle_clean_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    is_dry = True
    if args.apply or args.yes:
        is_dry = False
    if args.dry_run is True:
        is_dry = True
    deleted = await ctx.cleaner.global_self_cleanup(dry_run=is_dry)
    print(
        f"\n{UI.section(_('summary_header'), icon='◆')}\n{_('total_deleted_msgs', count=deleted)}"
    )
    if is_dry:
        print(UI.paint(_("dry_run_info"), UI.CLR_WARN))


async def _handle_export_pm_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    user_ent, unused = await get_safe_user_and_chat(ctx.client, args.user_id)
    if user_ent:
        await ctx.private_archive.archive_pm(user_ent)


async def _handle_menu_export(ctx: CLIContext) -> None:
    UI.print_header(_("menu_1"), _("menu_1_desc"))
    target_str = TerminalInput.prompt_with_esc(_("prompt_target") + ": ")
    if target_str is None or target_str.strip() == "0":
        return

    chat_str = TerminalInput.prompt_with_esc(_("prompt_chat") + ": ")
    if chat_str is None:
        return

    deep_choice = TerminalInput.prompt_with_esc(
        _("prompt_deep").replace("[y/N]", "[y]").replace("[Y/n]", "[y]") + ": "
    )
    if deep_choice is None:
        return
    active_deep = deep_choice.lower() != "n"

    active_depth = 2
    if active_deep:
        depth_str = TerminalInput.prompt_with_esc(f"{_('depth_label')} (1-5) [2]: ")
        if depth_str and depth_str.isdigit():
            active_depth = int(depth_str)

    user_ent, chat_ent = await get_safe_user_and_chat(
        ctx.client,
        target_str.strip(),
        chat_str.strip() if chat_str else None,
    )
    _store_resolved_user(ctx, user_ent)

    final_uid = user_ent.id if user_ent else resolve_id(target_str)
    ctx.active_uid = final_uid
    processed = 0
    try:
        processed = await _run_export_sync(
            ctx,
            final_uid=final_uid,
            user_ent=user_ent,
            chat_ent=chat_ent,
            deep_mode=active_deep,
            recursive_depth=active_depth,
        )
    finally:
        if ctx.pm.should_stop():
            print(
                f"\n{UI.paint('▲', UI.CLR_WARN, bold=True)} {UI.paint(_('text_interrupted_exporting_partial'), UI.CLR_WARN)}"
            )
        if final_uid:
            await _emit_export_summary(
                ctx,
                final_uid=final_uid,
                processed=processed,
                as_json=True,
                show_finalize_section=False,
                show_saved_path=False,
            )
    _pause_for_enter()


async def _handle_menu_update(ctx: CLIContext) -> None:
    UI.print_header(_("menu_2"), _("menu_2_desc"))
    updated_stats = await _sync_and_export_dirty_targets(
        ctx, emit_telemetry_summary=False
    )
    if updated_stats:
        _print_update_summary(updated_stats, title="Update")
    _pause_for_enter()


async def _handle_menu_clean(ctx: CLIContext) -> None:
    UI.print_header(_("menu_3"), _("sub_clean_info"))
    pm_choice = TerminalInput.prompt_with_esc(_("prompt_clean_pms") + ": ")
    if pm_choice is None:
        return
    confirm = TerminalInput.prompt_with_esc(_("clean_confirm") + " (y/n): ")
    if confirm and confirm.lower() == "y":
        deleted = await ctx.cleaner.global_self_cleanup(
            dry_run=False, include_pms=(pm_choice.lower() == "y")
        )
        print(
            f"\n{UI.section(_('summary_header'), icon='◆')}\n{_('total_deleted_msgs', count=deleted)}"
        )
    _pause_for_enter()


async def _handle_menu_export_pm(ctx: CLIContext) -> None:
    UI.print_header(_("menu_4"), _("menu_4_desc"))
    target_str = TerminalInput.prompt_with_esc(_("prompt_pm_target") + ": ")
    if target_str:
        user_ent, unused = await get_safe_user_and_chat(ctx.client, target_str.strip())
        if user_ent:
            await ctx.private_archive.archive_pm(user_ent)
    _pause_for_enter()


async def _handle_menu_delete_data(ctx: CLIContext) -> None:
    UI.print_header(_("menu_5"), _("menu_5_desc"))
    users = ctx.storage.get_primary_targets()
    if users:
        print_target_list(users)
        idx = TerminalInput.prompt_with_esc("\nChoice: ")
        if idx and idx.isdigit() and 1 <= int(idx) <= len(users):
            await ctx.cleaner.purge_user_data(users[int(idx) - 1]["user_id"])
        else:
            print(UI.paint(_("text_invalid_selection"), UI.CLR_WARN))
    else:
        print(UI.paint(_("no_targets"), UI.CLR_WARN))
    _pause_for_enter()


async def _handle_menu_schedule(ctx: CLIContext) -> None:
    UI.print_header(_("menu_6"), _("help_desc_6"))
    await setup_scheduler()
    _pause_for_enter()


async def _handle_menu_setup(ctx: CLIContext) -> None:
    UI.print_header(_("menu_7"), _("sub_setup_info"))
    _print_alias_install_result(ctx, paint_errors=True)
    _pause_for_enter()


async def _handle_menu_about(ctx: CLIContext) -> None:
    UI.print_header(_("menu_8"), _("about_text"))
    _pause_for_enter()


async def _handle_menu_db_export(ctx: CLIContext) -> None:
    UI.print_header(_("menu_9"), _("sub_db_export_info"))
    users = ctx.storage.get_primary_targets()
    if users:
        print_target_list(users)
        idx_str = TerminalInput.prompt_with_esc("\n" + _("choice_prompt") + ": ")
        if idx_str and idx_str.isdigit() and 1 <= int(idx_str) <= len(users):
            target = users[int(idx_str) - 1]
            fmt = TerminalInput.prompt_with_esc(_("label_format_prompt"))
            if fmt == "1":
                await ctx.db_exporter.export_user_messages(
                    target["user_id"], as_json=True
                )
            elif fmt == "2":
                await ctx.db_exporter.export_user_messages(
                    target["user_id"], as_json=False
                )
    else:
        print(UI.paint(_("no_targets"), UI.CLR_WARN))
    _pause_for_enter()


async def _dispatch_main_menu_choice(ctx: CLIContext, choice: str) -> bool:
    if choice == "L":
        set_lang("en" if get_lang() == "ru" else "ru")
        return True
    if choice == "0":
        return False

    handlers = {
        "1": _handle_menu_export,
        "2": _handle_menu_update,
        "3": _handle_menu_clean,
        "4": _handle_menu_export_pm,
        "5": _handle_menu_delete_data,
        "6": _handle_menu_schedule,
        "7": _handle_menu_setup,
        "8": _handle_menu_about,
        "9": _handle_menu_db_export,
    }
    handler = handlers.get(choice)
    if handler is not None:
        await handler(ctx)
    return True


async def run_cli():
    """Main CLI entry point with subcommand support."""
    parser = build_cli_parser()
    args = parser.parse_args()

    if not args.command:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            parser.print_help()
            return
        await main_menu()
        return

    ctx = CLIContext(needs_client=_command_needs_client(args.command))

    try:
        await ctx.initialize()
        handlers = {
            "setup": _handle_setup_command,
            "schedule": _handle_schedule_command,
            "delete": _handle_delete_command,
            "db-export": _handle_db_export_command,
            "export": _handle_export_command,
            "update": _handle_update_command,
            "clean": _handle_clean_command,
            "export-pm": _handle_export_pm_command,
        }
        handler = handlers.get(args.command)
        if handler is not None:
            await handler(ctx, args)

    finally:
        await ctx.shutdown()


async def main_menu():
    """Main interactive menu logic."""
    ctx = CLIContext(needs_client=True)
    try:
        await ctx.initialize()
        me = await ctx.client.get_me()
        me_id = me.id if me else "Unknown"

        while True:
            _render_main_menu(me_id)
            sys.stdout.write(_("choice_prompt") + ": ")
            sys.stdout.flush()
            char = TerminalInput.get_char()
            if char == "\x1b":
                continue
            choice = char.upper()
            print(choice)
            if not await _dispatch_main_menu_choice(ctx, choice):
                break
    finally:
        await ctx.shutdown()


def main():
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
