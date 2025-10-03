"""Dataclasses describing upload planning state."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UploadPlan:
    """Represents one video slated for upload."""

    index: int
    source: str  # original file path or URL from CSV/UI
    playlist_hint: str
    resolved_path: Optional[Path]
    is_remote: bool
    base_tag: Optional[str]
    language: Optional[str]
    inferred_date: str
    planned_playlist_name: str
    file_exists: bool
    original_name: str

    @property
    def ready(self) -> bool:
        """Return True when the plan has a concrete local file to upload."""

        return self.file_exists and not self.is_remote


@dataclass
class UploadJob:
    """Concrete upload task derived from a plan."""

    plan: UploadPlan
    local_path: Path
    playlist_name: str
    title: str
    downloaded: bool  # whether the source was fetched from a remote URL


@dataclass
class UploadResult:
    """Summary of an attempted upload."""

    index: int
    source: str
    local_path: Optional[Path]
    playlist_name: str
    playlist_id: Optional[str]
    video_id: Optional[str]
    status: str  # success | skipped | failed
    message: str
