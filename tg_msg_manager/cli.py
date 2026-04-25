import os
import asyncio
import logging
import sys
import argparse
import platform
from datetime import datetime
from typing import Optional, Any

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
            if char == '\x1b': # ESC
                sys.stdout.write("\n")
                return None
            if char == '\r' or char == '\n': # Enter
                sys.stdout.write("\n")
                return input_str
            if char == '\x7f' or char == '\x08': # Backspace
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                continue
            if char.isprintable(): # Regular printable chars
                input_str += char
                sys.stdout.write(char)
                sys.stdout.flush()

from .core.config import settings
from .core.logging import setup_logging
from .core.process import ProcessManager
from .core.telegram.client import TelethonClientWrapper
from .infrastructure.storage.sqlite import SQLiteStorage
from .services.exporter import ExportService
from .services.cleaner import CleanerService
from .services.db_exporter import DBExportService
from .services.private_archive import PrivateArchiveService
from .services.alias_manager import AliasManager
from .services.scheduler import setup_scheduler, remove_scheduler
from .i18n import _, set_lang, get_lang
from .utils.ui import UI

logger = logging.getLogger(__name__)

def resolve_id(id_str: str) -> Any:
    """Helper to convert string IDs to int if they look like numbers."""
    try: return int(id_str)
    except (ValueError, TypeError): return id_str

async def get_safe_user_and_chat(client: TelethonClientWrapper, user_id_str: str, chat_id_str: Optional[str] = None):
    """Safely resolves user and chat entities."""
    user_id = resolve_id(user_id_str)
    chat_id = resolve_id(chat_id_str) if chat_id_str else None
    
    chat_entity = None
    if chat_id:
        try: chat_entity = await client.get_entity(chat_id)
        except Exception as e: logger.warning(f"Could not resolve chat {chat_id}: {e}")
    
    user_entity = None
    try: user_entity = await client.get_entity(user_id)
    except Exception as e: logger.warning(f"Could not resolve user {user_id} directly: {e}")
    
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
        if not self.pm.acquire_lock():
            print(_("error_locked"))
            sys.exit(1)
        
        # Setup async signals early
        self.pm.setup_async_signals(asyncio.get_running_loop(), self.emergency_callback)
        
        self.storage = SQLiteStorage(settings.db_path, process_manager=self.pm)
        await self.storage.start()
        
        self.db_exporter = DBExportService(self.storage)
        
        if self.needs_client:
            self.client = TelethonClientWrapper(settings.session_name, settings.api_id, settings.api_hash)
            await self.client.connect()
            self.exporter = ExportService(self.client, self.storage)
            self.private_archive = PrivateArchiveService(self.client, self.storage)

        self.cleaner = CleanerService(self.client, self.storage, whitelist=settings.whitelist_chats, include_list=settings.include_chats)

    async def shutdown(self):
        if self.client: await self.client.disconnect()
        if self.storage: await self.storage.close()
        if self.pm: self.pm.release_lock()

    async def emergency_callback(self):
        """Async callback for signal handling."""
        if self.active_uid and self.db_exporter:
            sys.stdout.write(f"\n⚠️ Performing emergency JSON export for User ID: {self.active_uid}...\n")
            path = await self.db_exporter.export_user_messages(self.active_uid, as_json=True, include_date=False)
            if path: sys.stdout.write(f"✅ Emergency dump saved to: {path}\n")
            sys.stdout.flush()

def print_target_list(targets: list):
    """Prints a formatted, color-coded list of primary targets."""
    for i, u in enumerate(targets):
        display_name = f"{UI.CLR_USER}{u['author_name']}{UI.CLR_RESET}"
        user_id_str = f"{UI.CLR_ID}{u['user_id']}{UI.CLR_RESET}"
        chat_info = f" | {UI.CLR_CHAT}{u['chat_title']}{UI.CLR_RESET}" if u.get('chat_title') else ""
        
        u_cnt = f"{UI.CLR_SUCCESS}{u['user_msg_count']}{UI.CLR_RESET}"
        c_cnt = f"{UI.CLR_STATS}{u['context_msg_count']}{UI.CLR_RESET}"
        
        stats = f" ( Сообщ: {u_cnt} | Контекст: {c_cnt} )"
        idx_str = f"[{i+1:02}]"
        print(f" {idx_str} 👤 {display_name}{stats} ( ID: {user_id_str} ){chat_info}")

async def run_cli():
    """Main CLI entry point with subcommand support."""
    parser = argparse.ArgumentParser(description="TG.MSG.CLEANER CLI", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    # export
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--user-id", required=True)
    export_parser.add_argument("--chat-id", default=None)
    export_parser.add_argument("--deep", action="store_true", default=True)
    export_parser.add_argument("--flat", action="store_false", dest="deep")
    export_parser.add_argument("--force-resync", action="store_true")
    export_parser.add_argument("--context-window", type=int, default=3)
    export_parser.add_argument("--max-cluster", type=int, default=10)
    export_parser.add_argument("--depth", type=int, default=3)
    export_parser.add_argument("--limit", type=int, default=None)
    export_parser.add_argument("--json", action="store_true")

    # update
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--force-resync", action="store_true")

    # clean
    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("--user-id", default="all")
    clean_parser.add_argument("--dry-run", action="store_true", default=None)
    clean_parser.add_argument("--apply", action="store_true")
    clean_parser.add_argument("--yes", "-y", action="store_true")

    # export-pm, delete, schedule, setup, db-export
    subparsers.add_parser("export-pm").add_argument("--user-id", required=True)
    subparsers.add_parser("delete").add_argument("--user-id", required=True)
    subparsers.add_parser("schedule")
    subparsers.add_parser("setup")
    db_parser = subparsers.add_parser("db-export")
    db_parser.add_argument("--user-id", required=True)
    db_parser.add_argument("--json", action="store_true", default=True)

    args, unknown = parser.parse_known_args()

    if not args.command:
        await main_menu()
        return

    # Special handling for setup/schedule (no client needed)
    needs_client = args.command not in ("setup", "schedule", "db-export")
    ctx = CLIContext(needs_client=needs_client)
    
    try:
        await ctx.initialize()
        
        if args.command == "setup":
            res = ctx.alias_manager.install()
            if "success" in res:
                print(res["message"])
                if "activate_cmd" in res: print(res["activate_cmd"])
                print("\n" + _("alias_header"))
                for line in ctx.alias_manager.get_alias_help()[1:]: print(line)
            else: print(res.get("error", "Error during setup"))

        elif args.command == "schedule":
            await setup_scheduler()

        elif args.command == "delete":
            uid = resolve_id(args.user_id)
            await ctx.cleaner.purge_user_data(uid)

        elif args.command == "db-export":
            uid = resolve_id(args.user_id)
            await ctx.db_exporter.export_user_messages(uid, as_json=args.json)

        elif args.command == "export":
            uid = resolve_id(args.user_id)
            ctx.active_uid = uid
            user_ent, chat_ent = await get_safe_user_and_chat(ctx.client, args.user_id, args.chat_id)
            
            if user_ent:
                ctx.active_uid = user_ent.id
                ctx.storage.upsert_user(
                    user_id=user_ent.id,
                    first_name=getattr(user_ent, 'first_name', None),
                    last_name=getattr(user_ent, 'last_name', None),
                    username=getattr(user_ent, 'username', None)
                )
            
            processed = 0
            try:
                if chat_ent:
                    processed = await ctx.exporter.sync_chat(
                        chat_ent, from_user_id=ctx.active_uid,
                        deep_mode=args.deep, force_resync=args.force_resync,
                        context_window=args.context_window, max_cluster=args.max_cluster,
                        recursive_depth=args.depth, limit=args.limit
                    )
                elif user_ent:
                    processed = await ctx.exporter.sync_all_dialogs_for_user(
                        ctx.active_uid, target_chat_ids=settings.chats_to_search_user_msgs,
                        deep_mode=args.deep, force_resync=args.force_resync,
                        context_window=args.context_window, max_cluster=args.max_cluster,
                        recursive_depth=args.depth, limit=args.limit
                    )
                else: print(f"❌ Error: Could not resolve target {args.user_id}")
                
                print(f"\n📂 Finalizing export to filesystem...")
                path = await ctx.db_exporter.export_user_messages(ctx.active_uid, as_json=True)
                if path: print(f"✅ Export successfully saved to: {path}")
                
                user_info = ctx.storage.get_user(ctx.active_uid)
                name = UI.format_name(user_info) if user_info else f"ID:{ctx.active_uid}"
                UI.print_final_summary("sync_summary_title", [{
                    "title": f"Export: {name}",
                    "lines": [("processed", processed)],
                }])

            except Exception as e:
                if not ctx.pm.should_stop(): logger.error(f"Error during export: {e}")

        elif args.command == "update":
            stats = await ctx.exporter.sync_all_outdated(threshold_seconds=3600)
            total_processed = sum(item["count"] for item in stats.values() if isinstance(item, dict))
            UI.print_final_summary("sync_summary_title", [{
                "title": "Update",
                "lines": [
                    ("processed", total_processed),
                    ("targets", len(stats)),
                ],
            }])

        elif args.command == "clean":
            is_dry = True
            if args.apply or args.yes: is_dry = False
            if args.dry_run is True: is_dry = True
            deleted = await ctx.cleaner.global_self_cleanup(dry_run=is_dry)
            print(f"\n{_('summary_header')}\n{_('total_deleted_msgs', count=deleted)}")
            if is_dry: print(f"\033[93m{_('dry_run_info')}\033[0m")

        elif args.command == "export-pm":
            user_ent, unused = await get_safe_user_and_chat(ctx.client, args.user_id)
            if user_ent: await ctx.private_archive.archive_pm(user_ent)

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
            UI.clear_screen()
            UI.print_gradient_banner()
            print("="*105)
            print(f" 🚀 Version 4.0 Hyper-Acceleration | Account: {me_id}")
            print(f" 💡 Tip: Press [ESC] to Cancel/Back anytime | [0] to Exit/Back")
            print("="*105)
            for i in range(1, 10):
                print(f" [{i}] {_('menu_' + str(i))} ({_('menu_' + str(i) + '_desc')})")
            print(f" [L] {_('menu_lang')}")
            print(f" [0] {_('menu_exit')}")
            
            sys.stdout.write(_("choice_prompt") + ": ")
            sys.stdout.flush()
            char = TerminalInput.get_char()
            if char == '\x1b': continue
            choice = char.upper()
            print(choice) # Safer than sys.stdout.write for terminal state
            
            if choice == "1":
                UI.print_header(_("menu_1"), _("menu_1_desc"))
                target_str = TerminalInput.prompt_with_esc(_("prompt_target") + ": ")
                if target_str is None or target_str.strip() == "0": continue
                
                chat_str = TerminalInput.prompt_with_esc("Chat ID (Enter for all): ")
                if chat_str is None: continue
                
                deep_choice = TerminalInput.prompt_with_esc("Deep Mode? (y/n) [y]: ")
                if deep_choice is None: continue
                active_deep = deep_choice.lower() != 'n'
                
                active_depth = 3
                if active_deep:
                    depth_str = TerminalInput.prompt_with_esc("Recursive Depth (1-5) [3]: ")
                    if depth_str and depth_str.isdigit(): active_depth = int(depth_str)
                
                user_ent, chat_ent = await get_safe_user_and_chat(ctx.client, target_str.strip(), chat_str.strip() if chat_str else None)
                if user_ent:
                    ctx.storage.upsert_user(user_id=user_ent.id, first_name=getattr(user_ent, 'first_name', None), last_name=getattr(user_ent, 'last_name', None), username=getattr(user_ent, 'username', None))
                
                final_uid = user_ent.id if user_ent else resolve_id(target_str)
                ctx.active_uid = final_uid
                
                processed = 0
                try:
                    if chat_ent:
                        processed = await ctx.exporter.sync_chat(chat_ent, from_user_id=final_uid, deep_mode=active_deep, recursive_depth=active_depth)
                    elif user_ent:
                        processed = await ctx.exporter.sync_all_dialogs_for_user(final_uid, target_chat_ids=settings.chats_to_search_user_msgs, deep_mode=active_deep, recursive_depth=active_depth)
                    else: print(f"❌ Error: Could not resolve target {target_str}")
                finally:
                    if ctx.pm.should_stop(): print(f"\n⚠️ Interrupted. Exporting partial data...")
                    if final_uid:
                        await ctx.db_exporter.export_user_messages(final_uid, as_json=True, include_date=False)
                        u_info = ctx.storage.get_user(final_uid)
                        target_name = UI.format_name(u_info) if u_info else f"ID:{final_uid}"
                        UI.print_final_summary("sync_summary_title", [{
                            "title": f"Export: {target_name}",
                            "lines": [("processed", processed)],
                        }])
                
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()
                
            elif choice == "2":
                UI.print_header(_("menu_2"), _("menu_2_desc"))
                updated_stats = await ctx.exporter.sync_all_outdated()
                if updated_stats:
                    for uid in updated_stats: await ctx.db_exporter.export_user_messages(uid, as_json=True, include_date=False)
                    total_processed = sum(item["count"] for item in updated_stats.values() if isinstance(item, dict))
                    UI.print_final_summary("sync_summary_title", [{
                        "title": "Update",
                        "lines": [
                            ("processed", total_processed),
                            ("targets", len(updated_stats)),
                        ],
                    }])
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()
                
            elif choice == "3":
                UI.print_header(_("menu_3"), _("sub_clean_info"))
                pm_choice = TerminalInput.prompt_with_esc(_("prompt_clean_pms") + ": ")
                if pm_choice is None: continue
                confirm = TerminalInput.prompt_with_esc(_("clean_confirm") + " (y/n): ")
                if confirm and confirm.lower() == "y":
                    deleted = await ctx.cleaner.global_self_cleanup(dry_run=False, include_pms=(pm_choice.lower() == 'y'))
                    print(f"\n{_('summary_header')}\n{_('total_deleted_msgs', count=deleted)}")
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()

            elif choice == "4":
                UI.print_header(_("menu_4"), _("menu_4_desc"))
                target_str = TerminalInput.prompt_with_esc(_("prompt_pm_target") + ": ")
                if target_str:
                    user_ent, unused = await get_safe_user_and_chat(ctx.client, target_str.strip())
                    if user_ent: await ctx.private_archive.archive_pm(user_ent)
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()

            elif choice == "5":
                UI.print_header(_("menu_5"), _("menu_5_desc"))
                users = ctx.storage.get_primary_targets()
                if users:
                    print_target_list(users)
                    idx = TerminalInput.prompt_with_esc("\nChoice: ")
                    if idx and idx.isdigit() and 1 <= int(idx) <= len(users):
                        await ctx.cleaner.purge_user_data(users[int(idx)-1]['user_id'])
                    else: print("Invalid selection.")
                else: print(_("no_targets"))
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()

            elif choice == "6":
                UI.print_header(_("menu_6"), _("help_desc_6"))
                await setup_scheduler()
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()

            elif choice == "7":
                UI.print_header(_("menu_7"), _("sub_setup_info"))
                res = ctx.alias_manager.install()
                if "success" in res:
                    print(res["message"])
                    if "activate_cmd" in res: print(res["activate_cmd"])
                    print("\n" + _("alias_header"))
                    for line in ctx.alias_manager.get_alias_help()[1:]: print(line)
                else: print(res.get("error", "Error during setup."))
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()
                
            elif choice == "8":
                UI.print_header(_("menu_8"), _("about_text"))
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()
                
            elif choice == "9":
                UI.print_header(_("menu_9"), _("sub_db_export_info"))
                users = ctx.storage.get_primary_targets()
                if users:
                    print_target_list(users)
                    idx_str = TerminalInput.prompt_with_esc("\n" + _("choice_prompt") + ": ")
                    if idx_str and idx_str.isdigit() and 1 <= int(idx_str) <= len(users):
                        u = users[int(idx_str)-1]
                        fmt = TerminalInput.prompt_with_esc("Format: [1] JSON [2] TXT: ")
                        if fmt == "1": await ctx.db_exporter.export_user_messages(u['user_id'], as_json=True)
                        elif fmt == "2": await ctx.db_exporter.export_user_messages(u['user_id'], as_json=False)
                else: print(_("no_targets"))
                sys.stdout.write("\n" + _("press_enter")); sys.stdout.flush(); TerminalInput.get_char()

            elif choice == "L": set_lang("en" if get_lang() == "ru" else "ru")
            elif choice == "0": break
    finally:
        await ctx.shutdown()

def main():
    try: asyncio.run(run_cli())
    except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
