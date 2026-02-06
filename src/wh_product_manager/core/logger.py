"""
Logging utility for the application
Provides consistent logging across all modules
"""

import logging
import sys
from pathlib import Path
from typing import Optional


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
        level: str = "INFO",
        log_dir: Optional[Path] = None,
    ):
        """
        Initialize the logger

        Args:
            name: Logger name (default: wh_product_manager)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (default: None, console only)
        """
        self.name = name
        self.log_dir = log_dir

        # Create base logger
        self.logger = logging.getLogger(name)

        # Set logging level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Console handler with colors
        self._add_console_handler(log_level)

        # File handler if log_dir specified
        if log_dir:
            self._add_file_handler(log_level, log_dir)

    def _add_console_handler(self, level: int) -> None:
        """
        Add console handler with colored output

        Args:
            level: Logging level
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Colored formatter for console
        formatter = _ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

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
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log an info message"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, exc_info: bool = False, **kwargs) -> None:
        """
        Log an error message

        Args:
            message: Error message
            exc_info: Include exception traceback
        """
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """
        Log an exception with full traceback

        Args:
            message: Error message
        """
        self.logger.exception(message, *args, **kwargs)


class _ColoredFormatter(logging.Formatter):
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
            record.levelname = f"{color}{levelname}{reset}"

        # Format the message
        result = super().format(record)

        return result
