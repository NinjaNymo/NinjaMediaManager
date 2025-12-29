"""
File scanning service for finding media files
"""
from pathlib import Path
from typing import Generator


class FileScanner:
    """Service for scanning directories for media files"""

    def __init__(self):
        self.supported_extensions = {".mkv"}

    def scan_for_mkv(self, directory: Path, recursive: bool = True) -> list[Path]:
        """
        Scan a directory for MKV files.

        Args:
            directory: The directory to scan
            recursive: Whether to scan subdirectories

        Returns:
            List of Path objects for found MKV files
        """
        if not directory.is_dir():
            return []

        mkv_files = []
        pattern = "**/*.mkv" if recursive else "*.mkv"

        for path in directory.glob(pattern):
            if path.is_file() and not path.name.startswith("."):
                mkv_files.append(path)

        return sorted(mkv_files, key=lambda x: x.name.lower())

    def iter_mkv_files(self, directory: Path, recursive: bool = True) -> Generator[Path, None, None]:
        """
        Iterator version for memory-efficient scanning of large directories.

        Args:
            directory: The directory to scan
            recursive: Whether to scan subdirectories

        Yields:
            Path objects for found MKV files
        """
        if not directory.is_dir():
            return

        pattern = "**/*.mkv" if recursive else "*.mkv"

        for path in directory.glob(pattern):
            if path.is_file() and not path.name.startswith("."):
                yield path
