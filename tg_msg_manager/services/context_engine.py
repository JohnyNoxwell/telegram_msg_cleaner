import asyncio
import uuid
import logging
from typing import List, Optional, Any, Dict, Set, Tuple
from ..core.telegram.interface import TelegramClientInterface
from ..infrastructure.storage.interface import BaseStorage
from ..core.models.message import MessageData

logger = logging.getLogger(__name__)

class DeepModeEngine:
    """
    Implements high-performance 'Deep Mode' logic with parallel processing and recursion.
    """

    def __init__(self, client: TelegramClientInterface, storage: BaseStorage, max_concurrency: int = 15):
        self.client = client
        self.storage = storage
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._processed_ids: Set[Tuple[int, int]] = set()

    def reset(self):
        """Clears per-run processed state so separate syncs do not leak into each other."""
        self._processed_ids.clear()

    @staticmethod
    def _message_key(chat_id: int, message_id: int) -> Tuple[int, int]:
        return (chat_id, message_id)

    async def extract_batch_context(self, entity: Any, target_messages: List[MessageData], 
                                  target_id: Optional[int] = None,
                                  window_size: int = 3, max_cluster: int = 20, 
                                  recursive_depth: int = 3,
                                  on_progress: Optional[Any] = None):
        """
        Recursively extracts context (replies and neighbors) for a batch of messages.
        Maximum acceleration via parallel execution and batching.
        """
        if not target_messages or recursive_depth <= 0:
            return

        chat_id = target_messages[0].chat_id
        
        # 1. Assign clusters to targets and save them
        clusters = {}
        clustered_targets: List[MessageData] = []
        for msg in target_messages:
            msg_key = self._message_key(msg.chat_id, msg.message_id)
            if msg_key in self._processed_ids:
                continue
            self._processed_ids.add(msg_key)
            c_id = msg.context_group_id or str(uuid.uuid4())
            clusters[msg.message_id] = c_id
            clustered_targets.append(self._with_cluster(msg, c_id))

        if clustered_targets:
            await self.storage.save_messages(clustered_targets, target_id=target_id)

        if on_progress: await on_progress()

        if not clusters:
            return

        # 2. Parallel Workloads (Bulk Optimized)
        tasks = []
        
        # We group targets into "Density Clusters" - ranges of IDs that can be fetched in one go
        ranges = self._calculate_ranges(list(clusters.keys()), window_size * 2 + 5) # Buffer for replies
        for start_id, end_id in ranges:
            tasks.append(self._prefetch_context_slice(entity, start_id, end_id, clusters, window_size, target_id, on_progress))

        # -- Task B: Fetch Parent Replies (Still needed if parents are far away) --
        parent_reply_ids = {
            m.reply_to_id
            for m in target_messages
            if m.reply_to_id and self._message_key(chat_id, m.reply_to_id) not in self._processed_ids
        }
        if parent_reply_ids:
            missing_parent_ids = self.storage.filter_existing_ids(chat_id, list(parent_reply_ids))
            if missing_parent_ids:
                tasks.append(self._fetch_parent_replies(entity, missing_parent_ids, clusters, target_messages, target_id, on_progress))
            else:
                tasks.append(self._load_and_associate_parents(chat_id, list(parent_reply_ids), clusters, target_messages, target_id, on_progress))

        # Run all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect new context messages for recursion
        newly_found: List[MessageData] = []
        for res in results:
            if isinstance(res, list):
                # Filter out ones we've already seen to prevent cycles
                candidates = [
                    m
                    for m in res
                    if self._message_key(m.chat_id, m.message_id) not in self._processed_ids
                ]
                newly_found.extend(candidates)
            elif isinstance(res, Exception):
                logger.error(f"Error in context task: {res}")

        # 3. Recursion: Dive deeper if needed
        if recursive_depth > 1 and newly_found:
            # We don't want to explode too much, so we limit the recursion branch
            # but for this specific request we go full depth -3
            await self.extract_batch_context(
                entity, newly_found[:100], # Limit branch width per step for stability
                target_id=target_id,
                window_size=max(1, window_size - 1), # Narrow window as we go deeper
                max_cluster=max_cluster,
                recursive_depth=recursive_depth - 1,
                on_progress=on_progress
            )

    async def _prefetch_context_slice(self, entity: Any, start_id: int, end_id: int, 
                                    clusters: Dict[int, str], window: int, 
                                    target_id: Optional[int] = None,
                                    on_progress: Optional[Any] = None) -> List[MessageData]:
        """
        Hyper-Acceleration: Fetches a bulk slice of history to find neighbors and replies LOCALLY.
        Eliminates the need for dozens of individual search/replies requests.
        """
        all_msgs = []
        # Expand the slice a bit to catch more replies
        fetch_start = max(1, start_id)
        fetch_limit = end_id - fetch_start + 1 + 50 # Extra buffer for newer replies
        
        async with self.semaphore:
            # GetHistory is much faster and less flood-prone than Search/GetReplies
            async for msg_data in self.client.iter_messages(entity, limit=fetch_limit, offset_id=end_id + 25):
                all_msgs.append(msg_data)

        found_context = []
        for m in all_msgs:
            if self._message_key(m.chat_id, m.message_id) in self._processed_ids:
                continue
            
            associated = False
            # Check if it's a neighbor of ANY target in this cluster
            for t_id, c_id in clusters.items():
                if abs(m.message_id - t_id) <= window:
                    m = self._with_cluster(m, c_id)
                    found_context.append(m)
                    associated = True
                    break
            
            # Check if it's a reply TO any target in this cluster (if not already added as neighbor)
            if not associated and m.reply_to_id in clusters:
                c_id = clusters[m.reply_to_id]
                m = self._with_cluster(m, c_id)
                found_context.append(m)
        
        if found_context:
            await self.storage.save_messages(found_context, target_id=target_id)
            if on_progress: await on_progress()
        
        return found_context

    async def _fetch_parent_replies(self, entity: Any, ids: List[int], 
                                     clusters: Dict[int, str], target_messages: List[MessageData], 
                                     target_id: Optional[int] = None,
                                     on_progress: Optional[Any] = None) -> List[MessageData]:
        """Fetches the messages that the targets are replying to."""
        if not ids: return []
        try:
            async with self.semaphore:
                msgs = await self.client.get_messages(entity, message_ids=ids)
            
            results = []
            for m in msgs:
                if m:
                    # Associate with the correct cluster(s)
                    for tm in target_messages:
                        if tm.reply_to_id == m.message_id:
                            c_id = clusters.get(tm.message_id)
                            if c_id:
                                m_clustered = self._with_cluster(m, c_id)
                                results.append(m_clustered)
            if results:
                await self.storage.save_messages(results, target_id=target_id)
            
            if results and on_progress: await on_progress()
            return results
        except Exception as e:
            if "FloodWait" in str(e):
                logger.debug(f"FloodWait during get_messages: {e}. Slowing down.")
                await asyncio.sleep(getattr(e, 'seconds', 5))
                return await self._fetch_parent_replies(
                    entity,
                    ids,
                    clusters,
                    target_messages,
                    target_id=target_id,
                    on_progress=on_progress,
                )
            raise e

    async def _load_and_associate_parents(self, chat_id: int, ids: List[int], 
                                          clusters: Dict[int, str], target_messages: List[MessageData],
                                          target_id: Optional[int] = None,
                                          on_progress: Optional[Any] = None) -> List[MessageData]:
        """Loads messages from storage and associates them with new clusters."""
        results = []
        for mid in ids:
            m = await asyncio.to_thread(self.storage.get_message, chat_id, mid)
            if m:
                for tm in target_messages:
                    if tm.reply_to_id == m.message_id:
                        c_id = clusters.get(tm.message_id)
                        if c_id:
                            m_clustered = self._with_cluster(m, c_id)
                            results.append(m_clustered)
        if results:
            await self.storage.save_messages(results, target_id=target_id)
        return results

    def _calculate_ranges(self, ids: List[int], window: int) -> List[tuple]:
        """Merges nearby message IDs into continuous ranges."""
        if not ids: return []
        sorted_ids = sorted(ids)
        ranges = []
        curr_start = sorted_ids[0] - window
        curr_end = sorted_ids[0] + window
        for i in range(1, len(sorted_ids)):
            next_start = sorted_ids[i] - window
            next_end = sorted_ids[i] + window
            if next_start <= curr_end + 2:
                curr_end = max(curr_end, next_end)
            else:
                ranges.append((max(1, curr_start), curr_end))
                curr_start = next_start
                curr_end = next_end
        ranges.append((max(1, curr_start), curr_end))
        return ranges

    def _with_cluster(self, msg: MessageData, cluster_id: str) -> MessageData:
        from dataclasses import replace
        return replace(msg, context_group_id=cluster_id)

    async def extract_context(self, entity: Any, target_msg: MessageData, window_size: int = 5, max_cluster: int = 10) -> str:
        # Clear processed state for new single call
        self.reset()
        await self.extract_batch_context(entity, [target_msg], window_size, max_cluster, recursive_depth=3)
        return ""
