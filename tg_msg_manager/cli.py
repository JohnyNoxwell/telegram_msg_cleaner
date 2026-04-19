import argparse
import os
import sys
from pathlib import Path

from .core import run_from_config, ts_print
from .exporter import run_export


def draw_banner():
    """Рисует стилизованный баннер с градиентом."""
    banner = [
        "████████╗ ██████╗     ███╗   ███╗███████╗ ██████╗      ██████╗██╗     ███████╗ █████╗ ███╗   ██╗███████╗██████╗ ",
        "╚══██╔══╝██╔════╝     ████╗ ████║██╔════╝██╔════╝     ██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║██╔════╝██╔══██╗",
        "   ██║   ██║  ███╗    ██╔████╔██║███████╗██║  ███╗    ██║     ██║     █████╗  ███████║██╔██╗ ██║█████╗  ██████╔╝",
        "   ██║   ██║   ██║    ██║╚██╔╝██║╚════██║██║   ██║    ██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║██╔══╝  ██╔══██╗",
        "   ██║   ╚██████╔╝    ██║ ╚═╝ ██║███████║╚██████╔╝    ╚██████╗███████╗███████╗██║  ██║██║ ╚████║███████╗██║  ██║",
        "   ╚═╝    ╚═════╝     ╚═╝     ╚═╝╚══════╝ ╚═════╝      ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝"
    ]
    # Градиент от синего к циану (ANSI 256)
    colors = [26, 27, 32, 33, 38, 39]
    
    print("") # Отступ сверху
    for i, line in enumerate(banner):
        color = colors[i] if i < len(colors) else colors[-1]
        print(f"\033[38;5;{color}m{line}\033[0m")
    
    print(f"\n\033[1;37m{' '*42}TG.MSG.CLEANER\033[0m")
    print(f"\033[1;33m{' '*45}by R.P.\033[0m\n")


BACK_SIGNAL = "__BACK__"

def prompt_backable(label, default=None, validator=None):
    """Ввод с возможностью отмены через '0' и валидацией."""
    from .core import ts_print
    while True:
        prompt_text = f"{label} (0 - Назад): "
        val = input(prompt_text).strip()
        
        if val == '0':
            return BACK_SIGNAL
        
        final_val = val or default
        if validator:
            try:
                result = validator(final_val)
                if result is False:
                    print("\033[1;31m❌ Ошибка: Неверный формат. Попробуйте снова.\033[0m")
                    continue
                # Если валидатор вернул преобразованное значение (например int), используем его
                if not isinstance(result, bool):
                     return result
            except ValueError as e:
                print(f"\033[1;31m❌ Ошибка: {e}\033[0m")
                continue
        
        if not final_val and not default:
            print("\033[1;31m❌ Ошибка: Значение не может быть пустым.\033[0m")
            continue
            
        return final_val


def sub_header(title):
    """Очистка экрана и вывод заголовка подменю."""
    os.system('cls' if os.name == 'nt' else 'clear')
    draw_banner()
    print(f"\033[1;36m{'='*60}\033[0m")
    print(f" \033[1;33m>>> {title.upper()}\033[0m")
    print(f"\033[1;36m{'='*60}\033[0m\n")


def interactive_menu(config_dir: str):
    """Главное интерактивное меню (TUI) с поддержкой подменю."""
    import asyncio
    from .exporter import run_export_update_async, remove_user_data
    from .pm_exporter import run_export_pm
    from .scheduler import run_scheduler
    from .setup import run_setup
    from .storage import SQLiteStorage
    from .core import validate_user_target, validate_int

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        draw_banner()
        
        print(f"\033[1;36m{'='*60}\033[0m")
        print(" [1] 📥 \033[1;37mЭкспорт\033[0m        - Выгрузить историю нового пользователя\n")
        print(" [2] 🔄 \033[1;37mОбновление\033[0m     - Синхронизировать все активные цели\n")
        print(" [3] 🧹 \033[1;37mОчистка\033[0m        - Удалить ваши сообщения из групп\n")
        print(" [4] 💬 \033[1;37mЛичка + Медиа\033[0m  - Полный архив приватного чата\n")
        print(" [5] 🗑️  \033[1;37mУдалить данные\033[0m - Полная очистка по ID пользователя\n")
        print(" [6] ⏳ \033[1;37mРасписание\033[0m     - Настройка фоновых задач (launchd/cron)\n")
        print(" [7] ⚙️  \033[1;37mНастройка\033[0m      - Установка быстрых алиасов в терминал\n")
        print(" [8] ℹ️  \033[1;37mО программе\033[0m    - Помощь и описание функций\n")
        print(f"\033[0;31m [0] ❌ Выход\033[0m")
        print(f"\033[1;36m{'='*60}\033[0m")
        
        choice = input("\n👉 \033[1;33mВыберите пункт меню:\033[0m ").strip()
        
        if choice == '0':
            ts_print("Завершение работы. До встречи!")
            break

        elif choice == '1': # EXPORT
            sub_header("Экспорт пользователя")
            uid = prompt_backable("👤 Введите ID или username", validator=validate_user_target)
            if uid == BACK_SIGNAL: continue
            
            ctx_window = prompt_backable(
                "🔍 Глубина поиска (окно)", 
                default="3", 
                validator=lambda v: validate_int(v, "Глубина", min_val=0)
            )
            if ctx_window == BACK_SIGNAL: continue
            
            ts_print(f"🚀 Запуск экспорта для {uid} (окно: {ctx_window})...")
            run_export(config_dir=config_dir, target_user=uid, as_json=True, context_window=ctx_window)

        elif choice == '2': # UPDATE
            sub_header("Обновление архивов")
            print(" [1] 🔄 Запустить синхронизацию")
            print(" [0] 🔙 Назад")
            check = input("\n Ваш выбор: ").strip()
            if check != '1': continue
            
            ts_print("🔄 Запуск массового обновления...")
            asyncio.run(run_export_update_async(config_dir=config_dir, as_json=True))

        elif choice == '3': # CLEAN
            sub_header("Очистка ваших сообщений")
            print(" [1] 🛡️ Репетиция (dry-run)")
            print(" [2] 🧨 Боевое удаление")
            print(" [0] 🔙 Назад")
            mode = input("\n Выберите режим: ").strip()
            
            if mode == '0': continue
            if mode not in ('1', '2'):
                print("\033[1;31m⚠️ Некорректный выбор режима. Возврат...\033[0m")
                asyncio.sleep(1)
                continue

            dry_run = (mode != '2')
            if not dry_run:
                confirm = input(" \033[0;31m❗ Уверены? Сообщения будут удалены. [y/N]: \033[0m").strip().lower()
                if confirm != 'y': continue
            
            run_from_config(config_dir=config_dir, dry_run_override=dry_run, resume=True, reset_state=False, assume_yes=False)

        elif choice == '4': # EXPORT-PM
            sub_header("Архив личной переписки")
            uid = prompt_backable("👤 Введите ID/username", validator=validate_user_target)
            if uid == BACK_SIGNAL: continue
            ts_print(f"🚀 Запуск выгрузки приватного чата {uid}...")
            run_export_pm(config_dir=config_dir, target_user=uid)

        elif choice == '5': # DELETE
            sub_header("Полное удаление данных")
            from .core import load_settings
            settings = load_settings(config_dir)
            db_name = f"{settings.account_name}_messages.db" if settings.account_name else "messages.db"
            db_path = os.path.join(settings.config_dir, db_name)
            storage = SQLiteStorage(db_path)
            users = storage.get_unique_sync_users()
            
            if not users:
                print("\033[1;33mℹ️  В базе данных пока нет отслеживаемых пользователей.\033[0m")
            else:
                print("📋 \033[1;37mВыберите пользователя для полного удаления данных:\033[0m\n")
                for i, u in enumerate(users, 1):
                    print(f" [{i}] {u['author_name']} (ID: {u['user_id']})")
                print(f"\n\033[0;31m [0] 🔙 Назад\033[0m")
                
                sel_idx = prompt_backable(
                    "\n👉 Введите номер", 
                    validator=lambda v: validate_int(v, "Номер", min_val=1, max_val=len(users))
                )
                
                if sel_idx != BACK_SIGNAL:
                    target = users[sel_idx - 1]
                    uid, name = target['user_id'], target['author_name']
                    
                    print(f"\n\033[0;31m❗ ВНИМАНИЕ: Будут удалены ВСЕ сообщения и файлы для '{name}'.\033[0m")
                    confirm = input(" ✅ Подтверждаете удаление? [y/N]: ").strip().lower()
                    if confirm in ('y', 'yes', 'д', 'да'):
                        remove_user_data(config_dir=config_dir, user_id=str(uid))
                    else:
                        print(" ❌ Отменено пользователем.")

        elif choice == '6': # SCHEDULE
            sub_header("Планировщик задач")
            print(" [1] ⏳ Настроить расписание")
            print(" [0] 🔙 Назад")
            if input("\n Ваш выбор: ").strip() == '1':
                run_scheduler(config_dir=config_dir)

        elif choice == '7': # SETUP
            while True:
                sub_header("Настройка системы")
                print(" [1] ⚙️  Установить алиасы (tg, tge, tgu...)")
                print(" [2] 🔑 Настроить Telegram API (ID/Hash)")
                print("\n \033[0;31m[0] 🔙 Назад\033[0m")
                
                sub_choice = input("\n Ваш выбор: ").strip()
                if sub_choice == '0':
                    break
                elif sub_choice == '1':
                    run_setup(config_dir=config_dir)
                    input("\nНажмите Enter для продолжения...")
                elif sub_choice == '2':
                    manage_api_credentials(config_dir)
                    input("\nНажмите Enter для продолжения...")

        elif choice == '8': # HELP
            help_menu()

        else:
            print("\033[1;31m⚠️ Некорректный выбор. Пожалуйста, выберите пункт от 0 до 8.\033[0m")
            import time
            time.sleep(1.5)
            continue
        
        input("\n\033[1;32m✅ Действие завершено. Нажмите Enter для возврата...\033[0m")


def manage_api_credentials(config_dir: str):
    """Гид по настройке API ID и API Hash."""
    from .core import update_config_file, validate_int
    
    sub_header("Настройка Telegram API")
    print("\n \033[1;37mДля работы скрипта требуются API ID и API Hash.\033[0m")
    print(" \033[1;36m──────────────────────────────────────────────────────────\033[0m")
    print(" 1. Перейдите на сайт: \033[4;34mhttps://my.telegram.org\033[0m")
    print(" 2. Введите свой номер телефона и код подтверждения из Telegram.")
    print(" 3. Выберите пункт \033[1;37m'API development tools'\033[0m.")
    print(" 4. Создайте новое приложение (App title и Short name - любые).")
    print(" 5. Скопируйте значения \033[1;32mapp api_id\033[0m и \033[1;32mapp api_hash\033[0m.")
    print(" \033[1;36m──────────────────────────────────────────────────────────\033[0m")
    print("\n \033[1;33m[Введите '0' на любом этапе для отмены]\033[0m\n")
    
    new_id_res = prompt_backable("👉 Введите App api_id (число)", validator=lambda v: validate_int(v, "API ID"))
    if new_id_res == BACK_SIGNAL: return
    
    new_hash = prompt_backable("👉 Введите App api_hash (строка)", validator=lambda v: v.strip() if v.strip() else None)
    if new_hash == BACK_SIGNAL: return
    
    # Сохраняем
    update_config_file(config_dir, {"api_id": int(new_id_res), "api_hash": new_hash})
    print("\n\033[1;32m✅ Настройки API успешно сохранены в config.local.json!\033[0m")


def help_menu():
    """Раздел помощи и информации о функциях."""
    while True:
        sub_header("Помощь и Информация")
        print(" [1] 📥 Экспорт (Normal vs DEEP)")
        print(" [2] 🔄 Обновление (Smart Sync)")
        print(" [3] 🧹 Очистка сообщений")
        print(" [4] 💬 Личные архивы (PM)")
        print(" [5] 🗑️  Удаление данных")
        print(" [6] ⏳ Расписание и автоматизация")
        print("\n \033[0;31m[0] 🔙 Назад в главное меню\033[0m")
        
        choice = input("\n👉 Выберите тему для справки: ").strip()
        
        if choice == '0':
            break
        
        os.system('cls' if os.name == 'nt' else 'clear')
        draw_banner()
        print(f"\033[1;36m{'='*60}\033[0m")
        
        if choice == '1':
            print(" \033[1;33m>>> ЭКСПОРТ (NORMAL vs DEEP)\033[0m\n")
            print(" • \033[1;37mNormal\033[0m: Выгружает только сообщения целевого пользователя.")
            print("   Быстро, занимает мало места. Подходит для простых логов.\n")
            print(" • \033[1;37mDEEP\033[0m: Режим «глубокого» погружения. Скрипт анализирует")
            print("   каждое сообщение пользователя. Если это ответ на реплику")
            print("   или начало обсуждения, скрипт выкачивает весь контекст")
            print("   вокруг (до 5-10 сообщений).")
            print("   Позволяет читать переписку как полноценный диалог в контексте.")
        elif choice == '2':
            print(" \033[1;33m>>> СМАРТ-ОБНОВЛЕНИЕ\033[0m\n")
            print(" Эта функция автоматически синхронизирует все ваши «Цели».")
            print(" Программа помнит, на каком сообщении она остановилась в прошлый")
            print(" раз для каждого чата, и скачивает только новые данные.")
            print(" Режим (Normal/DEEP) сохраняется автоматически из истории.")
        elif choice == '3':
            print(" \033[1;33m>>> ОЧИСТКА СООБЩЕНИЙ\033[0m\n")
            print(" Удаляет ВАШИ сообщения из публичных групп и каналов.")
            print(" • \033[1;32mDry-run\033[0m: Режим репетиции. Просто показывает статистику.")
            print(" • \033[1;31mУдаление\033[0m: Реальное удаление из Telegram.")
            print(" \033[0;31mВНИМАНИЕ:\033[0m Удаленные сообщения невозможно восстановить.")
        elif choice == '4':
            print(" \033[1;33m>>> ЛИЧНЫЕ АРХИВЫ (PM)\033[0m\n")
            print(" Полная выгрузка истории личной переписки (один-на-один).")
            print(" В отличие от обычного экспорта, этот режим всегда выгружает")
            print(" ВСЕ сообщения обоих участников, включая медиафайлы.")
        elif choice == '5':
            print(" \033[1;33m>>> УДАЛЕНИЕ ДАННЫХ\033[0m\n")
            print(" Полная очистка локальной базы данных и всех файлов конкретного")
            print(" пользователя. Используйте это, чтобы начать сбор истории")
            print(" заново или если данные больше не требуются.")
        elif choice == '6':
            print(" \033[1;33m>>> РАСПИСАНИЕ И АВТОМАТИЗАЦИЯ\033[0m\n")
            print(" Позволяет настроить скрипт для работы в фоновом режиме.")
            print(" • \033[1;37mScheduler\033[0m: Настройка системных служб запуска (launchd).")
            print(" • \033[1;37mSetup\033[0m: Установка быстрых команд (алиасов) для терминала.")
        else:
            print(" ⚠️ Тема не найдена.")

        print(f"\n\033[1;36m{'='*60}\033[0m")
        input("\nНажмите Enter, чтобы вернуться к оглавлению...")


def main() -> None:
    # Обратная совместимость: если первый аргумент не является командой и это старые флаги, подставляем 'clean'
    if len(sys.argv) > 1 and not sys.argv[1] in ('clean', 'export', 'export-pm', 'update', 'schedule', 'setup', 'delete', '-h', '--help'):
        # Если это старый формат вроде --apply или --dry-run
        sys.argv.insert(1, 'clean')

    parser = argparse.ArgumentParser(
        prog="tg-msg-manager",
        description="Инструмент для работы с вашими сообщениями в Telegram (удаление/экспорт).",
    )

    parser.add_argument(
        "--config-dir",
        default=None,
        help="Директория, где лежит config.local.json/config.json (по умолчанию: $TGMC_CONFIG_DIR или текущая).",
    )

    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    # --- Подпарсер CLEAN ---
    clean_parser = subparsers.add_parser("clean", help="Удалить ваши сообщения (поведение по умолчанию)")
    
    dry = clean_parser.add_mutually_exclusive_group()
    dry.add_argument("--apply", action="store_true", help="Реально удалить сообщения (override dry_run).")
    dry.add_argument("--dry-run", dest="dry_run_flag", action="store_true", help="Только проверить (override dry_run).")

    clean_parser.add_argument("--no-resume", action="store_true", help="Оставлено для совместимости.")
    clean_parser.add_argument("--reset-state", action="store_true", help="Оставлено для совместимости.")
    clean_parser.add_argument("--yes", action="store_true", help="Без подтверждения.")

    # --- Подпарсер EXPORT ---
    export_parser = subparsers.add_parser("export", help="Экспортировать сообщения пользователя")
    export_parser.add_argument("--user-id", required=True, help="ID или username пользователя, сообщения которого нужно выгрузить.")
    export_parser.add_argument("--chat-id", default=None, help="ID или username конкретного чата (если не указано, ищет по всем чатам).")
    export_parser.add_argument("--out", default=None, help="Путь до файла выгрузки (по умолчанию 'Экспорт_{Ник}_{ID}.txt').")
    export_parser.add_argument("--json", action="store_true", default=True, help="Выгрузить в формате JSONL (по умолчанию).")
    export_parser.add_argument("--txt", action="store_false", dest="json", help="Выгрузить в текстовом формате вместо JSONL.")
    export_parser.add_argument("--deep", action="store_true", default=True, help="Включить глубокий поиск контекста (теперь по умолчанию True).")
    export_parser.add_argument("--flat", action="store_true", help="Отключить контекст (только сообщения автора).")
    export_parser.add_argument("--context-window", type=int, default=3, help="Размер окна контекста (по умолчанию: 3).")
    export_parser.add_argument("--time-threshold", type=int, default=120, help="Временной порог связи (сек).")
    export_parser.add_argument("--max-window", type=int, default=5, help="Макс. сообщений в одну сторону.")
    export_parser.add_argument("--merge-gap", type=int, default=2, help="Разрыв для объединения окон.")
    export_parser.add_argument("--max-cluster", type=int, default=10, help="Макс. сообщений в кластере (по умолчанию: 10).")
    export_parser.add_argument("--force-resync", action="store_true", help="Сбросить историю и перекачать всё заново с текущими настройками.")

    # --- Подпарсер UPDATE ---
    update_parser = subparsers.add_parser("update", help="Инкрементально обновить все собранные экспорты")
    update_parser.add_argument("--json", action="store_true", default=True, help="Обновлять файлы .jsonl (по умолчанию).")
    update_parser.add_argument("--txt", action="store_false", dest="json", help="Обновлять текстовые файлы вместо JSONL.")
    update_parser.add_argument("--deep", action="store_true", help="Включить глубокий поиск (если еще не включен в базе).")
    update_parser.add_argument("--flat", action="store_true", help="Принудительно перевести в плоский режим.")
    update_parser.add_argument("--context-window", type=int, default=None, help="Переопределить размер окна контекста.")
    update_parser.add_argument("--force-resync", action="store_true", help="Сбросить историю всех целей и перекачать заново.")

    # --- Подпарсер EXPORT-PM ---
    export_pm_parser = subparsers.add_parser("export-pm", help="Экспорт приватного диалога (текст + медиа)")
    export_pm_parser.add_argument("--user-id", required=True, help="ID или username пользователя, чей приватный диалог нужно выгрузить.")

    # --- Подпарсер DELETE ---
    delete_parser = subparsers.add_parser("delete", help="Удалить все локальные данные пользователя (БД + файлы)")
    delete_parser.add_argument("--user-id", required=True, help="ID пользователя, данные которого нужно удалить.")
    delete_parser.add_argument("--yes", action="store_true", help="Пропустить подтверждение.")

    # --- Подпарсер SETUP ---
    setup_parser = subparsers.add_parser("setup", help="Установить быстрые алиасы (tgr, tgd, tge, tgu, tgpm, tg) в ваш терминал")

    args = parser.parse_args()

    config_dir = args.config_dir
    if not config_dir:
        env_dir = os.getenv("TGMC_CONFIG_DIR")
        if env_dir:
            config_dir = str(Path(env_dir).expanduser())
        else:
            config_dir = os.getcwd()

    command = args.command

    if command is None:
        interactive_menu(config_dir)
        return

    if command == "clean":
        dry_run_override = None
        if getattr(args, 'apply', False):
            dry_run_override = False
        elif getattr(args, 'dry_run_flag', False):
            dry_run_override = True

        run_from_config(
            config_dir=config_dir,
            dry_run_override=dry_run_override,
            resume=True,
            reset_state=False,
            assume_yes=getattr(args, 'yes', False),
        )
    elif command == "export":
        ctx_win = args.context_window
        # Логика приоритетов: --flat отключает всё, иначе используем окно (которое теперь 3 по умолчанию)
        if args.flat: ctx_win = 0
        
        run_export(
            config_dir=config_dir, target_user=args.user_id, chat_id=args.chat_id, output_file=args.out,
            as_json=args.json, context_window=ctx_win, time_threshold=args.time_threshold,
            max_window=args.max_window, merge_gap=args.merge_gap, max_cluster=args.max_cluster,
            force_resync=args.force_resync
        )
    elif command == "update":
        from .exporter import run_export_update_async
        import asyncio
        # Передаем параметры как Optional, чтобы exporter знал, когда использовать значения из БД
        ctx_win = args.context_window
        if args.flat: ctx_win = 0
        asyncio.run(run_export_update_async(
            config_dir=config_dir, as_json=args.json, 
            context_window=ctx_win, 
            force_resync=args.force_resync
        ))
    elif command == "export-pm":
        from .pm_exporter import run_export_pm
        run_export_pm(config_dir=config_dir, target_user=args.user_id)
    elif command == "schedule":
        from .scheduler import run_scheduler
        run_scheduler(config_dir=config_dir)
    elif command == "setup":
        from .setup import run_setup
        run_setup(config_dir=config_dir)
    elif command == "delete":
        from .exporter import remove_user_data
        uid = args.user_id
        if not args.yes:
            ts_print(f"⚠️  ВНИМАНИЕ: Это действие удалит ВСЕ сообщения из базы данных и ВСЕ файлы экспорта для ID {uid}.")
            ans = input(f" Продолжить? [y/N]: ").strip().lower()
            if ans != 'y':
                ts_print("Отмена удаления.")
                return
        remove_user_data(config_dir=config_dir, user_id=uid)


if __name__ == "__main__":
    main()
