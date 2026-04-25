import os
import sys
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import shutil

from .file_writer import FileRotateWriter
from ..infrastructure.storage.interface import BaseStorage
from ..core.telegram.interface import TelegramClientInterface
from ..core.telemetry import telemetry
from ..core.models.message import MessageData
from ..utils.ui import UI

logger = logging.getLogger(__name__)

class PrivateArchiveService:
    """
    Service for exporting private chats (PMs) with full media downloading capability.
    """
    def __init__(self, client: TelegramClientInterface, storage: BaseStorage, 
                 base_dir: str = "PRIVAT_DIALOGS",
                 max_file_size: int = 50 * 1024 * 1024):
        self.client = client
        self.storage = storage
        self.base_dir = base_dir
        self.max_file_size = max_file_size
        self.download_semaphore = asyncio.Semaphore(3)

    def _get_user_folder_name(self, user_id: int, first_name: str, last_name: str, username: str) -> str:
        name = UI.format_name({'first_name': first_name, 'last_name': last_name, 'username': username, 'user_id': user_id})
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        return f"{safe_name}_{user_id}"

    def _media_category(self, media_type: Optional[str]) -> str:
        if not media_type:
            return "documents"
        normalized = media_type.lower()
        if "photo" in normalized:
            return "photos"
        if "video" in normalized:
            return "videos"
        if "voice" in normalized or "audio" in normalized:
            return "voices"
        return "documents"

    async def _download_media(self, msg_data: MessageData, media_dir: str) -> Optional[str]:
        media_ref = getattr(msg_data, "media_ref", None)
        if media_ref is None:
            return None

        category = self._media_category(msg_data.media_type)
        target_dir = os.path.join(media_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        base_name = f"{msg_data.message_id}"
        target_path = os.path.join(target_dir, base_name)

        return await self.client.download_media(media_ref, file=target_path)

    async def archive_pm(self, user_entity: Any):
        """
        Main entry point for PM archiving.
        """
        user_id = getattr(user_entity, 'id', 0)
        first_name = getattr(user_entity, 'first_name', '') or ''
        last_name = getattr(user_entity, 'last_name', '') or ''
        username = getattr(user_entity, 'username', '') or ''
        
        target_name = UI.format_name(user_entity)
        folder_name = self._get_user_folder_name(user_id, first_name, last_name, username)
        user_dir = os.path.join(self.base_dir, folder_name)
        media_dir = os.path.join(user_dir, "media")
        
        for sub in ("photos", "videos", "voices", "documents"):
            os.makedirs(os.path.join(media_dir, sub), exist_ok=True)
            
        chat_log_path = os.path.join(user_dir, "chat_log.txt")
        writer = FileRotateWriter(chat_log_path, as_json=False, max_msgs=5000)
        
        last_id = self.storage.get_last_msg_id(user_id) 
        
        # Register as primary target
        self.storage.register_target(user_id, target_name, user_id)
        
        if UI.is_tty():
            print(f"\n📂 [PM Archive: {target_name} ({user_id})]")
            print(f"   Saving to: {user_dir}")
        logger.info(f"PM Archive start for {user_id}. Last ID: {last_id}")
        
        count = 0
        stats = {"Photo": 0, "Video": 0, "Voice": 0, "Document": 0}
        
        async for msg_data in self.client.iter_messages(user_entity, limit=None, offset_id=0):
            if msg_data.message_id <= last_id:
                break
                
            await self.storage.save_message(msg_data)
            log_entry = self._format_pm_log(msg_data)
            
            if msg_data.media_type:
                # Track media count by type
                m_type = msg_data.media_type
                if m_type in stats:
                    stats[m_type] += 1
                else:
                    # Generic document if not matched
                    stats["Document"] += 1
                telemetry.track_messages(1)
                downloaded_path = await self._download_media(msg_data, media_dir)
                if downloaded_path and UI.is_tty():
                    print(f"   ↳ saved media: {os.path.basename(downloaded_path)}")
                
            await writer.write_block(log_entry + "\n\n" + "-"*40 + "\n\n", 1)
            count += 1
            
            if count % 5 == 0:
                media_str = f"P:{stats['Photo']} V:{stats['Video']} S:{stats['Voice']} D:{stats['Document']}"
                UI.print_status("Archiving", count, extra=f"messages | Media: {media_str}")
            
        media_total = f"P:{stats['Photo']} V:{stats['Video']} S:{stats['Voice']} D:{stats['Document']}"
        if UI.is_tty():
            UI.print_status("Complete", count, extra=f"messages | Final Media: {media_total}")
            sys.stdout.write("\n")
            sys.stdout.flush()
        logger.info(f"PM Archive complete for {user_id}. {count} messages, {sum(stats.values())} media.")
        return user_dir

    def _format_pm_log(self, m: MessageData) -> str:
        dt_str = m.timestamp.strftime("%Y-%m-%d][%H:%M")
        author = m.author_name or f"User_{m.user_id}"
        header = f"[{dt_str}] <{author}> (ID: {m.user_id}):"
        media_note = f" <Attached {m.media_type}>" if m.media_type else ""
        return f"{header}{media_note}\n{m.text or '(empty)'}"
