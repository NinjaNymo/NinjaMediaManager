"""
Media info service using ffprobe
"""
import subprocess
import json
from pathlib import Path
from typing import Optional

from backend.models.schemas import MediaInfo, Track, TrackType


class MediaInfoService:
    """Service for extracting media information using ffprobe"""

    def __init__(self):
        self.ffprobe_cmd = "ffprobe"

    async def get_info(self, media_path: Path) -> MediaInfo:
        """
        Get detailed information about a media file.

        Args:
            media_path: Path to the media file

        Returns:
            MediaInfo object with all track details
        """
        # Run ffprobe
        cmd = [
            self.ffprobe_cmd,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(media_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"ffprobe failed (code {result.returncode}): {error_msg}. Path: {media_path}")

        data = json.loads(result.stdout)

        # Parse tracks
        tracks = []
        for stream in data.get("streams", []):
            track = self._parse_stream(stream)
            if track:
                tracks.append(track)

        # Get format info
        format_info = data.get("format", {})

        return MediaInfo(
            path=str(media_path),
            filename=media_path.name,
            size=int(format_info.get("size", 0)),
            duration=float(format_info.get("duration", 0)) if format_info.get("duration") else None,
            format=format_info.get("format_name", "unknown"),
            tracks=tracks,
        )

    def _parse_stream(self, stream: dict) -> Optional[Track]:
        """Parse a stream dictionary into a Track object"""
        codec_type = stream.get("codec_type")

        if codec_type == "video":
            return Track(
                index=stream.get("index", 0),
                type=TrackType.VIDEO,
                codec=stream.get("codec_name", "unknown"),
                language=self._get_language(stream),
                title=self._get_title(stream),
                default=self._is_default(stream),
                forced=self._is_forced(stream),
                width=stream.get("width"),
                height=stream.get("height"),
                bitrate=self._get_bitrate(stream),
                frame_rate=self._get_frame_rate(stream),
            )
        elif codec_type == "audio":
            return Track(
                index=stream.get("index", 0),
                type=TrackType.AUDIO,
                codec=stream.get("codec_name", "unknown"),
                language=self._get_language(stream),
                title=self._get_title(stream),
                default=self._is_default(stream),
                forced=self._is_forced(stream),
                channels=stream.get("channels"),
                sample_rate=int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else None,
                bitrate=self._get_bitrate(stream),
            )
        elif codec_type == "subtitle":
            return Track(
                index=stream.get("index", 0),
                type=TrackType.SUBTITLE,
                codec=stream.get("codec_name", "unknown"),
                language=self._get_language(stream),
                title=self._get_title(stream),
                default=self._is_default(stream),
                forced=self._is_forced(stream),
            )

        return None

    def _get_language(self, stream: dict) -> Optional[str]:
        """Extract language from stream tags"""
        tags = stream.get("tags", {})
        return tags.get("language")

    def _get_title(self, stream: dict) -> Optional[str]:
        """Extract title from stream tags"""
        tags = stream.get("tags", {})
        return tags.get("title")

    def _is_default(self, stream: dict) -> bool:
        """Check if stream is marked as default"""
        disposition = stream.get("disposition", {})
        return disposition.get("default", 0) == 1

    def _is_forced(self, stream: dict) -> bool:
        """Check if stream is marked as forced"""
        disposition = stream.get("disposition", {})
        return disposition.get("forced", 0) == 1

    def _get_bitrate(self, stream: dict) -> Optional[int]:
        """Extract bitrate from stream (bits per second)"""
        # Try bit_rate first (most common for non-MKV or some encoders)
        if stream.get("bit_rate"):
            return int(stream["bit_rate"])

        # For MKV files, bitrate is often in tags with various naming conventions
        tags = stream.get("tags", {})

        # mkvtoolnix often adds language suffix like "BPS-eng", "BPS-ger", etc.
        # Search for any key that starts with "bps" (case-insensitive)
        for key, value in tags.items():
            if key.lower().startswith("bps"):
                try:
                    return int(value)
                except ValueError:
                    pass

        return None

    def _get_frame_rate(self, stream: dict) -> Optional[float]:
        """Extract frame rate from video stream"""
        # Try avg_frame_rate first (e.g., "24000/1001" for 23.976)
        avg_frame_rate = stream.get("avg_frame_rate")
        if avg_frame_rate and avg_frame_rate != "0/0":
            try:
                num, den = avg_frame_rate.split("/")
                if int(den) != 0:
                    return round(int(num) / int(den), 3)
            except (ValueError, ZeroDivisionError):
                pass
        # Fallback to r_frame_rate
        r_frame_rate = stream.get("r_frame_rate")
        if r_frame_rate and r_frame_rate != "0/0":
            try:
                num, den = r_frame_rate.split("/")
                if int(den) != 0:
                    return round(int(num) / int(den), 3)
            except (ValueError, ZeroDivisionError):
                pass
        return None
