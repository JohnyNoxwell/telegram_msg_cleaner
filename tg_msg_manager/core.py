import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import hashlib
import os
from typing import List, Optional, Set

from telethon import TelegramClient
from telethon.errors import FloodWaitError
 


DEFAULT_CONFIG_CANDIDATES = ["config.local.json", "config.json"]
DEFAULT_LOG_NAME = "delete_log.txt"
DEFAULT_STATE_NAME = "tg_msg_manager_state.json"
STATE_VERSION = 1


@dataclass
class Settings:
    api_id: int
    api_hash: str
    session_name: str = "tg_delete_my_msgs"

    dry_run: bool = True
    min_date_days_ago: Optional[int] = None

    include_chats: Optional[Set[int]] = None
    exclude_chats: Optional[Set[int]] = None
    # case-insensitive сравнение по `dialog.name`/`dialog.title`
    exclude_chat_titles: Optional[Set[str]] = None

    delete_media: bool = True
    delete_text: bool = True
    delete_forwards: bool = True

    base_delay_sec: float = 0.15
    max_delay_sec: float = 5.0

    batch_size: int = 50

    config_dir: str = "."
    log_path: Optional[str] = None


def _config_path(config_dir: str) -> str:
    for name in DEFAULT_CONFIG_CANDIDATES:
        path = os.path.join(config_dir, name)
        if os.path.exists(path):
            return path
    # Если ничего не нашли — возвращаем путь по умолчанию (для сообщения об ошибке)
    return os.path.join(config_dir, DEFAULT_CONFIG_CANDIDATES[0])


def _log_path(settings: Settings) -> str:
    if settings.log_path:
        return settings.log_path
    return os.path.join(settings.config_dir, DEFAULT_LOG_NAME)


def load_settings(config_dir: str = ".") -> Settings:
    path = _config_path(config_dir)
    if not os.path.exists(path):
        raise RuntimeError(
            f"Не найден конфиг. Ожидается один из файлов: {', '.join(DEFAULT_CONFIG_CANDIDATES)}. "
            f"Для примера используйте `config.example.json`, затем создайте локальный файл "
            f"`config.local.json`."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    def _to_set(name: str) -> Optional[Set[int]]:
        v = raw.get(name)
        if not v:
            return None
        return {int(x) for x in v}

    def _to_title_set(name: str) -> Optional[Set[str]]:
        v = raw.get(name)
        if not v:
            return None
        titles: Set[str] = set()
        for x in v:
            s = str(x).strip()
            if s:
                titles.add(s.casefold())
        return titles or None

    return Settings(
        api_id=int(raw["api_id"]),
        api_hash=str(raw["api_hash"]),
        session_name=raw.get("session_name", "tg_delete_my_msgs"),
        dry_run=bool(raw.get("dry_run", True)),
        min_date_days_ago=raw.get("min_date_days_ago"),
        include_chats=_to_set("include_chats"),
        exclude_chats=_to_set("exclude_chats"),
        exclude_chat_titles=_to_title_set("exclude_chat_titles"),
        delete_media=bool(raw.get("delete_media", True)),
        delete_text=bool(raw.get("delete_text", True)),
        delete_forwards=bool(raw.get("delete_forwards", True)),
        base_delay_sec=float(raw.get("base_delay_sec", 0.15)),
        max_delay_sec=float(raw.get("max_delay_sec", 5.0)),
        batch_size=int(raw.get("batch_size", 50)),
        config_dir=config_dir,
        log_path=raw.get("log_path"),
    )


def _stable_json_dumps(data) -> str:
    # ensure_ascii=False важен для читабельности при локальном дебаге.
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _normalized_int_set(v: Optional[Set[int]]) -> Optional[List[int]]:
    if v is None:
        return None
    return sorted(int(x) for x in v)


def compute_run_key(settings: Settings) -> str:
    """
    Ключ “сессии настроек” — чтобы при смене фильтров/режима не продолжать с неверного state.
    """
    key_data = {
        "dry_run": settings.dry_run,
        "min_date_days_ago": settings.min_date_days_ago,
        "include_chats": _normalized_int_set(settings.include_chats),
        "exclude_chats": _normalized_int_set(settings.exclude_chats),
        "delete_media": settings.delete_media,
        "delete_text": settings.delete_text,
        "delete_forwards": settings.delete_forwards,
    }
    raw = _stable_json_dumps(key_data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _state_path(config_dir: str, state_path: Optional[str]) -> str:
    if state_path:
        return state_path
    return os.path.join(config_dir, DEFAULT_STATE_NAME)


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        # Если state битый, безопаснее начать заново.
        return {}


def save_state(path: str, state: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def reset_state_file(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def append_log(settings: Settings, line: str) -> None:
    log_path = _log_path(settings)
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {line}\n")


def message_passes_filters(msg, me_id: int, settings: Settings, min_date: Optional[datetime]) -> bool:
    # При выборке через `from_user=...` Telethon обычно уже ограничивает сообщения.
    # Но в некоторых типах чатов/сообщений `sender_id` может быть `None`,
    # поэтому сравнение делаем только когда значение есть.
    if msg.sender_id is not None and msg.sender_id != me_id:
        return False

    if min_date is not None:
        msg_date = msg.date
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        else:
            msg_date = msg_date.astimezone(timezone.utc)
        if msg_date < min_date:
            return False

    if msg.fwd_from and not settings.delete_forwards:
        return False

    has_media = bool(msg.media)
    is_text = bool(msg.message)

    if has_media and not settings.delete_media:
        return False
    if is_text and not settings.delete_text:
        return False

    return True


async def delete_my_messages(settings: Settings, state_path: Optional[str] = None) -> None:
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.start()

    me = await client.get_me()
    my_id = me.id

    print(f"Вошли как: {me.first_name} (id={my_id})")
    append_log(settings, f"Запуск. Пользователь: {me.first_name} ({my_id}), dry_run={settings.dry_run}")

    min_date: Optional[datetime] = None
    if settings.min_date_days_ago is not None:
        min_date = datetime.now(timezone.utc) - timedelta(days=settings.min_date_days_ago)
        print(f"Будут затронуты сообщения новее: {min_date}")

    total_deleted = 0
    total_candidates = 0

    delay = settings.base_delay_sec

    total_dialogs = 0
    eligible_dialogs = 0
    debug_samples = []
    chat_index = 0

    async for dialog in client.iter_dialogs():
        total_dialogs += 1
        entity = dialog.entity

        if len(debug_samples) < 10:
            debug_samples.append(
                {
                    "title": getattr(dialog, "name", None) or getattr(dialog, "title", None),
                    "id": getattr(dialog, "id", None),
                    "is_group": getattr(dialog, "is_group", None),
                    "is_channel": getattr(dialog, "is_channel", None),
                    "entity_type": type(entity).__name__,
                }
            )

        # Telethon по-разному типизирует input_entity/peer объекты.
        # Поэтому используем флаги dialog, чтобы не отфильтровать все диалоги.
        if not (getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False)):
            continue
        eligible_dialogs += 1

        chat_id = dialog.id

        if settings.include_chats is not None and chat_id not in settings.include_chats:
            continue
        if settings.exclude_chats is not None and chat_id in settings.exclude_chats:
            continue

        title = getattr(dialog, "name", None) or getattr(dialog, "title", None) or ""
        if settings.exclude_chat_titles is not None and title.casefold() in settings.exclude_chat_titles:
            continue

        chat_index += 1
        print(f"\nЧат #{chat_index}: {title} (id={chat_id})")
        append_log(settings, f"Обработка чата: {title} (id={chat_id})")

        candidates: List[int] = []

        # Важно: используем числовой id вместо строки "me",
        # так Telethon надежнее возвращает отправленные нами сообщения.
        async for msg in client.iter_messages(entity, from_user=me):
            if message_passes_filters(msg, my_id, settings, min_date):
                candidates.append(msg.id)

        candidates_count = len(candidates)
        total_candidates += candidates_count
        print(f"Найдено подходящих сообщений: {candidates_count}")
        append_log(settings, f"Чат {title}: найдено кандидатов {candidates_count}")

        chat_had_error = False
        if not candidates_count:
            continue

        if settings.dry_run:
            print("DRY-RUN: удаление не выполняется.")
            continue

        candidates.sort()

        deleted_in_chat = 0
        for i in range(0, candidates_count, settings.batch_size):
            batch = candidates[i : i + settings.batch_size]
            try:
                await client.delete_messages(entity, batch)
                deleted_in_chat += len(batch)
                total_deleted += len(batch)
                await asyncio.sleep(delay)
            except FloodWaitError as e:
                print(f"FloodWait: пауза {e.seconds} секунд...")
                append_log(settings, f"FloodWait в чате {title}: {e.seconds} секунд")
                # Не блокируем event-loop, чтобы Telethon мог корректно обслуживать I/O.
                await asyncio.sleep(e.seconds)
                delay = min(delay * 2, settings.max_delay_sec)
            except Exception as e:
                print(f"Ошибка при удалении в чате {title}: {e}")
                append_log(settings, f"Ошибка при удалении в чате {title}: {e}")
                chat_had_error = True

        print(f"Удалено сообщений в чате '{title}': {deleted_in_chat}")
        append_log(settings, f"Чат {title}: удалено {deleted_in_chat}")

    await client.disconnect()

    print("\n=== Итог ===")
    print(f"Диалогов обработано: {total_dialogs}, групп/каналов: {eligible_dialogs}")
    print(f"Всего подходящих сообщений: {total_candidates}")
    if eligible_dialogs == 0:
        print("Похоже, фильтр групп/каналов отфильтровал все диалоги. Примеры:")
        for s in debug_samples:
            print(
                f"- {s['title']} (id={s['id']}), is_group={s['is_group']}, is_channel={s['is_channel']}, entity_type={s['entity_type']}"
            )
    if settings.dry_run:
        print("Это был DRY-RUN, ничего не удалено. Измени 'dry_run' в config.json на false для реального удаления.")
    else:
        print(f"Всего удалено сообщений: {total_deleted}")

    append_log(
        settings,
        f"Завершение. Кандидатов: {total_candidates}, удалено: {total_deleted}, dry_run={settings.dry_run}",
    )


def run_from_config(
    config_dir: str = ".",
    dry_run_override: Optional[bool] = None,
    resume: bool = True,
    reset_state: bool = False,
    state_path: Optional[str] = None,
    assume_yes: bool = False,
) -> None:
    settings = load_settings(config_dir=config_dir)

    # CLI переопределения
    if dry_run_override is not None:
        settings.dry_run = dry_run_override

    resolved_state_path = _state_path(config_dir, state_path)

    print("Настройки загружены:")
    print(f"  dry_run: {settings.dry_run}")
    print(f"  min_date_days_ago: {settings.min_date_days_ago}")
    print(f"  include_chats: {settings.include_chats}")
    print(f"  exclude_chats: {settings.exclude_chats}")
    print(f"  resume: {resume}")

    if not assume_yes:
        answer = input("Продолжить с этими настройками? [y/N]: ").strip().lower()
        if answer not in ("y", "yes", "д", "да"):
            print("Отменено пользователем.")
            return

    # Сброс state при необходимости (например, если нужно заново пройти все чаты).
    # Делаем это только после подтверждения, чтобы не потерять прогресс при отмене.
    if reset_state or not resume:
        reset_state_file(resolved_state_path)

    asyncio.run(delete_my_messages(settings, state_path=resolved_state_path))

