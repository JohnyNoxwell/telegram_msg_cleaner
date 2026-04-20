import os
import json
import logging
from datetime import datetime
from .context import get_chat_id, get_trace_id

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for easier ingestion by log processors.
    Automatically includes context fields from contextvars.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "chat_id": get_chat_id(),
            "trace_id": get_trace_id(),
        }
        
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Include extra fields if any
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        return json.dumps(log_data, ensure_ascii=False)

class HumanFormatter(logging.Formatter):
    """
    Clean text formatter for terminal output.
    """
    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_icons = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }
        icon = level_icons.get(record.levelname, record.levelname)
        return f"[{dt}] {icon} {record.getMessage()}"

def setup_logging(level: str = "INFO", console_level: str = "WARNING", log_to_file: bool = True):
    """
    Configures logging:
    - StreamHandler: Human readable (Console) - Default to WARNING for cleaner UI
    - FileHandler: JSON (LOGS/app.log) - Default to INFO for detailed history
    """
    root_logger = logging.getLogger()
    # Remove existing handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    
    # 1. Console Handler (Human)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(HumanFormatter())
    console_handler.setLevel(console_level)
    root_logger.addHandler(console_handler)
    
    # 2. File Handler (JSON)
    if log_to_file:
        log_dir = "LOGS"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
        
    root_logger.setLevel(logging.DEBUG) # Allow handlers to filter
    
    # Suppress verbose loggers
    logging.getLogger("telethon").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
