import asyncio
import logging
import sys
import argparse
from typing import Optional, Any

from .core.logging import setup_logging
from .core.process import ProcessManager
from .core.runtime import AppRuntime, build_app_runtime
from .core.telemetry import telemetry
from .core.telegram.client import TelethonClientWrapper
from .core.models.sync_report import TrackedSyncRunReport
from .core.models.setup import SchedulerSetupRequest, SchedulerSetupResult
from .cli_io import (
    TerminalInput,
    pause_for_enter,
    print_target_list,
    print_update_summary,
    render_main_menu,
    render_service_event,
)
from .i18n import _, set_lang, get_lang, use_lang
from .infrastructure.storage.records import PrimaryTarget
from .infrastructure.storage.sqlite import SQLiteStorage
from .services.alias_manager import AliasManager
from .services.cleaner import CleanerService
from .services.db_exporter import DBExportService
from .services.exporter import ExportService
from .services.private_archive import PrivateArchiveService
from .services.scheduler import setup_scheduler
from .utils.ui import UI


logger = logging.getLogger(__name__)


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

    def __init__(self, runtime: AppRuntime, needs_client: bool = True):
        self.runtime = runtime
        self.settings = runtime.settings
        self.paths = runtime.paths
        self.pm = ProcessManager(lock_path=self.paths.lock_path)
        self.storage: Optional[SQLiteStorage] = None
        self.client: Optional[TelethonClientWrapper] = None
        self.needs_client = needs_client

        # Services
        self.exporter: Optional[ExportService] = None
        self.cleaner: Optional[CleanerService] = None
        self.db_exporter: Optional[DBExportService] = None
        self.private_archive: Optional[PrivateArchiveService] = None
        self.alias_manager = AliasManager(
            project_root=self.paths.project_root,
            python_executable=self.runtime.python_executable,
        )

        self.active_uid = None

    async def initialize(self):
        setup_logging()
        telemetry.reset()
        if not self.pm.acquire_lock():
            print(_("error_locked"))
            sys.exit(1)

        # Setup async signals early
        self.pm.setup_async_signals(asyncio.get_running_loop(), self.emergency_callback)

        self.storage = SQLiteStorage(self.paths.db_path, process_manager=self.pm)
        await self.storage.start()

        self.db_exporter = DBExportService(
            self.storage,
            default_output_dir=self.paths.db_exports_dir,
        )

        if self.needs_client:
            self.client = TelethonClientWrapper(
                self.settings.session_name,
                self.settings.api_id,
                self.settings.api_hash,
                max_rps=self.settings.max_rps,
            )
            await self.client.connect()
            self.exporter = ExportService(
                self.client, self.storage, event_sink=render_service_event
            )
            self.private_archive = PrivateArchiveService(
                self.client,
                self.storage,
                base_dir=self.paths.private_dialogs_dir,
                event_sink=render_service_event,
            )

        self.cleaner = CleanerService(
            self.client,
            self.storage,
            whitelist=self.settings.whitelist_chats,
            include_list=self.settings.include_chats,
            artifact_roots=self.paths.artifact_roots(),
            event_sink=render_service_event,
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


def get_dirty_target_ids(stats: Any) -> list:
    """Returns only targets that actually received new messages during update."""
    try:
        report = TrackedSyncRunReport.coerce(stats)
    except TypeError:
        return []
    return report.dirty_user_ids()


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
            target_chat_ids=ctx.settings.chats_to_search_user_msgs,
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
) -> TrackedSyncRunReport:
    stats = await ctx.exporter.sync_all_tracked()
    for uid in get_dirty_target_ids(stats):
        await ctx.db_exporter.export_user_messages(
            uid, as_json=True, include_date=False
        )
    if emit_telemetry_summary:
        telemetry.log_summary("Update telemetry summary")
    return stats


def _print_alias_install_result(ctx: CLIContext, *, paint_errors: bool) -> None:
    res = ctx.alias_manager.install()
    if res.success:
        if res.rc_path:
            print(_("setup_success_unix", path=res.rc_path))
            print(_("setup_activate", path=res.rc_path))
        elif res.bin_dir:
            print(_("setup_success_win", dir=res.bin_dir))
        print("\n" + _("alias_header"))
        for spec in ctx.alias_manager.get_alias_specs():
            print(f"  {spec.alias:<4} -> {_(spec.label_key)}")
        return

    if res.error_kind == "unsupported_platform":
        error_message = _("setup_platform_error", plt=res.platform)
    else:
        error_message = res.error_detail or (
            "Error during setup." if paint_errors else "Error during setup"
        )
    if paint_errors:
        print(UI.paint(error_message, UI.CLR_ERROR))
    else:
        print(error_message)


def _prompt_scheduler_setup_request() -> SchedulerSetupRequest:
    default_request = SchedulerSetupRequest()
    try:
        time_input = input(_("sched_time_prompt")).strip()
    except EOFError:
        return default_request

    if not time_input:
        return default_request

    try:
        hour_str, minute_str = time_input.split(":", 1)
        return SchedulerSetupRequest(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, TypeError):
        print(UI.paint(_("sched_invalid_time"), UI.CLR_WARN))
        return default_request


def _print_scheduler_setup_result(
    result: SchedulerSetupResult, *, paint_errors: bool
) -> None:
    if result.success:
        mode = _("sched_daily_at", time=f"{result.hour:02d}:{result.minute:02d}")
        print(_("sched_success_macos", mode=mode))
        print(_("sched_logs_path", path=result.logs_dir))
        print(_("sched_complete"))
        return

    if result.error_kind == "launchctl_load_failed":
        error_message = _("sched_register_error", error=result.error_detail or "")
    else:
        error_message = _("sched_unexpected_error", error=result.error_detail or "")

    if paint_errors:
        print(UI.paint(error_message, UI.CLR_ERROR))
    else:
        print(error_message)


async def _handle_setup_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    _print_alias_install_result(ctx, paint_errors=False)


async def _handle_schedule_command(ctx: CLIContext, args: argparse.Namespace) -> None:
    request = _prompt_scheduler_setup_request()
    result = await setup_scheduler(
        request,
        project_root=ctx.paths.project_root,
        python_path=ctx.runtime.python_executable,
    )
    _print_scheduler_setup_result(result, paint_errors=False)


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
    print_update_summary(stats, title=_("label_update"))


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
    pause_for_enter()


async def _handle_menu_update(ctx: CLIContext) -> None:
    UI.print_header(_("menu_2"), _("menu_2_desc"))
    updated_stats = await _sync_and_export_dirty_targets(
        ctx, emit_telemetry_summary=False
    )
    if updated_stats:
        print_update_summary(updated_stats, title="Update")
    pause_for_enter()


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
    pause_for_enter()


async def _handle_menu_export_pm(ctx: CLIContext) -> None:
    UI.print_header(_("menu_4"), _("menu_4_desc"))
    target_str = TerminalInput.prompt_with_esc(_("prompt_pm_target") + ": ")
    if target_str:
        user_ent, unused = await get_safe_user_and_chat(ctx.client, target_str.strip())
        if user_ent:
            await ctx.private_archive.archive_pm(user_ent)
    pause_for_enter()


async def _handle_menu_delete_data(ctx: CLIContext) -> None:
    UI.print_header(_("menu_5"), _("menu_5_desc"))
    users = ctx.storage.get_primary_targets()
    if users:
        print_target_list(users)
        idx = TerminalInput.prompt_with_esc("\nChoice: ")
        if idx and idx.isdigit() and 1 <= int(idx) <= len(users):
            target = PrimaryTarget.coerce(users[int(idx) - 1])
            await ctx.cleaner.purge_user_data(target.user_id)
        else:
            print(UI.paint(_("text_invalid_selection"), UI.CLR_WARN))
    else:
        print(UI.paint(_("no_targets"), UI.CLR_WARN))
    pause_for_enter()


async def _handle_menu_schedule(ctx: CLIContext) -> None:
    UI.print_header(_("menu_6"), _("help_desc_6"))
    request = _prompt_scheduler_setup_request()
    result = await setup_scheduler(
        request,
        project_root=ctx.paths.project_root,
        python_path=ctx.runtime.python_executable,
    )
    _print_scheduler_setup_result(result, paint_errors=True)
    pause_for_enter()


async def _handle_menu_setup(ctx: CLIContext) -> None:
    UI.print_header(_("menu_7"), _("sub_setup_info"))
    _print_alias_install_result(ctx, paint_errors=True)
    pause_for_enter()


async def _handle_menu_about(ctx: CLIContext) -> None:
    UI.print_header(_("menu_8"), _("about_text"))
    pause_for_enter()


async def _handle_menu_db_export(ctx: CLIContext) -> None:
    UI.print_header(_("menu_9"), _("sub_db_export_info"))
    users = ctx.storage.get_primary_targets()
    if users:
        print_target_list(users)
        idx_str = TerminalInput.prompt_with_esc("\n" + _("choice_prompt") + ": ")
        if idx_str and idx_str.isdigit() and 1 <= int(idx_str) <= len(users):
            target = PrimaryTarget.coerce(users[int(idx_str) - 1])
            fmt = TerminalInput.prompt_with_esc(_("label_format_prompt"))
            if fmt == "1":
                await ctx.db_exporter.export_user_messages(target.user_id, as_json=True)
            elif fmt == "2":
                await ctx.db_exporter.export_user_messages(
                    target.user_id, as_json=False
                )
    else:
        print(UI.paint(_("no_targets"), UI.CLR_WARN))
    pause_for_enter()


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


async def run_cli(runtime: Optional[AppRuntime] = None):
    """Main CLI entry point with subcommand support."""
    active_runtime = runtime or build_app_runtime()
    with use_lang(active_runtime.settings.lang):
        parser = build_cli_parser()
        args = parser.parse_args()

        if not args.command:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                parser.print_help()
                return
            await main_menu(runtime=active_runtime)
            return

        ctx = CLIContext(
            active_runtime, needs_client=_command_needs_client(args.command)
        )

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


async def main_menu(runtime: Optional[AppRuntime] = None):
    """Main interactive menu logic."""
    active_runtime = runtime or build_app_runtime()
    with use_lang(active_runtime.settings.lang):
        ctx = CLIContext(active_runtime, needs_client=True)
        try:
            await ctx.initialize()
            me = await ctx.client.get_me()
            me_id = me.id if me else "Unknown"

            while True:
                render_main_menu(me_id)
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
        asyncio.run(run_cli(runtime=build_app_runtime()))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
