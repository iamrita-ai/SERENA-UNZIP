# utils/gdrive.py
from urllib.parse import urlparse, parse_qs
from typing import Optional


def _extract_file_id(url: str) -> Optional[str]:
    """
    Handle variants:
    - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    - https://drive.google.com/open?id=FILE_ID
    - https://drive.google.com/uc?export=download&id=FILE_ID
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "id" in qs:
        return qs["id"][0]

    parts = [p for p in parsed.path.split("/") if p]
    if "d" in parts:
        idx = parts.index("d")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return None


def get_gdrive_direct_link(url: str) -> Optional[str]:
    """
    Convert normal Google Drive share link to direct download link.
    Big files (virus scan bypass) may still fail (confirm token),
    but small/medium files usually work.
    """
    file_id = _extract_file_id(url)
    if not file_id:
        return None
    return f"https://drive.google.com/uc?export=download&id={file_id}"
