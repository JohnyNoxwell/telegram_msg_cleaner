import logging
from typing import List, Set, Any, Optional
from ..core.telegram.interface import TelegramClientInterface
from ..infrastructure.storage.interface import BaseStorage
from ..utils.ui import UI

logger = logging.getLogger(__name__)

class CleanerService:
    """
    Safely deletes messages from Telegram and updates the local storage.
    Enforces whitelist protection and dry-run mode.
    """

    def __init__(self, client: Optional[TelegramClientInterface], storage: BaseStorage, whitelist: Set[Any] = None, include_list: Set[Any] = None):
        self.client = client
        self.storage = storage
        self.whitelist = whitelist or set()
        self.include_list = include_list or set()

    def _require_client(self):
        if self.client is None:
            raise RuntimeError("Telegram client is not initialized for live cleanup operations")

    async def delete_chat_messages(self, entity: Any, message_ids: List[int], dry_run: bool = True) -> int:
        """
        Deletes a batch of messages for a specific chat.
        """
        chat_id = getattr(entity, 'id', 0)
        
        # 1. Whitelist check
        if chat_id in self.whitelist:
            logger.warning(f"Aborting deletion: Chat {chat_id} is in the whitelist.")
            return 0

        if not message_ids:
            return 0

        # Tarce logging
        logger.info(f"Targeting {len(message_ids)} messages for deletion in chat {chat_id} (Dry Run: {dry_run})")

        if dry_run:
            for mid in message_ids:
                logger.info(f"[DRY RUN] Would delete message {mid} in chat {chat_id}")
            return 0

        # 2. Live Deletion from Telegram
        # The client already handles FloodWait and Throttling
        self._require_client()
        deleted_count = await self.client.delete_messages(entity, message_ids)
        
        if deleted_count > 0:
            # 3. Update Storage
            # We only remove from DB what was actually deleted from Telegram 
            # (In this simple wrapper, we assume all requested were deleted or handled by error logic)
            storage_count = self.storage.delete_messages(chat_id, message_ids)
            logger.info(f"Successfully deleted {deleted_count} messages from Telegram and {storage_count} from DB.")
            return deleted_count
            
        return 0

    async def cleanup_entire_chat(self, entity: Any, dry_run: bool = True) -> int:
        """
        Finds all stored messages for a chat and deletes them.
        """
        chat_id = getattr(entity, 'id', 0)
        
        # Whitelist protection
        if chat_id in self.whitelist:
            logger.warning(f"Aborting full cleanup: Chat {chat_id} is in the whitelist.")
            return 0

        # Load all IDs from storage
        message_ids = self.storage.get_all_message_ids_for_chat(chat_id)
        
        if not message_ids:
            logger.info(f"No messages found in storage for chat {chat_id}.")
            return 0

        # Delegate to batch deletion
        return await self.delete_chat_messages(entity, message_ids, dry_run=dry_run)

    async def global_self_cleanup(self, dry_run: bool = True, include_pms: bool = False) -> int:
        """
        Scans dialogs and deletes all messages from 'me'.
        By default, skips private dialogues unless include_pms=True.
        """
        from ..i18n import _
        import sys

        mode_str = "DRY RUN" if dry_run else "REAL DELETION"
        target_str = "Groups & PMs" if include_pms else "Groups only"
        logger.info(f"Starting Global Self-Clean ({mode_str}) | Scope: {target_str}...")
        self._require_client()
        
        dialogs = await self.client.get_dialogs()
        
        # Pre-filter eligible dialogs for accurate counter
        eligible_dialogs = []
        for d in dialogs:
            is_eligible = d.is_group or d.is_channel
            if include_pms and d.is_user:
                is_eligible = True
            
            if not is_eligible:
                continue

            # 1. Include List check (if not empty, only these are eligible)
            if self.include_list:
                in_include = False
                if d.id in self.include_list:
                    in_include = True
                else:
                    ent = getattr(d, 'entity', None)
                    username = getattr(ent, 'username', None)
                    if username and username in self.include_list:
                        in_include = True
                
                if not in_include:
                    continue

            # 2. Robust whitelist check
            is_whitelisted = False
            # 1. Check ID (normalized to int in settings)
            if d.id in self.whitelist:
                is_whitelisted = True
            
            # 2. Check username/title if ID didn't match
            if not is_whitelisted:
                # Telethon Dialog entity might have a username
                ent = getattr(d, 'entity', None)
                username = getattr(ent, 'username', None)
                if username and username in self.whitelist:
                    is_whitelisted = True
                elif name := getattr(d, 'name', None):
                    # Fallback to display name (if user put it in whitelist)
                    if name in self.whitelist:
                        is_whitelisted = True

            if not is_whitelisted:
                eligible_dialogs.append(d)

        total = len(eligible_dialogs)
        total_deleted = 0
        total_found = 0
        
        for i, dialog in enumerate(eligible_dialogs):
            name = dialog.name or str(dialog.id)
            # Print progress to terminal
            UI.print_status("Cleaning", f"[{i+1}/{total}] {name}")
            
            logger.info(f"Scanning chat {dialog.id} ({name}) for your messages...")
            
            my_msg_ids = []
            async for msg_data in self.client.iter_messages(dialog.entity, from_user='me'):
                # Essential Fix: Skip service messages (like 'Channel created' ID 1)
                # They often show up as from 'me' but cannot be deleted via the standard API.
                if msg_data.is_service:
                    continue
                my_msg_ids.append(msg_data.message_id)
                
            if my_msg_ids:

                total_found += len(my_msg_ids)
                UI.print_status("Found", len(my_msg_ids), extra=f"messages in {name}")
                sys.stdout.write("\n")
                sys.stdout.flush()
                
                count = await self.delete_chat_messages(dialog.entity, my_msg_ids, dry_run=dry_run)
                total_deleted += count
                
        logger.info(f"Global Self-Clean finished. Total found: {total_found}, Total deleted: {total_deleted}")
        return total_deleted


    async def purge_user_data(self, user_id: int):
        """
        Completely removes all user data from the database and deletes associated export files.
        """
        import os
        # 1. Clear database
        msg_count, target_count = self.storage.delete_user_data(user_id)
        logger.info(f"Purged {msg_count} messages from DB for user {user_id}")

        # 2. Clear filesystem
        dirs_to_scan = ["PUBLIC_GROUPS", "PRIVAT_DIALOGS", "DB_EXPORTS"]
        deleted_count = 0
        pattern = f"_{user_id}"
        
        for dname in dirs_to_scan:
            if not os.path.exists(dname):
                continue
            for root, dirs, files in os.walk(dname):
                for fname in files:
                    if pattern in fname:
                        fpath = os.path.join(root, fname)
                        try:
                            os.remove(fpath)
                            deleted_count += 1
                            logger.debug(f"Deleted file: {fpath}")
                        except Exception as e:
                            logger.error(f"Error deleting file {fpath}: {e}")
                
                # Check directories
                for d in list(dirs):
                    if pattern in d:
                        dpath = os.path.join(root, d)
                        import shutil
                        try:
                            shutil.rmtree(dpath)
                            deleted_count += 1
                            dirs.remove(d)
                            logger.debug(f"Deleted directory: {dpath}")
                        except Exception as e:
                            logger.error(f"Error deleting directory {dpath}: {e}")
        
        logger.info(f"Purge complete. Deleted {deleted_count} files/objects for user {user_id}")
        return msg_count, deleted_count
