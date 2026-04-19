import asyncio
import json
import os
import re
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Set, Dict, Tuple, Any

from telethon import TelegramClient, utils
from telethon.tl.types import User, Message
from telethon.errors import ChatAdminRequiredError, RPCError
from tqdm.asyncio import tqdm

from .core import load_settings, Settings, ts_print, robust_client_start
from .storage import SQLiteStorage
from .models import MessageData

MAX_MESSAGES_PER_FILE = 5000

class FileRotateWriter:
    def __init__(self, base_path: str, as_json: bool = False, max_msgs: int = MAX_MESSAGES_PER_FILE):
        self.base_path = base_path
        self.as_json = as_json
        self.max_msgs = max_msgs
        self.lock = asyncio.Lock()
        
        # Determine actual file name and initial count
        self.directory = os.path.dirname(base_path)
        self.filename = os.path.basename(base_path)
        self.name_no_ext, self.ext = os.path.splitext(self.filename)
        
        self.current_part = 1
        self.current_count = 0
        self.current_file_path = self._get_path()
        
        # If file exists, we might need to find the latest part
        self._detect_current_state()

    def _get_path(self):
        if self.current_part == 1:
            return os.path.join(self.directory, f"{self.name_no_ext}{self.ext}")
        return os.path.join(self.directory, f"{self.name_no_ext}_part{self.current_part}{self.ext}")

    def _detect_current_state(self):
        # Find the highest part number that exists
        while True:
            path = self._get_path()
            if os.path.exists(path):
                # Count messages in current file
                with open(path, "r", encoding="utf-8") as f:
                    if self.as_json:
                        self.current_count = sum(1 for _ in f)
                    else:
                        # For text, we're approximating or just continuing
                        self.current_count = 0 # Text splitting is secondary, but let's support it if asked
                
                if self.current_count >= self.max_msgs:
                    self.current_part += 1
                    continue
                break
            else:
                break
        self.current_file_path = self._get_path()

    async def write_block(self, block_text: str, msg_count: int = 1):
        async with self.lock:
            # Check for rotation
            if self.current_count + msg_count > self.max_msgs:
                self.current_part += 1
                self.current_count = 0
                self.current_file_path = self._get_path()
                ts_print(f"Файл заполнен (5000 сообщений). Переход к части {self.current_part}: {os.path.basename(self.current_file_path)}")

            with open(self.current_file_path, "a", encoding="utf-8") as f:
                f.write(block_text)
                f.flush()
            self.current_count += msg_count

# --- Helper Functions ---

def clean_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()

def _get_author_info(sender) -> tuple[str, int, Optional[str]]:
    if isinstance(sender, User):
        name = " ".join(filter(None, [sender.first_name, sender.last_name])) or sender.username or f"User_{sender.id}"
        return (name, sender.id, sender.username)
    elif sender:
        return (getattr(sender, 'title', 'Unknown'), getattr(sender, 'id', 0), getattr(sender, 'username', None))
    return ("Unknown", 0, None)

def _get_chat_id(entity) -> int:
    return getattr(entity, 'id', 0)

def format_export_block(m: MessageData, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(m.to_dict(), ensure_ascii=False)
    
    reply_str = f" (в ответ на {m.reply_to_msg_id})" if m.is_reply else ""
    fwd_str = f" [FWD from {m.fwd_from_name or m.fwd_from_id}]" if m.is_forward else ""
    media_str = f" [{m.media_type}]" if m.media_type else ""
    
    dt_str = m.date.strftime("%Y-%m-%d][%H:%M:%S")
    header = f"[{dt_str}] <{m.author_name} ({m.author_id})>{reply_str}{fwd_str}{media_str}:"
    
    lines = []
    if m.is_reply and m.original_msg:
        o = m.original_msg
        o_dt = o.date.strftime("%Y-%m-%d][%H:%M:%S")
        lines.append(f"--- Ответ на сообщение от {o.author_name} ({o_dt}) ---")
        lines.append(o.text); lines.append("---")
    
    lines.append(header); lines.append(m.text)
    return "\n".join(lines)

# Кэш для имен пользователей, чтобы не запрашивать их каждый раз через API
USER_CACHE: Dict[int, str] = {}

async def process_message(client: TelegramClient, entity, msg: Message, target_name: str = None, target_id: int = None, target_uname: str = None) -> MessageData:
    sender_id = msg.sender_id or 0
    
    # Если это наша цель, используем переданное имя
    if target_name and (sender_id == target_id or target_id is None):
        author_name = target_name
    else:
        # Если автора нет в кэше, пытаемся получить его из сообщения
        if sender_id not in USER_CACHE:
            try:
                sender = await msg.get_sender()
                name, _, _ = _get_author_info(sender)
                USER_CACHE[sender_id] = name
            except Exception:
                USER_CACHE[sender_id] = "Unknown"
        author_name = USER_CACHE.get(sender_id, "Unknown")

    text = (msg.raw_text or "").replace('\u200b', '')
    
    fwd_id = None
    if msg.forward and msg.forward.from_id:
        try: fwd_id = utils.get_peer_id(msg.forward.from_id)
        except: fwd_id = None

    m_data = MessageData(
        date=msg.date, author_name=author_name, author_id=sender_id,
        author_username=target_uname if sender_id == target_id else getattr(msg.sender, 'username', None), 
        text=text, msg_id=msg.id, chat_id=_get_chat_id(entity),
        chat_title=getattr(entity, 'title', ''), is_reply=bool(msg.reply_to),
        reply_to_msg_id=msg.reply_to.reply_to_msg_id if msg.reply_to else None,
        is_forward=bool(msg.forward), fwd_from_id=fwd_id,
        fwd_from_name=msg.forward.from_name if msg.forward else None,
        media_type=type(msg.media).__name__ if msg.media else None, edit_date=msg.edit_date,
        reactions=[]
    )
    
    # Extract reactions
    if msg.reactions and msg.reactions.results:
        for r_count in msg.reactions.results:
            if hasattr(r_count.reaction, 'emoticon'):
                m_data.reactions.append(r_count.reaction.emoticon)
            elif hasattr(r_count.reaction, 'document_id'):
                m_data.reactions.append(f"custom_emoji_{r_count.reaction.document_id}")
    
    if m_data.is_reply and m_data.reply_to_msg_id:
        try:
            orig = await client.get_messages(entity, ids=m_data.reply_to_msg_id)
            if orig and hasattr(orig, "date"):
                s = await orig.get_sender()
                n, i, u = _get_author_info(s)
                m_data.original_msg = MessageData(date=orig.date, author_name=n, author_id=i, author_username=u, text=orig.raw_text or "(медиа)")
        except Exception: pass
    return m_data

async def _run_export_in_chat(
    client: TelegramClient, entity, target_user, t_name: str, t_id: int, t_uname: Optional[str],
    writer: Optional[FileRotateWriter], storage: SQLiteStorage,
    as_json: bool = True, context_window: int = 3,
    time_threshold: int = 120, max_window: int = 5, merge_gap: int = 2, max_cluster: int = 10,
    status_callback: Optional[callable] = None, force_resync: bool = False
) -> Tuple[int, Optional[datetime], int]:
    chat_id = _get_chat_id(entity)
    chat_title = getattr(entity, 'title', '')
    
    # Регистрация цели в БД с текущими настройками
    mode_str = 'deep' if context_window > 0 else 'normal'
    storage.add_sync_target(t_id, chat_id, t_name, chat_title, mode=mode_str, window=context_window, max_cluster=max_cluster)
    
    # Источник истины — база данных. Если force_resync=True, начинаем с 0.
    if force_resync:
        last_msg_id = 0
    else:
        last_msg_id = storage.get_last_msg_id(t_id, chat_id)
        
    count = 0; highest_id = last_msg_id; latest_date = None

    async def get_keywords(text):
        return {w.lower() for w in re.split(r'\W+', text or "") if len(w) > 2}

    async def is_related(msg: Message, target_msg_data: MessageData, target_keywords: set) -> bool:
        text = (msg.raw_text or "").lower()
        if t_uname and t_uname.lower() in text: return True
        if t_name and t_name.lower() in text: return True
        msg_keywords = await get_keywords(msg.raw_text)
        if target_keywords & msg_keywords: return True
        if abs((msg.date - target_msg_data.date).total_seconds()) <= time_threshold: return True
        if len(text.strip()) < 5 and re.search(r'[✅❌👍👎😊😂😢]|да|нет|ок', text): return True
        return False

    async def write_results(messages):
        nonlocal count, highest_id, latest_date
        blocks = []
        for m in messages:
            author_info = _get_author_info(m.sender) if hasattr(m, 'sender') else (None, None, None)
            data = await process_message(client, entity, m, t_name if m.sender_id == t_id else None, target_id=t_id, target_uname=t_uname)
            
            # 1. Save to Files
            if writer:
                blocks.append(format_export_block(data, as_json))
            
            # 2. Save to Storage (DB)
            if storage:
                storage.save_message(data)
                
            if m.id > highest_id: highest_id = m.id
            if latest_date is None or m.date > latest_date: latest_date = m.date
        
        if writer and blocks:
            sep = "\n" if as_json else "\n\n" + "-" * 40 + "\n\n"
            await writer.write_block(sep.join(blocks) + sep, len(blocks))
            
        count += len(messages) # We count all processed messages from target
        if status_callback: status_callback(len(blocks))

    if context_window == 0:
        search_kwargs = {"from_user": target_user, "reverse": True, "min_id": last_msg_id}
        current_batch = []
        try:
            async for msg in client.iter_messages(entity, **search_kwargs):
                current_batch.append(msg)
                if len(current_batch) >= 50:
                    await write_results(current_batch); current_batch = []
            if current_batch: await write_results(current_batch)
        except (ChatAdminRequiredError, RPCError, Exception) as e:
            if "ChatAdminRequired" in str(e) or "bool()" in str(e):
                limit = 0 if last_msg_id > 0 else 3000
                scan_kwargs = {"reverse": True, "min_id": last_msg_id}
                if limit > 0: scan_kwargs["limit"] = limit
                ts_print(f"  - [{getattr(entity, 'title', chat_id)}] Поиск ограничен. Ручной скан...")
                async for msg in client.iter_messages(entity, **scan_kwargs):
                    if msg.sender_id == t_id:
                        current_batch.append(msg)
                        if len(current_batch) >= 50:
                            await write_results(current_batch); current_batch = []
                if current_batch: await write_results(current_batch)
            else: raise e
    else:
        # DEEP Clustering Logic
        target_msgs = []
        try:
            async for msg in client.iter_messages(entity, from_user=target_user, reverse=True, min_id=last_msg_id):
                target_msgs.append(msg)
        except Exception:
            # Fallback for search in deep mode
            async for msg in client.iter_messages(entity, reverse=True, min_id=last_msg_id, limit=3000):
                if msg.sender_id == t_id: target_msgs.append(msg)
        
        if not target_msgs: return 0, None, highest_id

        clusters = []
        current_cluster = [target_msgs[0]]
        for i in range(1, len(target_msgs)):
            if target_msgs[i].id - target_msgs[i-1].id < (max_window * 2 + merge_gap):
                current_cluster.append(target_msgs[i])
            else:
                clusters.append(current_cluster); current_cluster = [target_msgs[i]]
        clusters.append(current_cluster)

        all_exported_ids = set()
        for cluster in clusters:
            start_id = max(1, cluster[0].id - max_window * 5)
            end_id = cluster[-1].id + max_window * 5
            window_msgs = []
            async for msg in client.iter_messages(entity, min_id=start_id-1, max_id=end_id+1, reverse=True):
                window_msgs.append(msg)
            
            target_in_window = {m.id for m in cluster}
            cluster_msg_data_list = []
            cluster_msg_count = 0
            
            for msg in window_msgs:
                if msg.id in all_exported_ids or cluster_msg_count >= max_cluster: continue
                related = msg.id in target_in_window
                if not related:
                    for t_msg in cluster:
                        if abs((msg.date - t_msg.date).total_seconds()) > time_threshold * 2: continue
                        t_keywords = await get_keywords(t_msg.raw_text)
                        t_data = MessageData(date=t_msg.date, author_name=t_name, author_id=t_id, author_username=t_uname, text=t_msg.raw_text)
                        if await is_related(msg, t_data, t_keywords):
                            related = True; break
                
                if related:
                    m_data = await process_message(client, entity, msg, t_name if msg.sender_id == t_id else None)
                    cluster_msg_data_list.append(m_data)
                    all_exported_ids.add(msg.id)
                    cluster_msg_count += 1
                    
                    # КРИТИЧЕСКИЙ ФИКС: высший ID должен обновляться ТОЛЬКО от сообщений цели,
                    # чтобы контекст не "перепрыгивал" будущие сообщения пользователя при следующем поиске.
                    if msg.sender_id == t_id:
                        if msg.id > highest_id: highest_id = msg.id
                        if latest_date is None or msg.date > latest_date: latest_date = msg.date

            if cluster_msg_data_list:
                blocks = [format_export_block(d, as_json) for d in cluster_msg_data_list]
                if not as_json:
                    blocks.insert(0, f"=== КЛАСТЕР ВОКРУГ СООБЩЕНИЙ ПОЛЬЗОВАТЕЛЯ ({len(cluster)} шт) ===")
                sep = "\n" if as_json else "\n\n" + "-" * 40 + "\n\n"
                await writer.write_block(sep.join(blocks) + sep, len(cluster_msg_data_list))
                count += len(cluster_msg_data_list)
                if status_callback: status_callback(len(cluster_msg_data_list))

    return count, latest_date, highest_id

async def _get_all_dialogs(client: TelegramClient) -> list:
    return [d.entity async for d in client.iter_dialogs() if getattr(d, "is_group", False) or getattr(d, "is_channel", False)]

async def _get_target_dialogs(client: TelegramClient, settings: Settings, chat_identifier: Optional[str]) -> list:
    if chat_identifier:
        try:
            c_id = int(chat_identifier) if str(chat_identifier).strip('-').isdigit() else chat_identifier
            return [await client.get_entity(c_id)]
        except Exception as e:
            ts_print(f" [!] Ошибка загрузки указанного чата '{chat_identifier}': {e}")
            return []
    
    if settings.default_export_chats:
        ts_print(f"Используем чаты по умолчанию из конфига: {settings.default_export_chats}")
        dialogs = []
        for cid in settings.default_export_chats:
            try:
                c_id = int(cid) if str(cid).strip('-').isdigit() else cid
                dialogs.append(await client.get_entity(c_id))
            except Exception as e:
                ts_print(f"  [!] Ошибка загрузки чата '{cid}': {e}")
        return dialogs
        
    return await _get_all_dialogs(client)

async def export_messages_async(settings: Settings, target_identifier: str, chat_identifier: Optional[str], output_file: Optional[str], as_json: bool = True, context_window: int = 3, force_resync: bool = False, **kwargs):
    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await robust_client_start(client)
    
    # Initialize Storage
    db_name = f"{settings.account_name}_messages.db" if settings.account_name else "messages.db"
    db_path = os.path.join(settings.config_dir, db_name)
    storage = SQLiteStorage(db_path)
    
    try:
        try: target_user = await client.get_entity(int(target_identifier))
        except ValueError: target_user = await client.get_entity(target_identifier)
        t_name, t_id, t_uname = _get_author_info(target_user)
    except Exception as e:
        ts_print(f"Ошибка поиска пользователя: {e}"); await client.disconnect(); return

    export_dir = "PUBLIC_GROUPS"; os.makedirs(export_dir, exist_ok=True)
    if not output_file:
        safe_name = clean_filename(t_name)
        ext = ".jsonl" if as_json else ".txt"
        output_file = os.path.join(export_dir, f"Экспорт_{safe_name}_{t_id}{'_DEEP' if context_window > 0 else ''}{ext}")
    
    writer = FileRotateWriter(output_file, as_json=as_json)
    dialogs = await _get_target_dialogs(client, settings, chat_identifier)
        
    ts_print(f"Пользователь: {t_name}. Чатов: {len(dialogs)}")
    
    total_found = 0; chats_done = 0; sem = asyncio.Semaphore(10)
    
    def update_status(new_count=0, chat_finished=False):
        nonlocal total_found, chats_done
        if chat_finished: chats_done += 1
        total_found += new_count
        print(f"\r🔍 Поиск... [{chats_done}/{len(dialogs)} чатов] | 📥 Собрано сообщений: {total_found}", end="", flush=True)

    async def process(chat):
        async with sem:
            try: 
                res = await _run_export_in_chat(
                    client, chat, target_user, t_name, t_id, t_uname, 
                    writer, storage=storage, as_json=as_json, 
                    context_window=context_window, 
                    status_callback=lambda n: update_status(n),
                    force_resync=force_resync, **kwargs
                )
                update_status(chat_finished=True)
                return (chat.id, *res)
            except Exception as e: 
                ts_print(f"\n  [!] Ошибка в чате {getattr(chat, 'title', chat.id)}: {e}")
                update_status(chat_finished=True)
                return (None, 0, None, 0)

    # Initial print
    update_status()
    results = await asyncio.gather(*[process(c) for c in dialogs])
    print() # New line after status line
    
    total = sum(r[1] for r in results)
    
    ts_print(f"Готово! Всего сообщений: {total}"); await client.disconnect()

async def run_export_update_async(config_dir: str, as_json: bool = True, context_window: Optional[int] = None, force_resync: bool = False):
    settings = load_settings(config_dir=config_dir)
    db_name = f"{settings.account_name}_messages.db" if settings.account_name else "messages.db"
    db_path = os.path.join(settings.config_dir, db_name)
    storage = SQLiteStorage(db_path)
    
    # 1. Получаем список активных целей из базы данных
    active_targets = storage.get_active_sync_targets()
    
    if not active_targets:
        ts_print("⚠️ Активные цели для синхронизации в БД не найдены. Сначала запустите обычный 'export'.")
        await client.disconnect(); return

    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
    await robust_client_start(client)
    
    sem = asyncio.Semaphore(10)
    ts_print(f"🔄 Смарт-обновление: запуск для {len(active_targets)} отслеживаемых пар (пользователь-чат)...")
    
    # Группируем цели по пользователям, чтобы не пересоздавать клиента/сущности
    from collections import defaultdict
    user_groups = defaultdict(list)
    for t in active_targets:
        user_groups[t['user_id']].append(t)

    for uid, targets in user_groups.items():
        try:
            # Получаем актуальную информацию о пользователе один раз для группы чатов
            try:
                user = await client.get_entity(uid)
                u_name, u_id, u_uname = _get_author_info(user)
            except Exception:
                u_name = targets[0]['author_name']; u_id = uid; u_uname = None
                ts_print(f"  [!] Не удалось обновить сущность пользователя {uid}, используем имя из базы.")

            safe_name = clean_filename(u_name)
            ext = ".jsonl" if as_json else ".txt"
            # Для имени файла в апдейте используем либо переданное окно, либо просто проверяем, было ли оно передано
            # Если не передано, не добавляем суффикс (он уже есть в существующем файле или не нужен)
            suffix = ""
            if context_window is not None and context_window > 0:
                suffix = "_DEEP"
            
            opath = os.path.join("PUBLIC_GROUPS", f"Экспорт_{safe_name}_{u_id}{suffix}{ext}")
            
            writer = FileRotateWriter(opath, as_json=as_json)
            
            for t in targets:
                cid = t['chat_id']
                c_title = t['chat_title'] or f"Chat_{cid}"
                
                try:
                    chat_entity = await client.get_entity(cid)
                except Exception:
                    ts_print(f"  [!] Чат {c_title} не найден или недоступен. Пропускаем.")
                    continue

                # Приоритет: 1. Явный CLI флаг, 2. Значение из БД, 3. Глобальный дефолт (3)
                target_window = context_window if context_window is not None else t.get('window_size', 3)
                target_max_cluster = t.get('max_cluster', 10)

                ts_print(f"  🔄 Обновление {u_name} в '{c_title}' (окно: {target_window}, сброс: {force_resync})...")
                
                res = await _run_export_in_chat(
                    client, chat_entity, user, u_name, u_id, u_uname, 
                    writer, storage, as_json=as_json, 
                    context_window=target_window,
                    max_cluster=target_max_cluster,
                    force_resync=force_resync
                )
                
                if res[0] > 0:
                    storage.update_sync_timestamp(u_id, cid)
                    ts_print(f"    📥 Добавлено: {res[0]} сообщений.")
                else:
                    ts_print(f"    ✅ Новых сообщений нет.")

        except Exception as e: 
            ts_print(f"Ошибка при обновлении пользователя {uid}: {e}")
        
    await client.disconnect()

def run_export(config_dir: str, target_user: str, chat_id: Optional[str], output_file: Optional[str], **kwargs):
    asyncio.run(export_messages_async(load_settings(config_dir), target_user, chat_id, output_file, **kwargs))

def remove_user_data(config_dir: str, user_id: str):
    settings = load_settings(config_dir=config_dir)
    db_name = f"{settings.account_name}_messages.db" if settings.account_name else "messages.db"
    db_path = os.path.join(settings.config_dir, db_name)
    storage = SQLiteStorage(db_path)
    
    try:
        u_id_int = int(user_id)
    except ValueError:
        ts_print(f" [!] Ошибка: ID пользователя должен быть числом (получено '{user_id}').")
        return

    # 1. Database Purge
    msg_count, target_count = storage.delete_user_data(u_id_int)
    ts_print(f" --- Очистка БД завершена ---")
    ts_print(f" Удалено сообщений: {msg_count}")
    ts_print(f" Удалено целей синхронизации: {target_count}")

    # 2. Filesystem Cleanup
    dirs_to_scan = ["PUBLIC_GROUPS", "PRIVAT_DIALOGS"]
    deleted_files = 0
    
    # Ищем файлы, содержащие _ID (например, Экспорт_Имя_12345.jsonl)
    pattern = f"_{u_id_int}"
    
    for dname in dirs_to_scan:
        if not os.path.exists(dname): continue
        for root, dirs, files in os.walk(dname):
            # Проверка файлов
            for fname in files:
                if pattern in fname:
                    fpath = os.path.join(root, fname)
                    try:
                        os.remove(fpath)
                        deleted_files += 1
                        ts_print(f" [x] Удален файл: {fpath}")
                    except Exception as e:
                        ts_print(f" [!] Ошибка удаления файла {fpath}: {e}")
            
            # Проверка директорий (актуально для PRIVAT_DIALOGS)
            for d in list(dirs):
                if pattern in d:
                    dpath = os.path.join(root, d)
                    try:
                        shutil.rmtree(dpath)
                        deleted_files += 1
                        ts_print(f" [x] Удалена папка: {dpath}")
                        dirs.remove(d) # Чтобы os.walk не пытался зайти в удаленную папку
                    except Exception as e:
                        ts_print(f" [!] Ошибка удаления папки {dpath}: {e}")

    ts_print(f" --- Очистка файлов завершена ---")
    ts_print(f" Удалено объектов: {deleted_files}")
    ts_print(f"\nВсе данные для пользователя {u_id_int} стерты.")
