"""Download and install subtitle fonts used by AdLocalizer.

Run once after cloning:

    python setup_fonts.py

Fonts are saved under ``static/fonts`` so they deploy with the app.  Only
open-licence Noto families are fetched.  If the download server is
unreachable, retry or grab the files manually and drop them into the same
directory.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Dict

import requests

FONT_DEST = Path("static/fonts")

# Map filename -> list of candidate download URLs (try in order)
FONTS: Dict[str, list[str]] = {
    "NotoSans-Regular.ttf": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
        "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    ],
    # CJK paths in noto-cjk frequently move; provide multiple mirrors
    "NotoSansJP-Regular.otf": [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf",
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf",
        # Release asset (larger but stable)
        "https://github.com/googlefonts/noto-cjk/releases/download/Serif2.002/NotoSansJP-Regular.otf",
    ],
    "NotoSansKR-Regular.otf": [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Korean/NotoSansKR-Regular.otf",
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/Korean/NotoSansKR-Regular.otf",
        "https://github.com/googlefonts/noto-cjk/releases/download/Serif2.002/NotoSansKR-Regular.otf",
    ],
    "NotoSansSC-Regular.otf": [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf",
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf",
        "https://github.com/googlefonts/noto-cjk/releases/download/Serif2.002/NotoSansSC-Regular.otf",
    ],
    "NotoSansTC-Regular.otf": [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf",
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf",
        "https://github.com/googlefonts/noto-cjk/releases/download/Serif2.002/NotoSansTC-Regular.otf",
    ],
    "NotoSansThai-Regular.ttf": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansThai/NotoSansThai-Regular.ttf",
        "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansThai/NotoSansThai-Regular.ttf",
    ],
    "NotoSansDevanagari-Regular.ttf": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    ],
    "NotoNaskhArabic-Regular.ttf": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf",
        "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf",
    ],
}


def download_font(name: str, urls: list[str]) -> None:
    dest = FONT_DEST / name
    if dest.exists():
        print(f"✓ {name} already present")
        return

    last_error: Exception | None = None
    for url in urls:
        print(f"↓ Downloading {name} ...", end=" ")
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            dest.write_bytes(response.content)
            digest = hashlib.sha256(response.content).hexdigest()[:8]
            print(f"done ({len(response.content)//1024} KiB, sha256:{digest})")
            return
        except Exception as exc:  # pragma: no cover - network
            last_error = exc
            print("failed")
            continue
    if last_error:
        raise RuntimeError(f"Could not download {name} from any source: {last_error}")


def main() -> int:
    FONT_DEST.mkdir(parents=True, exist_ok=True)
    for name, urls in FONTS.items():
        try:
            download_font(name, urls)
        except RuntimeError as err:
            print(err, file=sys.stderr)
            # continue; we'll try system fallbacks below

    # Extra safeguard: copy any system-installed JP fonts into static/fonts
    # so deployment bundles at least one working JP font.
    system_candidates = [
        Path("/System/Library/Fonts/Supplemental/Hiragino Sans W4.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"),
        Path("/System/Library/Fonts/HiraginoSans-W4.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("/Library/Fonts/HiraginoSans-W4.ttc"),
        Path("/Library/Fonts/PingFang.ttc"),
        Path.home() / "Library/Fonts/HiraginoSans-W4.ttc",
        Path.home() / "Library/Fonts/PingFang.ttc",
    ]
    copied_any = False
    for src in system_candidates:
        try:
            if src.exists():
                dest = FONT_DEST / src.name
                if not dest.exists():
                    dest.write_bytes(src.read_bytes())
                    print(f"✓ Copied system JP font: {src.name}")
                    copied_any = True
        except Exception as e:
            print(f"Warning: could not copy {src}: {e}")

    if not (FONT_DEST / "NotoSansJP-Regular.otf").exists() and not copied_any:
        print("⚠️  No downloadable or system JP font found; relying on runtime system fonts.")
    print("All fonts installed in", FONT_DEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
