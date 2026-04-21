import os
import asyncio
import logging
import sys
import argparse
import platform
from typing import Optional, Any
try:
    import tty
    import termios
except ImportError:
    tty = None
    termios = None

class TerminalInput:
    """
    Helper to read raw input including Escape key on Unix systems.
    """
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
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    @staticmethod
    def prompt_with_esc(prompt: str = "") -> Optional[str]:
        """
        Equivalent to input() but returns None if ESC is pressed.
        """
        sys.stdout.write(prompt)
        sys.stdout.flush()
        
        input_str = ""
        while True:
            char = TerminalInput.get_char()
            
            # ESC
            if char == '\x1b':
                sys.stdout.write("\n")
                return None
            
            # Enter
            if char == '\r' or char == '\n':
                sys.stdout.write("\n")
                return input_str
            
            # Backspace
            if char == '\x7f' or char == '\x08':
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                continue
                
            # Regular printable chars
            if char.isprintable():
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
from .i18n import _, set_lang, get_lang

logger = logging.getLogger(__name__)

def clear_screen():
    """Clears the terminal screen."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def resolve_id(id_str: str) -> Any:
    """Helper to convert string IDs to int if they look like numbers."""
    try:
        return int(id_str)
    except (ValueError, TypeError):
        return id_str

async def get_safe_user_and_chat(client: TelethonClientWrapper, user_id_str: str, chat_id_str: Optional[str] = None):
    """
    Safely resolves user and chat entities.
    """
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

def print_gradient_banner():
    """Prints the ASCII banner with a vertical color gradient."""
    print() # Add top margin
    banner = [
        "████████╗ ██████╗      ███╗   ███╗███████╗ ██████╗      ███╗   ███╗███╗   ██╗ ██████╗ ██████╗",
        "╚══██╔══╝██╔════╝      ████╗ ████║██╔════╝██╔════╝      ████╗ ████║████╗  ██║██╔════╝██╔══██╗",
        "   ██║   ██║  ███╗     ██╔████╔██║███████╗██║  ███╗     ██╔████╔██║██╔██╗ ██║██║  ███╗██████╔╝",
        "   ██║   ██║   ██║     ██║╚██╔╝██║╚════██║██║   ██║     ██║╚██╔╝██║██║╚██╗██║██║   ██║██╔══██╗",
        "   ██║   ╚██████╔╝     ██║ ╚═╝ ██║███████║╚██████╔╝     ██║ ╚═╝ ██║██║ ╚████║╚██████╔╝██║  ██║",
        "   ╚═╝    ╚═════╝      ╚═╝     ╚═╝╚══════╝ ╚═════╝      ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝",
    ]
    
    # Gradient from Cyan (0, 255, 255) to Magenta (255, 0, 255)
    steps = len(banner)
    for i, line in enumerate(banner):
        r = int(0 + (255 - 0) * (i / (steps - 1)))
        g = int(255 + (0 - 255) * (i / (steps - 1)))
        b = 255
        # ANSI 24-bit color: \033[38;2;R;G;Bm
        print(f"\033[38;2;{r};{g};{b}m{line}\033[0m")
    
    print(f"\n\033[1;36m                     TG_MSG_MNGR by R.P.\033[0m")

async def run_cli():
    """
    Main CLI entry point with subcommand support.
    """
    setup_logging()
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

    # export-pm
    subparsers.add_parser("export-pm").add_argument("--user-id", required=True)

    # delete
    subparsers.add_parser("delete").add_argument("--user-id", required=True)

    # schedule
    subparsers.add_parser("schedule")

    # db-export
    db_parser = subparsers.add_parser("db-export")
    db_parser.add_argument("--user-id", required=True)
    db_parser.add_argument("--json", action="store_true", default=True)

    args, unknown = parser.parse_known_args()

    if not args.command:
        await main_menu()
        return

    pm = ProcessManager()
    if not pm.acquire_lock():
        print(_("error_locked"))
        sys.exit(1)
    
    # State for emergency export
    state = {"active_uid": None}
    storage = SQLiteStorage(settings.db_path)
    db_export_service = DBExportService(storage)

    async def emergency_export_callback():
        uid = state.get("active_uid")
        storage.request_stop() # Signal all workers to halt
        if uid:
            sys.stdout.write(f"\n⚠️ Performing emergency JSON export for User ID: {uid}...\n")
            sys.stdout.flush()
            path = await db_export_service.export_user_messages(uid, as_json=True, include_date=False)
            if path:
                sys.stdout.write(f"✅ Emergency dump saved to: {path}\n")
            else:
                sys.stdout.write(f"❌ No messages found in DB for emergency dump.\n")
            sys.stdout.flush()

    # Register async signals
    pm.setup_async_signals(asyncio.get_running_loop(), emergency_export_callback)
    
    await storage.start()
    client = TelethonClientWrapper(settings.session_name, settings.api_id, settings.api_hash)
    
    export_service = ExportService(client, storage)
    cleaner_service = CleanerService(client, storage, whitelist=settings.whitelist_chats)
    pm_service = PrivateArchiveService(client, storage)

    try:
        await client.connect()
        if args.command == "export":
            uid = resolve_id(args.user_id)
            state["active_uid"] = uid # Set for emergency export
            
            user_ent, chat_ent = await get_safe_user_and_chat(client, args.user_id, args.chat_id)
            if user_ent:
                state["active_uid"] = user_ent.id # Update with real ID if resolved
                storage.upsert_user(
                    user_id=user_ent.id,
                    first_name=getattr(user_ent, 'first_name', None),
                    last_name=getattr(user_ent, 'last_name', None),
                    username=getattr(user_ent, 'username', None)
                )
            
            # Start sync
            try:
                if chat_ent:
                    # Sync specific chat
                    await export_service.sync_chat(
                        chat_ent,
                        from_user_id=state["active_uid"],
                        deep_mode=args.deep,
                        force_resync=args.force_resync,
                        context_window=args.context_window,
                        max_cluster=args.max_cluster,
                        recursive_depth=args.depth
                    )
                elif user_ent:
                    # Global sync for user - constrained by config
                    await export_service.sync_all_dialogs_for_user(
                        state["active_uid"],
                        target_chat_ids=settings.chats_to_search_user_msgs,
                        deep_mode=args.deep,
                        force_resync=args.force_resync,
                        context_window=args.context_window,
                        max_cluster=args.max_cluster,
                        recursive_depth=args.depth
                    )
                else:
                    print(f"❌ Error: Could not resolve target {args.user_id}")
                
                # Perform FINAL export from DB to Filesystem
                print(f"\n📂 Finalizing export to filesystem...")
                path = await db_export_service.export_user_messages(state["active_uid"], as_json=True)
                if path:
                    print(f"✅ Export successfully saved to: {path}")

            except Exception as e:
                # If shutdown requested, we don't log as error
                if not pm.should_stop():
                    logger.error(f"Error during export: {e}")

        elif args.command == "update":
            await export_service.sync_all_outdated()
        elif args.command == "clean":
            await cleaner_service.global_self_cleanup(dry_run=True)
    finally:
        await client.disconnect()
        await storage.close()
        pm.release_lock()

def print_submenu_header(title: str, description: str):
    """Prints a consistent header for sub-menus."""
    clear_screen()
    print_gradient_banner()
    print("="*105)
    print(f" 📂 {title}")
    print("="*105)
    print(description)
    print("-" * 105)

async def main_menu():
    setup_logging()
    pm = ProcessManager()
    if not pm.acquire_lock():
        print(_("error_locked"))
        sys.exit(1)
    
    # Use async-native signals for reliable graceful shutdown
    pm.setup_async_signals(asyncio.get_running_loop())
    storage = SQLiteStorage(settings.db_path, process_manager=pm)
    await storage.start()
    client = TelethonClientWrapper(settings.session_name, settings.api_id, settings.api_hash)
    
    export_service = ExportService(client, storage)
    cleaner_service = CleanerService(client, storage, whitelist=settings.whitelist_chats)
    db_export_service = DBExportService(storage)
    pm_service = PrivateArchiveService(client, storage)

    try:
        await client.connect()
        me = await client.get_me()
        me_id = me.id if me else "Unknown"
        
        while True:
            clear_screen()
            print_gradient_banner()
            print("="*105)
            print(f" 🚀 Version 4.0 Hyper-Acceleration | Account: {me_id}")
            print(f" 💡 Tip: Press [ESC] to Cancel/Back anytime | [0] to Exit/Back")
            print("="*105)
            print(f" [1] {_('menu_1')} ({_('menu_1_desc')})")
            print(f" [2] {_('menu_2')} ({_('menu_2_desc')})")
            print(f" [3] {_('menu_3')} ({_('menu_3_desc')})")
            print(f" [4] {_('menu_4')} ({_('menu_4_desc')})")
            print(f" [5] {_('menu_5')} ({_('menu_5_desc')})")
            print(f" [8] {_('menu_8')}")
            print(f" [9] {_('menu_9')}")
            print(f" [L] {_('menu_lang')}")
            print(f" [0] {_('menu_exit')}")
            
            sys.stdout.write(_("choice_prompt") + ": ")
            sys.stdout.flush()
            char = TerminalInput.get_char()
            if char == '\x1b': continue
            choice = char.upper()
            sys.stdout.write(choice + "\n")
            
            if choice == "1":
                print_submenu_header(
                    _("menu_1"),
                    "Синхронизация истории сообщений. Программа сканирует чаты,\n"
                    "находит сообщения целевого пользователя и сохраняет их вместе с \n"
                    "окружающим контекстом для последующего анализа."
                )
                target_str = TerminalInput.prompt_with_esc(_("prompt_target") + ": ")
                if target_str is None or target_str == "0": continue
                
                chat_str = TerminalInput.prompt_with_esc("Chat ID (Leave empty for config-based scan): ")
                if chat_str is None: continue
                
                # New: Ask for Deep Mode and Depth
                deep_choice = TerminalInput.prompt_with_esc("Enable Deep Mode? (y/n) [Default: y]: ")
                if deep_choice is None: continue
                active_deep = deep_choice.lower() != 'n'
                
                active_depth = 3
                if active_deep:
                    print("\n--- Глубина рекурсии (Recursive Depth) ---")
                    print(" 1: Только прямое сообщение, на которое ответили")
                    print(" 2-3: Оптимально (цепочки ответов в обсуждении)")
                    print(" 5: Максимальный контекст (длинные ветки диалогов)")
                    
                    depth_str = TerminalInput.prompt_with_esc("\nRecursive Depth (1-5) [Default: 3]: ")
                    if depth_str is None: continue
                    if depth_str.isdigit():
                        active_depth = int(depth_str)
                
                await client.connect()
                user_ent, chat_ent = await get_safe_user_and_chat(client, target_str.strip(), chat_str.strip() if chat_str else None)
                if user_ent:
                    storage.upsert_user(
                        user_id=user_ent.id,
                        first_name=getattr(user_ent, 'first_name', None),
                        last_name=getattr(user_ent, 'last_name', None),
                        username=getattr(user_ent, 'username', None)
                    )
                
                final_uid = user_ent.id if user_ent else resolve_id(target_str)
                
                try:
                    if chat_ent:
                        await export_service.sync_chat(chat_ent, from_user_id=final_uid, deep_mode=active_deep, recursive_depth=active_depth)
                    elif user_ent:
                        if not settings.chats_to_search_user_msgs:
                            print("⚠️ No chats defined in chats_to_search_user_msgs config. Scanning all dialogs...")
                        await export_service.sync_all_dialogs_for_user(final_uid, target_chat_ids=settings.chats_to_search_user_msgs, deep_mode=active_deep, recursive_depth=active_depth)
                    else:
                        print(f"❌ Error: Could not resolve target {target_str}")
                finally:
                    # If stopped manually or finished, we ensure a local JSON dump is updated
                    if pm.should_stop():
                        print(f"\n⚠️ Interrupted. Performing emergency JSON export of partial data for {final_uid}...")
                    
                    if final_uid:
                        await db_export_service.export_user_messages(final_uid, as_json=True, include_date=False)
                
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()
                
            elif choice == "2":
                print_submenu_header(
                    _("menu_2"),
                    "Синхронизация всех активных целей. Автоматическое обновление базы данных\n"
                    "для всех пользователей, чьи сообщения вы когда-либо выгружали."
                )
                await client.connect()
                updated_uids = await export_service.sync_all_outdated()
                
                if updated_uids:
                    print(f"\n💾 Updating JSON files for {len(updated_uids)} targets...")
                    for uid in updated_uids:
                        await db_export_service.export_user_messages(uid, as_json=True, include_date=False)
                    print("✅ All exports updated.")
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()
                
            elif choice == "3":
                print_submenu_header(
                    _("menu_3"),
                    "Глобальная очистка ваших сообщений. Позволяет массово удалить ваши\n"
                    "собственные сообщения из всех групп и чатов, где вы участвуете\n"
                    "(кроме тех, что находятся в белом списке)."
                )
                confirm = TerminalInput.prompt_with_esc("Proceed? (y/n): ")
                if confirm and confirm.lower() == "y":
                    await client.connect()
                    await cleaner_service.global_self_cleanup(dry_run=True)
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()

            elif choice == "4":
                print_submenu_header(
                    _("menu_4"),
                    "Архив личных сообщений. Создает полный медиа-архив приватного чата\n"
                    "с пользователем, включая фотографии, видео и документы."
                )
                target_str = TerminalInput.prompt_with_esc(_("prompt_pm_target") + ": ")
                if target_str:
                    await client.connect()
                    user_ent, unused = await get_safe_user_and_chat(client, target_str.strip())
                    if user_ent: await pm_service.archive_pm(user_ent)
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()

            elif choice == "5":
                print_submenu_header(
                    _("menu_5"),
                    "Удаление локальных данных. Безвозвратное удаление всех скачанных\n"
                    "сообщений и метаданных конкретного пользователя из локальной базы."
                )
                users = storage.get_primary_targets()
                if users:
                    print("\nSelect user to purge:")
                    for i, u in enumerate(users):
                        display_name = u['author_name']
                        chat_info = f" | {u['chat_title']}" if u.get('chat_title') else ""
                        print(f" [{i+1}] {display_name} ( ID: {u['user_id']} ){chat_info}")
                    idx = TerminalInput.prompt_with_esc("\nChoice: ")
                    if idx and idx.isdigit() and 1 <= int(idx) <= len(users):
                        u = users[int(idx)-1]
                        await cleaner_service.purge_user_data(u['user_id'])
                    else:
                        print("Invalid selection.")
                else:
                    print(_("no_targets"))
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()
                
            elif choice == "8":
                print_submenu_header(
                    _("menu_8"),
                    "Информация о системе. TG_MSG_MNGR — это мощный инструмент для\n"
                    "управления сообщениями в Telegram, предоставляющий возможности\n"
                    "синхронизации, архивации и умной очистки данных."
                )
                print(_("about_text"))
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()
                
            elif choice == "9":
                print_submenu_header(
                    _("menu_9"),
                    _("sub_db_export_info")
                )
                users = storage.get_primary_targets()
                if users:
                    print("\n" + _("select_user_export") + ":")
                    for i, u in enumerate(users):
                        display_name = u['author_name']
                        chat_info = f" | {u['chat_title']}" if u.get('chat_title') else ""
                        print(f" [{i+1}] {display_name} ( ID: {u['user_id']} ){chat_info}")
                    
                    idx_str = TerminalInput.prompt_with_esc("\n" + _("choice_prompt") + " (0 - " + _("back") + "): ")
                    if idx_str is None or idx_str == "0": continue
                    
                    if idx_str.isdigit() and 1 <= int(idx_str) <= len(users):
                        u = users[int(idx_str)-1]
                        
                        # Внутреннее меню выбора формата
                        print("\n" + _("select_format") + ":")
                        print(f" [1] JSON - {_('fmt_json')}")
                        print(f" [2] TXT  - {_('fmt_txt')}")
                        print(f" [0] {_('back')}")
                        
                        sys.stdout.write(_("choice_prompt") + ": ")
                        sys.stdout.flush()
                        fmt_char = TerminalInput.get_char()
                        sys.stdout.write(fmt_char + "\n")
                        
                        if fmt_char == "1":
                            await db_export_service.export_user_messages(u['user_id'], as_json=True)
                        elif fmt_char == "2":
                            await db_export_service.export_user_messages(u['user_id'], as_json=False)
                        elif fmt_char == "0" or fmt_char == '\x1b':
                            continue
                        else:
                            print(_("error") + ": " + _("invalid_choice", start=0, end=2))
                    else:
                        print(_("error") + ": " + _("invalid_choice", start=1, end=len(users)))
                else:
                    print(_("no_targets"))
                sys.stdout.write("\n" + _("press_enter"))
                sys.stdout.flush()
                TerminalInput.get_char()

            elif choice == "L":
                set_lang("en" if get_lang() == "ru" else "ru")
                continue

            elif choice == "0":
                break
    finally:
        await client.disconnect()
        await storage.close()
        pm.release_lock()

def main():
    try: asyncio.run(run_cli())
    except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
