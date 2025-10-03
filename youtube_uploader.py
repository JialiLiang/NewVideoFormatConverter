"""CLI tool for previewing (and soon executing) YouTube playlist uploads."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Iterable, Sequence

from youtube_upload import (
    DEFAULT_DATE_CODE,
    build_plan,
    iter_preview_lines,
    read_csv,
)
from youtube_upload.runner import process_plans, write_results_csv
from youtube_upload.uploader import YoutubeUploadClient


def print_preview(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Preview YouTube playlist uploads from CSV input.')
    parser.add_argument('--csv', required=True, help='Path to CSV file with file_path and playlist_hint columns.')
    parser.add_argument(
        '--date',
        dest='date_code',
        default=DEFAULT_DATE_CODE,
        help='Fallback DDMMYYYY date code when the hint is missing one (default: today UTC).',
    )
    parser.add_argument(
        '--run',
        action='store_true',
        help='Execute uploads (requires youtube.upload OAuth scope). Default is preview only.',
    )
    parser.add_argument(
        '--output',
        help='Optional path for the upload results CSV when running uploads.',
    )
    parser.add_argument(
        '--tmp-dir',
        help='Directory for temporary downloads when processing remote URLs.',
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Disable launching a browser for OAuth; requires valid cached token.',
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    try:
        rows = read_csv(csv_path)
        plans = build_plan(rows, csv_dir=csv_path.parent, default_date=args.date_code)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print('\nPlanned uploads:')
    print_preview(iter_preview_lines(plans))

    missing_files = sum(1 for plan in plans if not plan.file_exists and not plan.is_remote)
    unresolved = sum(1 for plan in plans if plan.planned_playlist_name == 'UNRESOLVED')
    total = len(plans)

    print('\nSummary:')
    print(f"  Total rows: {total}")
    print(f"  Missing local files: {missing_files}")
    print(f"  Remote sources: {sum(1 for plan in plans if plan.is_remote)}")
    print(f"  Unresolved playlist hints: {unresolved}")

    if not args.run:
        print('\nNext steps:')
        print('  - Review planned playlist names and ensure the target playlists exist.')
        print('  - Provide missing files or clarify hints before enabling actual uploads.')
        print('  - Re-run with --run to perform uploads once everything is ready.')
        return 0

    print('\nStarting upload run...')
    try:
        uploader = YoutubeUploadClient(allow_browser=not args.no_browser)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to initialize YouTube client: {exc}", file=sys.stderr)
        return 1

    results = process_plans(plans, uploader=uploader, temp_dir=Path(args.tmp_dir) if args.tmp_dir else None)

    success = sum(1 for r in results if r.status == 'success')
    skipped = sum(1 for r in results if r.status == 'skipped')
    failed = sum(1 for r in results if r.status == 'failed')

    timestamp = dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = Path(args.output) if args.output else Path(args.csv).with_name(f'youtube_upload_results_{timestamp}.csv')
    write_results_csv(results, output_path)

    print('\nUpload run complete:')
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Report saved to: {output_path}")

    if failed:
        print('\nCheck the report for errors. Fix issues and retry only the failed rows (they are safe to re-run).')

    return 0 if failed == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
