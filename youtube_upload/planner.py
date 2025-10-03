"""Planning helpers shared by CLI and future upload services."""
from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import UploadPlan
from language_config import LANGUAGES, LANGUAGE_CODE_MAPPING

FEATURE_ALIASES = {
    'AIBG': 'AIBG',
    'IGSTORY': 'IGSTORY',
    'LOGO': 'LOGO',
    'ANIM': 'ANIM',
    'MIX': 'MIX',
    'AIFILL': 'AIFILL',
    'RETOUCH': 'RETOUCH',
    'IMGT_CHANGE': 'IMGT-CHANGE',
    'IMGT_MODEL': 'IMGT-MODEL',
    'IMGT_STAGE': 'IMGT-STAGE',
    'IMGT_BEAUTIFY': 'IMGT-BEAUTIFY',
    'RND': 'RND',
}

LANGUAGE_MAP = {code.lower(): code.lower() for code in LANGUAGES.keys()}
for old, iso in LANGUAGE_CODE_MAPPING.items():
    LANGUAGE_MAP[old.lower()] = iso.lower()
for meta in LANGUAGES.values():
    old = meta.get('old_code')
    if old:
        LANGUAGE_MAP[old.lower()] = meta['iso_639_1']
LANGUAGE_CODES = set(LANGUAGE_MAP.keys())

_URL_RE = re.compile(r"^[a-z]+://", re.IGNORECASE)
DEFAULT_DATE_CODE = dt.datetime.utcnow().strftime("%d%m%Y")


def is_remote_source(value: str) -> bool:
    """Return True when the provided string looks like a URL."""

    return bool(_URL_RE.match(value.strip()))


def parse_playlist_hint(hint: str, *, default_date: str = DEFAULT_DATE_CODE) -> tuple[str | None, str | None, str]:
    """Extract base tag, language code, and date code from a legacy playlist hint."""

    tokens: List[str] = []
    start = 0
    while True:
        start = hint.find('[', start)
        if start == -1:
            break
        end = hint.find(']', start + 1)
        if end == -1:
            break
        token = hint[start + 1 : end].strip()
        if token:
            tokens.append(token)
        start = end + 1

    base_tag = tokens[0].upper() if tokens else None
    language = tokens[1].lower() if len(tokens) > 1 else None

    if base_tag:
        base_tag = FEATURE_ALIASES.get(base_tag.replace('-', '_'), base_tag)
    if language:
        language = LANGUAGE_MAP.get(language.lower(), language.lower())

    inferred_date = default_date
    parts = hint.rsplit('_', maxsplit=1)
    if parts:
        tail = parts[-1]
        if len(tail) >= 8 and tail[:8].isdigit():
            inferred_date = tail[:8]

    if not base_tag or base_tag not in FEATURE_ALIASES.values() or not language or language not in LANGUAGE_CODES:
        fallback_base, fallback_lang = _fallback_from_tokens(hint)
        if (not base_tag or base_tag not in FEATURE_ALIASES.values()) and fallback_base:
            base_tag = fallback_base
        if fallback_lang:
            language = LANGUAGE_MAP.get(fallback_lang, fallback_lang)

    return base_tag, language, inferred_date


def _fallback_from_tokens(hint: str) -> tuple[str | None, str | None]:
    parts = hint.replace('.', '_').split('_')
    base = None
    lang = None
    for token in reversed(parts):
        cleaned = token.strip()
        if not cleaned:
            continue
        normalized = cleaned.replace('-', '_')
        lower = normalized.lower()
        upper = normalized.upper()

        if lang is None and lower in LANGUAGE_CODES:
            lang = LANGUAGE_MAP.get(lower, lower)
            continue

        if base is None:
            canonical = FEATURE_ALIASES.get(upper)
            if canonical:
                base = canonical
        if base and lang:
            break

    return base, lang


def resolve_source_path(raw_path: str, csv_dir: Path) -> tuple[Path | None, bool]:
    """Resolve a CSV file_path value to a local path when possible."""

    raw_path = raw_path.strip()
    if not raw_path:
        return None, False

    if is_remote_source(raw_path):
        return None, True

    path = Path(raw_path)
    if not path.is_absolute():
        path = (csv_dir / path).resolve()

    return path, False


def build_plan(
    rows: Sequence[dict[str, str]],
    *,
    csv_dir: Path,
    default_date: str = DEFAULT_DATE_CODE,
) -> List[UploadPlan]:
    plans: List[UploadPlan] = []
    for idx, row in enumerate(rows, start=1):
        raw_path = (row.get('file_path') or row.get('filepath') or '').strip()
        hint = (row.get('playlist_hint') or row.get('hint') or '').strip()

        if not raw_path or not hint:
            raise ValueError(f"Row {idx}: both 'file_path' and 'playlist_hint' are required")

        resolved_path, is_remote = resolve_source_path(raw_path, csv_dir)
        original_name = (row.get('original_name') or Path(raw_path).name or '').strip()
        if not original_name:
            original_name = Path(raw_path).name or 'upload'

        base_tag, language, inferred_date = parse_playlist_hint(hint, default_date=default_date)

        if base_tag and language:
            planned_name = f"[{base_tag}]_[{language}]_{inferred_date}"
        else:
            planned_name = 'UNRESOLVED'

        file_exists = resolved_path.exists() if resolved_path else False

        plans.append(
            UploadPlan(
                index=idx,
                source=raw_path,
                playlist_hint=hint,
                resolved_path=resolved_path,
                is_remote=is_remote,
                base_tag=base_tag,
                language=language,
                inferred_date=inferred_date,
                planned_playlist_name=planned_name,
                file_exists=file_exists,
                original_name=original_name,
            )
        )
    return plans


def read_csv(path: Path) -> List[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader if any((value or '').strip() for value in row.values())]
        if not rows:
            raise ValueError('CSV file contains no data rows')
        return rows


def iter_preview_lines(plans: Iterable[UploadPlan]) -> Iterable[str]:
    header = (
        f"{'#':>3}  {'Ready':<5}  {'Remote':<6}  {'Playlist Name':<35}  "
        f"{'Base Tag':<8}  {'Lang':<5}  {'Date':<8}  Source"
    )
    yield header
    yield '-' * len(header)
    for plan in plans:
        ready = 'yes' if plan.ready else 'no'
        remote = 'yes' if plan.is_remote else 'no'
        yield (
            f"{plan.index:>3}  {ready:<5}  {remote:<6}  {plan.planned_playlist_name:<35}  "
            f"{(plan.base_tag or '-'):<8}  {(plan.language or '-'):<5}  {plan.inferred_date:<8}  {plan.source}"
        )
