import argparse
import os
from pathlib import Path

from .core import run_from_config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tg-message-cleaner",
        description="Удаляет ваши сообщения из групп/каналов Telegram (Telethon).",
    )

    parser.add_argument(
        "--config-dir",
        default=None,
        help="Директория, где лежит config.local.json/config.json (по умолчанию: $TGMC_CONFIG_DIR или текущая).",
    )

    dry = parser.add_mutually_exclusive_group()
    dry.add_argument("--apply", action="store_true", help="Реально удалить сообщения (override dry_run).")
    dry.add_argument("--dry-run", dest="dry_run_flag", action="store_true", help="Только проверить (override dry_run).")

    # Эти опции оставлены для обратной совместимости с прошлой версией,
    # где использовался state/progress. Сейчас каждый запуск делает полный проход.
    parser.add_argument("--no-resume", action="store_true", help="Оставлено для совместимости; сейчас progress не используется.")
    parser.add_argument("--reset-state", action="store_true", help="Оставлено для совместимости; удаляет state-файл (если он есть).")
    parser.add_argument("--yes", action="store_true", help="Без подтверждения (не задавать интерактивный вопрос).")

    args = parser.parse_args()

    config_dir = args.config_dir
    if not config_dir:
        env_dir = os.getenv("TGMC_CONFIG_DIR")
        if env_dir:
            config_dir = str(Path(env_dir).expanduser())
        else:
            config_dir = os.getcwd()

    dry_run_override = None
    if args.apply:
        dry_run_override = False
    elif args.dry_run_flag:
        dry_run_override = True

    run_from_config(
        config_dir=config_dir,
        dry_run_override=dry_run_override,
        resume=not args.no_resume,
        reset_state=args.reset_state,
        assume_yes=args.yes,
    )


if __name__ == "__main__":
    main()

