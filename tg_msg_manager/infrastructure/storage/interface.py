from abc import ABC, abstractmethod
from typing import List, Optional
from ...core.models.message import MessageData

class BaseStorage(ABC):
    """
    Abstract base class for all storage backends.
    De-couples the core logic from specific database implementations.
    """

    @abstractmethod
    def save_message(self, msg: MessageData, target_id: Optional[int] = None) -> bool:
        """
        Save a single message.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def save_messages(self, msgs: List[MessageData], target_id: Optional[int] = None) -> int:
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
    def get_user(self, user_id: int) -> Optional[dict]:
        """
        Retrieves user metadata (name, etc.) from storage.
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

    @abstractmethod
    def register_target(self, user_id: int, author_name: str, chat_id: int,
                        first_name: Optional[str] = None, 
                        last_name: Optional[str] = None, 
                        username: Optional[str] = None,
                        deep_mode: bool = False,
                        recursive_depth: int = 0):
        """Registers a primary sync target with metadata and settings."""
        pass

    @abstractmethod
    def get_primary_targets(self) -> List[dict]:
        """Returns only manually requested targets."""
        pass

    @abstractmethod
    def upsert_user(self, user_id: int, first_name: Optional[str] = None, last_name: Optional[str] = None, username: Optional[str] = None, phone: Optional[str] = None):
        """Persists or updates user metadata."""
        pass

    @abstractmethod
    def get_sync_status(self, chat_id: int, user_id: int) -> dict:
        """Retrieves synchronization status for a specific chat/user pair."""
        pass

    @abstractmethod
    def upsert_chat(self, chat_id: int, title: str, chat_type: Optional[str] = None):
        """Persists or updates chat metadata in the storage."""
        pass
    
    @abstractmethod
    def has_target_link(self, chat_id: int, message_id: int, target_id: int) -> bool:
        """Returns True if the message is already linked to the specified target."""
        pass

    @abstractmethod
    def close(self):
        """Closes the storage connection."""
        pass
