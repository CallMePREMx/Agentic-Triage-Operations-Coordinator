"""
Logging configuration for the application.

Provides structured logging with both file and console handlers.
Each agent gets its own logger for traceable audit trails.
"""

import logging
import logging.handlers
from datetime import datetime
from config.settings import LOG_DIR, APP_NAME


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root application logger.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured root logger instance.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # File handler with rotation
    log_file = LOG_DIR / f"atoc_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    # Root logger
    root_logger = logging.getLogger(APP_NAME)
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates on re-initialization
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("Logging initialized [level=%s, file=%s]", level, log_file.name)
    return root_logger


def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a child logger namespaced under the application for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'IntakeAgent').

    Returns:
        Child logger instance.
    """
    return logging.getLogger(f"{APP_NAME}.{agent_name}")
