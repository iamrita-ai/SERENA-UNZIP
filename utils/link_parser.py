import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


URL_REGEX = re.compile(
    r"(https?://[^\s]+)",
    re.IGNORECASE
)

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".tar.gz"}


def find_links_in_text(text: str) -> List[str]:
    return [m.group(1).strip().strip(".,)") for m in URL_REGEX.finditer(text)]


def classify_link(url: str) -> str:
    u = url.lower()
    if "drive.google.com" in u:
        return "gdrive"
    if "t.me/" in u or "telegram.me/" in u:
        return "telegram"
    if u.endswith(".m3u8"):
        return "m3u8"
    # simple extension check for direct file
    for ext in VIDEO_EXT | ARCHIVE_EXT:
        if u.endswith(ext):
            return "direct"
    return "unknown"


def extract_links_from_folder(base_dir: str) -> Dict[str, List[str]]:
    """
    Scan .txt and .m3u/.m3u8 files inside extracted archive for links.
    """
    base = Path(base_dir)
    all_links: Dict[str, List[str]] = {
        "direct": [],
        "m3u8": [],
        "gdrive": [],
        "telegram": [],
        "unknown": [],
    }

    for root, dirs, files in os.walk(base):
        for f in files:
            p = Path(root) / f
            ext = p.suffix.lower()
            if ext not in {".txt", ".m3u", ".m3u8"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            urls = find_links_in_text(text)
            for url in urls:
                kind = classify_link(url)
                all_links.setdefault(kind, [])
                if url not in all_links[kind]:
                    all_links[kind].append(url)

    return all_links
