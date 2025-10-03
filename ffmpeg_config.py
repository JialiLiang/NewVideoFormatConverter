"""Central configuration helpers for FFmpeg runtime options."""
from __future__ import annotations

import os
from typing import Tuple

_MIN_THREADS = 2


def _resolve_threads() -> Tuple[int, str]:
    """Resolve the ffmpeg thread count from environment or CPU availability."""
    env_value = os.environ.get("FFMPEG_THREADS")
    if env_value:
        try:
            thread_count = int(env_value)
            if thread_count >= 1:
                return thread_count, str(thread_count)
        except ValueError:
            pass

    cpu_threads = os.cpu_count() or _MIN_THREADS
    thread_count = max(_MIN_THREADS, cpu_threads)
    return thread_count, str(thread_count)


FFMPEG_THREADS, FFMPEG_THREAD_STR = _resolve_threads()

__all__ = ["FFMPEG_THREADS", "FFMPEG_THREAD_STR"]
