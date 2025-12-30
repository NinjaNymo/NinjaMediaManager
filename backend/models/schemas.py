"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class FileType(str, Enum):
    DIRECTORY = "directory"
    MKV = "mkv"
    OTHER = "other"


class FileItem(BaseModel):
    """Represents a file or directory in the file browser"""
    name: str
    path: str
    type: FileType
    size: Optional[int] = None
    modified: Optional[str] = None


class BrowseResponse(BaseModel):
    """Response for file browsing endpoint"""
    path: str
    parent: Optional[str] = None
    items: list[FileItem]


class TrackType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


class SubtitleFormat(str, Enum):
    SRT = "subrip"
    ASS = "ass"
    PGS = "hdmv_pgs_subtitle"
    VOBSUB = "dvd_subtitle"
    OTHER = "other"


class Track(BaseModel):
    """Represents a track in an MKV file"""
    index: int
    type: TrackType
    codec: str
    language: Optional[str] = None
    title: Optional[str] = None
    default: bool = False
    forced: bool = False
    # Additional fields for specific track types
    width: Optional[int] = None  # video
    height: Optional[int] = None  # video
    bitrate: Optional[int] = None  # video/audio (bits per second)
    frame_rate: Optional[float] = None  # video (fps)
    channels: Optional[int] = None  # audio
    sample_rate: Optional[int] = None  # audio


class MediaInfo(BaseModel):
    """Full media information for an MKV file"""
    path: str
    filename: str
    size: int
    duration: Optional[float] = None
    format: str
    tracks: list[Track]


class ExtractRequest(BaseModel):
    """Request to extract a subtitle track"""
    media_path: str
    track_index: int
    output_format: Optional[str] = None  # None = keep original format


class ExtractResponse(BaseModel):
    """Response after extracting a subtitle"""
    success: bool
    output_path: Optional[str] = None
    message: str


class OCRRequest(BaseModel):
    """Request to OCR a PGS subtitle track"""
    media_path: str
    track_index: int
    language: str = "eng"


class OCRResponse(BaseModel):
    """Response after OCR processing"""
    success: bool
    output_path: Optional[str] = None
    message: str
    subtitle_count: Optional[int] = None


class SubtitleLine(BaseModel):
    """A single subtitle entry"""
    index: int
    start_time: str  # Format: HH:MM:SS,mmm
    end_time: str
    text: str


class CompareRequest(BaseModel):
    """Request to compare two subtitle files"""
    srt_path_1: str
    srt_path_2: str


class CompareResult(BaseModel):
    """Result of subtitle comparison"""
    file1: str
    file2: str
    file1_count: int
    file2_count: int
    time_offset_ms: int  # Suggested offset to sync file2 to file1
    matches: list[dict]  # Matching subtitle pairs


class SubtitleInfoResponse(BaseModel):
    """Response for subtitle file info"""
    path: str
    filename: str
    size: int
    line_count: int
    duration: Optional[str] = None  # e.g., "01:45:23"
    preview: Optional[str] = None  # First few lines


class SpellCheckRequest(BaseModel):
    """Request for spell check operation"""
    path: str
    # New unified replacement system: "key=value,key=value" format
    # e.g., "|=I,'=',/=I,\"=\",\"=\""
    replacements_enabled: bool = True
    replacements: str = "|=I,'=',/=I,\"=\",\"=\""
    # Ignore list for spell checker and illegal character detection
    # Comma-separated words/characters to skip
    ignore_enabled: bool = False
    ignore_list: str = ""
    language: str = "en"


class IssueType(str, Enum):
    INVALID_CHARACTER = "invalid_character"
    SPELLING = "spelling"


class SpellCheckIssue(BaseModel):
    """A unified issue found during spell check (invalid char or misspelling)"""
    type: IssueType
    index: int  # Subtitle index number
    text: str  # Full text of the subtitle
    position: int  # Position in text
    # For invalid character issues
    character: Optional[str] = None  # The problematic character
    # For spelling issues
    word: Optional[str] = None  # The misspelled word
    suggestions: list[str] = []  # Suggested corrections (up to 3)


class SpellCheckResponse(BaseModel):
    """Response from spell check operation"""
    path: str
    replacements_made: int  # Number of | -> I replacements
    issues: list[SpellCheckIssue]  # All issues (invalid chars + misspellings)
    invalid_char_count: int  # Count of invalid character issues
    spelling_count: int  # Count of spelling issues
    has_pgs_source: bool = False  # True if .sup file exists for image comparison


class PgsImageResponse(BaseModel):
    """Response containing a PGS subtitle image"""
    index: int
    image: str  # Base64-encoded PNG image


class PgsPreviewResponse(BaseModel):
    """Response for PGS/SUP file preview"""
    index: int
    total_count: int  # Total number of subtitles in the SUP file
    image: str  # Base64-encoded BMP image


class SubtitleEditRequest(BaseModel):
    """Request to edit a subtitle entry"""
    path: str
    index: int  # Subtitle index number to edit
    new_text: str


class SubtitleEditResponse(BaseModel):
    """Response after editing a subtitle"""
    success: bool
    message: str


class AddStampRequest(BaseModel):
    """Request to add a creator stamp to an SRT file"""
    path: str
    start_time: str = "00:00:05,000"  # Default: 5 seconds
    end_time: str = "00:00:15,000"    # Default: 15 seconds
    text: str = "Subtitles by NinjaNymo\nMade with NinjaMediaManager"


class AddStampResponse(BaseModel):
    """Response after adding a stamp"""
    success: bool
    message: str
    collision: bool = False  # True if stamp couldn't be added due to collision
    colliding_subtitles: list[int] = []  # Indices of conflicting subtitles


class RemoveStampResponse(BaseModel):
    """Response after removing a stamp"""
    success: bool
    message: str


class CheckStampCollisionResponse(BaseModel):
    """Response from checking stamp collision"""
    collision: bool
    colliding_subtitles: list[int] = []
    has_stamp: bool = False  # True if stamp already exists in file
