import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Set, Dict, Tuple

from telethon import TelegramClient
from telethon.tl.types import User, Message

from .core import load_settings, Settings


@dataclass
class MessageData:
    date: datetime
    author_name: str
    author_id: int
    author_username: Optional[str]
    text: str
    is_reply: bool = False
    reply_to_msg_id: Optional[int] = None
    original_msg: Optional['MessageData'] = None


class ExportStateManager:
    def __init__(self, state_file: str = "export_state.json"):
        self.state_file = state_file
        self.state: Dict[str, Dict[str, any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, any]]:
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
        
        current = self.state[u_id].get(c_id, 0)
        if isinstance(current, int) and msg_id > current:
            self.state[u_id][c_id] = msg_id
            self._save()
            
    def get_nicknames(self, user_id: int) -> List[str]:
        u_id = str(user_id)
        return self.state.get(u_id, {}).get("__nicknames__", [])
        
    def add_nickname(self, user_id: int, nickname: str) -> bool:
        """Returns True if the nickname was newly added (i.e. name changed)."""
        u_id = str(user_id)
        if u_id not in self.state:
            self.state[u_id] = {}
            
        nicks = self.state[u_id].get("__nicknames__", [])
        if nickname not in nicks:
            nicks.append(nickname)
            self.state[u_id]["__nicknames__"] = nicks
            self._save()
            return True
        return False


def clean_filename(name: str) -> str:
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return safe_name.strip()


def _get_author_info(sender) -> tuple[str, int, Optional[str]]:
    if isinstance(sender, User):
        name_parts = filter(None, [sender.first_name, sender.last_name])
        name = " ".join(name_parts) or sender.username or f"User_{sender.id}"
        return (name, sender.id, sender.username)
    elif sender:
        name = getattr(sender, 'title', 'Unknown Chat')
        uid = getattr(sender, 'id', 0)
        uname = getattr(sender, 'username', None)
        return (name, uid, uname)
    return ("Unknown", 0, None)


async def fetch_original_message(client: TelegramClient, entity, msg_id: int) -> MessageData:
    try:
        orig = await client.get_messages(entity, ids=msg_id)
        if not orig or not hasattr(orig, "date"):
            return MessageData(
                date=datetime.now(), 
                author_name="Unknown", 
                author_id=0,
                author_username=None,
                text="(сообщение недоступно)"
            )
            
        sender = await orig.get_sender()
        name, uid, uname = _get_author_info(sender)
        return MessageData(
            date=orig.date,
            author_name=name,
            author_id=uid,
            author_username=uname,
            text=orig.raw_text or "(медиа/пустое сообщение)",
        )
    except Exception as e:
         return MessageData(
            date=datetime.now(), 
            author_name="Unknown", 
            author_id=0,
            author_username=None,
            text="(сообщение недоступно / ошибка загрузки)"
        )


async def process_message(client: TelegramClient, entity, msg: Message, target_author_name: str, target_author_id: int, target_author_username: Optional[str]) -> MessageData:
    is_reply = bool(msg.reply_to)
    reply_to_id = msg.reply_to.reply_to_msg_id if is_reply else None
    
    text = msg.raw_text or "(медиа/пустое сообщение)"
    
    msg_data = MessageData(
        date=msg.date,
        author_name=target_author_name,
        author_id=target_author_id,
        author_username=target_author_username,
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
    
    def format_header(dt: datetime, name: str, uid: int, uname: Optional[str]) -> str:
        dt_str = dt.strftime("%Y-%m-%d][%H:%M")
        uname_str = f"@{uname}" if uname else "null"
        return f"[{dt_str}] <{name}> (ID: {uid}, username: {uname_str}):"
    
    if msg_data.is_reply and msg_data.original_msg:
        orig = msg_data.original_msg
        lines.append(format_header(orig.date, orig.author_name, orig.author_id, orig.author_username))
        lines.append(orig.text)
        lines.append("")
        
    lines.append(format_header(msg_data.date, msg_data.author_name, msg_data.author_id, msg_data.author_username))
    lines.append(msg_data.text)
    
    return "\n".join(lines)


def _get_chat_id(entity) -> int:
    if hasattr(entity, 'id'):
        return entity.id
    return 0


async def _run_export_in_chat(
    client: TelegramClient, 
    entity, 
    target_user, 
    target_author_name: str, 
    target_author_id: int,
    target_author_username: Optional[str],
    file_obj, 
    state_manager: ExportStateManager,
    file_lock: Optional[asyncio.Lock] = None
) -> Tuple[int, Optional[datetime], int]:
    chat_title = getattr(entity, 'title', getattr(entity, 'id', 'Unknown'))
    chat_id = _get_chat_id(entity)
    user_id = target_user.id
    
    last_msg_id = state_manager.get_last_msg_id(user_id, chat_id)
        
    count = 0
    highest_msg_id = last_msg_id
    latest_date = None

    kwargs = {"from_user": target_user, "reverse": True}
    if last_msg_id > 0:
        kwargs["min_id"] = last_msg_id

    messages_chunk = []

    async def process_and_flush_chunk():
        nonlocal count
        if not messages_chunk:
            return
            
        reply_ids = list({m.reply_to.reply_to_msg_id for m in messages_chunk if m.reply_to and m.reply_to.reply_to_msg_id})
        original_msgs_dict = {}
        
        if reply_ids:
            try:
                for i in range(0, len(reply_ids), 100):
                    batch_ids = reply_ids[i:i+100]
                    orig_msgs = await client.get_messages(entity, ids=batch_ids)
                    if orig_msgs:
                        if not isinstance(orig_msgs, list):
                            orig_msgs = [orig_msgs]
                        for m in orig_msgs:
                            if m and getattr(m, 'id', None):
                                original_msgs_dict[m.id] = m
            except Exception:
                pass
                
        blocks_to_write = []
        for msg in messages_chunk:
            is_reply = bool(msg.reply_to)
            reply_to_id = msg.reply_to.reply_to_msg_id if is_reply else None
            text = msg.raw_text or "(медиа/пустое сообщение)"
            
            msg_data = MessageData(
                date=msg.date,
                author_name=target_author_name,
                author_id=target_author_id,
                author_username=target_author_username,
                text=text,
                is_reply=is_reply,
                reply_to_msg_id=reply_to_id
            )
            
            if is_reply and reply_to_id:
                orig_msg_obj = original_msgs_dict.get(reply_to_id)
                if orig_msg_obj and getattr(orig_msg_obj, "date", None):
                    try:
                        sender = await orig_msg_obj.get_sender()
                        name, uid, uname = _get_author_info(sender)
                        msg_data.original_msg = MessageData(
                            date=orig_msg_obj.date,
                            author_name=name,
                            author_id=uid,
                            author_username=uname,
                            text=orig_msg_obj.raw_text or "(медиа/пустое сообщение)"
                        )
                    except Exception:
                        msg_data.original_msg = MessageData(
                            date=orig_msg_obj.date,
                            author_name="Unknown",
                            author_id=0,
                            author_username=None,
                            text="(ошибка загрузки профиля)"
                        )
                else:
                    msg_data.original_msg = MessageData(
                        date=datetime.now(), 
                        author_name="Unknown", 
                        author_id=0,
                        author_username=None,
                        text="(сообщение недоступно/ошибка загрузки)"
                    )

            blocks_to_write.append(format_export_block(msg_data))
            
        text_to_write = ""
        for block in blocks_to_write:
            text_to_write += block + "\n\n" + "-" * 40 + "\n\n"
            
        if file_lock:
            async with file_lock:
                file_obj.write(text_to_write)
                file_obj.flush()
        else:
            file_obj.write(text_to_write)
            file_obj.flush()
            
        count += len(messages_chunk)
        if count % 200 == 0:
            print(f"  ... [Чат: {str(chat_title)[:15]}] экспортировано {count} сообщений")
        messages_chunk.clear()

    async for msg in client.iter_messages(entity, **kwargs):
        if not msg.date:
            continue
            
        messages_chunk.append(msg)
        if msg.id > highest_msg_id:
            highest_msg_id = msg.id
        if latest_date is None or msg.date > latest_date:
            latest_date = msg.date
            
        if len(messages_chunk) >= 100:
            await process_and_flush_chunk()

    if messages_chunk:
        await process_and_flush_chunk()
            
    return count, latest_date, highest_msg_id


def update_export_file_header(filepath: str, nicknames: List[str]):
    """Добавляет или обновляет историю никнеймов в начале файла."""
    if not os.path.exists(filepath):
        return

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Ищем, была ли уже шапка. Если да - удаляем старую.
    header_start = -1
    header_end = -1
    for i, line in enumerate(lines[:20]):
        if line.startswith("=== ИСТОРИЯ НИКНЕЙМОВ ==="):
            header_start = i
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() == "=========================":
                    header_end = j
                    break
            break

    if header_start != -1 and header_end != -1:
        del lines[header_start:header_end+1]
        if len(lines) > header_start and lines[header_start].strip() == "":
            del lines[header_start]

    # Формируем новую шапку
    new_header = [
        "=== ИСТОРИЯ НИКНЕЙМОВ ===\n",
        f"Зафиксированные никнеймы: {', '.join(nicknames)}\n",
        "=========================\n\n"
    ]
    
    lines = new_header + lines
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)


async def _get_all_dialogs(client: TelegramClient) -> list:
    dialogs = []
    async for dialog in client.iter_dialogs():
        if getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False):
            dialogs.append(dialog.entity)
    return dialogs


async def export_messages_async(settings: Settings, target_user_identifier: str, chat_identifier: Optional[str], output_file: Optional[str]):
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.start()

    try:
        try:
           target_user_id = int(target_user_identifier)
           target_user = await client.get_entity(target_user_id)
        except ValueError:
           target_user = await client.get_entity(target_user_identifier)
           
        target_author_name, target_author_id, target_author_uname = _get_author_info(target_user)
        print(f"Пользователь для экспорта: {target_author_name} (ID: {target_user.id})")
    except Exception as e:
        print(f"Ошибка при поиске пользователя (проверьте ID/юзернейм): {e}")
        await client.disconnect()
        return

    export_dir = "EXPORTED_USRS"
    os.makedirs(export_dir, exist_ok=True)

    if not output_file:
        safe_name = clean_filename(target_author_name)
        output_file = os.path.join(export_dir, f"Экспорт_{safe_name}_{target_user.id}.txt")
    else:
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
        dialogs_to_check = await _get_all_dialogs(client)

    print(f"Количество чатов для проверки: {len(dialogs_to_check)}")
    
    state_manager = ExportStateManager(os.path.join(settings.config_dir, "export_state.json"))
    
    nick_changed = state_manager.add_nickname(target_author_id, target_author_name)
    nicks = state_manager.get_nicknames(target_author_id)
    if nick_changed or (os.path.exists(output_file) and len(nicks) > 1):
        update_export_file_header(output_file, nicks)

    total_messages = 0
    file_lock = asyncio.Lock()
    sem = asyncio.Semaphore(10)
    
    with open(output_file, "a", encoding="utf-8") as file_obj:
        print("Начинаем параллельный поиск по чатам...")
        async def process_chat(chat_entity):
            async with sem:
                try:
                    chat_id = _get_chat_id(chat_entity)
                    found, latest_date, highest_id = await _run_export_in_chat(
                        client, chat_entity, target_user, target_author_name, 
                        target_author_id, target_author_uname, file_obj, 
                        state_manager, file_lock
                    )
                    return chat_id, found, latest_date, highest_id
                except Exception:
                    return None, 0, None, 0
                    
        tasks = [process_chat(chat) for chat in dialogs_to_check]
        results = await asyncio.gather(*tasks)
        
        for chat_id, found, _, highest_id in results:
            if chat_id is not None and highest_id > 0:
                state_manager.update_last_msg_id(target_user.id, chat_id, highest_id)
            total_messages += found
                
    print(f"\nВыгрузка завершена! Всего НОВЫХ сообщений экспортировано: {total_messages}")
    await client.disconnect()


async def export_update_async(settings: Settings):
    export_dir = "EXPORTED_USRS"
    if not os.path.exists(export_dir):
        print("Папка EXPORTED_USRS не найдена. Нечего обновлять.")
        return

    user_files = {} 
    for filename in os.listdir(export_dir):
        if not filename.endswith(".txt") or filename == "changelog.txt":
            continue
        
        match = re.search(r'_(\d+)\.txt$', filename)
        if match:
            u_id = int(match.group(1))
            user_files[u_id] = os.path.join(export_dir, filename)

    if not user_files:
        print("В папке EXPORTED_USRS нет подходящих файлов формата _ID.txt для обновления.")
        return

    print(f"Найдено {len(user_files)} пользователей для массового обновления.")
    
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await client.start()
    
    print("Собираем список всех групп/каналов один раз...")
    dialogs_to_check = await _get_all_dialogs(client)
    print(f"Количество чатов для проверки: {len(dialogs_to_check)}\n")

    state_manager = ExportStateManager(os.path.join(settings.config_dir, "export_state.json"))
    changelog_lines = []

    for target_user_id, output_file in user_files.items():
        try:
            target_user = await client.get_entity(target_user_id)
            target_author_name, target_author_id, target_author_uname = _get_author_info(target_user)
        except Exception as e:
            print(f"Ошибка получения юзера с ID {target_user_id}. Пропуск.")
            continue

        print(f"Обновляем пользователя: {target_author_name} (ID: {target_user_id})")
        
        nick_changed = state_manager.add_nickname(target_author_id, target_author_name)
        nicks = state_manager.get_nicknames(target_author_id)
        if nick_changed or len(nicks) > 1:
            update_export_file_header(output_file, nicks)

        total_new_msgs = 0
        latest_overall_date = None
        file_lock = asyncio.Lock()
        sem = asyncio.Semaphore(10)
        
        with open(output_file, "a", encoding="utf-8") as file_obj:
            async def process_chat(chat_entity):
                async with sem:
                    try:
                        chat_id = _get_chat_id(chat_entity)
                        found, latest_date, highest_id = await _run_export_in_chat(
                            client, chat_entity, target_user, target_author_name, 
                            target_author_id, target_author_uname, file_obj, 
                            state_manager, file_lock
                        )
                        return chat_id, found, latest_date, highest_id
                    except Exception:
                        return None, 0, None, 0

            tasks = [process_chat(chat) for chat in dialogs_to_check]
            results = await asyncio.gather(*tasks)
            
            for chat_id, found, latest_date, highest_id in results:
                if chat_id is not None and highest_id > 0:
                    state_manager.update_last_msg_id(target_user.id, chat_id, highest_id)
                total_new_msgs += found
                if latest_date:
                    if latest_overall_date is None or latest_date > latest_overall_date:
                        latest_overall_date = latest_date
        
        print(f"    Завершено. Новых сообщений для {target_author_name}: {total_new_msgs}")
        
        if total_new_msgs > 0 or nick_changed:
            u_str = f"@{target_author_uname}" if target_author_uname else "null"
            log_block = [f"{target_author_name} (ID: {target_user_id}, username: {u_str}):"]
            if nick_changed:
                log_block.append(f"  [!] Пользователь сменил никнейм на: {target_author_name}")
            if total_new_msgs > 0:
                log_block.append(f"  Новых сообщений: {total_new_msgs}")
                if latest_overall_date:
                    dt_str = latest_overall_date.strftime("%Y-%m-%d][%H:%M")
                    log_block.append(f"  Дата последнего сообщения: [{dt_str}]")
            log_block.append("")
            changelog_lines.extend(log_block)

    if changelog_lines:
        changelog_path = os.path.join(export_dir, "changelog.txt")
        now_str = datetime.now().strftime("%Y-%m-%d][%H:%M:%S")
        with open(changelog_path, "a", encoding="utf-8") as f:
            f.write(f"--- ОБНОВЛЕНИЕ ОТ {now_str} ---\n")
            f.write("\n".join(changelog_lines))
            f.write("\n")
        print(f"\nЗапись в changelog.txt выполнена.")
    else:
        print("\nНет новых сообщений или изменений никнеймов ни по одному пользователю. Changelog не записывался.")

    await client.disconnect()


def run_export(config_dir: str, target_user: str, chat_id: Optional[str], output_file: Optional[str]):
    settings = load_settings(config_dir=config_dir)
    asyncio.run(export_messages_async(settings, target_user, chat_id, output_file))

def run_export_update(config_dir: str):
    settings = load_settings(config_dir=config_dir)
    asyncio.run(export_update_async(settings))
