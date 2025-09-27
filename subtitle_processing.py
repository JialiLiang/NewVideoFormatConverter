"""Subtitle text processing helpers derived from 2_OpenAI_SRT_Term_split.py.

This module centralizes the language-aware line splitting logic so that we can
reuse it when generating SRT files directly from Whisper segments inside the
web app.
"""

from __future__ import annotations

import importlib.util
import re
from typing import List

from language_config import (
    LANGUAGE_CODE_MAPPING,
    get_iso_code_from_old,
    get_old_code_from_iso,
)

HAS_FUGASHI = importlib.util.find_spec("fugashi") is not None
HAS_OPENCC = importlib.util.find_spec("opencc") is not None

CHINESE_PUNCTUATION = "，。！？、；：""''「」【】《》（）…~～"
ALL_PUNCTUATION = CHINESE_PUNCTUATION + ",.!?;:\"'()[]{}<>…-"
PRESERVED_TERMS = ["Photoroom", "AI", "App"]

MAX_LENGTHS = {
    'CN': 16,
    'HK': 16,
    'JP': 16,
    'KR': 16,
    'TH': 20,
}
DEFAULT_MAX_LENGTH = 24
RTL_LANGUAGES = {'SA'}


def _normalize_codes(language_code: str) -> tuple[str, str]:
    code = (language_code or '').strip()
    if not code:
        return 'en', 'EN'
    lower = code.lower()
    upper = code.upper()
    if lower in LANGUAGE_CODE_MAPPING.values() or lower in ('en', 'zh', 'ja', 'ko'):
        return lower, get_old_code_from_iso(lower)
    if upper in LANGUAGE_CODE_MAPPING:
        return LANGUAGE_CODE_MAPPING[upper].lower(), upper
    return lower, upper


def _is_punctuation(char: str) -> bool:
    return char in ALL_PUNCTUATION


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"([,.!?;:])([\w])", r"\1 \2", text)
    return text


def _convert_traditional(text: str) -> str:
    if not HAS_OPENCC:
        return text
    try:
        import opencc

        converter = opencc.OpenCC('s2t')
        return converter.convert(text)
    except Exception:
        return text


def _split_cjk_text(text: str, max_length: int, traditional: bool = False) -> List[str]:
    if traditional:
        text = _convert_traditional(text)
    text = _clean_text(text)

    lines: List[str] = []
    current = ''
    i = 0
    while i < len(text):
        if current == '' and _is_punctuation(text[i]):
            if lines and len(lines[-1]) + 1 <= max_length:
                lines[-1] += text[i]
            i += 1
            continue

        preserved = False
        for term in PRESERVED_TERMS:
            if text[i:].startswith(term):
                preserved = True
                if len(current) + len(term) <= max_length:
                    current += term
                else:
                    if current:
                        lines.append(current)
                    current = term
                i += len(term)
                break
        if preserved:
            continue

        char = text[i]
        lookahead = text[i + 1] if i + 1 < len(text) else ''
        if len(current) + 1 <= max_length:
            if lookahead and _is_punctuation(lookahead) and len(current) + 2 <= max_length:
                current += char + lookahead
                i += 2
            else:
                current += char
                i += 1
        else:
            if current:
                lines.append(current)
            current = char
            i += 1

        if current and current.endswith(('。', '！', '!', '？', '?')):
            lines.append(current)
            current = ''

    if current:
        lines.append(current)

    return [line for line in lines if line.strip()]


def _split_japanese(text: str, max_length: int) -> List[str]:
    if not HAS_FUGASHI:
        return _split_cjk_text(text, max_length)
    try:
        import fugashi

        tagger = fugashi.Tagger()
        words = [word.surface for word in tagger(text)]
        lines: List[str] = []
        current = ''
        for word in words:
            if any(term in word for term in PRESERVED_TERMS):
                word_text = word
            else:
                word_text = word
            if len(current) + len(word_text) <= max_length:
                current += word_text
            else:
                if current:
                    lines.append(current)
                current = word_text
        if current:
            lines.append(current)
        return [line for line in lines if line.strip()]
    except Exception:
        return _split_cjk_text(text, max_length)


def _split_lines(text: str, max_length: int, is_cjk: bool, language: Optional[str] = None) -> List[str]:
    lines: List[str] = []

    if language == 'JP':
        return _split_japanese(text, max_length)
    if language == 'CN':
        return _split_cjk_text(text, max_length, traditional=False)
    if language == 'HK':
        return _split_cjk_text(text, max_length, traditional=True)
    if language == 'KR':
        return _split_cjk_text(text, max_length)
    if language == 'TH':
        return _split_cjk_text(text, max_length)
    if language in RTL_LANGUAGES:
        words = text.split()
        current_line = ''
        for word in words:
            candidate = (word + ' ' + current_line).strip()
            if len(candidate) <= max_length:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
    if is_cjk:
        return _split_cjk_text(text, max_length)

    words = text.split()
    current_line = ''
    for word in words:
        candidate_len = len(current_line) + (len(word) + 1 if current_line else len(word))
        if candidate_len <= max_length:
            current_line += (' ' + word) if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def _split_text(text: str, language_code: str) -> List[str]:
    iso_code, old_code = _normalize_codes(language_code)
    max_len = MAX_LENGTHS.get(old_code, DEFAULT_MAX_LENGTH)
    is_cjk = old_code in {'JP', 'CN', 'KR', 'HK', 'TH'}
    language = old_code
    return _split_lines(text, max_len, is_cjk, language=language)


def refine_segments(segments: List[dict], language_code: str) -> List[dict]:
    refined: List[dict] = []
    if not segments:
        return refined

    for segment in segments:
        text = (segment.get('text') or '').strip()
        if not text:
            continue
        try:
            start = float(segment.get('start', 0.0))
        except (TypeError, ValueError):
            start = 0.0
        try:
            end = float(segment.get('end', start))
        except (TypeError, ValueError):
            end = start
        if end <= start:
            end = start + 0.5

        lines = _split_text(text, language_code)
        if not lines:
            continue

        duration = max(end - start, 0.5)
        slice_duration = duration / len(lines)
        for index, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            seg_start = start + index * slice_duration
            seg_end = start + (index + 1) * slice_duration
            refined.append({
                'start': seg_start,
                'end': seg_end,
                'text': line,
            })
    return refined
