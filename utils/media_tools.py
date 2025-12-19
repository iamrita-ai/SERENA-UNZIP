# utils/media_tools.py
import asyncio
import os
from typing import List


class FFmpegError(RuntimeError):
    pass


async def run_ffmpeg(cmd: list):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise FFmpegError(err.decode(errors="ignore"))


async def extract_audio(video_path: str, output_path: str):
    # ffmpeg -i input -vn -acodec copy output
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "copy",
        output_path
    ]
    await run_ffmpeg(cmd)


async def merge_videos(video_paths: List[str], output_path: str):
    # Create a temp txt list file and use concat demuxer
    list_file = output_path + ".txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for path in video_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]
    await run_ffmpeg(cmd)
    try:
        os.remove(list_file)
    except OSError:
        pass


async def split_video(video_path: str, start: str, duration: str, output_path: str):
    # start like "00:01:00", duration like "00:00:30"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", start,
        "-t", duration,
        "-c", "copy",
        output_path
    ]
    await run_ffmpeg(cmd)


async def generate_thumbnail(
    video_path: str,
    thumb_path: str,
    time_pos: str = "00:00:02",
):
    """
    Thumbnail generate karega video se:
    ffmpeg -ss time_pos -i video -vframes 1 -q:v 2 thumb.jpg
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", time_pos,
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path,
    ]
    await run_ffmpeg(cmd)
    return thumb_path
