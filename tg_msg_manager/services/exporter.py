import sys
import asyncio
import logging
from typing import Optional, Any
from ..core.telegram.interface import TelegramClientInterface
from ..infrastructure.storage.interface import BaseStorage
from ..core.context import set_chat_id
from ..core.telemetry import telemetry
from .context_engine import DeepModeEngine

logger = logging.getLogger(__name__)

class ExportService:
    """
    Orchestrates the export and synchronization of Telegram messages.
    Links the API abstraction layer with the Storage layer.
    """

    def __init__(self, client: TelegramClientInterface, storage: BaseStorage):
        self.client = client
        self.storage = storage
        self.context_engine = DeepModeEngine(client, storage)

    def _get_entity_name(self, entity: Any) -> str:
        """Helper to get a human readable name from a Telethon entity."""
        if hasattr(entity, 'first_name'):
            first = getattr(entity, 'first_name', '') or ''
            last = getattr(entity, 'last_name', '') or ''
            return f"{first} {last}".strip() or f"ID:{entity.id}"
        elif hasattr(entity, 'title'):
            return getattr(entity, 'title', f"ID:{entity.id}")
        return f"ID:{getattr(entity, 'id', 'Unknown')}"

    async def sync_chat(self, entity: Any, 
                        from_user_id: Optional[int] = None,
                        limit: Optional[int] = None, 
                        deep_mode: bool = False,
                        force_resync: bool = False,
                        context_window: int = 3,
                        max_cluster: int = 20,
                        recursive_depth: int = 3):
        """
        Synchronizes a specific chat with a clean real-time global status counter.
        """
        # 1. Resolve entity info
        chat_id = getattr(entity, 'id', 0)
        target_name = self._get_entity_name(entity)
        set_chat_id(chat_id)
        
        # 2. Get last synced message ID (Target-specific if filtering by user)
        if from_user_id:
            last_id = 0 if force_resync else self.storage.get_last_target_msg_id(chat_id, from_user_id)
        else:
            # For full chat sync, we use the global last_id
            # Note: I should keep a global chat-level helper as well or use 0
            last_id = 0 if force_resync else self.storage.get_last_target_msg_id(chat_id, chat_id)
        
        # 3. Register as primary target
        uid = from_user_id or chat_id
        self.storage.register_target(uid, target_name, chat_id)
        
        # 4. Resolve Target Name (User name)
        user_display_name = ""
        if from_user_id:
            try:
                user_ent = await self.client.get_entity(from_user_id)
                user_display_name = f" | User: {self._get_entity_name(user_ent)}"
            except:
                user_display_name = f" | User: {from_user_id}"

        mode_str = f"DEEP (Depth {recursive_depth})" if deep_mode else "FLAT"
        header = f"👤 Target: {target_name}{user_display_name} | Mode: {mode_str}"
        print(f"\n{header}")
        
        # 3. Parallel Scanning Strategy (Hyper-Acceleration v4)
        worker_count = 4
        batch_size = 200
        context_batch_size = 50
        
        # Get the latest message to determine the ID range for parallelization
        latest_msg = await self.client.get_messages(entity, limit=1)
        max_id = latest_msg[0].message_id if latest_msg else 1000000
        
        # Define worker ranges (backwards scanning)
        chunk_size = max_id // worker_count
        ranges = []
        for i in range(worker_count):
            start_off = 0 if i == 0 else max_id - (i * chunk_size)
            stop_id = max_id - ((i + 1) * chunk_size) if i < worker_count - 1 else 0
            ranges.append((start_off, stop_id))

        if hasattr(self.context_engine, '_processed_ids'):
            self.context_engine._processed_ids.clear()

        async def draw_status():
            db_total = self.storage.get_message_count(chat_id)
            sys.stdout.write(f"\r   📊 Total Exported: {db_total} messages...                    ")
            sys.stdout.flush()

        async def scan_worker(offset, stop_id):
            w_processed = 0
            w_batch = []
            w_context_batch = []
            
            async for msg_data in self.client.iter_messages(entity, limit=limit, offset_id=offset, from_user=from_user_id):
                # 1. Respect worker boundary and global sync state
                if msg_data.message_id <= stop_id:
                    break
                if not force_resync and msg_data.message_id <= last_id:
                    break

                if deep_mode:
                    w_context_batch.append(msg_data)
                    if len(w_context_batch) >= context_batch_size:
                        await self.context_engine.extract_batch_context(
                            entity, w_context_batch, 
                            window_size=context_window,
                            max_cluster=max_cluster,
                            recursive_depth=recursive_depth,
                            on_progress=draw_status
                        )
                        w_context_batch = []
                        await draw_status()
                else:
                    w_batch.append(msg_data)
                
                w_processed += 1
                if len(w_batch) >= batch_size:
                    await self.storage.save_messages(w_batch)
                    telemetry.track_messages(len(w_batch))
                    w_batch = []
                    await draw_status()

            # Final flushes for worker
            if w_context_batch:
                await self.context_engine.extract_batch_context(
                    entity, w_context_batch, 
                    window_size=context_window,
                    max_cluster=max_cluster,
                    recursive_depth=recursive_depth,
                    on_progress=draw_status
                )
            if w_batch:
                await self.storage.save_messages(w_batch)
                telemetry.track_messages(len(w_batch))
            
            return w_processed

        async def draw_status_loop():
            """Periodic UI updates to avoid terminal lag."""
            while not done_event.is_set():
                await draw_status()
                await asyncio.sleep(0.5)

        done_event = asyncio.Event()
        status_task = asyncio.create_task(draw_status_loop())
        
        try:
            results = await asyncio.gather(*[scan_worker(r[0], r[1]) for r in ranges])
            total_processed = sum(results)
        finally:
            done_event.set()
            await status_task
            await draw_status()
            
        # 4. Final summary
        db_count = self.storage.get_message_count(chat_id)
        sys.stdout.write(f"\r   ✅ Export Finished! Total in DB: {db_count} messages.               \n")
        sys.stdout.flush()
        
        return total_processed

    async def sync_all_outdated(self, threshold_hours: int = 48):
        """Finds chats that haven't been synced recently and runs sync."""
        threshold_seconds = threshold_hours * 3600
        outdated_chat_ids = self.storage.get_outdated_chats(threshold_seconds)
        
        if not outdated_chat_ids:
            print("\n✅ All chats are already up to date.")
            return

        print(f"\n🔄 [Updating {len(outdated_chat_ids)} chats...]")
        
        for chat_id in outdated_chat_ids:
            try:
                entity = await self.client.get_entity(chat_id)
                await self.sync_chat(entity)
            except Exception as e:
                logger.error(f"Failed to sync chat {chat_id}: {e}")
                telemetry.track_error()
        
        telemetry.log_summary()
