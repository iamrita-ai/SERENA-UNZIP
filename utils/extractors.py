# utils/extractors.py
import os
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List, Optional

import py7zr
import rarfile

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
PDF_EXT = {".pdf"}
APK_EXT = {".apk", ".xapk", ".apks"}
TXT_EXT = {".txt"}
M3U_EXT = {".m3u", ".m3u8"}


def _scan_stats(base_dir: Path) -> Dict[str, Any]:
    stats = {
        "total_files": 0,
        "videos": 0,
        "pdf": 0,
        "apk": 0,
        "txt": 0,
        "m3u": 0,
        "others": 0,
        "folders": 0,
    }
    files: List[str] = []

    for root, dirs, fls in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        if rel_root != ".":
            stats["folders"] += 1

        for f in fls:
            stats["total_files"] += 1
            p = Path(root) / f
            rel_path = os.path.relpath(p, base_dir)
            ext = p.suffix.lower()

            if ext in VIDEO_EXT:
                stats["videos"] += 1
            elif ext in PDF_EXT:
                stats["pdf"] += 1
            elif ext in APK_EXT:
                stats["apk"] += 1
            elif ext in TXT_EXT:
                stats["txt"] += 1
            elif ext in M3U_EXT:
                stats["m3u"] += 1
            else:
                stats["others"] += 1

            files.append(rel_path)

    return {"stats": stats, "files": files}


def _archive_type(path: str) -> Optional[str]:
    """
    Robust archive type detection based on suffixes and headers.
    Returns: 'zip' | 'tar' | '7z' | 'rar' | None
    """
    p = Path(path)
    lower = str(p).lower()
    suffixes = "".join(p.suffixes).lower()

    # explicit suffix combos
    if suffixes.endswith(".zip"):
        return "zip"
    if suffixes.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")):
        return "tar"
    if suffixes.endswith(".tar"):
        return "tar"
    if suffixes.endswith(".7z"):
        return "7z"
    if suffixes.endswith(".rar"):
        return "rar"

    # fallback by single suffix
    s = p.suffix.lower()
    if s == ".zip":
        return "zip"
    if s in (".tar", ".gz", ".bz2", ".xz"):
        return "tar"
    if s == ".7z":
        return "7z"
    if s == ".rar":
        return "rar"

    # header based fallback
    try:
        if zipfile.is_zipfile(path):
            return "zip"
    except Exception:
        pass

    try:
        with rarfile.RarFile(path) as _:
            return "rar"
    except Exception:
        pass

    return None


def is_zip_encrypted(path: str) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            for zinfo in z.infolist():
                if zinfo.flag_bits & 0x1:
                    return True
    except Exception:
        return False
    return False


def detect_encrypted(path: str) -> bool:
    """
    Basic encrypted detection for zip/rar/7z.
    """
    t = _archive_type(path)
    if t == "zip":
        return is_zip_encrypted(path)

    try:
        if t == "rar":
            with rarfile.RarFile(path) as rf:
                _ = rf.infolist()
        elif t == "7z":
            with py7zr.SevenZipFile(path, mode="r") as z:
                _ = z.getnames()
        else:
            return False
    except (rarfile.NeedFirstVolume, rarfile.PasswordRequired, py7zr.exceptions.PasswordRequired):
        return True
    except Exception:
        return False

    return False


def extract_archive(
    archive_path: str,
    dest_dir: str,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extracts archive to dest_dir.
    Supports: zip, rar, 7z, tar, tar.gz, tgz, tar.bz2, tbz2, gz, bz2
    Returns: { "stats": {...}, "files": [relative paths] }
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    t = _archive_type(archive_path)

    if t is None:
        raise ValueError("Unsupported archive format.")

    if t == "zip":
        with zipfile.ZipFile(archive_path) as z:
            if password:
                z.setpassword(password.encode("utf-8"))
            z.extractall(dest_dir)

    elif t == "tar":
        # tarfile automatically handles .tar, .tar.gz, .tgz, .tar.bz2 etc.
        with tarfile.open(archive_path, "r:*") as tfile:
            # tar generally no password
            tfile.extractall(dest_dir)

    elif t == "7z":
        with py7zr.SevenZipFile(archive_path, mode="r", password=password) as z:
            z.extractall(dest_dir)

    elif t == "rar":
        with rarfile.RarFile(archive_path) as rf:
            if password:
                rf.setpassword(password)
            rf.extractall(dest_dir)

    else:
        raise ValueError("Unsupported archive format.")

    return _scan_stats(Path(dest_dir))
