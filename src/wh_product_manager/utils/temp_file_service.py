"""
Cross-platform helpers for temporary files and directories.

This service wraps Python's tempfile APIs with safe defaults that work on
both Windows and Linux. In particular, temporary file paths are generated
with mkstemp and the file descriptor is closed immediately, so the file can
be reopened by other libraries on Windows.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir, mkstemp
from typing import Iterator

from wh_product_manager.core.logger import Logger


class TempFileService:
    """Service for creating and cleaning temporary files and directories."""

    def __init__(self, logger: Logger, base_temp_dir: Path | None = None):
        """
        Initialize the temporary file service.

        Args:
            base_temp_dir: Optional override for the parent temp directory.
                If omitted, the operating system's default temp location is used.
        """
        self.logger = logger

        self.base_temp_dir = base_temp_dir

    def get_system_temp_dir(self) -> Path:
        """Return the temp directory used by this runtime."""
        temp_dir = Path(gettempdir())
        self.logger.debug("Resolved system temp directory: %s", temp_dir)
        return temp_dir

    @contextmanager
    def temporary_directory(
        self,
        prefix: str = "whpm-",
        suffix: str = "",
    ) -> Iterator[Path]:
        """
        Create a temporary directory and clean it up automatically.

        Args:
            prefix: Directory name prefix.
            suffix: Directory name suffix.

        Yields:
            Path to the created temporary directory.
        """
        with TemporaryDirectory(
            prefix=prefix,
            suffix=suffix,
            dir=str(self.base_temp_dir) if self.base_temp_dir else None,
        ) as temp_dir:
            temp_path = Path(temp_dir)
            self.logger.debug(
                "Created temporary directory: %s (prefix=%s, suffix=%s)",
                temp_path,
                prefix,
                suffix,
            )
            try:
                yield temp_path
            finally:
                self.logger.debug("Temporary directory cleanup complete: %s", temp_path)

    @contextmanager
    def temporary_file_path(
        self,
        prefix: str = "whpm-",
        suffix: str = "",
        create_parent_dir: bool = False,
    ) -> Iterator[Path]:
        """
        Create a temporary file path that can be safely reopened on Windows.

        The file is created with mkstemp to reserve a unique path. Its file
        descriptor is immediately closed so other code can open it normally.
        The path is deleted on context exit.

        Args:
            prefix: File name prefix.
            suffix: File name suffix.
            create_parent_dir: If true, create a per-file temp directory under
                the base temp dir. This directory is removed on context exit.

        Yields:
            Path to the created temporary file.
        """
        parent_dir: Path | None = None

        if create_parent_dir:
            with TemporaryDirectory(
                prefix=f"{prefix}dir-",
                dir=str(self.base_temp_dir) if self.base_temp_dir else None,
            ) as temp_parent:
                parent_dir = Path(temp_parent)
                self.logger.debug(
                    "Created parent temp directory for file path: %s", parent_dir
                )
                file_path = self._mkstemp_path(
                    prefix=prefix, suffix=suffix, dir_path=parent_dir
                )
                try:
                    yield file_path
                finally:
                    self.cleanup_path(file_path)
                    self.logger.debug(
                        "Temporary file path context exited and cleaned: %s", file_path
                    )
        else:
            file_path = self._mkstemp_path(
                prefix=prefix, suffix=suffix, dir_path=self.base_temp_dir
            )
            try:
                yield file_path
            finally:
                self.cleanup_path(file_path)
                self.logger.debug(
                    "Temporary file path context exited and cleaned: %s", file_path
                )

    def make_temp_file_path(
        self,
        prefix: str = "whpm-",
        suffix: str = "",
    ) -> Path:
        """
        Create and return a temp file path without context management.

        Caller is responsible for cleanup via cleanup_path.

        Args:
            prefix: File name prefix.
            suffix: File name suffix.

        Returns:
            Path to the created temporary file.
        """
        file_path = self._mkstemp_path(
            prefix=prefix, suffix=suffix, dir_path=self.base_temp_dir
        )
        self.logger.debug("Created unmanaged temporary file path: %s", file_path)
        return file_path

    def cleanup_path(self, path: Path, missing_ok: bool = True) -> None:
        """
        Remove a temporary file or directory recursively.

        Args:
            path: Path to remove.
            missing_ok: If true, do not raise if the path is already gone.
        """
        try:
            if path.is_dir():
                self.logger.debug("Cleaning temporary directory recursively: %s", path)
                for child in path.iterdir():
                    self.cleanup_path(child, missing_ok=True)
                path.rmdir()
                self.logger.debug("Removed temporary directory: %s", path)
                return

            path.unlink(missing_ok=missing_ok)
            self.logger.debug("Removed temporary file: %s", path)
        except FileNotFoundError:
            if not missing_ok:
                raise
            self.logger.debug("Temporary path already missing during cleanup: %s", path)
        except Exception:
            self.logger.exception("Failed to clean temporary path: %s", path)
            raise

    def _mkstemp_path(self, prefix: str, suffix: str, dir_path: Path | None) -> Path:
        """Create a unique temp file path and close its descriptor immediately."""
        fd, raw_path = mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=str(dir_path) if dir_path else None,
        )
        os.close(fd)
        file_path = Path(raw_path)
        self.logger.debug(
            "Created temporary file path: %s (prefix=%s, suffix=%s, dir=%s)",
            file_path,
            prefix,
            suffix,
            dir_path,
        )
        return file_path
