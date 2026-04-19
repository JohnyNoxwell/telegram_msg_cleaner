import argparse
import os
import sys
from pathlib import Path

from .core import run_from_config, ts_print
from .exporter import run_export


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

    command = args.command or "clean"

    if command == "clean":
        dry_run_override = None
        if getattr(args, 'apply', False):
            dry_run_override = False
        elif getattr(args, 'dry_run_flag', False):
            dry_run_override = True

        run_from_config(
            config_dir=config_dir,
            dry_run_override=dry_run_override,
            resume=not getattr(args, 'no_resume', False),
            reset_state=getattr(args, 'reset_state', False),
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
