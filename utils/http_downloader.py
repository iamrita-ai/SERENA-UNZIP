# utils/http_downloader.py
import os
from typing import Optional

import aiohttp


async def download_file(
    url: str,
    dest_path: str,
    chunk_size: int = 64 * 1024,
    timeout: Optional[int] = None,
) -> str:
    """
    Simple HTTP downloader using aiohttp.
    Koi progress bar nahi, sirf straight download.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)

    return dest_path
