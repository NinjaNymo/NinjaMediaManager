"""
File browsing API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import os
from datetime import datetime

from backend.models.schemas import FileItem, FileType, BrowseResponse
from backend.services.file_scanner import FileScanner

router = APIRouter()
scanner = FileScanner()


def get_media_root() -> Path:
    """Get the media root path from environment"""
    return Path(os.environ.get("MEDIA_PATH", "/media"))


def get_output_root() -> Path:
    """Get the output root path from environment"""
    return Path(os.environ.get("OUTPUT_PATH", "/output"))


def validate_path(path: str) -> Path:
    """
    Validate and resolve a path, preventing path traversal attacks.
    Returns the resolved path if valid, raises HTTPException if not.
    """
    media_root = get_media_root()

    # Handle empty or root path
    if not path or path == "/":
        return media_root

    # Resolve the full path
    try:
        full_path = (media_root / path.lstrip("/")).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Ensure the resolved path is within media_root
    try:
        full_path.relative_to(media_root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside media directory")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    return full_path


@router.get("/browse", response_model=BrowseResponse)
async def browse_directory(path: str = Query(default="", description="Directory path to browse")):
    """
    Browse a directory and list its contents.
    Only shows directories and .mkv files.
    """
    full_path = validate_path(path)
    media_root = get_media_root()

    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items: list[FileItem] = []

    try:
        for entry in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                items.append(FileItem(
                    name=entry.name,
                    path=str(entry.relative_to(media_root)),
                    type=FileType.DIRECTORY,
                ))
            elif entry.suffix.lower() == ".mkv":
                stat = entry.stat()
                items.append(FileItem(
                    name=entry.name,
                    path=str(entry.relative_to(media_root)),
                    type=FileType.MKV,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Calculate parent path
    parent = None
    if full_path != media_root.resolve():
        parent_path = full_path.parent
        if parent_path >= media_root.resolve():
            parent = str(parent_path.relative_to(media_root))
            if parent == ".":
                parent = ""

    return BrowseResponse(
        path=str(full_path.relative_to(media_root)) if full_path != media_root else "",
        parent=parent,
        items=items,
    )


@router.get("/scan")
async def scan_directory(
    path: str = Query(default="", description="Directory path to scan"),
    recursive: bool = Query(default=True, description="Scan subdirectories"),
):
    """
    Scan a directory for all .mkv files.
    Returns a flat list of all MKV files found.
    """
    full_path = validate_path(path)
    media_root = get_media_root()

    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    mkv_files = scanner.scan_for_mkv(full_path, recursive=recursive)

    return {
        "path": str(full_path.relative_to(media_root)) if full_path != media_root else "",
        "count": len(mkv_files),
        "files": [
            {
                "name": f.name,
                "path": str(f.relative_to(media_root)),
                "size": f.stat().st_size,
            }
            for f in mkv_files
        ],
    }


@router.get("/browse-output", response_model=BrowseResponse)
async def browse_output_directory(path: str = Query(default="", description="Directory path to browse")):
    """
    Browse the output directory and list its contents.
    Shows directories and subtitle files (.srt, .ass, .sup, .sub).
    """
    output_root = get_output_root()

    # Ensure output directory exists
    output_root.mkdir(parents=True, exist_ok=True)

    # Handle empty or root path
    if not path or path == "/":
        full_path = output_root
    else:
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
        # Return empty list for non-existent paths in output
        return BrowseResponse(path=path, parent="" if path else None, items=[])

    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items: list[FileItem] = []
    subtitle_extensions = {".srt", ".ass", ".ssa", ".sup", ".sub"}

    try:
        for entry in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                items.append(FileItem(
                    name=entry.name,
                    path=str(entry.relative_to(output_root)),
                    type=FileType.DIRECTORY,
                ))
            elif entry.suffix.lower() in subtitle_extensions:
                stat = entry.stat()
                items.append(FileItem(
                    name=entry.name,
                    path=str(entry.relative_to(output_root)),
                    type=FileType.OTHER,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Calculate parent path
    parent = None
    if full_path != output_root.resolve():
        parent_path = full_path.parent
        if parent_path >= output_root.resolve():
            parent = str(parent_path.relative_to(output_root))
            if parent == ".":
                parent = ""

    return BrowseResponse(
        path=str(full_path.relative_to(output_root)) if full_path != output_root else "",
        parent=parent,
        items=items,
    )
