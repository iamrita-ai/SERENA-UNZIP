# utils/http_downloader.py
import os
import time
from typing import Optional

import aiohttp
from pyrogram.types import Message

from utils.progress import progress_for_pyrogram


async def download_file(
    url: str,
    dest_path: str,
    chunk_size: int = 64 * 1024,
    timeout: Optional[int] = None,
    status_message: Optional[Message] = None,
    file_name: Optional[str] = None,
    direction: str = "from web",
) -> str:
    """
    Simple HTTP downloader using aiohttp.
    Agar status_message diya ho aur server ne Content-Length diya ho
    to progress bar + ETA show karega (Telegram wale style me).
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            start = time.time()

            fname = file_name or os.path.basename(dest_path) or "file"

            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)

                    if status_message and total > 0:
                        # show progress every few seconds
                        await progress_for_pyrogram(
                            downloaded,
                            total,
                            status_message,
                            start,
                            fname,
                            direction,
                        )

            # final 100% update agar total > 0
            if status_message and total > 0 and downloaded == total:
                await progress_for_pyrogram(
                    downloaded,
                    total,
                    status_message,
                    start,
                    fname,
                    direction,
                )

    return dest_path
