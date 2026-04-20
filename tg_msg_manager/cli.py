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
    
    pm.setup_signals()
    storage = SQLiteStorage(settings.db_path)
    await storage.start()
    client = TelethonClientWrapper(settings.session_name, settings.api_id, settings.api_hash)
    
    export_service = ExportService(client, storage)
    cleaner_service = CleanerService(client, storage, whitelist=settings.whitelist_chats)
    pm_service = PrivateArchiveService(client, storage)

    try:
        await client.connect()
        if args.command == "export":
            uid = resolve_id(args.user_id)
            await export_service.sync_chat(uid, from_user_id=uid) # Simplified for recovery
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
    
    pm.setup_signals()
    storage = SQLiteStorage(settings.db_path)
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
                    "Синхронизация истории сообщений. Программа сканирует указанные чаты,\n"
                    "находит сообщения целевого пользователя и сохраняет их вместе с \n"
                    "окружающим контекстом для последующего анализа."
                )
                target_str = TerminalInput.prompt_with_esc(_("prompt_target") + ": ")
                if target_str is None or target_str == "0": continue
                await client.connect()
                user_ent, chat_ent = await get_safe_user_and_chat(client, target_str.strip())
                if user_ent:
                    await export_service.sync_chat(user_ent, from_user_id=user_ent.id)
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
                await export_service.sync_all_outdated()
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
                    for i, u in enumerate(users): print(f" [{i+1}] {u['author_name']} ({u['user_id']})")
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
                    "Экспорт из локальной базы. Позволяет выгрузить сохраненные сообщения\n"
                    "пользователя в JSON или текстовый формат для стороннего просмотра\n"
                    "и дальнейшей обработки."
                )
                users = storage.get_unique_sync_users()
                if users:
                    print("\nSelect user to export:")
                    for i, u in enumerate(users): print(f" [{i+1}] {u['author_name']} (ID: {u['user_id']})")
                    idx = TerminalInput.prompt_with_esc("\nChoice: ")
                    if idx and idx.isdigit() and 1 <= int(idx) <= len(users):
                        u = users[int(idx)-1]
                        await db_export_service.export_user_messages(u['user_id'])
                    else:
                        print("Invalid selection.")
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
