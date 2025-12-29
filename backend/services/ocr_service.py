"""
OCR service for PGS subtitle processing using pgs-to-srt
"""
import asyncio
from pathlib import Path

from backend.services.media_info import MediaInfoService
from backend.services.task_manager import task_manager, Task


class OCRService:
    """Service for OCR processing of PGS subtitles using pgs-to-srt"""

    def __init__(self):
        self.media_service = MediaInfoService()

    async def process_pgs(
        self,
        media_path: Path,
        track_index: int,
        output_dir: Path,
        language: str = "eng",
        task: Task = None,
    ) -> dict:
        """
        Process a PGS subtitle track with OCR using pgs-to-srt.

        Args:
            media_path: Path to the media file
            track_index: Index of the PGS subtitle track
            output_dir: Directory to save the output SRT
            language: Tesseract language code (eng, nor, etc.)
            task: Optional task for progress reporting

        Returns:
            Dict with output_path and subtitle_count
        """
        if task:
            task_manager.log(task, f"Analyzing {media_path.name}...")

        # Validate track is PGS
        info = await self.media_service.get_info(media_path)
        track = None
        for t in info.tracks:
            if t.index == track_index:
                track = t
                break

        if not track:
            raise ValueError(f"Track {track_index} not found")

        if track.codec != "hdmv_pgs_subtitle":
            raise ValueError(f"Track {track_index} is not a PGS subtitle (codec: {track.codec})")

        if task:
            task_manager.log(task, f"Found PGS track: {track.language or 'unknown'}")
            task_manager.update_progress(task, 5)

        # Create output filenames (Plex-compatible: MovieName.lang.ext)
        lang_suffix = f".{track.language}" if track.language else ""
        srt_filename = f"{media_path.stem}{lang_suffix}.srt"
        sup_filename = f"{media_path.stem}{lang_suffix}.sup"
        output_path = output_dir / srt_filename
        sup_path = output_dir / sup_filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        if task:
            task_manager.log(task, "Extracting PGS subtitle stream...")
            task_manager.update_progress(task, 10)

        # Step 1: Extract SUP file using ffmpeg (kept for later comparison)
        await self._extract_sup(media_path, track_index, sup_path, task)

        sup_size = sup_path.stat().st_size
        if task:
            task_manager.log(task, f"Extracted SUP file ({sup_size / 1024:.1f} KB)")
            task_manager.update_progress(task, 30)

        # Step 2: Convert SUP to SRT using pgs-to-srt
        if task:
            task_manager.log(task, f"Running OCR with pgs-to-srt (language: {language})...")
            task_manager.update_progress(task, 40)

        srt_content = await self._run_pgs_to_srt(sup_path, language, task)

        # Write SRT file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Count subtitles (count lines that are just numbers)
        subtitle_count = sum(1 for line in srt_content.split('\n') if line.strip().isdigit())

        if task:
            task_manager.log(task, f"Written {subtitle_count} subtitles to SRT")

        if task:
            task_manager.update_progress(task, 100, f"OCR complete: {subtitle_count} subtitles")

        return {
            "output_path": output_path,
            "subtitle_count": subtitle_count,
        }

    async def _extract_sup(
        self,
        media_path: Path,
        track_index: int,
        sup_path: Path,
        task: Task = None,
    ):
        """Extract SUP file from media using ffmpeg"""
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(media_path),
            "-map", f"0:{track_index}",
            "-c", "copy",
            str(sup_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()

        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise RuntimeError(f"Failed to extract PGS: {stderr.decode()}")

    async def _run_pgs_to_srt(
        self,
        sup_path: Path,
        language: str,
        task: Task = None,
    ) -> str:
        """
        Run pgs-to-srt to convert SUP file to SRT.

        pgs-to-srt is installed at /opt/pgs-to-srt and uses tessdata at /opt/tessdata
        """
        # Map language code to tessdata file
        tessdata_path = f"/opt/tessdata/{language}.traineddata"

        cmd = [
            "deno",
            "run",
            "--allow-read",
            "/opt/pgs-to-srt/pgs-to-srt.js",
            tessdata_path,
            str(sup_path),
        ]

        if task:
            task_manager.log(task, f"Executing: deno run pgs-to-srt.js {language}.traineddata ...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"pgs-to-srt failed: {error_msg}")

        if task:
            task_manager.update_progress(task, 90, "OCR complete, writing output...")

        return stdout.decode("utf-8")
