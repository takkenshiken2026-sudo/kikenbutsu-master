#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNS シェア用 OGP 画像（og-image.png）を生成する。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tools.site_config import brand_mark, brand_name, exam_name  # noqa: E402

OUT = ROOT / "og-image.png"
W, H = 1200, 630
INK = "#111111"
EXAM_INK = "#333333"
BG = "#f4f4f5"
SURFACE = "#ffffff"
FONT_WEIGHT = 6


def _load_font(size: int, *, weight: int = FONT_WEIGHT) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    weight = max(0, min(9, weight))
    candidates = [
        f"/System/Library/Fonts/ヒラギノ角ゴシック W{weight}.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    *,
    start_size: int,
    min_size: int,
) -> ImageFont.ImageFont:
    for size in range(start_size, min_size - 1, -1):
        font = _load_font(size)
        if _text_size(draw, text, font)[0] <= max_w:
            return font
    return _load_font(min_size)


def generate() -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pad = 28
    draw.rounded_rectangle((pad, pad, W - pad, H - pad), radius=28, fill=SURFACE)

    mark_size = 280
    gap = 44
    mark_font = _load_font(118)
    name_font = _load_font(100)

    mark_text = brand_mark()
    site_name = brand_name()
    exam = exam_name()

    max_text_w = W - pad * 2 - mark_size - gap - 56
    exam_font = _fit_font(draw, exam, max_text_w, start_size=46, min_size=42)

    name_w, name_h = _text_size(draw, site_name, name_font)
    exam_w, exam_h = _text_size(draw, exam, exam_font)
    text_w = max(name_w, exam_w)

    name_exam_gap = 28
    text_block_h = name_h + name_exam_gap + exam_h

    block_w = mark_size + gap + text_w
    block_h = max(mark_size, text_block_h)
    start_x = (W - block_w) // 2
    block_top = (H - block_h) // 2

    mark_x = start_x
    mark_y = block_top + (block_h - mark_size) // 2
    draw.rounded_rectangle((mark_x, mark_y, mark_x + mark_size, mark_y + mark_size), radius=44, fill=INK)
    mw, mh = _text_size(draw, mark_text, mark_font)
    draw.text(
        (mark_x + (mark_size - mw) / 2, mark_y + (mark_size - mh) / 2 - 6),
        mark_text,
        fill="#ffffff",
        font=mark_font,
    )

    text_x = start_x + mark_size + gap
    text_y = block_top + (block_h - text_block_h) // 2
    draw.text((text_x, text_y), site_name, fill=INK, font=name_font)
    draw.text((text_x, text_y + name_h + name_exam_gap), exam, fill=EXAM_INK, font=exam_font)

    img.save(OUT, format="PNG", optimize=True)
    return OUT


def main() -> int:
    path = generate()
    print(f"generate_og_image.py: wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
