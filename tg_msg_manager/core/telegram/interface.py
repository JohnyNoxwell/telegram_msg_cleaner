from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional, Any
from ..models.message import MessageData

class TelegramClientInterface(ABC):
    """
    Abstract interface for Telegram client interactions.
    Ensures that core logic depends on abstractions, not library-specific details.
    """

    @abstractmethod
    async def connect(self):
        """Connects the client and authenticates the user."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Safely disconnects the client."""
        pass

    @abstractmethod
    async def get_me(self):
        """Returns the current user entity."""
        pass

    @abstractmethod
    async def iter_messages(self, entity, limit: Optional[int] = None, 
                            offset_id: int = 0, from_user: Optional[Any] = None) -> AsyncGenerator[MessageData, None]:
        """Iterates over messages in a chat and returns them as normalized MessageData."""
        pass

    @abstractmethod
    async def delete_messages(self, entity, message_ids: List[int]) -> int:
        """Deletes messages and returns the count of deleted items."""
        pass

    @abstractmethod
    async def get_dialogs(self) -> List[Any]:
        """Retrieves a list of active dialogs."""
        pass

    @abstractmethod
    async def get_entity(self, entity_id: Any) -> Any:
        """Resolves an entity (user, chat, channel) by ID or username."""
        pass

    @abstractmethod
    async def get_messages(self, entity, message_ids: List[int]) -> List[MessageData]:
        """Fetches multiple messages by their IDs in a single batch."""
        pass

    @abstractmethod
    async def download_media(self, media: Any, file: Optional[str] = None) -> Optional[str]:
        """Downloads a media object and returns the resulting file path."""
        pass
