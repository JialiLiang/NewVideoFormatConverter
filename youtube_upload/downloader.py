"""Utilities for fetching remote video sources before upload."""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


class DownloadError(Exception):
    """Raised when a remote source cannot be downloaded."""


def _derive_filename(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if not name:
        return fallback
    return name


def _ensure_extension(name: str, response: requests.Response) -> str:
    path = Path(name)
    if path.suffix:
        return name

    content_type = response.headers.get('content-type', '').split(';')[0].strip()
    guessed = mimetypes.guess_extension(content_type) if content_type else None
    if guessed:
        return f"{name}{guessed}"
    return f"{name}.mp4"


def download_to_directory(url: str, directory: Path, *, prefix: str = 'remote') -> Path:
    """Download the remote file into *directory* and return the local path."""

    directory.mkdir(parents=True, exist_ok=True)
    fallback_name = f"{prefix}_{os.urandom(4).hex()}"

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise DownloadError(f"Failed to download {url}: {exc}") from exc

    filename = _derive_filename(url, fallback_name)
    filename = _ensure_extension(filename, response)

    target = directory / filename
    counter = 1
    while target.exists():
        target = directory / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
        counter += 1

    try:
        with target.open('wb') as handle:
            for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                if chunk:
                    handle.write(chunk)
    except Exception as exc:  # noqa: BLE001
        raise DownloadError(f"Error writing download for {url}: {exc}") from exc

    return target
