import os
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Any

from .file_writer import FileRotateWriter
from ..infrastructure.storage.interface import PrivateArchiveStorage
from ..core.telegram.interface import TelegramClientInterface
from ..core.telemetry import telemetry
from ..core.models.message import MessageData
from ..core.models.service_payloads import (
    PrivateArchiveCompletedPayload,
    PrivateArchiveMediaStats,
    PrivateArchiveMediaSavedPayload,
    PrivateArchiveProgressPayload,
    PrivateArchiveStartedPayload,
    PrivateArchiveTransferStats,
)
from ..core.service_events import (
    PrivateArchiveEvents,
    ServiceEventSink,
    emit_service_event,
)
from ..utils.ui import UI

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ArchiveContext:
    user_id: int
    target_name: str
    user_dir: str
    media_dir: str
    chat_log_path: str


class PrivateArchiveService:
    """
    Service for exporting private chats (PMs) with full media downloading capability.
    """

    def __init__(
        self,
        client: TelegramClientInterface,
        storage: PrivateArchiveStorage,
        base_dir: str = "PRIVAT_DIALOGS",
        max_file_size: int = 50 * 1024 * 1024,
        event_sink: ServiceEventSink = None,
    ):
        self.client = client
        self.storage = storage
        self.base_dir = base_dir
        self.max_file_size = max_file_size
        self.download_semaphore = asyncio.Semaphore(3)
        self.event_sink = event_sink

    def _emit_event(self, name: str, **payload: Any) -> None:
        emit_service_event(self.event_sink, name, **payload)

    def _get_user_folder_name(
        self, user_id: int, first_name: str, last_name: str, username: str
    ) -> str:
        name = UI.format_name(
            {
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "user_id": user_id,
            }
        )
        safe_name = (
            "".join(c for c in name if c.isalnum() or c in (" ", "_"))
            .strip()
            .replace(" ", "_")
        )
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

    async def _download_media(
        self, msg_data: MessageData, media_dir: str
    ) -> Optional[str]:
        media_ref = getattr(msg_data, "media_ref", None)
        if media_ref is None:
            return None

        category = self._media_category(msg_data.media_type)
        target_dir = os.path.join(media_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        base_name = f"{msg_data.message_id}"
        target_path = os.path.join(target_dir, base_name)

        return await self.client.download_media(media_ref, file=target_path)

    def _prepare_archive_context(self, user_entity: Any) -> _ArchiveContext:
        user_id = getattr(user_entity, "id", 0)
        first_name = getattr(user_entity, "first_name", "") or ""
        last_name = getattr(user_entity, "last_name", "") or ""
        username = getattr(user_entity, "username", "") or ""

        target_name = UI.format_name(user_entity)
        folder_name = self._get_user_folder_name(
            user_id, first_name, last_name, username
        )
        user_dir = os.path.join(self.base_dir, folder_name)
        media_dir = os.path.join(user_dir, "media")
        chat_log_path = os.path.join(user_dir, "chat_log.txt")
        return _ArchiveContext(
            user_id=user_id,
            target_name=target_name,
            user_dir=user_dir,
            media_dir=media_dir,
            chat_log_path=chat_log_path,
        )

    def _ensure_archive_dirs(self, media_dir: str) -> None:
        for sub in ("photos", "videos", "voices", "documents"):
            os.makedirs(os.path.join(media_dir, sub), exist_ok=True)

    @staticmethod
    def _initial_media_stats() -> PrivateArchiveMediaStats:
        return PrivateArchiveMediaStats()

    @staticmethod
    def _initial_archive_stats() -> PrivateArchiveTransferStats:
        return PrivateArchiveTransferStats()

    def _emit_archive_start(
        self, *, target_name: str, user_id: int, user_dir: str, last_id: int
    ) -> None:
        payload = PrivateArchiveStartedPayload(
            target_name=target_name,
            user_id=user_id,
            user_dir=user_dir,
            last_id=last_id,
        )
        self._emit_event(
            PrivateArchiveEvents.STARTED,
            **payload.as_dict(),
        )
        logger.info(f"PM Archive start for {user_id}. Last ID: {last_id}")

    def _emit_archive_progress(
        self,
        *,
        count: int,
        stats: PrivateArchiveMediaStats,
        archive_stats: PrivateArchiveTransferStats,
    ) -> None:
        payload = PrivateArchiveProgressPayload(
            count=count,
            stats=stats,
            archive_stats=archive_stats,
        )
        self._emit_event(
            PrivateArchiveEvents.PROGRESS,
            **payload.as_dict(),
        )

    def _emit_archive_complete(
        self,
        *,
        user_entity: Any,
        count: int,
        stats: PrivateArchiveMediaStats,
        archive_stats: PrivateArchiveTransferStats,
    ) -> None:
        payload = PrivateArchiveCompletedPayload(
            target_name=UI.format_name(user_entity),
            count=count,
            stats=stats,
            archive_stats=archive_stats,
        )
        self._emit_event(
            PrivateArchiveEvents.COMPLETED,
            **payload.as_dict(),
        )

    def _track_media_stats(
        self, stats: PrivateArchiveMediaStats, media_type: Optional[str]
    ) -> None:
        stats.increment(media_type)

    async def _process_archive_media(
        self,
        msg_data: MessageData,
        *,
        media_dir: str,
        stats: PrivateArchiveMediaStats,
        archive_stats: PrivateArchiveTransferStats,
    ) -> None:
        if not msg_data.media_type:
            return

        self._track_media_stats(stats, msg_data.media_type)
        telemetry.track_messages(1)
        downloaded_path = await self._download_media(msg_data, media_dir)
        if downloaded_path:
            archive_stats.downloaded += 1
            payload = PrivateArchiveMediaSavedPayload(
                filename=os.path.basename(downloaded_path),
                path=downloaded_path,
            )
            self._emit_event(
                PrivateArchiveEvents.MEDIA_SAVED,
                **payload.as_dict(),
            )
        else:
            archive_stats.skipped += 1

    async def _archive_message(
        self,
        msg_data: MessageData,
        *,
        user_id: int,
        media_dir: str,
        writer: FileRotateWriter,
        stats: PrivateArchiveMediaStats,
        archive_stats: PrivateArchiveTransferStats,
    ) -> None:
        await self.storage.save_message(msg_data, target_id=user_id)
        await self._process_archive_media(
            msg_data,
            media_dir=media_dir,
            stats=stats,
            archive_stats=archive_stats,
        )
        log_entry = self._format_pm_log(msg_data)
        await writer.write_block(log_entry + "\n\n" + "-" * 40 + "\n\n", 1)

    async def _archive_message_stream(
        self,
        user_entity: Any,
        *,
        user_id: int,
        last_id: int,
        media_dir: str,
        writer: FileRotateWriter,
    ) -> tuple[int, PrivateArchiveMediaStats, PrivateArchiveTransferStats]:
        count = 0
        stats = self._initial_media_stats()
        archive_stats = self._initial_archive_stats()

        async for msg_data in self.client.iter_messages(
            user_entity, limit=None, offset_id=0
        ):
            if msg_data.message_id <= last_id:
                break

            await self._archive_message(
                msg_data,
                user_id=user_id,
                media_dir=media_dir,
                writer=writer,
                stats=stats,
                archive_stats=archive_stats,
            )
            count += 1

            if count % 5 == 0:
                self._emit_archive_progress(
                    count=count, stats=stats, archive_stats=archive_stats
                )

        return count, stats, archive_stats

    async def archive_pm(self, user_entity: Any):
        """
        Main entry point for PM archiving.
        """
        archive_ctx = self._prepare_archive_context(user_entity)
        self._ensure_archive_dirs(archive_ctx.media_dir)

        writer = FileRotateWriter(
            archive_ctx.chat_log_path, as_json=False, max_msgs=5000
        )
        last_id = self.storage.get_last_msg_id(archive_ctx.user_id)

        self.storage.register_target(
            archive_ctx.user_id, archive_ctx.target_name, archive_ctx.user_id
        )
        self._emit_archive_start(
            target_name=archive_ctx.target_name,
            user_id=archive_ctx.user_id,
            user_dir=archive_ctx.user_dir,
            last_id=last_id,
        )
        count, stats, archive_stats = await self._archive_message_stream(
            user_entity,
            user_id=archive_ctx.user_id,
            last_id=last_id,
            media_dir=archive_ctx.media_dir,
            writer=writer,
        )
        self._emit_archive_complete(
            user_entity=user_entity,
            count=count,
            stats=stats,
            archive_stats=archive_stats,
        )
        if hasattr(self.storage, "update_last_sync_at"):
            self.storage.update_last_sync_at(archive_ctx.user_id, archive_ctx.user_id)
        logger.info(
            f"PM Archive complete for {archive_ctx.user_id}. {count} messages, {stats.total} media, "
            f"downloaded={archive_stats.downloaded}, skipped={archive_stats.skipped}."
        )
        return archive_ctx.user_dir

    def _format_pm_log(self, m: MessageData) -> str:
        dt_str = m.timestamp.strftime("%Y-%m-%d][%H:%M")
        author = m.author_name or f"User_{m.user_id}"
        header = f"[{dt_str}] <{author}> (ID: {m.user_id}):"
        media_note = f" <Attached {m.media_type}>" if m.media_type else ""
        return f"{header}{media_note}\n{m.text or '(empty)'}"
