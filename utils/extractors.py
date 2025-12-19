import os
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List, Optional

import py7zr
import rarfile

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
PDF_EXT = {".pdf"}
APK_EXT = {".apk", ".xapk"}
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
    files = []

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
    lower = path.lower()
    if lower.endswith(".zip"):
        return is_zip_encrypted(path)
    # rar/7z detection basic: we just try to list
    try:
        if lower.endswith(".rar"):
            with rarfile.RarFile(path) as rf:
                _ = rf.infolist()
        elif lower.endswith(".7z"):
            with py7zr.SevenZipFile(path, mode="r") as z:
                _ = z.getnames()
    except rarfile.BadRarFile:
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
    Supports: zip, rar, 7z, tar, tar.gz, tgz, tar.bz2
    Returns: { "stats": {...}, "files": [relative paths] }
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    lower = archive_path.lower()

    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as z:
            if password:
                z.setpassword(password.encode("utf-8"))
            z.extractall(dest_dir)
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        mode = "r:*"
        with tarfile.open(archive_path, mode) as t:
            if password:
                # tar generally doesn't support password; ignore
                pass
            t.extractall(dest_dir)
    elif lower.endswith(".7z"):
        with py7zr.SevenZipFile(archive_path, mode="r", password=password) as z:
            z.extractall(dest_dir)
    elif lower.endswith(".rar"):
        with rarfile.RarFile(archive_path) as rf:
            if password:
                rf.setpassword(password)
            rf.extractall(dest_dir)
    else:
        raise ValueError("Unsupported archive format.")

    return _scan_stats(Path(dest_dir))


def extract_single_file(
    archive_path: str,
    dest_dir: str,
    member_rel_path: str,
    password: Optional[str] = None,
) -> str:
    """
    Extract only one file from archive.
    Returns absolute path of extracted file.
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    lower = archive_path.lower()
    member_rel_path = member_rel_path.replace("\\", "/")

    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as z:
            if password:
                z.setpassword(password.encode("utf-8"))
            z.extract(member_rel_path, dest_dir)
            return str(Path(dest_dir) / member_rel_path)
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        with tarfile.open(archive_path, "r:*") as t:
            t.extract(member_rel_path, dest_dir)
            return str(Path(dest_dir) / member_rel_path)
    elif lower.endswith(".7z"):
        with py7zr.SevenZipFile(archive_path, mode="r", password=password) as z:
            # py7zr cannot extract single directly by path easily,
            # but we can filter by target
            allnames = z.getnames()
            if member_rel_path not in allnames:
                raise FileNotFoundError(member_rel_path)
            z.extract(targets=[member_rel_path], path=dest_dir)
            return str(Path(dest_dir) / member_rel_path)
    elif lower.endswith(".rar"):
        with rarfile.RarFile(archive_path) as rf:
            if password:
                rf.setpassword(password)
            rf.extract(member_rel_path, dest_dir)
            return str(Path(dest_dir) / member_rel_path)
    else:
        raise ValueError("Unsupported archive format.")
