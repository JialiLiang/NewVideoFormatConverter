import json
import os
import logging
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from moviepy.editor import CompositeVideoClip, ImageClip, VideoFileClip
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import Image, ImageDraw, ImageFont

try:  # Optional dependencies for proper RTL shaping
    import arabic_reshaper  # type: ignore
except Exception:  # pragma: no cover - optional runtime dep
    arabic_reshaper = None

try:  # Optional bidi ordering for RTL scripts
    from bidi.algorithm import get_display as bidi_get_display  # type: ignore
except Exception:  # pragma: no cover - optional runtime dep
    bidi_get_display = None

from subtitle_processing import refine_segments

from language_config import (
    LANGUAGES,
    LANGUAGE_CODE_MAPPING,
    get_iso_code_from_old,
    get_old_code_from_iso,
)

LOGGER = logging.getLogger(__name__)
FONT_DIRECTORY = Path(__file__).parent / "static" / "fonts"


def _collect_font_dirs() -> List[Path]:
    dirs: List[Path] = []
    env_single = os.getenv('ADLOCALIZER_FONT_DIR', '')
    env_multi = os.getenv('ADLOCALIZER_FONT_DIRS', '')
    env_multi_list = [p for p in env_multi.split(os.pathsep) if p]
    candidates = [FONT_DIRECTORY]
    if env_single:
        candidates.append(Path(env_single))
    candidates.extend(Path(p) for p in env_multi_list)
    candidates.extend([
        Path.home() / "Documents/AdLocaliserV1/New clean ones 2025/font",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
    ])
    for entry in candidates:
        if not entry:
            continue
        try:
            path = Path(entry)
        except TypeError:
            continue
        if path.exists() and path not in dirs:
            dirs.append(path)
    return dirs


FONT_SEARCH_DIRS = _collect_font_dirs()

LANGUAGE_FONT_CANDIDATES: Dict[str, List[str]] = {
    "CN": ["NotoSansCJKsc-Regular.otf", "NotoSansSC-Regular.otf", "PingFang.ttc"],
    "HK": ["NotoSansCJKtc-Regular.otf", "NotoSansTC-Regular.otf", "PingFang.ttc"],
    "JP": [
        "Gen Jyuu Gothic Monospace Bold.ttf",
        "GenJyuuGothic-Monospace-Bold.ttf",
        "NotoSansJP-Regular.otf",
        "HiraginoSans-W4.ttc"
    ],
    "KR": ["NotoSansKR-Regular.otf", "AppleGothic.ttf", "AppleSDGothicNeo.ttc"],
    "SA": ["NotoNaskhArabic-Regular.ttf", "GeezaPro.ttf"],
    "TH": ["NotoSansThai-Regular.ttf", "Thonburi.ttc"],
    "IN": ["NotoSansDevanagari-Regular.ttf", "Mangal.ttf"],
    "VN": ["NotoSans-Regular.ttf"],
    "ID": ["NotoSans-Regular.ttf"],
    "MY": ["NotoSans-Regular.ttf"],
}

DEFAULT_FONT_CANDIDATES: List[str] = [
    "NotoSans-Regular.ttf",
    "DejaVuSans.ttf",
    "Arial.ttf",
    "Helvetica.ttf",
]

SUBTITLE_STYLES: Dict[str, Dict[str, object]] = {
    "default": {
        "name": "Rounded White",
        "description": "Rounded white capsule with bold black text",
        "text_color": "#111111",
        "background_color": "#FFFFFFFF",
        "padding": (48, 28),
        "border_radius": 28,
        "font_size": 88,
        "stroke_width": 0,
        "stroke_fill": "#00000000",
        "vertical_position": 0.72,
        "max_width_ratio": 0.92,
        "base_video_height": 1080,
        "base_video_width": 1080,
        "min_scale": 0.85,
        "max_scale": 1.2,
    },
    "tiktok": {
        "name": "TikTok Native",
        "description": "White text with subtle black stroke",
        "text_color": "#FFFFFF",
        "background_color": "#00000000",
        "padding": (40, 22),
        "border_radius": 16,
        "font_size": 84,
        "stroke_width": 2,
        "stroke_fill": "#000000FF",
        "vertical_position": 0.78,
        "max_width_ratio": 0.92,
        "base_video_height": 1080,
        "base_video_width": 1080,
        "min_scale": 0.85,
        "max_scale": 1.2,
    },
    "contrast": {
        "name": "High Contrast",
        "description": "Bold yellow background with dark text",
        "text_color": "#101010",
        "background_color": "#FFED4AEE",
        "padding": (42, 26),
        "border_radius": 18,
        "font_size": 58,
        "stroke_width": 0,
        "vertical_position": 0.74,
        "max_width_ratio": 0.76,
    },
    "minimal": {
        "name": "Minimal Shadow",
        "description": "Transparent black with light text and drop shadow",
        "text_color": "#F5F5F5",
        "background_color": "#00000080",
        "padding": (32, 22),
        "border_radius": 16,
        "font_size": 54,
        "stroke_width": 0,
        "vertical_position": 0.78,
        "max_width_ratio": 0.82,
    },
}

CJK_OLD_CODES = {"CN", "HK", "JP", "KR", "TH"}
RTL_OLD_CODES = {"SA"}


def _parse_color(color: object, default_alpha: int = 255) -> Tuple[int, int, int, int]:
    if isinstance(color, tuple):
        if len(color) == 4:
            return tuple(color)  # type: ignore[return-value]
        if len(color) == 3:
            r, g, b = color
            return int(r), int(g), int(b), default_alpha
    if isinstance(color, str):
        value = color.lstrip("#")
        if len(value) == 6:
            r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
            return r, g, b, default_alpha
        if len(value) == 8:
            r, g, b, a = (
                int(value[0:2], 16),
                int(value[2:4], 16),
                int(value[4:6], 16),
                int(value[6:8], 16),
            )
            return r, g, b, a
    return 255, 255, 255, default_alpha


def get_available_subtitle_styles() -> List[Dict[str, str]]:
    return [
        {"id": key, "name": config["name"], "description": config["description"]}
        for key, config in SUBTITLE_STYLES.items()
    ]


def _normalize_codes(lang_code: str) -> Tuple[str, str]:
    code = (lang_code or "").strip()
    if not code:
        return "en", "EN"
    lower = code.lower()
    upper = code.upper()
    if lower in LANGUAGES:
        return lower, get_old_code_from_iso(lower)
    if upper in LANGUAGE_CODE_MAPPING:
        return get_iso_code_from_old(upper), upper
    return lower, upper


def _shape_text_for_language(text: str, old_code: str) -> str:
    """Apply language-specific shaping (e.g., for Arabic RTL scripts)."""
    if not text:
        return text
    if old_code in RTL_OLD_CODES:
        shaped = text
        if arabic_reshaper is not None:
            try:
                shaped = arabic_reshaper.reshape(shaped)
            except Exception:  # pragma: no cover - optional dependency failure
                shaped = text
        if bidi_get_display is not None:
            try:
                shaped = bidi_get_display(shaped)
            except Exception:  # pragma: no cover - optional dependency failure
                pass
        return shaped
    return text


def _load_font(old_code: str, font_size: int) -> ImageFont.FreeTypeFont:
    candidates = LANGUAGE_FONT_CANDIDATES.get(old_code, []) + DEFAULT_FONT_CANDIDATES
    search_dirs = FONT_SEARCH_DIRS or [FONT_DIRECTORY]
    last_error: Optional[Exception] = None

    for candidate in candidates:
        for directory in search_dirs:
            candidate_path = directory / candidate
            if candidate_path.exists():
                try:
                    return ImageFont.truetype(str(candidate_path), font_size)
                except Exception as exc:
                    last_error = exc
                    continue
        try:
            return ImageFont.truetype(candidate, font_size)
        except Exception as exc:
            last_error = exc
            continue

    if last_error:
        LOGGER.warning("Font fallback for %s due to: %s", old_code, last_error)
    LOGGER.warning("Falling back to default PIL font for language %s", old_code)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, old_code: str) -> List[str]:
    if max_width <= 0:
        return [text]
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    if old_code in CJK_OLD_CODES:
        lines: List[str] = []
        current = ""
        for char in text:
            if char == "\n":
                lines.append(current)
                current = ""
                continue
            test = current + char
            width = draw.textlength(test, font=font)
            if width <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        width = draw.textlength(test, font=font)
        if width <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _create_text_clip(text: str, style_key: str, old_code: str, video_width: int, video_height: int) -> ImageClip:
    config = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["default"])
    base_height = float(config.get("base_video_height", 1920)) or 1920
    base_width = float(config.get("base_video_width", base_height)) or base_height
    raw_scale_height = video_height / base_height if base_height else 1.0
    raw_scale_width = video_width / base_width if base_width else raw_scale_height
    raw_scale = max(raw_scale_height, raw_scale_width)
    min_scale = float(config.get("min_scale", 0.55))
    max_scale = float(config.get("max_scale", 1.5))
    scale = max(min_scale, min(max_scale, raw_scale))

    font_size = int(config.get("font_size", 54) * scale)
    font = _load_font(old_code, font_size)

    max_ratio = float(config.get("max_width_ratio", 0.8))
    max_text_width = int(video_width * max_ratio)

    clean_text = text.strip() or " "
    logical_lines = _wrap_text(clean_text, font, max_text_width, old_code)
    if not logical_lines:
        logical_lines = [clean_text or " "]

    render_lines = [_shape_text_for_language(line, old_code) for line in logical_lines]

    background_color = _parse_color(config.get("background_color", "#000000A0"))
    text_color = _parse_color(config.get("text_color", "#FFFFFF"))
    stroke_width = max(0, int(config.get("stroke_width", 0) * scale))
    stroke_fill = _parse_color(config.get("stroke_fill", "#00000080"))
    border_radius = int(config.get("border_radius", 12) * scale)

    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bounding_boxes: List[Tuple[int, int, int, int]] = []
    line_heights: List[int] = []
    baseline_offsets: List[int] = []

    for line in render_lines:
        bbox: Optional[Tuple[int, int, int, int]]
        try:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
        except TypeError:
            bbox = draw.textbbox((0, 0), line, font=font)
        except Exception:
            bbox = None

        if bbox is None:
            width = int(draw.textlength(line, font=font))
            if hasattr(font, "getmetrics"):
                ascent, descent = font.getmetrics()
            else:  # pragma: no cover - fallback path
                ascent = font.size
                descent = max(2, int(font.size * 0.25))
            bbox = (0, -ascent, width, descent)

        bounding_boxes.append(bbox)
        line_height = (bbox[3] - bbox[1]) or max(font.size, 32)
        line_heights.append(line_height)
        baseline_offsets.append(-bbox[1])

    if not bounding_boxes:
        ascent = font.getmetrics()[0] if hasattr(font, "getmetrics") else font.size
        bounding_boxes = [(0, -ascent, font.size, font.size // 2)]
        line_heights = [font.size]
        baseline_offsets = [ascent]

    text_height = sum(line_heights)
    text_width = max((bbox[2] - bbox[0]) for bbox in bounding_boxes)

    padding_x, padding_y = config.get("padding", (36, 22))
    padding_x = int(padding_x * scale)
    padding_y = int(padding_y * scale)
    image_width = text_width + padding_x * 2
    image_height = text_height + padding_y * 2

    image = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    rect = ((0, 0), (image_width, image_height))
    if background_color[3] > 0:
        canvas.rounded_rectangle(rect, radius=border_radius, fill=background_color)

    current_y = padding_y
    align = "right" if old_code in RTL_OLD_CODES else "center"
    for idx, line in enumerate(render_lines):
        bbox = bounding_boxes[idx]
        width = bbox[2] - bbox[0]
        if align == "right":
            text_x = image_width - padding_x - width
        else:
            text_x = (image_width - width) // 2
        canvas.text(
            (text_x, current_y + baseline_offsets[idx]),
            line,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
            align=align,
        )
        current_y += line_heights[idx]

    array = np.array(image)
    return ImageClip(array).set_duration(1)


def format_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def build_srt_content(segments: List[Dict[str, float]]) -> str:
    entries: List[str] = []
    index = 1
    for segment in segments:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        start = format_timestamp(segment.get("start", 0.0))
        end = format_timestamp(segment.get("end", 0.0))
        entries.append(f"{index}\n{start} --> {end}\n{text}")
        index += 1
    return "\n\n".join(entries)


def transcribe_audio_for_subtitles(
    audio_path: Path,
    language_iso: str,
    openai_client,
    prompt: Optional[str] = None,
) -> Dict[str, object]:
    try:
        with open(audio_path, "rb") as audio_file:
            response = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                language=language_iso,
                prompt=prompt or "",
            )
        if hasattr(response, "model_dump"):
            payload = response.model_dump()
        elif isinstance(response, dict):
            payload = response
        else:
            payload = json.loads(response)
        segments = payload.get("segments", []) if isinstance(payload, dict) else []
        return {"success": True, "segments": segments, "text": payload.get("text", "")}
    except Exception as exc:  # pragma: no cover - relies on network API
        LOGGER.error("Subtitle transcription failed: %s", exc)
        return {"success": False, "error": str(exc)}


def generate_srt_file(
    audio_file: str,
    language_code: str,
    base_name: str,
    subtitles_dir: Path,
    openai_client,
) -> Dict[str, object]:
    if openai_client is None:
        return {"success": False, "error": "OpenAI client not configured"}

    iso_code, old_code = _normalize_codes(language_code)
    audio_path = Path(audio_file)
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    srt_path = subtitles_dir / f"{base_name}.srt"

    result = transcribe_audio_for_subtitles(audio_path, iso_code, openai_client)
    if not result.get("success"):
        return {"success": False, "error": result.get("error"), "language": old_code}

    raw_segments = result.get("segments", [])
    transcript_text = (result.get("text") or "").strip()

    refined_segments = refine_segments(raw_segments, language_code)
    fallback_used = False

    if not refined_segments and transcript_text:
        fallback_used = True
        approx_duration = max(len(transcript_text.split()) * 0.6, 4.0)
        refined_segments = refine_segments([
            {
                "start": 0.0,
                "end": approx_duration,
                "text": transcript_text,
            }
        ], language_code)

    if not refined_segments:
        fallback_used = True
        refined_segments = refine_segments([
            {
                "start": 0.0,
                "end": 4.0,
                "text": "(no subtitles available)",
            }
        ], language_code)

    if not refined_segments:
        return {"success": False, "error": "No subtitle content generated", "language": old_code}

    content = build_srt_content(refined_segments)
    srt_path.write_text(content, encoding="utf-8")

    transcript_path = subtitles_dir / f"{base_name}.json"
    try:
        transcript_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        transcript_path = None

    return {
        "success": True,
        "srt_path": str(srt_path),
        "srt_filename": srt_path.name,
        "language": old_code,
        "segments": refined_segments,
        "text": transcript_text,
        "fallback_used": fallback_used,
        "transcript_path": str(transcript_path) if transcript_path else None,
    }


def burn_subtitles_onto_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    language_code: str,
    style_key: str = "default",
    segments: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    video_clip = None
    subtitles = None
    result_clip = None
    try:
        _, old_code = _normalize_codes(language_code)
        video_clip = VideoFileClip(video_path)
        video_width, video_height = video_clip.size

        generator = partial(
            _create_text_clip,
            style_key=style_key,
            old_code=old_code,
            video_width=video_width,
            video_height=video_height,
        )

        segment_list = _ensure_segment_list(segments) if segments else _ensure_segment_list(_load_segments_from_srt(Path(srt_path)))
        fallback_generated = False
        if not segment_list:
            try:
                raw_lines = [
                    line.strip()
                    for line in Path(srt_path).read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.strip().isdigit() and '-->' not in line
                ]
                fallback_text = ' '.join(raw_lines).strip()
            except Exception:
                fallback_text = ''

            if fallback_text:
                fallback_generated = True
                duration = max(video_clip.duration - 0.5, 1.0)
                segment_list = _ensure_segment_list([
                    {
                        'start': 0.0,
                        'end': duration,
                        'text': fallback_text,
                    }
                ])

        if not segment_list:
            fallback_generated = True
            fallback_text = "(no subtitles available)"
            duration = max(video_clip.duration - 0.5, 1.0)
            segment_list = _ensure_segment_list([
                {
                    'start': 0.0,
                    'end': duration,
                    'text': fallback_text,
                }
            ])

        if not segment_list:
            return {"success": False, "error": "Subtitle file has no entries"}

        subtitle_tuples = [((seg['start'], seg['end']), seg['text']) for seg in segment_list]
        subtitles = SubtitlesClip(subtitle_tuples, generator)
        clip_list = (
            getattr(subtitles, 'clips', None)
            or getattr(subtitles, 'subclips', None)
            or getattr(subtitles, 'textclips', None)
            or getattr(subtitles, 'subtitles', [])
        )
        if not clip_list:
            return {"success": False, "error": "Subtitle file has no entries"}

        end_offset = 0.8
        subtitle_end = max(end for ((_, end), _) in subtitle_tuples)
        effective_end = min(subtitle_end, max(0, video_clip.duration - end_offset))
        subtitles = subtitles.subclip(0, effective_end)
        vertical_ratio = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["default"]).get("vertical_position", 0.75)
        pos_y = int(video_height * vertical_ratio)
        subtitles = subtitles.set_position(("center", pos_y))

        result_clip = CompositeVideoClip([video_clip, subtitles])
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result_clip.write_videofile(
            str(output_file),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_file.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
            threads=2,
            fps=video_clip.fps or 25,
            verbose=False,
            logger=None,
        )
        return {
            "success": True,
            "output_path": str(output_file),
            "language": old_code,
            "style": style_key,
            "fallback_generated": fallback_generated,
            "segments": segment_list,
        }
    except Exception as exc:  # pragma: no cover - relies on video processing
        LOGGER.exception("Failed to burn subtitles: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        for clip in (result_clip, subtitles, video_clip):
            try:
                if clip:
                    clip.close()
            except Exception:
                continue
def _ensure_segment_list(segment_list: List[Dict[str, object]]) -> List[Dict[str, object]]:
    valid_segments: List[Dict[str, object]] = []
    for segment in segment_list or []:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        try:
            start = float(segment.get("start", 0.0))
        except (TypeError, ValueError):
            start = 0.0
        try:
            end = float(segment.get("end", start + 0.5))
        except (TypeError, ValueError):
            end = start + 0.5
        if end <= start:
            end = start + 0.5
        valid_segments.append({"start": start, "end": end, "text": text})
    return valid_segments


def _parse_srt_timecode_to_seconds(value: str) -> float:
    try:
        time_part = value.replace(',', '.').strip()
        hours, minutes, seconds = time_part.split(':')
        secs, _, millis = seconds.partition('.')
        total = (int(hours) * 3600) + (int(minutes) * 60) + int(secs)
        if millis:
            total += float(f"0.{millis}")
        return float(total)
    except Exception:
        return 0.0


def _load_segments_from_srt(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="ignore")
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    segments: List[Dict[str, object]] = []
    for block in blocks:
        lines = [line.strip('\ufeff ') for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        # Remove leading index line if numeric
        if lines[0].isdigit():
            lines = lines[1:]
        if not lines:
            continue
        if '-->' not in lines[0]:
            continue
        timecode_line = lines[0]
        text_lines = lines[1:]
        if not text_lines:
            continue
        try:
            start_str, end_str = [part.strip() for part in timecode_line.split('-->')]
        except ValueError:
            continue
        start_seconds = _parse_srt_timecode_to_seconds(start_str)
        end_seconds = _parse_srt_timecode_to_seconds(end_str)
        if end_seconds <= start_seconds:
            end_seconds = start_seconds + 0.5
        text = ' '.join(text_lines).strip()
        if not text:
            continue
        segments.append({"start": start_seconds, "end": end_seconds, "text": text})
    return segments
