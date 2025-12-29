"""
Media info API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import os

from backend.models.schemas import MediaInfo
from backend.services.media_info import MediaInfoService
from backend.api.routes.files import validate_path, get_media_root

router = APIRouter()
media_service = MediaInfoService()


@router.get("/info", response_model=MediaInfo)
async def get_media_info(path: str = Query(..., description="Path to the MKV file")):
    """
    Get detailed information about an MKV file.
    Includes video, audio, and subtitle track details.
    """
    full_path = validate_path(path)

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    if full_path.suffix.lower() != ".mkv":
        raise HTTPException(status_code=400, detail="File is not an MKV")

    try:
        info = await media_service.get_info(full_path)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get media info: {str(e)}")


@router.get("/tracks")
async def get_tracks(
    path: str = Query(..., description="Path to the MKV file"),
    track_type: str = Query(default=None, description="Filter by track type: video, audio, subtitle"),
):
    """
    Get track listing for an MKV file.
    Optionally filter by track type.
    """
    full_path = validate_path(path)

    if not full_path.is_file() or full_path.suffix.lower() != ".mkv":
        raise HTTPException(status_code=400, detail="Invalid MKV file")

    try:
        info = await media_service.get_info(full_path)
        tracks = info.tracks

        if track_type:
            tracks = [t for t in tracks if t.type.value == track_type]

        return {"path": path, "tracks": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tracks: {str(e)}")
