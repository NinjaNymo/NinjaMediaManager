"""
Subtitle processing API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import asyncio
import base64
import os
import re

from backend.models.schemas import (
    ExtractRequest, ExtractResponse,
    OCRRequest, OCRResponse,
    CompareRequest, CompareResult,
    SubtitleInfoResponse, SpellCheckRequest, SpellCheckResponse,
    SpellCheckIssue, IssueType, PgsImageResponse, PgsPreviewResponse,
    SubtitleEditRequest, SubtitleEditResponse,
    AddStampRequest, AddStampResponse, RemoveStampResponse, DeleteSubtitleResponse,
    CheckStampCollisionResponse,
)
from spellchecker import SpellChecker
from backend.services.subtitle_extractor import SubtitleExtractor
from backend.services.ocr_service import OCRService
from backend.services.task_manager import task_manager
from backend.api.routes.files import validate_path, get_media_root

router = APIRouter()
extractor = SubtitleExtractor()
ocr_service = OCRService()


def get_output_root() -> Path:
    """Get the output root path from environment"""
    return Path(os.environ.get("OUTPUT_PATH", "/output"))


@router.post("/extract", response_model=ExtractResponse)
async def extract_subtitle(request: ExtractRequest):
    """
    Extract a subtitle track from an MKV file.
    Supports SRT, ASS, and PGS formats.
    """
    full_path = validate_path(request.media_path)
    output_root = get_output_root()

    if not full_path.is_file() or full_path.suffix.lower() != ".mkv":
        raise HTTPException(status_code=400, detail="Invalid MKV file")

    # Create a task for tracking
    task = task_manager.create_task(f"Extract subtitle track {request.track_index}")
    task_manager.start_task(task)

    try:
        output_path = await extractor.extract(
            media_path=full_path,
            track_index=request.track_index,
            output_dir=output_root,
            output_format=request.output_format,
            task=task,
        )

        task_manager.complete_task(task, {"output_path": str(output_path)})

        return ExtractResponse(
            success=True,
            output_path=str(output_path.relative_to(output_root)),
            message=f"Subtitle extracted successfully",
        )
    except ValueError as e:
        task_manager.fail_task(task, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        task_manager.fail_task(task, str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/ocr", response_model=OCRResponse)
async def ocr_subtitle(request: OCRRequest):
    """
    Perform OCR on a PGS subtitle track.
    Converts image-based subtitles to SRT text format.
    """
    full_path = validate_path(request.media_path)
    output_root = get_output_root()

    if not full_path.is_file() or full_path.suffix.lower() != ".mkv":
        raise HTTPException(status_code=400, detail="Invalid MKV file")

    # Create a task for tracking
    task = task_manager.create_task(f"OCR subtitle track {request.track_index}")
    task_manager.start_task(task)

    try:
        result = await ocr_service.process_pgs(
            media_path=full_path,
            track_index=request.track_index,
            output_dir=output_root,
            language=request.language,
            task=task,
        )

        task_manager.complete_task(task, {
            "output_path": str(result["output_path"]),
            "subtitle_count": result["subtitle_count"],
        })

        return OCRResponse(
            success=True,
            output_path=str(result["output_path"].relative_to(output_root)),
            message="OCR completed successfully",
            subtitle_count=result["subtitle_count"],
        )
    except ValueError as e:
        task_manager.fail_task(task, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        task_manager.fail_task(task, str(e))
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@router.post("/compare", response_model=CompareResult)
async def compare_subtitles(request: CompareRequest):
    """
    Compare two SRT subtitle files.
    Calculates time offset and finds matching lines.
    """
    output_root = get_output_root()

    # Validate paths (could be in output or media directories)
    path1 = output_root / request.srt_path_1.lstrip("/")
    path2 = output_root / request.srt_path_2.lstrip("/")

    if not path1.exists() or not path2.exists():
        raise HTTPException(status_code=404, detail="One or both subtitle files not found")

    try:
        from backend.services.subtitle_compare import SubtitleComparer
        comparer = SubtitleComparer()
        result = comparer.compare(path1, path2)

        return CompareResult(
            file1=request.srt_path_1,
            file2=request.srt_path_2,
            file1_count=result["file1_count"],
            file2_count=result["file2_count"],
            time_offset_ms=result["time_offset_ms"],
            matches=result["matches"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/download/{filepath:path}")
async def download_subtitle(filepath: str):
    """
    Download an extracted subtitle file.
    """
    output_root = get_output_root()
    full_path = (output_root / filepath).resolve()

    # Security check
    try:
        full_path.relative_to(output_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="application/x-subrip",
    )


def validate_output_path(path: str) -> Path:
    """
    Validate and resolve a path within the output directory.
    Returns the resolved path if valid, raises HTTPException if not.
    """
    output_root = get_output_root()

    if not path or path == "/":
        raise HTTPException(status_code=400, detail="Path required")

    try:
        full_path = (output_root / path.lstrip("/")).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Ensure the resolved path is within output_root
    try:
        full_path.relative_to(output_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside output directory")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return full_path


def parse_srt_time(time_str: str) -> int:
    """Parse SRT timestamp to milliseconds"""
    match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{1,3})", time_str)
    if not match:
        return 0
    h, m, s, ms = match.groups()
    # Pad milliseconds to 3 digits if needed (e.g., "54" -> "540")
    ms = ms.ljust(3, '0')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


def format_duration(ms: int) -> str:
    """Format milliseconds as HH:MM:SS"""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_srt_file(content: str) -> list[dict]:
    """
    Parse SRT file content into a list of subtitle entries.
    Each entry has: index, start_time, end_time, text, line_number
    """
    entries = []
    blocks = re.split(r'\n\n+', content.strip())

    line_number = 1
    for block in blocks:
        lines = block.strip().split('\n')
        # Need at least 2 lines (index and timestamp), text may be empty or on line 3+
        if len(lines) >= 2:
            try:
                index = int(lines[0])
                time_match = re.match(
                    r'(\d{2}:\d{2}:\d{2},\d{1,3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{1,3})',
                    lines[1]
                )
                if time_match:
                    text = '\n'.join(lines[2:]) if len(lines) > 2 else ''
                    entries.append({
                        'index': index,
                        'start_time': time_match.group(1),
                        'end_time': time_match.group(2),
                        'text': text,
                        'line_number': line_number + 2,  # Text starts on 3rd line of block
                    })
            except ValueError:
                pass
        line_number += len(lines) + 1  # +1 for the blank line

    return entries


@router.get("/info", response_model=SubtitleInfoResponse)
async def get_subtitle_info(path: str = Query(..., description="Path to subtitle file")):
    """
    Get information about a subtitle file.
    """
    full_path = validate_output_path(path)

    if not full_path.suffix.lower() in {'.srt', '.ass', '.ssa', '.sub', '.sup'}:
        raise HTTPException(status_code=400, detail="Not a subtitle file")

    try:
        stat = full_path.stat()

        # Read file for additional info
        content = full_path.read_text(encoding='utf-8', errors='replace')

        line_count = 0
        duration = None
        preview_lines = []

        if full_path.suffix.lower() == '.srt':
            entries = parse_srt_file(content)
            line_count = len(entries)

            # Get duration from last entry
            if entries:
                last_time = entries[-1]['end_time']
                duration = format_duration(parse_srt_time(last_time))

            # Generate preview (first 3 entries)
            for entry in entries[:3]:
                preview_lines.append(f"{entry['index']}")
                preview_lines.append(f"{entry['start_time']} --> {entry['end_time']}")
                preview_lines.append(entry['text'])
                preview_lines.append("")
        else:
            # For non-SRT, just count lines and show beginning
            lines = content.split('\n')
            line_count = len(lines)
            preview_lines = lines[:20]

        return SubtitleInfoResponse(
            path=path,
            filename=full_path.name,
            size=stat.st_size,
            line_count=line_count,
            duration=duration,
            preview='\n'.join(preview_lines).strip() if preview_lines else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read subtitle: {str(e)}")


def parse_replacements(replacements_str: str) -> list[tuple[str, str]]:
    """
    Parse replacement string in format: key=value,key=value
    e.g., "|=I,'=',/=I" -> [('|', 'I'), (''', "'"), ('/', 'I')]
    """
    pairs = []
    if not replacements_str.strip():
        return pairs

    # Split by comma, but handle escaped commas if needed
    parts = replacements_str.split(',')
    for part in parts:
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            if key and value is not None:  # Allow empty value for deletion
                pairs.append((key, value))
    return pairs


def parse_ignore_list(ignore_str: str) -> set[str]:
    """
    Parse ignore list: comma-separated words/characters
    e.g., "Gandalf,Frodo,™" -> {'Gandalf', 'Frodo', '™'}
    """
    if not ignore_str.strip():
        return set()
    return {item.strip() for item in ignore_str.split(',') if item.strip()}


@router.post("/spell-check", response_model=SpellCheckResponse)
async def spell_check_subtitle(request: SpellCheckRequest):
    """
    Perform spell check on an SRT subtitle file.

    Stage 1: Apply character replacements from user-defined list
    Stage 2: Find invalid characters (not in allowed set, excluding ignored)
    Stage 3: Dictionary-based spell checking (excluding ignored words)
    """
    full_path = validate_output_path(request.path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Spell check only supported for SRT files")

    try:
        content = full_path.read_text(encoding='utf-8', errors='replace')
        replacements_made = 0
        file_modified = False

        # Parse ignore list
        ignore_set = set()
        if request.ignore_enabled and request.ignore_list:
            ignore_set = parse_ignore_list(request.ignore_list)

        # Stage 1: Apply character replacements
        if request.replacements_enabled and request.replacements:
            replacement_pairs = parse_replacements(request.replacements)
            for old_char, new_char in replacement_pairs:
                count = content.count(old_char)
                if count > 0:
                    content = content.replace(old_char, new_char)
                    replacements_made += count
                    file_modified = True

        # Write file if any replacements were made
        if file_modified:
            full_path.write_text(content, encoding='utf-8')

        # Stage 2: Find invalid characters
        entries = parse_srt_file(content)
        issues: list[SpellCheckIssue] = []
        invalid_char_count = 0
        spelling_count = 0

        # Allowed characters: letters, digits, whitespace, and common punctuation
        allowed_pattern = re.compile(r'[a-zA-Z0-9\s!?.,:\-"\'\n\r…—–\'\'""()]')

        for entry in entries:
            text = entry['text']
            for pos, char in enumerate(text):
                if char not in '\n\r' and not allowed_pattern.match(char):
                    # Skip if character is in ignore list
                    if char in ignore_set:
                        continue
                    issues.append(SpellCheckIssue(
                        type=IssueType.INVALID_CHARACTER,
                        index=entry['index'],
                        text=text.replace('\n', ' '),
                        position=pos,
                        character=char,
                    ))
                    invalid_char_count += 1

        # Check if corresponding .sup file exists for PGS comparison
        sup_path = full_path.with_suffix('.sup')
        has_pgs_source = sup_path.exists()

        # Stage 3: Dictionary-based spell checking
        # Map language codes to pyspellchecker language
        lang_map = {
            'en': 'en',
            'no': 'de',  # Norwegian not directly supported, use German as fallback
        }
        spell_lang = lang_map.get(request.language, 'en')
        spell = SpellChecker(language=spell_lang)

        # Pattern to extract words (alphanumeric sequences)
        word_pattern = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")

        for entry in entries:
            text = entry['text']
            # Find all words in the subtitle text
            for match in word_pattern.finditer(text):
                word = match.group()
                # Skip very short words and words that are all caps (likely acronyms)
                if len(word) <= 2 or (word.isupper() and len(word) <= 4):
                    continue

                # Skip if word is in ignore list (case-insensitive check)
                if word in ignore_set or word.lower() in {w.lower() for w in ignore_set}:
                    continue

                # Check if word is misspelled
                if word.lower() not in spell:
                    # Get suggestions (up to 3)
                    suggestions = list(spell.candidates(word.lower()) or [])[:3]

                    issues.append(SpellCheckIssue(
                        type=IssueType.SPELLING,
                        index=entry['index'],
                        text=text.replace('\n', ' '),
                        position=match.start(),
                        word=word,
                        suggestions=suggestions,
                    ))
                    spelling_count += 1

        return SpellCheckResponse(
            path=request.path,
            replacements_made=replacements_made,
            issues=issues,
            invalid_char_count=invalid_char_count,
            spelling_count=spelling_count,
            has_pgs_source=has_pgs_source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spell check failed: {str(e)}")


def get_sup_path_for_srt(srt_path: Path) -> Path | None:
    """Find the corresponding .sup file for an SRT"""
    sup_path = srt_path.with_suffix('.sup')
    return sup_path if sup_path.exists() else None


@router.get("/pgs-image", response_model=PgsImageResponse)
async def get_pgs_image(
    path: str = Query(..., description="Path to SRT file"),
    index: int = Query(..., description="Subtitle index number"),
):
    """
    Extract a single subtitle image from the PGS source file.
    Returns the image as a base64-encoded PNG.
    """
    full_path = validate_output_path(path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Path must be an SRT file")

    # Find corresponding SUP file
    sup_path = get_sup_path_for_srt(full_path)
    if not sup_path:
        raise HTTPException(status_code=404, detail="No PGS source file found")

    try:
        # Use pgs-to-srt to extract single image by index
        # pgs-to-srt outputs BMP to stdout when given an index
        cmd = [
            "deno",
            "run",
            "--allow-read",
            "/opt/pgs-to-srt/pgs-to-srt.js",
            str(index),
            str(sup_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise HTTPException(status_code=500, detail=f"Failed to extract image: {error_msg}")

        if not stdout:
            raise HTTPException(status_code=404, detail=f"No image found for subtitle {index}")

        # stdout contains BMP data, convert to base64
        # The BMP is already a valid image format, but we'll serve it as-is
        # Frontend can display BMP directly or we could convert to PNG
        image_base64 = base64.b64encode(stdout).decode('ascii')

        return PgsImageResponse(
            index=index,
            image=image_base64,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image extraction failed: {str(e)}")


@router.get("/pgs-preview", response_model=PgsPreviewResponse)
async def get_pgs_preview(
    path: str = Query(..., description="Path to SUP file"),
    index: int = Query(0, description="Subtitle index number (0-based)"),
):
    """
    Get a preview image from a PGS/SUP subtitle file.
    Returns the image and total count for navigation.
    Total count is determined by trying to extract until failure.
    """
    full_path = validate_output_path(path)

    if not full_path.suffix.lower() == '.sup':
        raise HTTPException(status_code=400, detail="Path must be a SUP file")

    try:
        # Validate index is not negative
        if index < 0:
            raise HTTPException(status_code=400, detail="Index must be non-negative")

        # Get the image for the requested index
        # pgs-to-srt uses 1-based indexing for image export
        img_cmd = [
            "deno",
            "run",
            "--allow-read",
            "/opt/pgs-to-srt/pgs-to-srt.js",
            str(index + 1),  # Convert to 1-based index
            str(full_path),
        ]

        img_process = await asyncio.create_subprocess_exec(
            *img_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        img_stdout, img_stderr = await img_process.communicate()

        if img_process.returncode != 0 or not img_stdout:
            if index == 0:
                raise HTTPException(status_code=404, detail="No subtitles found in SUP file")
            else:
                raise HTTPException(status_code=404, detail=f"No image found for subtitle {index + 1}")

        image_base64 = base64.b64encode(img_stdout).decode('ascii')

        # Try to determine if there's a next subtitle by checking index+2
        # This lets us know if we're at the end
        next_cmd = [
            "deno",
            "run",
            "--allow-read",
            "/opt/pgs-to-srt/pgs-to-srt.js",
            str(index + 2),  # Check next one
            str(full_path),
        ]

        next_process = await asyncio.create_subprocess_exec(
            *next_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        next_stdout, _ = await next_process.communicate()
        has_next = next_process.returncode == 0 and bool(next_stdout)

        # We don't know exact total, but we can indicate if there's more
        # Use -1 to indicate "unknown total" or calculate based on has_next
        # For now, return index+2 if has_next, else index+1 as total
        total_count = index + 2 if has_next else index + 1

        return PgsPreviewResponse(
            index=index,
            total_count=total_count,
            image=image_base64,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PGS preview failed: {str(e)}")


@router.post("/edit", response_model=SubtitleEditResponse)
async def edit_subtitle(request: SubtitleEditRequest):
    """
    Edit a single subtitle entry in an SRT file.
    Preserves timestamps and only updates the text content.
    """
    full_path = validate_output_path(request.path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Only SRT files can be edited")

    try:
        content = full_path.read_text(encoding='utf-8', errors='replace')
        entries = parse_srt_file(content)

        # Find the entry to edit
        target_entry = None
        for entry in entries:
            if entry['index'] == request.index:
                target_entry = entry
                break

        if not target_entry:
            raise HTTPException(status_code=404, detail=f"Subtitle {request.index} not found")

        # Rebuild the SRT file with the updated text
        new_content_parts = []
        for entry in entries:
            new_content_parts.append(str(entry['index']))
            new_content_parts.append(f"{entry['start_time']} --> {entry['end_time']}")
            if entry['index'] == request.index:
                new_content_parts.append(request.new_text)
            else:
                new_content_parts.append(entry['text'])
            new_content_parts.append('')  # Blank line between entries

        new_content = '\n'.join(new_content_parts)

        # Write back to file
        full_path.write_text(new_content, encoding='utf-8')

        return SubtitleEditResponse(
            success=True,
            message=f"Subtitle {request.index} updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


def format_srt_time(ms: int) -> str:
    """Format milliseconds as SRT timestamp (HH:MM:SS,mmm)"""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def check_stamp_collision(entries: list[dict], stamp_start_ms: int, stamp_end_ms: int) -> list[int]:
    """
    Check if a stamp would collide with existing subtitles.
    Returns list of colliding subtitle indices.
    Collision formula: (sub.start < stamp.end) AND (sub.end > stamp.start)
    """
    colliding = []
    for entry in entries:
        sub_start = parse_srt_time(entry['start_time'])
        sub_end = parse_srt_time(entry['end_time'])
        if sub_start < stamp_end_ms and sub_end > stamp_start_ms:
            colliding.append(entry['index'])
    return colliding


def has_existing_stamp(entries: list[dict]) -> bool:
    """Check if a creator stamp already exists in the SRT file"""
    # Check if the first subtitle contains our stamp marker text
    if entries:
        first_text = entries[0]['text'].lower()
        if 'ninjamediamanager' in first_text or 'ninjanymo' in first_text:
            return True
    return False


@router.get("/check-stamp-collision", response_model=CheckStampCollisionResponse)
async def check_stamp_collision_endpoint(
    path: str = Query(..., description="Path to SRT file"),
    start_time: str = Query("00:00:05,000", description="Stamp start time (HH:MM:SS,mmm)"),
    end_time: str = Query("00:00:15,000", description="Stamp end time (HH:MM:SS,mmm)"),
):
    """
    Check if adding a stamp at the given time would collide with existing subtitles.
    Also checks if a stamp already exists in the file.
    """
    full_path = validate_output_path(path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Only SRT files are supported")

    try:
        content = full_path.read_text(encoding='utf-8', errors='replace')
        entries = parse_srt_file(content)

        # Parse stamp times
        stamp_start_ms = parse_srt_time(start_time)
        stamp_end_ms = parse_srt_time(end_time)

        if stamp_start_ms >= stamp_end_ms:
            raise HTTPException(status_code=400, detail="Start time must be before end time")

        # Check for collisions
        colliding = check_stamp_collision(entries, stamp_start_ms, stamp_end_ms)

        # Check if stamp already exists
        stamp_exists = has_existing_stamp(entries)

        return CheckStampCollisionResponse(
            collision=len(colliding) > 0,
            colliding_subtitles=colliding,
            has_stamp=stamp_exists,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collision check failed: {str(e)}")


@router.post("/add-stamp", response_model=AddStampResponse)
async def add_stamp(request: AddStampRequest):
    """
    Add a creator stamp to the beginning of an SRT file.
    The stamp is inserted as subtitle #1 and all existing subtitles are re-indexed.
    Returns an error if the stamp would collide with existing subtitles.
    """
    full_path = validate_output_path(request.path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Only SRT files are supported")

    try:
        content = full_path.read_text(encoding='utf-8', errors='replace')
        entries = parse_srt_file(content)

        # Parse stamp times
        stamp_start_ms = parse_srt_time(request.start_time)
        stamp_end_ms = parse_srt_time(request.end_time)

        if stamp_start_ms >= stamp_end_ms:
            raise HTTPException(status_code=400, detail="Start time must be before end time")

        # Check if stamp already exists
        if has_existing_stamp(entries):
            return AddStampResponse(
                success=False,
                message="A creator stamp already exists in this file",
                collision=False,
                colliding_subtitles=[],
            )

        # Check for collisions
        colliding = check_stamp_collision(entries, stamp_start_ms, stamp_end_ms)
        if colliding:
            return AddStampResponse(
                success=False,
                message=f"Stamp collides with existing subtitle(s): {', '.join(map(str, colliding))}",
                collision=True,
                colliding_subtitles=colliding,
            )

        # Build new SRT content with stamp as first entry
        new_content_parts = []

        # Add stamp as entry #1
        new_content_parts.append("1")
        new_content_parts.append(f"{request.start_time} --> {request.end_time}")
        new_content_parts.append(request.text)
        new_content_parts.append("")

        # Re-index and add existing entries
        for entry in entries:
            new_index = entry['index'] + 1
            new_content_parts.append(str(new_index))
            new_content_parts.append(f"{entry['start_time']} --> {entry['end_time']}")
            new_content_parts.append(entry['text'])
            new_content_parts.append("")

        new_content = '\n'.join(new_content_parts)

        # Write back to file
        full_path.write_text(new_content, encoding='utf-8')

        return AddStampResponse(
            success=True,
            message="Creator stamp added successfully",
            collision=False,
            colliding_subtitles=[],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add stamp failed: {str(e)}")


@router.post("/remove-stamp", response_model=RemoveStampResponse)
async def remove_stamp(path: str = Query(..., description="Path to SRT file")):
    """
    Remove a creator stamp from an SRT file.
    The stamp is identified by checking if the first subtitle contains NinjaMediaManager markers.
    All remaining subtitles are re-indexed starting from 1.
    """
    full_path = validate_output_path(path)

    if not full_path.suffix.lower() == '.srt':
        raise HTTPException(status_code=400, detail="Only SRT files are supported")

    try:
        content = full_path.read_text(encoding='utf-8', errors='replace')
        entries = parse_srt_file(content)

        if not entries:
            return RemoveStampResponse(
                success=False,
                message="No subtitles found in file",
            )

        # Check if stamp exists
        if not has_existing_stamp(entries):
            return RemoveStampResponse(
                success=False,
                message="No creator stamp found in this file",
            )

        # Remove the first entry (the stamp) and re-index remaining entries
        new_content_parts = []
        new_index = 1

        for entry in entries[1:]:  # Skip the first entry (stamp)
            new_content_parts.append(str(new_index))
            new_content_parts.append(f"{entry['start_time']} --> {entry['end_time']}")
            new_content_parts.append(entry['text'])
            new_content_parts.append("")
            new_index += 1

        new_content = '\n'.join(new_content_parts)

        # Write back to file
        full_path.write_text(new_content, encoding='utf-8')

        return RemoveStampResponse(
            success=True,
            message="Creator stamp removed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove stamp failed: {str(e)}")


@router.delete("/delete", response_model=DeleteSubtitleResponse)
async def delete_subtitle(path: str = Query(..., description="Path to subtitle file")):
    """
    Delete a subtitle file (.srt or .sup) from the output directory.
    """
    full_path = validate_output_path(path)

    # Only allow deleting subtitle files
    allowed_extensions = {'.srt', '.sup', '.ass', '.ssa', '.sub'}
    if full_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Only subtitle files can be deleted ({', '.join(allowed_extensions)})"
        )

    try:
        if not full_path.exists():
            return DeleteSubtitleResponse(
                success=False,
                message="File not found",
            )

        # Delete the file
        full_path.unlink()

        return DeleteSubtitleResponse(
            success=True,
            message=f"Deleted {full_path.name}",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
