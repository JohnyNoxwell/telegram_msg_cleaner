import sys
import asyncio
import logging
from typing import Optional, Any, Set
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

    def request_stop(self):
        """Sets the shutdown event to signal workers to stop."""
        self.storage.request_stop()

    async def sync_chat(self, entity: Any, 
                        from_user_id: Optional[int] = None,
                        limit: Optional[int] = None, 
                        deep_mode: bool = False,
                        force_resync: bool = False,
                        context_window: int = 3,
                        max_cluster: int = 20,
                        recursive_depth: int = 0):
        """
        Synchronizes a specific chat with a clean real-time global status counter.
        Now supports Resume and Dual-Sync (New + Historical).
        """
        # 1. Resolve entity info
        chat_id = getattr(entity, 'id', 0)
        chat_title = self._get_entity_name(entity)
        set_chat_id(chat_id)
        
        # Save chat metadata immediately
        self.storage.upsert_chat(chat_id, chat_title, chat_type=getattr(entity, '_', None))
        
        uid = from_user_id or chat_id
        target_name = chat_title # Default
        user_label = ""
        
        # 2. Resolve User Name if this is a user-specific sync
        if from_user_id:
            try:
                user_ent = await self.client.get_entity(from_user_id)
                target_name = self._get_entity_name(user_ent)
                user_label = f" | User: {target_name}"
                # Save user metadata
                self.storage.upsert_user(
                    user_id=user_ent.id,
                    first_name=getattr(user_ent, 'first_name', None),
                    last_name=getattr(user_ent, 'last_name', None),
                    username=getattr(user_ent, 'username', None)
                )
            except Exception as e:
                logger.warning(f"Could not resolve user {from_user_id}: {e}")
                user_label = f" | User: {from_user_id}"
        
        # 3. Get Sync Status
        status = self.storage.get_sync_status(chat_id, uid)
        
        # 3.1 Use saved settings if not explicitly overridden
        saved_deep = bool(status.get("deep_mode", 0))
        saved_depth = status.get("recursive_depth", 0)
        
        active_deep = deep_mode or saved_deep
        active_depth = recursive_depth if recursive_depth > 0 else (saved_depth if saved_depth > 0 else 3)

        head_id = 0 if force_resync else status["last_msg_id"]
        tail_id = 0 if force_resync else status["tail_msg_id"]
        is_complete = 0 if force_resync else status["is_complete"]
        
        # 4. Register as primary target with correct name and settings
        self.storage.register_target(uid, target_name, chat_id, 
                                     deep_mode=active_deep, 
                                     recursive_depth=active_depth)

        mode_str = f"DEEP (Depth {active_depth})" if active_deep else "FLAT"
        status_str = " (Resuming history...)" if tail_id > 0 and not is_complete else (" (Updating...)" if head_id > 0 else "")
        header = f"👤 Target: {chat_title}{user_label} | Mode: {mode_str}{status_str}"
        print(f"\n{header}")
        
        # 5. Determine Scan Boundaries
        # Get the latest message to determine current max
        latest_msg = await self.client.get_messages(entity, limit=1)
        current_max = latest_msg[0].message_id if latest_msg else 1000000
        
        # 6. Parallel Scanning Strategy (Advanced Range Partitioning)
        worker_count = 4
        batch_size = 200
        context_batch_size = 50
        ranges = []
        
        # Phase A: Update (Newest -> head_id)
        if head_id > 0 and current_max > head_id:
            ranges.append({"offset": current_max, "stop": head_id, "role": "HEAD"})
        
        # Phase B: Resume (tail_id or head_id -> 0)
        if not is_complete:
            h_start = tail_id if tail_id > 0 else (head_id if head_id > 0 else current_max)
            h_workers = worker_count - len(ranges)
            h_chunk = h_start // h_workers if h_workers > 0 else h_start
            
            for i in range(h_workers):
                w_offset = 0 if i == 0 else h_start - (i * h_chunk)
                w_stop = h_start - ((i + 1) * h_chunk) if i < h_workers - 1 else 0
                ranges.append({"offset": w_offset, "stop": w_stop, "role": "TAIL"})

        # Fallback if everything is complete
        if not ranges:
            ranges.append({"offset": current_max, "stop": head_id, "role": "HEAD"})

        if hasattr(self.context_engine, '_processed_ids'):
            self.context_engine._processed_ids.clear()

        async def draw_status(extra=""):
            db_total = self.storage.get_message_count(chat_id, target_id=uid)
            # Add a bit of movement even if count doesn't change
            sys.stdout.write(f"\r   📊 Total Exported: {db_total} messages {extra}                   ")
            sys.stdout.flush()

        async def scan_worker(offset, stop_id, role="TAIL"):
            w_processed = 0
            w_batch = []
            w_context_batch = []
            w_tail_id = offset
            w_head_id = head_id
            
            async for msg_data in self.client.iter_messages(entity, limit=limit, offset_id=offset, from_user=from_user_id):
                if self.storage.should_stop():
                    break
                # 1. Respect worker boundary
                if msg_data.message_id <= stop_id:
                    break
                
                # 2. Skip already synced blocks if this is a broad worker
                if not force_resync and role == "TAIL" and tail_id > 0 and tail_id < msg_data.message_id <= head_id:
                    continue 

                if active_deep:
                    # OPTIMIZATION: Skip context extraction if message is already linked to this target
                    if not force_resync and self.storage.has_target_link(chat_id, msg_data.message_id, uid):
                        w_processed += 1
                        if w_processed % 100 == 0:
                            await draw_status(f"(Skipping cached: {msg_data.message_id})")
                        continue

                    # OPTIMIZATION: Stop immediately on signal
                    if self.storage.should_stop(): 
                        break

                    w_context_batch.append(msg_data)
                    if len(w_context_batch) >= context_batch_size:
                        if self.storage.should_stop(): break # Double check
                        
                        await self.context_engine.extract_batch_context(
                            entity, w_context_batch, 
                            target_id=uid,
                            window_size=context_window,
                            max_cluster=max_cluster,
                            recursive_depth=active_depth,
                            on_progress=lambda: draw_status(f"(ID: {msg_data.message_id})")
                        )
                        w_context_batch = []
                        await draw_status(f"(ID: {msg_data.message_id})")
                else:
                    w_batch.append(msg_data)
                
                w_processed += 1
                
                # Update boundaries
                if role == "TAIL":
                    w_tail_id = msg_data.message_id
                else:
                    w_head_id = max(w_head_id, msg_data.message_id)
                
                # Periodically update status even if not saving yet
                if w_processed % 20 == 0:
                    await draw_status(f"(ID: {msg_data.message_id})")

                if len(w_batch) >= batch_size:
                    await self.storage.save_messages(w_batch, target_id=uid)
                    # Update DB state
                    if role == "TAIL" and offset <= (tail_id or current_max):
                        self.storage.update_sync_tail(chat_id, uid, w_tail_id, is_complete=False)
                    elif role == "HEAD":
                        self.storage.update_last_msg_id(chat_id, uid, w_head_id)
                    
                    telemetry.track_messages(len(w_batch))
                    w_batch = []
                    await draw_status()

            # Final flushes for worker
            if active_deep and w_context_batch:
                await self.context_engine.extract_batch_context(
                    entity, w_context_batch, 
                    target_id=uid,
                    window_size=context_window,
                    max_cluster=max_cluster,
                    recursive_depth=active_depth,
                    on_progress=draw_status
                )
            if w_batch:
                await self.storage.save_messages(w_batch, target_id=uid)
                if role == "TAIL" and offset <= (tail_id or current_max):
                    self.storage.update_sync_tail(chat_id, uid, w_tail_id, is_complete=(w_tail_id <= 10))
                elif role == "HEAD":
                    self.storage.update_last_msg_id(chat_id, uid, w_head_id)
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
            results = await asyncio.gather(*[scan_worker(r["offset"], r["stop"], role=r["role"]) for r in ranges])
            total_processed = sum(results)
        finally:
            done_event.set()
            await status_task
            await draw_status()
            
        # 4. Final summary
        db_count = self.storage.get_message_count(chat_id, target_id=uid)
        sys.stdout.write(f"\r   ✅ Export Finished! Total in DB: {db_count} messages.               \n")
        sys.stdout.flush()
        
        return total_processed

    async def sync_all_dialogs_for_user(self, from_user_id: int, 
                                       target_chat_ids: Optional[Set[Any]] = None,
                                       limit: Optional[int] = None, 
                                       deep_mode: bool = False,
                                       force_resync: bool = False,
                                       context_window: int = 3,
                                       max_cluster: int = 20,
                                       recursive_depth: int = 3):
        """
        Scans specified dialogs (from config or all) for a specific user's messages.
        """
        if target_chat_ids:
            print(f"\n🎯 [Targeted Search for User ID: {from_user_id} in {len(target_chat_ids)} pre-defined chats]")
            # Resolve specific entities from IDs/usernames
            targets = []
            for cid in target_chat_ids:
                try:
                    # Resolve string IDs to int if they are numeric
                    if isinstance(cid, str) and (cid.startswith('-') or cid.isdigit()):
                        try: resolved_cid = int(cid)
                        except ValueError: resolved_cid = cid
                    else:
                        resolved_cid = cid
                        
                    ent = await self.client.get_entity(resolved_cid)
                    targets.append(ent)
                except Exception as e:
                    logger.warning(f"Could not resolve config chat {cid}: {e}")
        else:
            print(f"\n🌍 [Searching all dialogs for User ID: {from_user_id}]")
            dialogs = await self.client.get_dialogs()
            # Filter for groups and supergroups only
            targets = [d.entity for d in dialogs if (d.is_group or d.is_channel) and not getattr(d.entity, 'broadcast', False)]
        
        print(f"   Scanning {len(targets)} dialogues...")
        
        total_processed = 0
        for i, dialog in enumerate(targets):
            try:
                dialog_title = self._get_entity_name(dialog)
                print(f"\n   --- [{i+1}/{len(targets)}] Scan: \"{dialog_title}\" ---")
                
                processed = await self.sync_chat(
                    dialog,
                    from_user_id=from_user_id,
                    limit=limit,
                    deep_mode=deep_mode,
                    force_resync=force_resync,
                    context_window=context_window,
                    max_cluster=max_cluster,
                    recursive_depth=recursive_depth
                )
                total_processed += processed
                # Small pause to be friendly
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error scanning dialog {getattr(dialog, 'name', 'Unknown')}: {e}")
        
        print(f"\n✅ Global Export Finished! Total synced: {total_processed} messages across all dialogs.")
        return total_processed

    async def sync_all_outdated(self, threshold_seconds: int = 86400) -> Set[int]:
        """Runs synchronization for all chats that haven't been updated in a while or are incomplete."""
        outdated = self.storage.get_outdated_chats(threshold_seconds=threshold_seconds)
        updated_uids = set()
        
        if not outdated:
            return updated_uids

        print(f"\n🔄 [Updating {len(outdated)} items...]")
        
        for chat_id, from_user_id in outdated:
            entity = await self.client.get_entity(chat_id)
            if entity:
                await self.sync_chat(entity, from_user_id=from_user_id)
                updated_uids.add(from_user_id)
                
        telemetry.log_summary()
        return updated_uids
