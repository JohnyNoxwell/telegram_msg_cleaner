import sys
import asyncio
import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Optional, Any, Set, List, Dict, Awaitable, Callable, AsyncIterator
from ..core.telegram.interface import TelegramClientInterface
from ..core.service_events import ServiceEventSink, emit_service_event
from ..infrastructure.storage.interface import ExportStorage
from ..core.context import set_chat_id
from ..core.telemetry import telemetry
from .context_engine import DeepModeEngine
from ..utils.ui import UI
from ..i18n import _

logger = logging.getLogger(__name__)


@dataclass
class _ScanWorkerState:
    processed: int = 0
    batch: List[Any] = field(default_factory=list)
    context_batch: List[Any] = field(default_factory=list)
    scan_buffer: List[Any] = field(default_factory=list)
    tail_id: Optional[int] = None
    head_id: int = 0
    head_scan_complete: bool = False
    tail_scan_complete: bool = False


@dataclass
class _TrackedTargetPlan:
    chat_id: int
    from_user_id: int
    effective_from_user_id: Optional[int]
    entity: Any
    current_max: int
    target_status: Dict[str, Any]
    last_msg_id: int
    is_complete: bool
    prefetched_messages: Optional[List[Any]] = None
    prefetched_head_complete: bool = False

class ExportService:
    """
    Orchestrates the export and synchronization of Telegram messages.
    Links the API abstraction layer with the Storage layer.
    """

    def __init__(
        self,
        client: TelegramClientInterface,
        storage: ExportStorage,
        event_sink: ServiceEventSink = None,
    ):
        self.client = client
        self.storage = storage
        self.context_engine = DeepModeEngine(client, storage)
        self.event_sink = event_sink

    def _emit_event(self, event_name: str, **payload: Any) -> None:
        emit_service_event(self.event_sink, event_name, **payload)

    # UI.format_name handles entity formatting

    def request_stop(self):
        """Sets the shutdown event to signal workers to stop."""
        self.storage.request_stop()

    @staticmethod
    def _partition_descending_ranges(
        upper_id: int,
        lower_id: int,
        parts: int,
        role: str,
    ) -> List[Dict[str, int]]:
        if upper_id < lower_id or upper_id <= 0 or parts <= 0:
            return []

        total = upper_id - lower_id + 1
        step = max(1, (total + parts - 1) // parts)
        ranges: List[Dict[str, int]] = []
        current_upper = upper_id

        while current_upper >= lower_id:
            current_lower = max(lower_id, current_upper - step + 1)
            ranges.append({"upper": current_upper, "lower": current_lower, "role": role})
            current_upper = current_lower - 1

        return ranges

    def _build_scan_ranges(
        self,
        current_max: int,
        head_id: int,
        tail_id: int,
        is_complete: bool,
        limit: Optional[int] = None,
        history_workers: int = 4,
        allow_history: bool = True,
    ) -> List[Dict[str, int]]:
        if current_max <= 0:
            return []

        first_full_sync = head_id <= 0 and tail_id <= 0 and not is_complete
        if limit is not None:
            if current_max > head_id and head_id > 0:
                return [{"upper": current_max, "lower": head_id + 1, "role": "HEAD"}]
            history_upper = current_max if first_full_sync else (tail_id - 1 if tail_id > 0 else head_id - 1)
            if allow_history and history_upper >= 1 and not is_complete:
                return [{"upper": history_upper, "lower": 1, "role": "TAIL"}]
            return []

        if first_full_sync and allow_history:
            return self._partition_descending_ranges(current_max, 1, history_workers, "TAIL")

        ranges: List[Dict[str, int]] = []
        if current_max > head_id and head_id > 0:
            ranges.append({"upper": current_max, "lower": head_id + 1, "role": "HEAD"})

        if allow_history and not is_complete:
            history_upper = tail_id - 1 if tail_id > 0 else head_id - 1
            if history_upper >= 1:
                ranges.extend(self._partition_descending_ranges(history_upper, 1, history_workers, "TAIL"))

        if not ranges and current_max > head_id:
            ranges.append({"upper": current_max, "lower": max(1, head_id + 1), "role": "HEAD"})

        return ranges

    @staticmethod
    def _resolve_tail_progress_checkpoint(tail_results: List[Dict[str, Any]]) -> Optional[int]:
        """
        Resolve the lowest contiguous history point we can safely checkpoint.

        Tail workers scan disjoint descending ranges. After interruption we must not
        claim progress for lower ranges if an earlier (higher) range was never
        covered, otherwise resume could skip history gaps. We therefore only advance
        the tail checkpoint across the highest contiguous prefix of completed or
        partially processed ranges.
        """
        if not tail_results:
            return None

        ordered = sorted(tail_results, key=lambda item: item["upper"], reverse=True)
        checkpoint = None
        for result in ordered:
            if result.get("tail_scan_complete"):
                checkpoint = result["lower"]
                continue

            tail_cursor = result.get("tail")
            if tail_cursor is not None:
                checkpoint = tail_cursor
            break

        return checkpoint

    def _build_sync_header_payload(
        self,
        *,
        chat_title: str,
        user_label: str,
        mode_str: str,
        status_str: str,
    ) -> Dict[str, str]:
        return {
            "chat_title": chat_title,
            "user_label": user_label,
            "mode_str": mode_str,
            "status_str": status_str,
        }

    async def _prepare_sync_target(
        self,
        entity: Any,
        *,
        from_user_id: Optional[int],
        deep_mode: bool,
        recursive_depth: int,
        force_resync: bool,
        resume_history: bool,
        resolve_user_entity: bool,
    ) -> Dict[str, Any]:
        chat_id = getattr(entity, "id", 0)
        chat_title = UI.format_name(entity)
        set_chat_id(chat_id)
        self.storage.upsert_chat(chat_id, chat_title, chat_type=getattr(entity, "_", None))

        uid = from_user_id or chat_id
        target_name = chat_title
        user_label = ""
        status = self.storage.get_sync_status(chat_id, uid)
        api_from_user = from_user_id
        local_sender_filter_id = None

        if from_user_id:
            if resolve_user_entity:
                try:
                    user_ent = await self.client.get_entity(from_user_id)
                    target_name = UI.format_name(user_ent)
                    user_label = target_name
                    api_from_user = user_ent
                    self.storage.upsert_user(
                        user_id=user_ent.id,
                        first_name=getattr(user_ent, "first_name", None),
                        last_name=getattr(user_ent, "last_name", None),
                        username=getattr(user_ent, "username", None),
                    )
                except Exception as e:
                    logger.warning(f"Could not resolve user {from_user_id}: {e}")
                    user_label = str(from_user_id)
                    api_from_user = None
                    local_sender_filter_id = from_user_id
            else:
                target_name = status.get("author_name") or str(from_user_id)
                user_label = target_name

        saved_deep = bool(status.get("deep_mode", 0))
        saved_depth = status.get("recursive_depth", 0)
        active_deep = deep_mode or saved_deep
        active_depth = recursive_depth if recursive_depth > 0 else (saved_depth if saved_depth > 0 else 2)

        head_id = 0 if force_resync else status["last_msg_id"]
        tail_id = 0 if force_resync else status["tail_msg_id"]
        is_complete = 0 if force_resync else status["is_complete"]

        self.storage.register_target(
            uid,
            target_name,
            chat_id,
            deep_mode=active_deep,
            recursive_depth=active_depth,
        )

        if active_deep:
            self.context_engine.reset()

        mode_str = f"DEEP (Depth {active_depth})" if active_deep else "FLAT"
        status_str = ""
        if resume_history and tail_id > 0 and not is_complete:
            status_str = _("text_resuming_history")
        elif head_id > 0:
            status_str = _("text_updating")

        return {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "uid": uid,
            "status": status,
            "api_from_user": api_from_user,
            "local_sender_filter_id": local_sender_filter_id,
            "active_deep": active_deep,
            "active_depth": active_depth,
            "head_id": head_id,
            "tail_id": tail_id,
            "is_complete": is_complete,
            "mode_str": mode_str,
            "header_payload": self._build_sync_header_payload(
                chat_title=chat_title,
                user_label=user_label,
                mode_str=mode_str,
                status_str=status_str,
            ),
        }

    def _apply_sync_scan_results(
        self,
        *,
        chat_id: int,
        uid: int,
        results: List[Dict[str, Any]],
        tail_range_count: int,
        is_complete: bool,
    ) -> None:
        completed_heads = [r["upper"] for r in results if r.get("head_scan_complete")]
        if completed_heads:
            self.storage.update_last_msg_id(chat_id, uid, max(completed_heads))
            telemetry.track_counter("sync.head_ranges_completed", len(completed_heads))

        tail_results = [r for r in results if r["role"] == "TAIL"]
        completed_tails = [r["lower"] for r in tail_results if r.get("tail_scan_complete")]
        tail_progress = self._resolve_tail_progress_checkpoint(tail_results)
        if tail_progress is not None:
            self.storage.update_sync_tail(chat_id, uid, tail_progress, is_complete=False)
        if completed_tails:
            telemetry.track_counter("sync.tail_ranges_completed", len(completed_tails))

        if self.storage.should_stop() or is_complete or not tail_results:
            return

        if tail_range_count > 1:
            if len(completed_tails) == tail_range_count:
                self.storage.update_sync_tail(chat_id, uid, 0, is_complete=True)
                self._emit_event("export.history_fully_synced")
            return

        tails = [r["tail"] for r in tail_results if r["tail"] is not None]
        min_tail = None
        if completed_tails:
            min_tail = min(completed_tails)
        elif tails:
            min_tail = min(tails)
        if min_tail is not None and min_tail <= 10:
            self.storage.update_sync_tail(chat_id, uid, 0, is_complete=True)
            self._emit_event("export.history_fully_synced")

    def _resolve_new_target_link_ids(
        self,
        *,
        chat_id: int,
        uid: int,
        messages: List[Any],
        force_resync: bool,
    ) -> Set[int]:
        started_at = perf_counter()
        if force_resync or not messages:
            resolved = {msg.message_id for msg in messages}
            telemetry.track_counter("sync.target_link_lookup.fast_path", len(resolved))
            telemetry.track_duration("sync.target_link_lookup.total", perf_counter() - started_at)
            return resolved

        message_ids = [msg.message_id for msg in messages]
        filter_missing = getattr(self.storage, "filter_missing_target_links", None)
        missing = None
        if callable(filter_missing):
            try:
                result = filter_missing(chat_id, uid, message_ids)
            except TypeError:
                result = None
            if isinstance(result, list):
                missing = set(result)

        if missing is None:
            missing = {
                msg.message_id
                for msg in messages
                if not self.storage.has_target_link(chat_id, msg.message_id, uid)
            }
        telemetry.track_counter("sync.target_link_lookup.batches", 1)
        telemetry.track_counter("sync.target_link_lookup.candidates", len(message_ids))
        telemetry.track_counter("sync.target_link_lookup.missing", len(missing))
        telemetry.track_duration("sync.target_link_lookup.total", perf_counter() - started_at)
        return missing

    def _checkpoint_worker_progress(
        self,
        *,
        chat_id: int,
        uid: int,
        role: str,
        can_checkpoint_tail: bool,
        worker_state: _ScanWorkerState,
    ) -> None:
        if role == "TAIL" and can_checkpoint_tail and worker_state.tail_id is not None:
            self.storage.update_sync_tail(chat_id, uid, worker_state.tail_id, is_complete=False)
        elif role == "HEAD":
            self.storage.update_last_msg_id(chat_id, uid, worker_state.head_id)

    async def _flush_flat_worker_batch(
        self,
        *,
        chat_id: int,
        uid: int,
        role: str,
        can_checkpoint_tail: bool,
        worker_state: _ScanWorkerState,
        progress_stats: Dict[str, int],
        draw_status: Callable[[str], Awaitable[None]],
    ) -> None:
        if not worker_state.batch:
            return

        batch_started = perf_counter()
        await self.storage.save_messages(worker_state.batch, target_id=uid, flush=False)
        telemetry.track_duration("sync.flat_batch_save.total", perf_counter() - batch_started)
        progress_stats["linked"] += len(worker_state.batch)
        telemetry.track_counter("sync.flat_batches", 1)
        telemetry.track_counter("sync.flat_messages", len(worker_state.batch))
        self._checkpoint_worker_progress(
            chat_id=chat_id,
            uid=uid,
            role=role,
            can_checkpoint_tail=can_checkpoint_tail,
            worker_state=worker_state,
        )
        telemetry.track_messages(len(worker_state.batch))
        worker_state.batch = []
        await draw_status()

    async def _flush_deep_worker_batch(
        self,
        *,
        entity: Any,
        chat_id: int,
        uid: int,
        role: str,
        can_checkpoint_tail: bool,
        worker_state: _ScanWorkerState,
        progress_stats: Dict[str, int],
        context_window: int,
        max_cluster: int,
        active_depth: int,
        draw_status: Callable[[str], Awaitable[None]],
    ) -> None:
        if not worker_state.context_batch:
            return

        batch_size_now = len(worker_state.context_batch)
        saved_count = await self.context_engine.extract_batch_context(
            entity,
            worker_state.context_batch,
            target_id=uid,
            window_size=context_window,
            max_cluster=max_cluster,
            recursive_depth=active_depth,
            on_progress=draw_status,
        )
        progress_stats["linked"] += saved_count
        telemetry.track_counter("sync.deep_batches", 1)
        telemetry.track_counter("sync.deep_messages", batch_size_now)
        self._checkpoint_worker_progress(
            chat_id=chat_id,
            uid=uid,
            role=role,
            can_checkpoint_tail=can_checkpoint_tail,
            worker_state=worker_state,
        )
        worker_state.context_batch = []

    async def _process_scan_buffer(
        self,
        *,
        entity: Any,
        chat_id: int,
        uid: int,
        role: str,
        force_resync: bool,
        active_deep: bool,
        active_depth: int,
        context_window: int,
        max_cluster: int,
        batch_size: int,
        context_batch_size: int,
        can_checkpoint_tail: bool,
        worker_state: _ScanWorkerState,
        progress_stats: Dict[str, int],
        draw_status: Callable[[str], Awaitable[None]],
    ) -> None:
        if not worker_state.scan_buffer:
            return

        missing_ids = self._resolve_new_target_link_ids(
            chat_id=chat_id,
            uid=uid,
            messages=worker_state.scan_buffer,
            force_resync=force_resync,
        )
        for msg_data in worker_state.scan_buffer:
            is_new = msg_data.message_id in missing_ids
            if not is_new and not force_resync:
                progress_stats["skipped"] += 1
                if progress_stats["skipped"] % 100 == 0:
                    await draw_status()
                continue

            if active_deep:
                if self.storage.should_stop():
                    break

                worker_state.context_batch.append(msg_data)
                if len(worker_state.context_batch) >= context_batch_size:
                    if self.storage.should_stop():
                        break

                    saved_count = await self.context_engine.extract_batch_context(
                        entity,
                        worker_state.context_batch,
                        target_id=uid,
                        window_size=context_window,
                        max_cluster=max_cluster,
                        recursive_depth=active_depth,
                        on_progress=lambda: draw_status(f"(ID: {msg_data.message_id})"),
                    )
                    progress_stats["linked"] += saved_count
                    telemetry.track_counter("sync.deep_batches", 1)
                    telemetry.track_counter("sync.deep_messages", len(worker_state.context_batch))
                    worker_state.context_batch = []
                    await draw_status()
            else:
                worker_state.batch.append(msg_data)

            worker_state.processed += 1
            progress_stats["processed"] += 1

            if role == "TAIL":
                worker_state.tail_id = msg_data.message_id
            else:
                worker_state.head_id = max(worker_state.head_id, msg_data.message_id)

            if worker_state.processed % 50 == 0:
                await draw_status()

            if len(worker_state.batch) >= batch_size:
                await self._flush_flat_worker_batch(
                    chat_id=chat_id,
                    uid=uid,
                    role=role,
                    can_checkpoint_tail=can_checkpoint_tail,
                    worker_state=worker_state,
                    progress_stats=progress_stats,
                    draw_status=draw_status,
                )

        worker_state.scan_buffer = []

    @staticmethod
    async def _iter_prefetched_messages(messages: List[Any]) -> AsyncIterator[Any]:
        for message in messages:
            yield message

    async def _scan_range(
        self,
        *,
        entity: Any,
        upper_id: int,
        lower_id: int,
        role: str,
        chat_id: int,
        uid: int,
        head_id: int,
        tail_id: int,
        api_from_user: Optional[Any],
        from_user_id: Optional[int],
        local_sender_filter_id: Optional[int],
        force_resync: bool,
        active_deep: bool,
        active_depth: int,
        context_window: int,
        max_cluster: int,
        batch_size: int,
        context_batch_size: int,
        single_worker_limit: Optional[int],
        can_checkpoint_tail: bool,
        prefetched_messages: Optional[List[Any]],
        prefetched_head_complete: bool,
        progress_stats: Dict[str, int],
        draw_status: Callable[[str], Awaitable[None]],
    ) -> Dict[str, Any]:
        worker_state = _ScanWorkerState(head_id=head_id)

        prefetched_iter = None
        if role == "HEAD" and prefetched_messages is not None:
            telemetry.track_counter("sync.prefetched_head.used", 1)
            prefetched_iter = prefetched_messages

        if prefetched_iter is None:
            message_stream = self.client.iter_messages(
                entity,
                limit=single_worker_limit,
                offset_id=upper_id + 1,
                from_user=api_from_user,
            )
        else:
            message_stream = self._iter_prefetched_messages(prefetched_iter)

        async for msg_data in message_stream:
            if self.storage.should_stop():
                break

            if msg_data.message_id < lower_id:
                if role == "HEAD" and single_worker_limit is None:
                    worker_state.head_scan_complete = True
                if role == "TAIL" and single_worker_limit is None:
                    worker_state.tail_scan_complete = True
                break

            if (prefetched_iter is not None or local_sender_filter_id is not None) and from_user_id and msg_data.user_id != from_user_id:
                continue

            if not force_resync and role == "TAIL" and tail_id > 0 and tail_id < msg_data.message_id <= head_id:
                continue
            worker_state.scan_buffer.append(msg_data)
            if len(worker_state.scan_buffer) >= 100:
                await self._process_scan_buffer(
                    entity=entity,
                    chat_id=chat_id,
                    uid=uid,
                    role=role,
                    force_resync=force_resync,
                    active_deep=active_deep,
                    active_depth=active_depth,
                    context_window=context_window,
                    max_cluster=max_cluster,
                    batch_size=batch_size,
                    context_batch_size=context_batch_size,
                    can_checkpoint_tail=can_checkpoint_tail,
                    worker_state=worker_state,
                    progress_stats=progress_stats,
                    draw_status=draw_status,
                )

        if (
            role == "HEAD"
            and single_worker_limit is None
            and not self.storage.should_stop()
            and (prefetched_iter is None or prefetched_head_complete)
        ):
            worker_state.head_scan_complete = True
        if role == "TAIL" and single_worker_limit is None and not self.storage.should_stop():
            worker_state.tail_scan_complete = True

        await self._process_scan_buffer(
            entity=entity,
            chat_id=chat_id,
            uid=uid,
            role=role,
            force_resync=force_resync,
            active_deep=active_deep,
            active_depth=active_depth,
            context_window=context_window,
            max_cluster=max_cluster,
            batch_size=batch_size,
            context_batch_size=context_batch_size,
            can_checkpoint_tail=can_checkpoint_tail,
            worker_state=worker_state,
            progress_stats=progress_stats,
            draw_status=draw_status,
        )
        if active_deep:
            await self._flush_deep_worker_batch(
                entity=entity,
                chat_id=chat_id,
                uid=uid,
                role=role,
                can_checkpoint_tail=can_checkpoint_tail,
                worker_state=worker_state,
                progress_stats=progress_stats,
                context_window=context_window,
                max_cluster=max_cluster,
                active_depth=active_depth,
                draw_status=draw_status,
            )
        await self._flush_flat_worker_batch(
            chat_id=chat_id,
            uid=uid,
            role=role,
            can_checkpoint_tail=can_checkpoint_tail,
            worker_state=worker_state,
            progress_stats=progress_stats,
            draw_status=draw_status,
        )

        return {
            "processed": worker_state.processed,
            "tail": worker_state.tail_id,
            "head": worker_state.head_id,
            "head_scan_complete": worker_state.head_scan_complete,
            "tail_scan_complete": worker_state.tail_scan_complete,
            "upper": upper_id,
            "lower": lower_id,
            "role": role,
        }

    async def _prefetch_chat_head_messages(
        self,
        entity: Any,
        current_max: int,
        lower_bound: int,
    ) -> tuple[List[Any], bool]:
        """
        Fetch a shared HEAD slice once for a chat and reuse it across many targets.
        Returns the collected messages in descending order and whether the slice
        fully covered the requested lower bound.
        """
        if current_max < lower_bound or current_max <= 0:
            return [], False

        collected: List[Any] = []
        complete = False
        async for msg_data in self.client.iter_messages(
            entity,
            offset_id=current_max + 1,
        ):
            if self.storage.should_stop():
                break
            if msg_data.message_id < lower_bound:
                complete = True
                break
            collected.append(msg_data)
        else:
            complete = True

        telemetry.track_counter("sync.shared_head_prefetch.calls", 1)
        telemetry.track_counter("sync.shared_head_prefetch.messages", len(collected))
        if complete:
            telemetry.track_counter("sync.shared_head_prefetch.complete", 1)
        return collected, complete

    @staticmethod
    def _normalize_target_item(item: Any) -> tuple[int, int]:
        if isinstance(item, tuple) and len(item) == 2:
            return item
        return item, item

    async def _get_or_load_entity(
        self,
        *,
        chat_id: int,
        entity_cache: Dict[int, Any],
    ) -> Optional[Any]:
        entity = entity_cache.get(chat_id)
        if entity is None:
            entity = await self.client.get_entity(chat_id)
            if entity:
                entity_cache[chat_id] = entity
        return entity

    async def _get_or_load_current_max(
        self,
        *,
        chat_id: int,
        entity: Any,
        current_max_cache: Dict[int, int],
    ) -> int:
        current_max = current_max_cache.get(chat_id)
        if current_max is None:
            latest_msg = await self.client.get_messages(entity, limit=1)
            current_max = latest_msg[0].message_id if latest_msg else 1000000
            current_max_cache[chat_id] = current_max
        return current_max

    def _get_cached_sync_status(
        self,
        *,
        chat_id: int,
        target_id: int,
        status_cache: Dict[tuple[int, int], Dict[str, Any]],
    ) -> Dict[str, Any]:
        status_key = (chat_id, target_id)
        status = status_cache.get(status_key)
        if status is None:
            loaded = self.storage.get_sync_status(chat_id, target_id)
            status = loaded if isinstance(loaded, dict) else {}
            status_cache[status_key] = status
        return status

    async def _prime_shared_head_prefetch_cache(
        self,
        *,
        items_by_chat: Dict[int, List[int]],
        entity_cache: Dict[int, Any],
        current_max_cache: Dict[int, int],
        shared_prefetch_cache: Dict[int, tuple[List[Any], bool]],
        status_cache: Dict[tuple[int, int], Dict[str, Any]],
    ) -> None:
        for chat_id, target_ids in items_by_chat.items():
            user_targets = [target_id for target_id in target_ids if target_id != chat_id]
            if len(user_targets) < 2:
                continue

            entity = await self._get_or_load_entity(chat_id=chat_id, entity_cache=entity_cache)
            if entity is None:
                continue

            current_max = await self._get_or_load_current_max(
                chat_id=chat_id,
                entity=entity,
                current_max_cache=current_max_cache,
            )
            lower_bounds = []
            for target_id in user_targets:
                status = self._get_cached_sync_status(
                    chat_id=chat_id,
                    target_id=target_id,
                    status_cache=status_cache,
                )
                last_msg_id = status.get("last_msg_id", 0)
                if (
                    isinstance(current_max, int)
                    and isinstance(last_msg_id, int)
                    and last_msg_id > 0
                    and current_max > last_msg_id
                ):
                    lower_bounds.append(last_msg_id + 1)

            if len(lower_bounds) < 2:
                continue

            shared_prefetch_cache[chat_id] = await self._prefetch_chat_head_messages(
                entity,
                current_max=current_max,
                lower_bound=min(lower_bounds),
            )

    async def _plan_tracked_sync_target(
        self,
        item: Any,
        *,
        entity_cache: Dict[int, Any],
        current_max_cache: Dict[int, int],
        shared_prefetch_cache: Dict[int, tuple[List[Any], bool]],
        status_cache: Dict[tuple[int, int], Dict[str, Any]],
    ) -> Optional[_TrackedTargetPlan]:
        chat_id, from_user_id = self._normalize_target_item(item)
        entity = await self._get_or_load_entity(chat_id=chat_id, entity_cache=entity_cache)
        if entity is None:
            return None

        current_max = await self._get_or_load_current_max(
            chat_id=chat_id,
            entity=entity,
            current_max_cache=current_max_cache,
        )
        target_status = self._get_cached_sync_status(
            chat_id=chat_id,
            target_id=from_user_id,
            status_cache=status_cache,
        )
        last_msg_id = target_status.get("last_msg_id", 0)
        if not isinstance(last_msg_id, int):
            last_msg_id = 0
        is_complete = bool(target_status.get("is_complete", 0))

        effective_from_user_id = None if from_user_id == chat_id else from_user_id
        prefetched_messages = None
        prefetched_head_complete = False
        if effective_from_user_id:
            prefetched = shared_prefetch_cache.get(chat_id)
            if prefetched is not None:
                prefetched_messages, prefetched_head_complete = prefetched

        return _TrackedTargetPlan(
            chat_id=chat_id,
            from_user_id=from_user_id,
            effective_from_user_id=effective_from_user_id,
            entity=entity,
            current_max=current_max,
            target_status=target_status,
            last_msg_id=last_msg_id,
            is_complete=is_complete,
            prefetched_messages=prefetched_messages,
            prefetched_head_complete=prefetched_head_complete,
        )

    def _resolve_target_report_name(
        self,
        *,
        from_user_id: int,
        target_status: Dict[str, Any],
    ) -> str:
        name = target_status.get("author_name") or f"ID:{from_user_id}"
        if not target_status.get("author_name") or target_status.get("author_name").startswith("ID:"):
            user_info = self.storage.get_user(from_user_id)
            if user_info:
                first = user_info.get("first_name") or ""
                last = user_info.get("last_name") or ""
                name = f"{first} {last}".strip() or user_info.get("username") or name
        return name

    def _ensure_user_stats_entry(
        self,
        *,
        user_stats: Dict[int, Dict[str, Any]],
        from_user_id: int,
        target_status: Dict[str, Any],
    ) -> None:
        if from_user_id in user_stats:
            return

        user_stats[from_user_id] = {
            "name": self._resolve_target_report_name(
                from_user_id=from_user_id,
                target_status=target_status,
            ),
            "count": 0,
            "dirty": False,
        }

    async def sync_chat(self, entity: Any, 
                        from_user_id: Optional[int] = None,
                        limit: Optional[int] = None, 
                        deep_mode: bool = False,
                        force_resync: bool = False,
                        context_window: int = 3,
                        max_cluster: int = 20,
                        recursive_depth: int = 0,
                        resume_history: bool = True,
                        current_max_hint: Optional[int] = None,
                        prefetched_messages: Optional[List[Any]] = None,
                        prefetched_head_complete: bool = False,
                        resolve_user_entity: bool = True,
                        emit_summary: bool = True):
        """
        Synchronizes a specific chat with a clean real-time global status counter.
        Now supports Resume and Dual-Sync (New + Historical).
        """
        sync_started = perf_counter()
        sync_ctx = await self._prepare_sync_target(
            entity,
            from_user_id=from_user_id,
            deep_mode=deep_mode,
            recursive_depth=recursive_depth,
            force_resync=force_resync,
            resume_history=resume_history,
            resolve_user_entity=resolve_user_entity,
        )
        chat_id = sync_ctx["chat_id"]
        chat_title = sync_ctx["chat_title"]
        uid = sync_ctx["uid"]
        api_from_user = sync_ctx["api_from_user"]
        local_sender_filter_id = sync_ctx["local_sender_filter_id"]
        active_deep = sync_ctx["active_deep"]
        active_depth = sync_ctx["active_depth"]
        head_id = sync_ctx["head_id"]
        tail_id = sync_ctx["tail_id"]
        is_complete = sync_ctx["is_complete"]
        self._emit_event("export.sync_chat_started", **sync_ctx["header_payload"])
        
        # 5. Determine Scan Boundaries
        # Get the latest message to determine current max
        current_max = current_max_hint
        if current_max is None:
            latest_msg = await self.client.get_messages(entity, limit=1)
            current_max = latest_msg[0].message_id if latest_msg else 1000000
        
        # 6. Parallel Scanning Strategy
        batch_size = 200
        context_batch_size = 50
        single_worker_limit = limit
        ranges = self._build_scan_ranges(
            current_max=current_max,
            head_id=head_id,
            tail_id=tail_id,
            is_complete=bool(is_complete),
            limit=limit,
            allow_history=resume_history or force_resync,
        )
        tail_range_count = sum(1 for item in ranges if item["role"] == "TAIL")
        can_checkpoint_tail = tail_range_count <= 1

        if not ranges:
            if (
                resume_history
                and not is_complete
                and tail_id <= 1
                and current_max <= head_id
                and not self.storage.should_stop()
            ):
                self.storage.update_sync_tail(chat_id, uid, 0, is_complete=True)
                self.storage.update_last_sync_at(chat_id, uid)
            return 0

        initial_db_total = self.storage.get_message_count(chat_id, target_id=uid)

        async def draw_status(extra=""):
            db_total = initial_db_total + progress_stats["linked"]
            self._emit_event(
                "export.sync_progress",
                db_total=db_total,
                extra=extra,
            )

        progress_stats = {"processed": 0, "skipped": 0, "linked": 0}

        async def draw_status_loop():
            """Periodic UI updates to avoid terminal lag."""
            while not done_event.is_set():
                await draw_status()
                await asyncio.sleep(0.5)

        done_event = asyncio.Event()
        status_task = asyncio.create_task(draw_status_loop())
        
        try:
            results = await asyncio.gather(*[
                self._scan_range(
                    entity=entity,
                    upper_id=r["upper"],
                    lower_id=r["lower"],
                    role=r["role"],
                    chat_id=chat_id,
                    uid=uid,
                    head_id=head_id,
                    tail_id=tail_id,
                    api_from_user=api_from_user,
                    from_user_id=from_user_id,
                    local_sender_filter_id=local_sender_filter_id,
                    force_resync=force_resync,
                    active_deep=active_deep,
                    active_depth=active_depth,
                    context_window=context_window,
                    max_cluster=max_cluster,
                    batch_size=batch_size,
                    context_batch_size=context_batch_size,
                    single_worker_limit=single_worker_limit,
                    can_checkpoint_tail=can_checkpoint_tail,
                    prefetched_messages=prefetched_messages,
                    prefetched_head_complete=prefetched_head_complete,
                    progress_stats=progress_stats,
                    draw_status=draw_status,
                )
                for r in ranges
            ])
            total_processed = sum(r["processed"] for r in results)
            self._apply_sync_scan_results(
                chat_id=chat_id,
                uid=uid,
                results=results,
                tail_range_count=tail_range_count,
                is_complete=bool(is_complete),
            )
        finally:
            done_event.set()
            await status_task
            await draw_status()

        flush_started = perf_counter()
        await self.storage.flush()
        telemetry.track_duration("sync.storage_flush.total", perf_counter() - flush_started)
            
        # 4. Final summary
        db_count = self.storage.get_message_count(chat_id, target_id=uid)
        breakdown = self.storage.get_target_message_breakdown(chat_id, uid)
        self._emit_event("export.sync_finished", db_count=db_count)
        
        # Only mark a target as freshly synced after a non-interrupted pass.
        if not self.storage.should_stop():
            self.storage.update_last_sync_at(chat_id, uid)
        elapsed_seconds = perf_counter() - sync_started
        telemetry.track_duration("sync.chat.total", elapsed_seconds)
        telemetry.track_counter("sync.chat.processed_messages", total_processed)
        telemetry.track_counter("sync.chat.linked_messages", progress_stats["linked"])
        telemetry.track_counter("sync.chat.skipped_messages", progress_stats["skipped"])
        logger.info(
            "Chat sync complete",
            extra={
                "event": "sync_chat_complete",
                "metrics": {
                    "chat_id": chat_id,
                    "target_id": uid,
                    "processed": total_processed,
                    "linked": progress_stats["linked"],
                    "skipped": progress_stats["skipped"],
                    "mode": "deep" if active_deep else "flat",
                    "depth": active_depth if active_deep else 0,
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "ranges": len(ranges),
                },
            },
        )
        if emit_summary:
            self._emit_event(
                "export.sync_summary",
                title=UI.format_name(entity),
                own_messages=breakdown["own_messages"],
                with_context=breakdown["with_context"],
            )
        
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
            started_at = perf_counter()
            self._emit_event(
                "export.targeted_dialog_search_started",
                from_user_id=from_user_id,
                dialog_count=len(target_chat_ids),
            )
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
            started_at = perf_counter()
            self._emit_event("export.dialog_search_started", from_user_id=from_user_id)
            dialogs = await self.client.get_dialogs()
            # Filter for groups and supergroups only
            targets = [d.entity for d in dialogs if (d.is_group or d.is_channel) and not getattr(d.entity, 'broadcast', False)]
        
        self._emit_event("export.dialog_search_scanning", dialog_count=len(targets))
        
        total_processed = 0

        for i, dialog in enumerate(targets):
            try:
                dialog_title = UI.format_name(dialog)
                self._emit_event(
                    "export.dialog_scan_started",
                    index=i + 1,
                    total=len(targets),
                    dialog_title=dialog_title,
                )
                
                processed = await self.sync_chat(
                    dialog,
                    from_user_id=from_user_id,
                    limit=limit,
                    deep_mode=deep_mode,
                    force_resync=force_resync,
                    context_window=context_window,
                    max_cluster=max_cluster,
                    recursive_depth=recursive_depth,
                    emit_summary=False
                )
                total_processed += processed
                # Small pause to be friendly
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error scanning dialog {getattr(dialog, 'name', 'Unknown')}: {e}")
        
        self._emit_event("export.global_export_finished", total_processed=total_processed)
        telemetry.track_counter("sync.dialogs.scanned", len(targets))
        telemetry.track_duration("sync.dialogs_for_user.total", perf_counter() - started_at)
        return total_processed

    async def sync_all_outdated(self, threshold_seconds: int = 86400) -> dict:
        """Runs synchronization for all chats that haven't been updated in a while or are incomplete."""
        outdated = self.storage.get_outdated_chats(threshold_seconds=threshold_seconds)
        return await self._sync_target_items(outdated)

    async def sync_all_tracked(self) -> dict:
        """Runs synchronization for every tracked primary target."""
        targets = self.storage.get_primary_targets()
        items = [(item["chat_id"], item["user_id"]) for item in targets]
        return await self._sync_target_items(items)

    async def _sync_target_items(self, items: list) -> dict:
        """Synchronize a list of target tuples in `(chat_id, user_id)` form."""
        user_stats = {} # user_id -> {"name": str, "count": int, "dirty": bool}
        entity_cache: Dict[int, Any] = {}
        current_max_cache: Dict[int, int] = {}
        shared_prefetch_cache: Dict[int, tuple[List[Any], bool]] = {}
        status_cache: Dict[tuple[int, int], Dict[str, Any]] = {}

        if not items:
            return user_stats

        self._emit_event("export.tracked_update_started", target_count=len(items))

        started_at = perf_counter()
        telemetry.track_counter("sync.tracked_items.total", len(items))
        items_by_chat: Dict[int, List[int]] = {}
        for item in items:
            chat_id, from_user_id = self._normalize_target_item(item)
            items_by_chat.setdefault(chat_id, []).append(from_user_id)

        await self._prime_shared_head_prefetch_cache(
            items_by_chat=items_by_chat,
            entity_cache=entity_cache,
            current_max_cache=current_max_cache,
            shared_prefetch_cache=shared_prefetch_cache,
            status_cache=status_cache,
        )

        for item in items:
            plan = await self._plan_tracked_sync_target(
                item,
                entity_cache=entity_cache,
                current_max_cache=current_max_cache,
                shared_prefetch_cache=shared_prefetch_cache,
                status_cache=status_cache,
            )
            if plan is None:
                continue

            if (
                isinstance(plan.current_max, int)
                and isinstance(plan.last_msg_id, int)
                and plan.current_max <= plan.last_msg_id
                and plan.is_complete
            ):
                telemetry.track_counter("sync.tracked_items.skipped_up_to_date", 1)
                self._ensure_user_stats_entry(
                    user_stats=user_stats,
                    from_user_id=plan.from_user_id,
                    target_status=plan.target_status,
                )
                continue

            processed = await self.sync_chat(
                plan.entity,
                from_user_id=plan.effective_from_user_id,
                resume_history=not plan.is_complete,
                current_max_hint=plan.current_max,
                prefetched_messages=plan.prefetched_messages,
                prefetched_head_complete=plan.prefetched_head_complete,
                resolve_user_entity=False,
                emit_summary=False,
            )

            self._ensure_user_stats_entry(
                user_stats=user_stats,
                from_user_id=plan.from_user_id,
                target_status=plan.target_status,
            )
            user_stats[plan.from_user_id]["count"] += processed
            if processed > 0:
                user_stats[plan.from_user_id]["dirty"] = True
                telemetry.track_counter("sync.tracked_items.changed", 1)
                
        telemetry.track_duration("sync.all_tracked.total", perf_counter() - started_at)
        telemetry.log_summary("Tracked sync telemetry summary")
        return user_stats
