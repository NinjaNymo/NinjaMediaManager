"""
Subtitle extraction service using ffmpeg/mkvextract
"""
import subprocess
import asyncio
import re
from pathlib import Path
from typing import Optional

from backend.services.media_info import MediaInfoService
from backend.services.task_manager import task_manager, Task


class SubtitleExtractor:
    """Service for extracting subtitles from media files"""

    def __init__(self):
        self.media_service = MediaInfoService()

    async def extract(
        self,
        media_path: Path,
        track_index: int,
        output_dir: Path,
        output_format: Optional[str] = None,
        task: Task = None,
    ) -> Path:
        """
        Extract a subtitle track from a media file.

        Args:
            media_path: Path to the media file
            track_index: Index of the subtitle track to extract
            output_dir: Directory to save the extracted subtitle
            output_format: Output format (srt, ass, sup). None = keep original
            task: Optional task for progress reporting

        Returns:
            Path to the extracted subtitle file
        """
        # Get media info to determine codec
        if task:
            task_manager.log(task, f"Analyzing {media_path.name}...")

        info = await self.media_service.get_info(media_path)

        # Find the requested track
        track = None
        for t in info.tracks:
            if t.index == track_index and t.type.value == "subtitle":
                track = t
                break

        if not track:
            raise ValueError(f"Subtitle track {track_index} not found")

        if task:
            task_manager.log(task, f"Found track {track_index}: {track.codec} ({track.language or 'unknown'})")

        # Determine output extension based on codec
        extension = self._get_extension(track.codec, output_format)

        # Create output filename (Plex-compatible: MovieName.lang.ext)
        lang_suffix = f".{track.language}" if track.language else ""
        output_filename = f"{media_path.stem}{lang_suffix}{extension}"
        output_path = output_dir / output_filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        if task:
            task_manager.log(task, f"Extracting to {output_filename}...")
            task_manager.update_progress(task, 10)

        # Extract using ffmpeg with progress
        await self._extract_with_ffmpeg(media_path, track_index, output_path, info.duration, task)

        if task:
            task_manager.update_progress(task, 100, "Extraction complete")

        return output_path

    async def _extract_with_ffmpeg(
        self,
        media_path: Path,
        track_index: int,
        output_path: Path,
        duration: float = None,
        task: Task = None,
    ):
        """Extract subtitle using ffmpeg with progress reporting"""
        # Determine codec based on output format
        if output_path.suffix in [".sup", ".ass", ".ssa"]:
            codec = "copy"
        else:
            codec = "srt"

        cmd = [
            "ffmpeg",
            "-y",
            "-progress", "pipe:1",
            "-i", str(media_path),
            "-map", f"0:{track_index}",
            "-c", "copy" if codec == "copy" else "srt",
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Parse progress output
        last_progress = 10
        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line = line.decode().strip()

            # Parse time progress
            if line.startswith("out_time_ms="):
                try:
                    time_ms = int(line.split("=")[1])
                    if duration and duration > 0:
                        progress = min(95, int(10 + (time_ms / 1000 / duration) * 85))
                        if progress > last_progress and task:
                            task_manager.update_progress(task, progress)
                            last_progress = progress
                except (ValueError, IndexError):
                    pass

        await process.wait()

        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise RuntimeError(f"ffmpeg extraction failed: {stderr.decode()}")

    def _get_extension(self, codec: str, requested_format: Optional[str]) -> str:
        """Determine output file extension"""
        if requested_format:
            format_map = {
                "srt": ".srt",
                "ass": ".ass",
                "ssa": ".ssa",
                "sup": ".sup",
                "pgs": ".sup",
            }
            return format_map.get(requested_format.lower(), ".srt")

        # Default based on codec
        codec_map = {
            "subrip": ".srt",
            "ass": ".ass",
            "ssa": ".ssa",
            "hdmv_pgs_subtitle": ".sup",
            "dvd_subtitle": ".sub",
        }
        return codec_map.get(codec, ".srt")
