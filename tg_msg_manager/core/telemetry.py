import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)

@dataclass
class TelemetryData:
    api_requests_total: int = 0
    messages_processed_total: int = 0
    errors_total: int = 0
    flood_wait_seconds_total: float = 0.0

class TelemetryTracker:
    """
    Singleton class to track application metrics.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryTracker, cls).__new__(cls)
            cls._instance.data = TelemetryData()
        return cls._instance

    def track_request(self):
        self.data.api_requests_total += 1

    def track_messages(self, count: int):
        self.data.messages_processed_total += count

    def track_error(self):
        self.data.errors_total += 1

    def track_flood_wait(self, seconds: float):
        self.data.flood_wait_seconds_total += seconds

    def get_summary(self) -> Dict:
        return {
            "api_requests": self.data.api_requests_total,
            "messages_processed": self.data.messages_processed_total,
            "errors": self.data.errors_total,
            "flood_wait_seconds": self.data.flood_wait_seconds_total
        }

    def log_summary(self):
        summary = self.get_summary()
        logger.info(f"Execution Summary: {summary}", extra={"metrics": summary})

# Global instance
telemetry = TelemetryTracker()
