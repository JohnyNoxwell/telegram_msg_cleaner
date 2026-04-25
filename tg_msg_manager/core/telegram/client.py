import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Any
from telethon import TelegramClient, types

from telethon.errors import FloodWaitError
from .interface import TelegramClientInterface
from .throttler import RateThrottler
from ..models.message import MessageData
from ..telemetry import telemetry

logger = logging.getLogger(__name__)

class TelethonClientWrapper(TelegramClientInterface):
    """
    Implementation of TelegramClientInterface using the Telethon library.
    Automatically handles throttling and FloodWait errors.
    """

    def __init__(self, session_name: str, api_id: int, api_hash: str, max_rps: float = 3.0, burst: int = 5):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.throttler = RateThrottler(rps=max_rps, burst=burst)

    async def connect(self):
        """Starts the Telethon client."""
        # Using the logic from previous robust_client_start
        await self.client.start()
        logger.info("Telethon client started successfully.")

    async def disconnect(self):
        await self.client.disconnect()

    async def get_me(self):
        return await self.client.get_me()

    async def get_dialogs(self) -> List[Any]:
        await self.throttler.throttle()
        telemetry.track_request()
        return await self.client.get_dialogs()

    async def get_entity(self, entity_id: Any) -> Any:
        await self.throttler.throttle()
        telemetry.track_request()
        return await self.client.get_entity(entity_id)

    async def get_messages(self, entity, message_ids: Optional[List[int]] = None, limit: Optional[int] = None) -> List[MessageData]:
        """
        Fetches multiple messages by ID or limit with adaptive throttling.
        """
        if message_ids is None and limit is None:
            return []
            
        await self.throttler.throttle()
        telemetry.track_request()
        
        try:
            # Telethon's get_messages handles both ids and limit
            msgs = await self.client.get_messages(entity, ids=message_ids, limit=limit)
            results = []
            for msg in msgs:
                if msg:
                    results.append(self._normalize_message(entity, msg))
            return results
        except FloodWaitError as e:
            logger.debug(f"FloodWait during get_messages: {e.seconds}s. Slowing down rps.")
            self.throttler.adjust_rate(0.6)
            telemetry.track_flood_wait(e.seconds)
            await asyncio.sleep(e.seconds)
            return await self.get_messages(entity, message_ids)

    def _normalize_message(self, entity, msg) -> MessageData:
        """Helper to convert Telethon Message to internal MessageData."""
        author_name = None
        if msg.sender:
            author_name = " ".join(filter(None, [getattr(msg.sender, 'first_name', ''), getattr(msg.sender, 'last_name', '')]))
        
        is_service = isinstance(msg, types.MessageService)
        
        return MessageData(
            message_id=msg.id,
            chat_id=getattr(entity, 'id', 0),
            user_id=msg.sender_id or 0,
            author_name=author_name,
            timestamp=msg.date,
            text=msg.message if hasattr(msg, 'message') else "",
            media_type=type(msg.media).__name__ if (hasattr(msg, 'media') and msg.media) else None,
            reply_to_id=msg.reply_to.reply_to_msg_id if (hasattr(msg, 'reply_to') and msg.reply_to) else None,
            fwd_from_id=msg.fwd_from.from_id.user_id if (hasattr(msg, 'fwd_from') and msg.fwd_from and msg.fwd_from.from_id and hasattr(msg.fwd_from.from_id, 'user_id')) else None,
            context_group_id=None,
            raw_payload=msg.to_dict(),
            is_service=is_service,
            media_ref=msg
        )


    async def iter_messages(self, entity, limit: Optional[int] = None, 
                            offset_id: int = 0, from_user: Optional[Any] = None, **kwargs) -> AsyncGenerator[MessageData, None]:
        """
        Iterates over messages and yields MessageData objects.
        Throttling is applied per batch (roughly every 100 messages) to maintain speed.
        """
        count = 0
        async for msg in self.client.iter_messages(entity, limit=limit, offset_id=offset_id, from_user=from_user, **kwargs):
            if count % 100 == 0:
                await self.throttler.throttle()
            
            yield self._normalize_message(entity, msg)
            count += 1

    async def delete_messages(self, entity, message_ids: List[int]) -> int:
        """
        Deletes messages with automatic FloodWait handling and adaptive throttling.
        """
        if not message_ids:
            return 0
            
        await self.throttler.throttle()
        telemetry.track_request()
        try:
            await self.client.delete_messages(entity, message_ids)
            return len(message_ids)
        except FloodWaitError as e:
            logger.debug(f"FloodWait encountered: sleeping for {e.seconds} seconds.")
            # Drastically slow down after FloodWait
            self.throttler.adjust_rate(0.5)
            telemetry.track_flood_wait(e.seconds)
            await asyncio.sleep(e.seconds)
            # Retry once after sleep
            await self.throttler.throttle()
            telemetry.track_request()
            await self.client.delete_messages(entity, message_ids)
            return len(message_ids)
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
            telemetry.track_error()
            return 0

    async def download_media(self, media, file: Optional[str] = None) -> Optional[str]:
        """Downloads media through Telethon with throttling and flood-wait handling."""
        if media is None:
            return None

        await self.throttler.throttle()
        telemetry.track_request()
        try:
            return await self.client.download_media(media, file=file)
        except FloodWaitError as e:
            logger.debug(f"FloodWait during download_media: {e.seconds}s. Slowing down rps.")
            self.throttler.adjust_rate(0.6)
            telemetry.track_flood_wait(e.seconds)
            await asyncio.sleep(e.seconds)
            return await self.download_media(media, file=file)
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            telemetry.track_error()
            return None
