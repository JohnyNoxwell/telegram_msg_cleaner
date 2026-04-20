import os
import logging
from datetime import datetime
from typing import List, Optional
from .file_writer import FileRotateWriter
from ..infrastructure.storage.interface import BaseStorage
from ..core.models.message import MessageData

logger = logging.getLogger(__name__)

class DBExportService:
    """
    Service responsible for exporting cached messages from the database into files.
    """
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def format_message(self, m: MessageData, as_json: bool = False) -> str:
        """Formats a MessageData object into a string for file output."""
        if as_json:
            import json
            return json.dumps(m.to_dict(), ensure_ascii=False)
        
        # Human-readable text format
        dt_str = m.timestamp.strftime("%Y-%m-%d][%H:%M:%S")
        reply_str = f" (в ответ на {m.reply_to_id})" if m.reply_to_id else ""
        fwd_str = f" [FWD from {m.fwd_from_id}]" if m.fwd_from_id else ""
        media_str = f" [{m.media_type}]" if m.media_type else ""
        
        # We use a placeholder for user_name if we have it in MessageData (I added it recently)
        author = m.author_name or f"User_{m.user_id}"
        header = f"[{dt_str}] <{author} ({m.user_id})>{reply_str}{fwd_str}{media_str}:"
        
        return f"{header}\n{m.text or '(пусто)'}"

    async def export_user_messages(self, user_id: int, output_dir: str = "DB_EXPORTS", as_json: bool = False) -> str:
        """
        Fetches all messages for a user from storage and writes them to parts using FileRotateWriter.
        Returns the base output path.
        """
        messages = self.storage.get_user_messages(user_id)
        if not messages:
            logger.warning(f"No messages found in DB for user {user_id}")
            return ""

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Find the correct author name for the filename (from the target user, not just the first message)
        target_author = "Unknown"
        for m in messages:
            if m.user_id == user_id and m.author_name:
                target_author = m.author_name
                break
        if target_author == "Unknown" and messages:
            target_author = messages[0].author_name or "Unknown"

        safe_name = target_author.replace(" ", "_")
        date_str = datetime.now().strftime("%m-%d")
        filename = f"{safe_name}_{user_id}_date({date_str})" + (".jsonl" if as_json else ".txt")
        output_path = os.path.join(output_dir, filename)

        writer = FileRotateWriter(output_path, as_json=as_json, overwrite=True)
        
        sep = "\n" if as_json else "\n\n----------------------------------------\n\n"
        
        count = 0
        for m in messages:
            block = self.format_message(m, as_json=as_json)
            await writer.write_block(block + sep, 1)
            count += 1
            if count % 100 == 0:
                logger.debug(f"Exported {count}/{len(messages)} messages from DB...")

        logger.info(f"DB Export complete for {target_author}: {count} messages.")
        return output_path
