import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Set, Dict

from telethon import TelegramClient
from telethon.tl.types import User, Message, PeerChannel, PeerChat, PeerUser

from .core import load_settings, Settings


@dataclass
class MessageData:
    date: datetime
    author_name: str
    text: str
    is_reply: bool = False
    reply_to_msg_id: Optional[int] = None
    original_msg: Optional['MessageData'] = None


class ExportStateManager:
    def __init__(self, state_file: str = "export_state.json"):
        self.state_file = state_file
        self.state: Dict[str, Dict[str, int]] = self._load()

    def _load(self) -> Dict[str, Dict[str, int]]:
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

    def get_last_msg_id(self, user_id: int, chat_id: int) -> int:
        u_id = str(user_id)
        c_id = str(chat_id)
        return self.state.get(u_id, {}).get(c_id, 0)

    def update_last_msg_id(self, user_id: int, chat_id: int, msg_id: int):
        u_id = str(user_id)
        c_id = str(chat_id)
        if u_id not in self.state:
            self.state[u_id] = {}
        
        # Обновляем только если новый msg_id больше старого
        current = self.state[u_id].get(c_id, 0)
        if msg_id > current:
            self.state[u_id][c_id] = msg_id
            self._save()


def clean_filename(name: str) -> str:
    """Удаляет запрещенные символы для создания безопасного имени файла."""
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return safe_name.strip()


def _get_author_name(sender) -> str:
    if isinstance(sender, User):
        name_parts = filter(None, [sender.first_name, sender.last_name])
        return " ".join(name_parts) or sender.username or f"User_{sender.id}"
    elif sender:
        return getattr(sender, 'title', 'Unknown Chat')
    return "Unknown"


async def fetch_original_message(client: TelegramClient, entity, msg_id: int) -> MessageData:
    try:
        orig = await client.get_messages(entity, ids=msg_id)
        if not orig or not hasattr(orig, "date"):
            return MessageData(
                date=datetime.now(), 
                author_name="Unknown", 
                text="(сообщение недоступно)"
            )
            
        sender = await orig.get_sender()
        return MessageData(
            date=orig.date,
            author_name=_get_author_name(sender),
            text=orig.raw_text or "(медиа/пустое сообщение)",
        )
    except Exception as e:
         return MessageData(
            date=datetime.now(), 
            author_name="Unknown", 
            text="(сообщение недоступно / ошибка загрузки)"
        )


async def process_message(client: TelegramClient, entity, msg: Message, target_author_name: str) -> MessageData:
    is_reply = bool(msg.reply_to)
    reply_to_id = msg.reply_to.reply_to_msg_id if is_reply else None
    
    text = msg.raw_text or "(медиа/пустое сообщение)"
    
    msg_data = MessageData(
        date=msg.date,
        author_name=target_author_name,
        text=text,
        is_reply=is_reply,
        reply_to_msg_id=reply_to_id
    )

    if is_reply and reply_to_id:
        msg_data.original_msg = await fetch_original_message(client, entity, reply_to_id)
        await asyncio.sleep(0.1)
        
    return msg_data


def format_export_block(msg_data: MessageData) -> str:
    lines = []
    
    if msg_data.is_reply and msg_data.original_msg:
        orig = msg_data.original_msg
        orig_dt = orig.date.strftime("%Y-%m-%d][%H:%M:%S")
        lines.append(f"[{orig_dt}] <{orig.author_name}>:")
        lines.append(orig.text)
        lines.append("")
        
    reply_dt = msg_data.date.strftime("%Y-%m-%d][%H:%M:%S")
    lines.append(f"[{reply_dt}] <{msg_data.author_name}>:")
    lines.append(msg_data.text)
    
    return "\n".join(lines)


def _get_chat_id(entity) -> int:
    """Безопасное получение ID из разных объектов Telethon"""
    if hasattr(entity, 'id'):
        return entity.id
    return 0


async def _run_export_in_chat(
    client: TelegramClient, 
    entity, 
    target_user, 
    target_author_name: str, 
    file_obj, 
    state_manager: ExportStateManager
):
    chat_title = getattr(entity, 'title', getattr(entity, 'id', 'Unknown'))
    chat_id = _get_chat_id(entity)
    user_id = target_user.id
    
    last_msg_id = state_manager.get_last_msg_id(user_id, chat_id)
    print(f"Поиск в чате: {chat_title}")
    if last_msg_id > 0:
        print(f"  (Продолжаем с message_id > {last_msg_id})")
        
    count = 0
    highest_msg_id = last_msg_id

    # reverse=True + min_id fetches newly written messages incrementally
    kwargs = {"from_user": target_user, "reverse": True}
    if last_msg_id > 0:
        kwargs["min_id"] = last_msg_id

    async for msg in client.iter_messages(entity, **kwargs):
        if not msg.date:
            continue
            
        data = await process_message(client, entity, msg, target_author_name)
        block = format_export_block(data)
        
        file_obj.write(block)
        file_obj.write("\n\n" + "-" * 40 + "\n\n")
        file_obj.flush()
        
        count += 1
        if msg.id > highest_msg_id:
            highest_msg_id = msg.id
            
        if count % 50 == 0:
            print(f"  ... найдено и выгружено {count} новых сообщений (последний ID: {highest_msg_id})")

    # Сохраняем прогресс после завершения обработки чата
    if highest_msg_id > last_msg_id:
        state_manager.update_last_msg_id(user_id, chat_id, highest_msg_id)
            
    print(f"  Готово для этого чата. Найдено новых: {count}")
    return count


async def export_messages_async(settings: Settings, target_user_identifier: str, chat_identifier: Optional[str], output_file: Optional[str]):
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.start()

    try:
        try:
           target_user_id = int(target_user_identifier)
           target_user = await client.get_entity(target_user_id)
        except ValueError:
           target_user = await client.get_entity(target_user_identifier)
           
        target_author_name = _get_author_name(target_user)
        print(f"Пользователь для экспорта: {target_author_name} (ID: {target_user.id})")
    except Exception as e:
        print(f"Ошибка при поиске пользователя (проверьте ID/юзернейм): {e}")
        await client.disconnect()
        return

    export_dir = "EXPORTED_USRS"
    os.makedirs(export_dir, exist_ok=True)

    # Автогенерация названия файла, если не передано
    if not output_file:
        safe_name = clean_filename(target_author_name)
        output_file = os.path.join(export_dir, f"Экспорт_{safe_name}_{target_user.id}.txt")
    else:
        # Если юзер указал свое имя файла, кладем его тоже в папку, если путь не абсолютный
        if not os.path.dirname(output_file) and not os.path.isabs(output_file):
            output_file = os.path.join(export_dir, output_file)
        
    print(f"Файл выгрузки: {output_file}")

    dialogs_to_check = []
    if chat_identifier:
        try:
             try:
                 c_id = int(chat_identifier)
                 chat_entity = await client.get_entity(c_id)
             except ValueError:
                 chat_entity = await client.get_entity(chat_identifier)
             dialogs_to_check.append(chat_entity)
        except Exception as e:
             print(f"Ошибка получения чата: {e}")
             await client.disconnect()
             return
    else:
        print("Собираем список всех групп/каналов...")
        async for dialog in client.iter_dialogs():
            if getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False):
                dialogs_to_check.append(dialog.entity)

    print(f"Количество чатов для проверки: {len(dialogs_to_check)}")
    
    state_manager = ExportStateManager(os.path.join(settings.config_dir, "export_state.json"))
    total_messages = 0
    
    # Открываем в 'a' (append) для дозаписи новых сообщений в конец файла
    with open(output_file, "a", encoding="utf-8") as file_obj:
        for chat_entity in dialogs_to_check:
            try:
                found = await _run_export_in_chat(client, chat_entity, target_user, target_author_name, file_obj, state_manager)
                total_messages += found
            except Exception as e:
                print(f"Пропуск чата (возможно, нет прав или другая ошибка): {e}")
                
    print(f"\nВыгрузка завершена! Всего НОВЫХ сообщений экспортировано: {total_messages}")

    await client.disconnect()


def run_export(config_dir: str, target_user: str, chat_id: Optional[str], output_file: Optional[str]):
    settings = load_settings(config_dir=config_dir)
    asyncio.run(export_messages_async(settings, target_user, chat_id, output_file))
