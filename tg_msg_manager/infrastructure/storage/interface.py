from abc import ABC, abstractmethod
from typing import List, Optional
from ...core.models.message import MessageData

class BaseStorage(ABC):
    """
    Abstract base class for all storage backends.
    De-couples the core logic from specific database implementations.
    """

    @abstractmethod
    def save_message(self, msg: MessageData) -> bool:
        """
        Save a single message.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def save_messages(self, msgs: List[MessageData]) -> int:
        """
        Save multiple messages in a single transaction.
        Returns the number of messages successfully saved.
        """
        pass

    @abstractmethod
    def get_message(self, chat_id: int, message_id: int) -> Optional[MessageData]:
        """
        Retrieve a single message by chat_id and message_id.
        """
        pass

    @abstractmethod
    def message_exists(self, chat_id: int, message_id: int) -> bool:
        """
        Quick check if a message exists in the storage.
        """
        pass

    @abstractmethod
    def get_last_msg_id(self, chat_id: int) -> int:
        """
        Get the highest message_id stored for a specific chat.
        Returns 0 if no messages are stored for the chat.
        """
        pass

    @abstractmethod
    def get_outdated_chats(self, threshold_seconds: int) -> List[int]:
        """
        Returns a list of chat_ids that haven't been synced for longer than threshold_seconds.
        """
        pass

    @abstractmethod
    def get_message_count(self, chat_id: int) -> int:
        """
        Returns the total number of messages stored for a specific chat.
        """
        pass

    @abstractmethod
    def delete_messages(self, chat_id: int, message_ids: List[int]) -> int:
        """
        Removes messages from the storage.
        Returns the number of records removed.
        """
        pass

    @abstractmethod
    def get_all_message_ids_for_chat(self, chat_id: int) -> List[int]:
        """
        Returns a list of all stored message_ids for a specific chat.
        """
        pass

    @abstractmethod
    def get_unique_sync_users(self) -> List[dict]:
        """
        Returns a list of unique users from synced messages.
        Returns: List of dicts with 'user_id' and 'author_name'.
        """
        pass

    @abstractmethod
    def get_user_messages(self, user_id: int) -> List[MessageData]:
        """
        Returns all messages for a specific user across all chats.
        """
        pass

    @abstractmethod
    def delete_user_data(self, user_id: int) -> tuple[int, int]:
        """
        Removes all messages and tracking data for a user.
        Returns: (messages_deleted, targets_deleted).
        """
        pass
