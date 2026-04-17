import asyncio
import json
import os
import re
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Tuple

from telethon import TelegramClient
from telethon.tl.types import (
    User, Message,
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeAudio, DocumentAttributeVideo,
    DocumentAttributeAnimated, DocumentAttributeFilename,
)

from .core import load_settings, Settings

# ────────────────────────────────────────────
# Константы
# ────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 МБ
MEDIA_DOWNLOAD_SEMAPHORE = 3            # макс. параллельных загрузок
MEDIA_JITTER_MIN = 0.5                  # мин. пауза между стартами загрузок (сек)
MEDIA_JITTER_MAX = 1.5                  # макс. пауза между стартами загрузок (сек)
PM_STATE_FILE = "pm_export_state.json"
BASE_DIR = "PRIVAT_DIALOGS"

# Расширения по умолчанию для каждой категории, если Telethon не вернёт своё
DEFAULT_EXTENSIONS = {
    "photos": ".jpg",
    "videos": ".mp4",
    "video_notes": ".mp4",
    "voices": ".ogg",
    "gifs": ".mp4",
    "documents": ".bin",
}


# ────────────────────────────────────────────
# Стейт-менеджер (инкрементальное обновление)
# ────────────────────────────────────────────
class PMStateManager:
    """Хранит ID последнего обработанного сообщения для каждого приватного диалога."""

    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state: Dict[str, int] = self._load()

    def _load(self) -> Dict[str, int]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def get_last_msg_id(self, user_id: int) -> int:
        return self.state.get(str(user_id), 0)

    def update_last_msg_id(self, user_id: int, msg_id: int):
        key = str(user_id)
        if msg_id > self.state.get(key, 0):
            self.state[key] = msg_id
            self._save()


# ────────────────────────────────────────────
# Хелперы
# ────────────────────────────────────────────
def _safe_name(text: str) -> str:
    """Убирает недопустимые символы из имени файла/папки."""
    return re.sub(r'[\\/*?:"<>|]', '_', text).strip()


def _build_user_folder_name(user: User) -> str:
    """
    Формат: Имя Фамилия_@username_+phone_ID
    Пропускает блоки, которых нет (скрытый телефон, отсутствие юзернейма и пр.).
    """
    parts = []

    # Имя
    name_parts = list(filter(None, [user.first_name, user.last_name]))
    name = " ".join(name_parts) if name_parts else f"User_{user.id}"
    parts.append(_safe_name(name))

    # Юзернейм
    if user.username:
        parts.append(f"@{user.username}")

    # Телефон
    if user.phone:
        parts.append(f"+{user.phone}")

    # ID (всегда)
    parts.append(str(user.id))

    return "_".join(parts)


def _classify_media(msg: Message) -> Optional[str]:
    """
    Определяет тип медиа в сообщении. Возвращает имя подпапки или None.
    Порядок проверки критичен: video_note и voice — частные случаи Document.
    """
    if msg.voice:
        return "voices"
    if msg.video_note:
        return "video_notes"
    if msg.gif:
        return "gifs"
    if msg.video:
        return "videos"
    if msg.photo:
        return "photos"
    # Остальные документы (PDF, ZIP, и т.д.)
    if msg.document:
        return "documents"
    return None


def _get_file_extension(msg: Message, category: str) -> str:
    """Получение расширения файла из атрибутов Telethon или значения по умолчанию."""
    if msg.file and msg.file.ext:
        return msg.file.ext
    # Попробуем вытащить из имени файла в атрибутах
    if msg.document:
        for attr in msg.document.attributes:
            if isinstance(attr, DocumentAttributeFilename) and "." in attr.file_name:
                return os.path.splitext(attr.file_name)[1]
    return DEFAULT_EXTENSIONS.get(category, ".bin")


def _get_file_size(msg: Message) -> int:
    """Получение размера файла в байтах. Для фото — всегда 0 (качаем без ограничений)."""
    if msg.photo:
        return 0  # Фото весят мало, не ограничиваем
    if msg.file and msg.file.size:
        return msg.file.size
    return 0


def _get_file_unique_id(msg: Message) -> Optional[str]:
    """
    Извлекает file_unique_id из медиа сообщения.
    Этот ID одинаков для абсолютно идентичных файлов (одна и та же GIF, отправленная 50 раз).
    """
    if msg.photo:
        # У фото уникальный ID хранится в последнем (самом большом) размере
        if hasattr(msg.photo, 'id'):
            return f"photo_{msg.photo.id}"
    if msg.document:
        if hasattr(msg.document, 'id'):
            return f"doc_{msg.document.id}"
    return None


def _build_media_filename(msg: Message, category: str) -> str:
    """
    Формат: YYYY-MM-DD_HH-MM_msgID.ext
    Например: 2026-04-17_14-25_msg8841.jpg
    """
    dt = msg.date
    date_str = dt.strftime("%Y-%m-%d_%H-%M")
    ext = _get_file_extension(msg, category)
    return f"{date_str}_msg{msg.id}{ext}"


def _human_size(size_bytes: int) -> str:
    """Красивый вывод размера файла."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"


def _media_label(category: str) -> str:
    """Человекочитаемое описание категории для лога."""
    labels = {
        "photos": "фото",
        "videos": "видео",
        "video_notes": "видеосообщение (кружок)",
        "voices": "голосовое сообщение",
        "gifs": "GIF-анимация",
        "documents": "документ",
    }
    return labels.get(category, "медиа")


# ────────────────────────────────────────────
# Форматирование текстового лога
# ────────────────────────────────────────────
def _format_log_line(msg: Message, sender_name: str, sender_id: int, 
                     sender_username: Optional[str], media_note: Optional[str] = None) -> str:
    """Форматирование одной записи в chat_log.txt."""
    dt_str = msg.date.strftime("%Y-%m-%d][%H:%M")
    uname = f"@{sender_username}" if sender_username else "null"
    header = f"[{dt_str}] <{sender_name}> (ID: {sender_id}, username: {uname}):"
    
    text = msg.raw_text or ""
    lines = [header]
    
    if media_note:
        lines.append(media_note)
    if text:
        lines.append(text)
    if not text and not media_note:
        lines.append("(пустое сообщение)")
    
    return "\n".join(lines)


# ────────────────────────────────────────────
# Основная логика экспорта
# ────────────────────────────────────────────
async def export_pm_async(
    settings: Settings,
    target_user_identifier: str,
    max_file_size: int = MAX_FILE_SIZE_BYTES,
):
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.start()
    me = await client.get_me()

    # ── Резолвим целевого пользователя ──
    try:
        try:
            uid = int(target_user_identifier)
            target_user = await client.get_entity(uid)
        except ValueError:
            target_user = await client.get_entity(target_user_identifier)

        if not isinstance(target_user, User):
            print("⚠️  Указанный ID принадлежит группе, а не пользователю. Для групп используйте команду export.")
            await client.disconnect()
            return
    except Exception as e:
        print(f"⚠️  Ошибка при поиске пользователя: {e}")
        await client.disconnect()
        return

    # ── Строим красивое имя папки ──
    folder_name = _build_user_folder_name(target_user)
    user_dir = os.path.join(BASE_DIR, folder_name)
    media_dir = os.path.join(user_dir, "media")

    # Создаём все подпапки разом
    for sub in ("photos", "videos", "video_notes", "voices", "gifs", "documents"):
        os.makedirs(os.path.join(media_dir, sub), exist_ok=True)

    chat_log_path = os.path.join(user_dir, "chat_log.txt")

    name_parts = list(filter(None, [target_user.first_name, target_user.last_name]))
    display_name = " ".join(name_parts) if name_parts else f"User_{target_user.id}"
    uname_display = f"@{target_user.username}" if target_user.username else ""
    phone_display = f"+{target_user.phone}" if target_user.phone else ""

    print(f"📁 Профиль: {display_name} {uname_display} {phone_display} (ID: {target_user.id})")
    print(f"📂 Папка выгрузки: {user_dir}")

    # ── Стейт-менеджер ──
    state_manager = PMStateManager(os.path.join(settings.config_dir, PM_STATE_FILE))
    last_msg_id = state_manager.get_last_msg_id(target_user.id)

    # Если папка была удалена пользователем — сбрасываем стейт и качаем с нуля
    if last_msg_id > 0 and not os.path.exists(chat_log_path):
        print("⚠️  Папка экспорта не найдена — сброс прогресса, качаем заново.")
        last_msg_id = 0
        state_manager.update_last_msg_id(target_user.id, 0)

    if last_msg_id > 0:
        print(f"🔄 Инкрементальный режим: докачиваем сообщения новее ID {last_msg_id}")

    # ── Итерируем сообщения (от старых к новым) ──
    kwargs = {"entity": target_user, "reverse": True}
    if last_msg_id > 0:
        kwargs["min_id"] = last_msg_id

    sem = asyncio.Semaphore(MEDIA_DOWNLOAD_SEMAPHORE)
    total_text = 0
    total_media = 0
    total_skipped = 0
    total_duplicates = 0
    highest_msg_id = last_msg_id

    # Дедупликация: file_unique_id -> относительный путь к первому скачанному экземпляру
    seen_files: Dict[str, str] = {}

    # Ставим буфер текстовых строк, чтобы сбрасывать на диск пачками
    log_buffer = []
    download_tasks = []

    async def _download_one(msg: Message, category: str, dest_path: str):
        """Загрузка одного медиафайла с задержкой‑джиттером."""
        nonlocal total_media
        async with sem:
            try:
                await client.download_media(msg, file=dest_path)
                total_media += 1
            except Exception as e:
                print(f"  ⚠️  Ошибка загрузки msg#{msg.id}: {e}")
            await asyncio.sleep(random.uniform(MEDIA_JITTER_MIN, MEDIA_JITTER_MAX))

    print("\n⏳ Сканирование приватного диалога...\n")

    async for msg in client.iter_messages(**kwargs):
        if not msg.date:
            continue

        if msg.id > highest_msg_id:
            highest_msg_id = msg.id

        # -- Определяем автора --
        if msg.sender_id == me.id:
            sender_name_parts = list(filter(None, [me.first_name, me.last_name]))
            sender_name = " ".join(sender_name_parts) if sender_name_parts else "Я"
            sender_id = me.id
            sender_uname = me.username
        else:
            sender_name = display_name
            sender_id = target_user.id
            sender_uname = target_user.username

        # -- Медиа-роутер --
        media_note = None
        category = _classify_media(msg)
        is_my_message = (msg.sender_id == me.id)

        if category and is_my_message:
            # Свои медиа не скачиваем — только помечаем в логе
            label = _media_label(category)
            media_note = f"<Ваше {label}>"
        elif category:
            file_size = _get_file_size(msg)
            if file_size > max_file_size:
                size_str = _human_size(file_size)
                media_note = f"<Файл слишком большой ({size_str}), пропущен>"
                total_skipped += 1
            else:
                # Проверка дубликатов по file_unique_id
                unique_id = _get_file_unique_id(msg)
                if unique_id and unique_id in seen_files:
                    # Дубликат — не качаем, ссылаемся на оригинал
                    original_path = seen_files[unique_id]
                    label = _media_label(category)
                    media_note = f"<Дубликат {label}, см. оригинал: {original_path}>"
                    total_duplicates += 1
                else:
                    filename = _build_media_filename(msg, category)
                    dest_path = os.path.join(media_dir, category, filename)
                    rel_path = os.path.join("media", category, filename)

                    # Запоминаем unique_id -> путь
                    if unique_id:
                        seen_files[unique_id] = rel_path

                    # Не перекачиваем уже скачанный файл
                    if not os.path.exists(dest_path):
                        download_tasks.append(
                            asyncio.create_task(_download_one(msg, category, dest_path))
                        )
                    
                    label = _media_label(category)
                    media_note = f"<Прикреплено {label}: {rel_path}>"

        # -- Форматируем текстовую строку --
        log_line = _format_log_line(msg, sender_name, sender_id, sender_uname, media_note)
        log_buffer.append(log_line)
        total_text += 1

        # Сбрасываем буфер на диск каждые 200 сообщений
        if len(log_buffer) >= 200:
            with open(chat_log_path, "a", encoding="utf-8") as f:
                for line in log_buffer:
                    f.write(line + "\n\n" + "-" * 40 + "\n\n")
            log_buffer.clear()
            print(f"  ... обработано {total_text} сообщений, медиа в очереди: {len(download_tasks)}")

    # -- Дописываем остаток буфера --
    if log_buffer:
        with open(chat_log_path, "a", encoding="utf-8") as f:
            for line in log_buffer:
                f.write(line + "\n\n" + "-" * 40 + "\n\n")
        log_buffer.clear()

    # -- Дожидаемся завершения всех загрузок медиа --
    if download_tasks:
        print(f"\n📥 Загрузка {len(download_tasks)} медиафайлов (параллельно по {MEDIA_DOWNLOAD_SEMAPHORE})...")
        await asyncio.gather(*download_tasks)

    # -- Обновляем стейт --
    if highest_msg_id > last_msg_id:
        state_manager.update_last_msg_id(target_user.id, highest_msg_id)

    await client.disconnect()

    # -- Итоги --
    print(f"\n{'='*45}")
    print(f"✅ Экспорт приватного диалога завершён!")
    print(f"   📝 Сообщений в логе: {total_text}")
    print(f"   📥 Медиафайлов загружено: {total_media}")
    if total_duplicates:
        print(f"   ♻️  Дубликатов пропущено: {total_duplicates}")
    if total_skipped:
        print(f"   ⏭️  Пропущено (превышение {_human_size(max_file_size)}): {total_skipped}")
    print(f"   📂 Результат: {user_dir}")
    print(f"{'='*45}")


# ────────────────────────────────────────────
# Точки входа (синхронные обёртки для CLI)
# ────────────────────────────────────────────
def run_export_pm(config_dir: str, target_user: str):
    settings = load_settings(config_dir=config_dir)
    asyncio.run(export_pm_async(settings, target_user))
