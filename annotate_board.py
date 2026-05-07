#!/usr/bin/env python3
"""Overlay letter detections on a cropped board image.

Usage:
    python3 annotate_board.py cropped/001_first.png
    python3 annotate_board.py cropped/*.png -o annotated/
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from detect_letters import detect_letters, DEFAULT_REFS
import json

TILE_SIZE = 64
COLS = 15
ROWS = 12

GRID_COLOR   = (255, 255, 255, 40)   # faint white grid
LETTER_BG    = (220,  50,  50, 180)  # red badge background
LETTER_FG    = (255, 255, 255, 255)  # white letter text
GRID_LINE    = (255, 255, 255, 60)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def annotate(board_path: Path, tile_dir: Path, refs: dict, out_path: Path) -> None:
    board = Image.open(board_path).convert("RGBA")
    overlay = Image.new("RGBA", board.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_letter = _load_font(28)
    font_coord  = _load_font(9)

    # Draw grid lines
    for col in range(COLS + 1):
        x = col * TILE_SIZE
        draw.line([(x, 0), (x, ROWS * TILE_SIZE)], fill=GRID_LINE, width=1)
    for row in range(ROWS + 1):
        y = row * TILE_SIZE
        draw.line([(0, y), (COLS * TILE_SIZE, y)], fill=GRID_LINE, width=1)

    # Draw row/col coordinates in each corner
    for row in range(ROWS):
        for col in range(COLS):
            x, y = col * TILE_SIZE, row * TILE_SIZE
            draw.text((x + 2, y + 2), f"{row},{col}", fill=(255,255,255,80), font=font_coord)

    # Draw detected letters
    letters = detect_letters(tile_dir, refs)
    for stem, letter in letters.items():
        row = int(stem[1:3])
        col = int(stem[5:7])
        x, y = col * TILE_SIZE, row * TILE_SIZE
        pad = 6
        draw.rounded_rectangle(
            [x + pad, y + pad, x + TILE_SIZE - pad, y + TILE_SIZE - pad],
            radius=6, fill=LETTER_BG,
        )
        # Centre the letter in the badge
        bbox = font_letter.getbbox(letter)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = x + (TILE_SIZE - tw) // 2 - bbox[0]
        ty = y + (TILE_SIZE - th) // 2 - bbox[1]
        draw.text((tx, ty), letter, fill=LETTER_FG, font=font_letter)

    result = Image.alpha_composite(board, overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate cropped board images with detected letters")
    parser.add_argument("boards", nargs="+", type=Path, help="Cropped board PNG files")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("annotated"),
                        help="Output directory (default: ./annotated)")
    parser.add_argument("--tiles", type=Path, default=Path("tiles"),
                        help="Root tiles directory (default: ./tiles)")
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    args = parser.parse_args()

    with open(args.refs) as f:
        refs = json.load(f)

    for board_path in args.boards:
        tile_dir = args.tiles / board_path.stem
        if not tile_dir.exists():
            print(f"SKIP {board_path.name}: no tile dir {tile_dir}")
            continue
        out_path = args.outdir / board_path.name
        annotate(board_path, tile_dir, refs, out_path)
        print(f"{board_path.name} -> {out_path}")


if __name__ == "__main__":
    main()
