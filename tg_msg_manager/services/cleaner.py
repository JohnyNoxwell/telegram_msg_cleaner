import logging
from typing import List, Set, Any, Optional, Tuple
from ..core.telegram.interface import TelegramClientInterface
from ..infrastructure.storage.interface import BaseStorage
from ..core.service_events import ServiceEventSink, emit_service_event

logger = logging.getLogger(__name__)

class CleanerService:
    """
    Safely deletes messages from Telegram and updates the local storage.
    Enforces whitelist protection and dry-run mode.
    """

    _CHANNEL_ID_SHIFT = 10**12

    def __init__(
        self,
        client: Optional[TelegramClientInterface],
        storage: BaseStorage,
        whitelist: Set[Any] = None,
        include_list: Set[Any] = None,
        event_sink: ServiceEventSink = None,
    ):
        self.client = client
        self.storage = storage
        self.whitelist = whitelist or set()
        self.include_list = include_list or set()
        self.event_sink = event_sink

    def _require_client(self):
        if self.client is None:
            raise RuntimeError("Telegram client is not initialized for live cleanup operations")

    @staticmethod
    def _dialog_display_name(dialog: Any) -> str:
        return getattr(dialog, "name", None) or str(getattr(dialog, "id", 0))

    def _emit_event(self, event_name: str, **payload: Any) -> None:
        emit_service_event(self.event_sink, event_name, **payload)

    @classmethod
    def _numeric_chat_id_variants(cls, value: Any) -> Set[int]:
        if value is None or isinstance(value, bool):
            return set()
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return set()

        variants = {numeric}
        if numeric <= -cls._CHANNEL_ID_SHIFT:
            variants.add(abs(numeric) - cls._CHANNEL_ID_SHIFT)
        elif numeric < 0:
            variants.add(abs(numeric))
        else:
            variants.add(-numeric)
            variants.add(-(cls._CHANNEL_ID_SHIFT + numeric))
        return variants

    def _target_chat_id_variants(self, target: Any) -> Set[int]:
        entity = getattr(target, "entity", None)
        variants: Set[int] = set()
        for raw_id in (getattr(target, "id", None), getattr(entity, "id", None)):
            variants.update(self._numeric_chat_id_variants(raw_id))
        return variants

    @staticmethod
    def _target_username(target: Any) -> Optional[str]:
        entity = getattr(target, "entity", None)
        username = getattr(entity, "username", None) or getattr(target, "username", None)
        return username if username else None

    def _target_matches_selectors(self, target: Any, selectors: Set[Any], *, include_name: bool) -> bool:
        target_ids = self._target_chat_id_variants(target)
        for selector in selectors:
            if self._numeric_chat_id_variants(selector) & target_ids:
                return True

        username = self._target_username(target)
        if username and username in selectors:
            return True

        if include_name:
            name = getattr(target, "name", None)
            if name and name in selectors:
                return True

        return False

    def _dialog_matches_include_list(self, dialog: Any) -> bool:
        if not self.include_list:
            return True
        return self._target_matches_selectors(dialog, self.include_list, include_name=False)

    def _dialog_is_whitelisted(self, dialog: Any) -> bool:
        return self._target_matches_selectors(dialog, self.whitelist, include_name=True)

    def _dialog_is_cleanup_eligible(self, dialog: Any, *, include_pms: bool) -> bool:
        is_eligible = bool(getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False))
        if include_pms and getattr(dialog, "is_user", False):
            is_eligible = True
        if not is_eligible:
            return False
        if not self._dialog_matches_include_list(dialog):
            return False
        return not self._dialog_is_whitelisted(dialog)

    def _eligible_cleanup_dialogs(self, dialogs: List[Any], *, include_pms: bool) -> List[Any]:
        return [
            dialog
            for dialog in dialogs
            if self._dialog_is_cleanup_eligible(dialog, include_pms=include_pms)
        ]

    async def _collect_self_message_ids(self, entity: Any) -> List[int]:
        message_ids: List[int] = []
        async for msg_data in self.client.iter_messages(entity, from_user='me'):
            if msg_data.is_service:
                continue
            message_ids.append(msg_data.message_id)
        return message_ids

    async def _cleanup_dialog(
        self,
        dialog: Any,
        *,
        index: int,
        total: int,
        dry_run: bool,
    ) -> Tuple[int, int]:
        name = self._dialog_display_name(dialog)
        self._emit_event(
            "cleaner.dialog_scan_started",
            index=index,
            total=total,
            name=name,
            chat_id=getattr(dialog, "id", 0),
        )
        logger.info(f"Scanning chat {dialog.id} ({name}) for your messages...")

        my_msg_ids = await self._collect_self_message_ids(dialog.entity)
        if not my_msg_ids:
            return 0, 0

        self._emit_event(
            "cleaner.dialog_messages_found",
            name=name,
            chat_id=getattr(dialog, "id", 0),
            count=len(my_msg_ids),
        )
        deleted_count = await self.delete_chat_messages(dialog.entity, my_msg_ids, dry_run=dry_run)
        return len(my_msg_ids), deleted_count

    async def delete_chat_messages(self, entity: Any, message_ids: List[int], dry_run: bool = True) -> int:
        """
        Deletes a batch of messages for a specific chat.
        """
        chat_id = getattr(entity, 'id', 0)
        
        # 1. Whitelist check
        if self._target_matches_selectors(entity, self.whitelist, include_name=False):
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
        if self._target_matches_selectors(entity, self.whitelist, include_name=False):
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
        mode_str = "DRY RUN" if dry_run else "REAL DELETION"
        target_str = "Groups & PMs" if include_pms else "Groups only"
        logger.info(f"Starting Global Self-Clean ({mode_str}) | Scope: {target_str}...")
        self._require_client()
        
        dialogs = await self.client.get_dialogs()
        eligible_dialogs = self._eligible_cleanup_dialogs(dialogs, include_pms=include_pms)

        total = len(eligible_dialogs)
        total_deleted = 0
        total_found = 0
        
        for i, dialog in enumerate(eligible_dialogs):
            found_count, deleted_count = await self._cleanup_dialog(
                dialog,
                index=i + 1,
                total=total,
                dry_run=dry_run,
            )
            total_found += found_count
            total_deleted += deleted_count
                
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
