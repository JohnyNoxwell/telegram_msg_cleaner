import os
import signal
import logging
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class ProcessManager:
    """
    Manages process-level concerns: file locking and signal handling.
    """

    def __init__(self, lock_path: str = ".tg_msg_manager.lock"):
        self.lock_path = lock_path
        self.lock_fd: Optional[int] = None
        self.shutdown_requested = False

    def acquire_lock(self) -> bool:
        """
        Attempts to acquire the process lock. Returns True if successful, False otherwise.
        """
        try:
            # Create lock file exclusively
            self.lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            # Write current PID to the lock file
            os.write(self.lock_fd, str(os.getpid()).encode())
            logger.debug(f"Process lock acquired at {self.lock_path}")
            return True
        except FileExistsError:
            # Check if PID is still alive (basic check)
            try:
                with open(self.lock_path, 'r') as f:
                    content = f.read().strip()
                if not content:
                    raise ValueError("Empty lock file")
                old_pid = int(content)
                os.kill(old_pid, 0) # Check if process exists
                return False
            except (OSError, ValueError):
                # Process is dead but lock file exists
                logger.warning(f"Stale lock file found. Overwriting.")
                try:
                    os.remove(self.lock_path)
                except:
                    pass
                return self.acquire_lock()

    def release_lock(self):
        """
        Releases the process lock and removes the file.
        """
        if self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
            except:
                pass
            self.lock_fd = None
        if os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except:
                pass
            logger.debug("Process lock released.")

    def __enter__(self):
        if not self.acquire_lock():
            raise RuntimeError("Could not acquire process lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_lock()

    def setup_signals(self, loop_stop_callback: Optional[Callable] = None):
        """
        Registers handlers for SIGINT, SIGTERM, and SIGHUP.
        Implements a multi-stage shutdown: 
        1st Ctrl+C = Graceful KeyboardInterrupt
        2nd Ctrl+C = Hard SystemExit
        """
        self._sig_count = 0
        
        def handler(sig, frame):
            self._sig_count += 1
            sig_name = "SIGHUP" if sig == signal.SIGHUP else ("SIGTERM" if sig == signal.SIGTERM else "SIGINT")
            
            if self._sig_count > 1:
                print(f"\n🧨 Forceful exit triggered by {sig_name}...")
                os._exit(1) # Immediate hard exit

            logger.warning(f"Signal {sig_name} ({sig}) received. Requesting graceful shutdown...")
            self.shutdown_requested = True
            
            if loop_stop_callback:
                loop_stop_callback()
            
            # For SIGINT, we raise KeyboardInterrupt to break current await calls
            if sig == signal.SIGINT:
                raise KeyboardInterrupt
            
            # For HUP or TERM, we usually want to exit immediately but nicely
            if sig in (signal.SIGHUP, signal.SIGTERM):
                raise SystemExit(0)

        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, handler)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def should_stop(self) -> bool:
        return self.shutdown_requested
