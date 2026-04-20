import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class RateThrottler:
    """
    Advanced Token Bucket throttler with burst support.
    Allows for initial high-speed bursts while maintaining an average rate.
    """

    def __init__(self, rps: float = 3.0, burst: int = 10):
        self.rps = rps
        self.capacity = burst
        self.tokens = float(burst)
        self.last_refill = time.perf_counter()
        self.lock = asyncio.Lock()

    async def throttle(self):
        """
        Consumes a token or waits until one is available.
        """
        async with self.lock:
            while self.tokens < 1:
                self._refill()
                if self.tokens < 1:
                    # Wait for at least one token to be partially available
                    wait_time = (1.0 - self.tokens) / self.rps
                    await asyncio.sleep(wait_time)
                self._refill()
            
            self.tokens -= 1
            # Ensure we don't refill too far in the past if we haven't used it for a while
            self.last_refill = time.perf_counter()

    def _refill(self):
        """Refills tokens based on elapsed time."""
        now = time.perf_counter()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rps
        
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def adjust_rate(self, factor: float):
        """Dynamically adjusts the RPS (e.g. slow down after FloodWait)."""
        self.rps = max(0.1, self.rps * factor)
        logger.info(f"RateThrottler adjusted RPS to {self.rps:.2f}")

    def wrap(self, func):
        """Decorator to automatically throttle an async function."""
        async def wrapper(*args, **kwargs):
            await self.throttle()
            return await func(*args, **kwargs)
        return wrapper
