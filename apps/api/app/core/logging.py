"""Structured JSON logging with automatic secret scrubbing."""
import json
import logging
import re
import sys
from typing import Any, Dict


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),
    re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"(\"password\"\s*:\s*\")[^\"]+(\")", re.IGNORECASE),
    re.compile(r"(\"secret\"\s*:\s*\")[^\"]+(\")", re.IGNORECASE),
    re.compile(r"(api_key=)[^&\s]+", re.IGNORECASE),
]


def scrub_secrets(text: str) -> str:
    """Mask any suspected API keys, tokens, or passwords in strings."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(r"[REDACTED_SECRET]", result)
    return result


class StructuredJsonFormatter(logging.Formatter):
    """Format logs as JSON lines, scrubbing credentials."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": scrub_secrets(record.getMessage()),
        }

        # Include custom extra fields if provided
        for key, val in record.__dict__.items():
            if key not in ("args", "asctime", "created", "exc_info", "exc_text", "filename",
                           "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                           "msg", "name", "pathname", "process", "processName", "relativeCreated",
                           "stack_info", "thread", "threadName"):
                if isinstance(val, str):
                    log_data[key] = scrub_secrets(val)
                else:
                    log_data[key] = val

        if record.exc_info:
            log_data["exception"] = scrub_secrets(self.formatException(record.exc_info))

        return json.dumps(log_data)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Clear existing handlers
    root_logger.handlers = [handler]


logger = logging.getLogger("ai_blog_platform")
