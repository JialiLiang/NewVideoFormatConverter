"""High-level orchestration for processing upload plans."""
from __future__ import annotations

import csv
import logging
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .downloader import DownloadError, download_to_directory
from .models import UploadJob, UploadPlan, UploadResult
from .uploader import YoutubeUploadClient

logger = logging.getLogger("youtube_upload.runner")


def prepare_job(plan: UploadPlan, temp_dir: Path, *, index_prefix: str) -> Tuple[Optional[UploadJob], List[UploadResult]]:
    """Prepare an UploadJob from a plan; return job and any immediate results."""

    if plan.planned_playlist_name == 'UNRESOLVED' or not plan.base_tag or not plan.language:
        result = UploadResult(
            index=plan.index,
            source=plan.source,
            local_path=None,
            playlist_name=plan.planned_playlist_name,
            playlist_id=None,
            video_id=None,
            status='skipped',
            message='Playlist hint could not be resolved (missing [TAG] and/or [lang])',
        )
        return None, [result]

    if plan.is_remote:
        try:
            local_path = download_to_directory(plan.source, temp_dir, prefix=f"job{index_prefix}")
            downloaded = True
        except DownloadError as exc:
            result = UploadResult(
                index=plan.index,
                source=plan.source,
                local_path=None,
                playlist_name=plan.planned_playlist_name,
                playlist_id=None,
                video_id=None,
                status='failed',
                message=str(exc),
            )
            return None, [result]
    else:
        if not plan.resolved_path or not plan.resolved_path.exists():
            result = UploadResult(
                index=plan.index,
                source=plan.source,
                local_path=plan.resolved_path,
                playlist_name=plan.planned_playlist_name,
                playlist_id=None,
                video_id=None,
                status='failed',
                message='Local file not found',
            )
            return None, [result]
        local_path = plan.resolved_path
        downloaded = False

    original_stem = Path(plan.original_name).stem or local_path.stem
    title = original_stem
    job = UploadJob(
        plan=plan,
        local_path=local_path,
        playlist_name=plan.planned_playlist_name,
        title=title,
        downloaded=downloaded,
    )
    return job, []


def process_plans(
    plans: Iterable[UploadPlan],
    *,
    uploader: YoutubeUploadClient,
    temp_dir: Path | None = None,
    overrides: Optional[dict[str, str]] = None,
) -> List[UploadResult]:
    """Process plans and return structured upload results."""

    results: List[UploadResult] = []
    overrides = overrides or {}

    with tempfile.TemporaryDirectory(dir=temp_dir) as tmp:
        tmp_dir = Path(tmp)
        for plan in plans:
            override_used = False
            if plan.base_tag and plan.language:
                key = f"{plan.base_tag.upper()}|{plan.language.lower()}"
                override_name = overrides.get(key)
                if override_name:
                    if override_name != plan.planned_playlist_name:
                        override_used = True
                    plan.planned_playlist_name = override_name

            job, immediate = prepare_job(plan, tmp_dir, index_prefix=str(plan.index))
            results.extend(immediate)
            if job is None:
                continue

            try:
                playlist_id = uploader.ensure_playlist(job.playlist_name)
                video_id = uploader.upload_video(job.local_path, title=job.title, made_for_kids=False)
                uploader.add_video_to_playlist(video_id, playlist_id)
                message = 'Uploaded and added to playlist'
                if override_used:
                    message += ' (reused existing playlist)'
                results.append(
                    UploadResult(
                        index=plan.index,
                        source=plan.source,
                        local_path=job.local_path,
                        playlist_name=job.playlist_name,
                        playlist_id=playlist_id,
                        video_id=video_id,
                        status='success',
                        message=message,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to process upload for %s", plan.source)
                results.append(
                    UploadResult(
                        index=plan.index,
                        source=plan.source,
                        local_path=job.local_path,
                        playlist_name=job.playlist_name,
                        playlist_id=None,
                        video_id=None,
                        status='failed',
                        message=str(exc),
                    )
                )
    return results


def write_results_csv(results: Iterable[UploadResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'index',
        'source',
        'local_path',
        'playlist_name',
        'playlist_id',
        'video_id',
        'status',
        'message',
    ]
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({
                'index': result.index,
                'source': result.source,
                'local_path': str(result.local_path) if result.local_path else '',
                'playlist_name': result.playlist_name,
                'playlist_id': result.playlist_id or '',
                'video_id': result.video_id or '',
                'status': result.status,
                'message': result.message,
            })
