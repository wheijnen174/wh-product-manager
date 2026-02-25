"""
Logging utility for the application
Provides consistent logging across all modules
"""

import logging
import sys
from pathlib import Path
from typing import Any

from wh_product_manager.utils.data_loader import get_data_dir


class Logger:
    """
    Custom logger wrapper for consistent logging across the application
    Handles file and console output with proper formatting
    """

    # Color codes for console output
    _COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(
        self,
        name: str = "wh_product_manager",
        level: str = "DEBUG",
    ):
        """
        Initialize the logger

        Args:
            name: Logger name (default: wh_product_manager)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (default: None, console only)
        """
        self.name = name
        self.log_dir = get_data_dir() / "logs"

        # Create base logger
        self.logger = logging.getLogger(name)

        # Set logging level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler if log_dir specified
        if self.log_dir:
            self._add_file_handler(0, self.log_dir)

        # Console handler with colors
        self._add_console_handler(log_level)

    def _add_file_handler(self, level: int, log_dir: Path) -> None:
        """
        Add file handler for persistent logging

        Args:
            level: Logging level
            log_dir: Directory to store log files
        """
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{self.name}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)

        # Standard formatter for file (no colors)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _add_console_handler(self, level: int) -> None:
        """
        Add console handler with colored output

        Args:
            level: Logging level
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Colored formatter for console
        console_formatter = _ConsoleFormatter(
            fmt="%(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.warning(message, *args, **kwargs)

    def error(
        self, message: str, *args: Any, exc_info: bool = True, **kwargs: Any
    ) -> None:
        """Log an error message"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.error(message, *args, exc_info=False, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with full traceback"""
        kwargs.setdefault("stacklevel", 2)
        self.logger.exception(message, *args, **kwargs)


class _ConsoleFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to console output
    Only applies colors to console, not file logs
    """

    _COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors

        Args:
            record: Log record to format

        Returns:
            Formatted log message with colors
        """
        # Get the log level name
        levelname = record.levelname

        # Apply color to level name
        if levelname in self._COLORS:
            color = self._COLORS[levelname]
            reset = self._COLORS["RESET"]
            record.levelname = f"{color}{levelname}{reset}:{' ' * (8 - len(levelname))}"  # Pad to 10 characters for alignment

        # Format the message
        result = super().format(record)

        return result
