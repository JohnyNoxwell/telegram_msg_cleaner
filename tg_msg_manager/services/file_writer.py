import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class FileRotateWriter:
    """
    Handles writing content to files with automatic rotation into multiple parts.
    Ensures that individual files do not exceed a certain message count.
    """
    def __init__(self, base_path: str, as_json: bool = False, max_msgs: int = 5000, overwrite: bool = False):
        self.base_path = base_path
        self.as_json = as_json
        self.max_msgs = max_msgs
        self.lock = asyncio.Lock()
        
        self.directory = os.path.dirname(base_path)
        if self.directory and not os.path.exists(self.directory):
            os.makedirs(self.directory)
            
        self.filename = os.path.basename(base_path)
        self.name_no_ext, self.ext = os.path.splitext(self.filename)
        
        self.current_part = 1
        self.current_count = 0
        
        if overwrite:
            self._cleanup_existing_files()
            
        self.current_file_path = self._get_path()
        self._detect_current_state()

    def _cleanup_existing_files(self):
        """Removes all parts of the export if a full resync is requested."""
        part = 1
        while True:
            path = self._get_path_for_part(part)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Removed old export file: {path}")
                except Exception as e:
                    logger.error(f"Error removing {path}: {e}")
                part += 1
            else:
                break

    def _get_path_for_part(self, part: int) -> str:
        if part == 1:
            return os.path.join(self.directory, f"{self.name_no_ext}{self.ext}")
        return os.path.join(self.directory, f"{self.name_no_ext}_part{part}{self.ext}")

    def _get_path(self) -> str:
        return self._get_path_for_part(self.current_part)

    def _detect_current_state(self):
        """Finds the highest part number that exists and counts its messages."""
        while True:
            path = self._get_path()
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        # For JSONL, count is number of lines
                        # For TXT, counting is more complex; we treat as 0 for simplicity or implement logic
                        if self.as_json:
                            self.current_count = sum(1 for _ in f)
                        else:
                            self.current_count = 0 # Simple override for text
                except Exception:
                    self.current_count = 0
                
                if self.current_count >= self.max_msgs:
                    self.current_part += 1
                    continue
                break
            else:
                break
        self.current_file_path = self._get_path()

    async def write_block(self, content: str, msg_count: int = 1):
        """Writes a block of content to the current file, rotating if needed."""
        async with self.lock:
            if self.current_count + msg_count > self.max_msgs:
                self.current_part += 1
                self.current_count = 0
                self.current_file_path = self._get_path()
                logger.info(f"File limit reached. Rotating to part {self.current_part}: {self.current_file_path}")

            with open(self.current_file_path, "a", encoding="utf-8") as f:
                f.write(content)
                f.flush()
            self.current_count += msg_count
