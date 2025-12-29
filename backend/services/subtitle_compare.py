"""
Subtitle comparison and synchronization service
"""
import pysrt
from pathlib import Path
from difflib import SequenceMatcher


class SubtitleComparer:
    """Service for comparing and synchronizing SRT files"""

    def compare(self, path1: Path, path2: Path) -> dict:
        """
        Compare two SRT subtitle files.

        Finds matching lines and calculates the time offset between them.

        Args:
            path1: Path to first SRT file (reference)
            path2: Path to second SRT file (to be synced)

        Returns:
            Dict with comparison results including suggested offset
        """
        subs1 = pysrt.open(str(path1))
        subs2 = pysrt.open(str(path2))

        matches = []
        offsets = []

        # Compare each subtitle in file2 against file1
        for sub2 in subs2:
            best_match = None
            best_ratio = 0

            for sub1 in subs1:
                # Calculate text similarity
                ratio = SequenceMatcher(None, sub1.text.lower(), sub2.text.lower()).ratio()

                if ratio > best_ratio and ratio > 0.7:  # 70% similarity threshold
                    best_ratio = ratio
                    best_match = sub1

            if best_match:
                # Calculate time offset in milliseconds
                offset = self._time_to_ms(sub2.start) - self._time_to_ms(best_match.start)
                offsets.append(offset)

                matches.append({
                    "index1": best_match.index,
                    "index2": sub2.index,
                    "text1": best_match.text,
                    "text2": sub2.text,
                    "time1": str(best_match.start),
                    "time2": str(sub2.start),
                    "similarity": round(best_ratio, 2),
                    "offset_ms": offset,
                })

        # Calculate median offset (more robust than average)
        median_offset = 0
        if offsets:
            sorted_offsets = sorted(offsets)
            mid = len(sorted_offsets) // 2
            median_offset = sorted_offsets[mid]

        return {
            "file1_count": len(subs1),
            "file2_count": len(subs2),
            "time_offset_ms": median_offset,
            "matches": matches[:50],  # Limit to first 50 matches for API response
        }

    def apply_offset(self, srt_path: Path, offset_ms: int, output_path: Path) -> Path:
        """
        Apply a time offset to an SRT file.

        Args:
            srt_path: Path to the SRT file
            offset_ms: Offset in milliseconds (positive = delay, negative = advance)
            output_path: Path for the output file

        Returns:
            Path to the modified SRT file
        """
        subs = pysrt.open(str(srt_path))

        # Apply offset
        subs.shift(milliseconds=offset_ms)

        # Save to new file
        subs.save(str(output_path), encoding="utf-8")

        return output_path

    def _time_to_ms(self, time) -> int:
        """Convert pysrt time to milliseconds"""
        return (
            time.hours * 3600000 +
            time.minutes * 60000 +
            time.seconds * 1000 +
            time.milliseconds
        )

    def get_preview(self, path: Path, limit: int = 10) -> list[dict]:
        """
        Get a preview of subtitle entries.

        Args:
            path: Path to the SRT file
            limit: Maximum number of entries to return

        Returns:
            List of subtitle entries
        """
        subs = pysrt.open(str(path))

        return [
            {
                "index": sub.index,
                "start": str(sub.start),
                "end": str(sub.end),
                "text": sub.text,
            }
            for sub in subs[:limit]
        ]
