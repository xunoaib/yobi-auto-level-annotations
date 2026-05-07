#!/usr/bin/env python3
"""Overlay terrain classifications and/or letter detections on a cropped board image.

Usage:
    python3 annotate_board.py cropped/001_first.png                 # both (default)
    python3 annotate_board.py cropped/001_first.png --show terrain
    python3 annotate_board.py cropped/001_first.png --show letters
    python3 annotate_board.py cropped/001_first.png --show both
    python3 annotate_board.py cropped/*.png -o annotated/
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from detect_letters import detect_letters, DEFAULT_REFS
from classify_terrain import classify_level, _build_lookup as build_terrain_lookup

TILE_SIZE = 64
COLS = 15
ROWS = 12

GRID_LINE   = (255, 255, 255, 60)
COORD_COLOR = (255, 255, 255, 80)

LETTER_BG   = (220,  50,  50, 180)
LETTER_FG   = (255, 255, 255, 255)

# Terrain label -> badge colour (RGBA)
TERRAIN_COLORS: dict[str, tuple] = {
    "sand":          ( 210, 180,  80, 160),
    "water":         (  50, 120, 220, 160),
    "forest":        (  30, 110,  30, 160),
    "grass":         ( 100, 200,  50, 160),
    "rock":          ( 130, 130, 130, 160),
    "mud":           ( 120,  70,  30, 160),
    "embers":        ( 230, 120,  20, 160),
    "pit":           (  20,  20,  20, 180),
}
TERRAIN_DEFAULT_COLOR = (160, 160, 160, 140)


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int,
                text: str, bg: tuple, fg: tuple, font: ImageFont.ImageFont,
                pad: int = 4) -> None:
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x + (TILE_SIZE - tw) // 2 - bbox[0]
    ty = y + (TILE_SIZE - th) // 2 - bbox[1]
    bx0, by0 = tx - pad, ty - pad
    bx1, by1 = tx + tw + pad, ty + th + pad
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4, fill=bg)
    draw.text((tx, ty), text, fill=fg, font=font)


def annotate(board_path: Path, tile_dir: Path,
             letter_refs: dict, terrain_lookup: dict,
             show: str, out_path: Path) -> None:

    board = Image.open(board_path).convert("RGBA")
    overlay = Image.new("RGBA", board.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_terrain = _load_font(11)
    font_letter  = _load_font(26)
    font_coord   = _load_font(9)

    # Grid lines
    for col in range(COLS + 1):
        draw.line([(col * TILE_SIZE, 0), (col * TILE_SIZE, ROWS * TILE_SIZE)],
                  fill=GRID_LINE, width=1)
    for row in range(ROWS + 1):
        draw.line([(0, row * TILE_SIZE), (COLS * TILE_SIZE, row * TILE_SIZE)],
                  fill=GRID_LINE, width=1)

    # Row/col coordinates
    for row in range(ROWS):
        for col in range(COLS):
            draw.text((col * TILE_SIZE + 2, row * TILE_SIZE + 2),
                      f"{row},{col}", fill=COORD_COLOR, font=font_coord)

    # Terrain badges
    if show in ("terrain", "both"):
        terrain = classify_level(tile_dir, terrain_lookup)
        for stem, label in terrain.items():
            row, col = int(stem[1:3]), int(stem[5:7])
            x, y = col * TILE_SIZE, row * TILE_SIZE
            bg = TERRAIN_COLORS.get(label, TERRAIN_DEFAULT_COLOR)
            fg = (255, 255, 255, 220)
            _draw_badge(draw, x, y, label, bg, fg, font_terrain, pad=3)

    # Letter badges (drawn on top of terrain so they're always visible)
    if show in ("letters", "both"):
        letters = detect_letters(tile_dir, letter_refs)
        for stem, letter in letters.items():
            row, col = int(stem[1:3]), int(stem[5:7])
            x, y = col * TILE_SIZE, row * TILE_SIZE
            _draw_badge(draw, x, y, letter, LETTER_BG, LETTER_FG, font_letter, pad=5)

    result = Image.alpha_composite(board, overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate cropped Yobi board images")
    parser.add_argument("boards", nargs="+", type=Path)
    parser.add_argument("-o", "--outdir", type=Path, default=Path("annotated"))
    parser.add_argument("--tiles", type=Path, default=Path("tiles"))
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    parser.add_argument("--show", choices=["letters", "terrain", "both"],
                        default="both", help="What to overlay (default: both)")
    args = parser.parse_args()

    with open(args.refs) as f:
        letter_refs = json.load(f)

    terrain_lookup = build_terrain_lookup()

    for board_path in args.boards:
        tile_dir = args.tiles / board_path.stem
        if not tile_dir.exists():
            print(f"SKIP {board_path.name}: no tile dir {tile_dir}")
            continue
        out_path = args.outdir / board_path.name
        annotate(board_path, tile_dir, letter_refs, terrain_lookup, args.show, out_path)
        print(f"{board_path.name} -> {out_path}  [--show {args.show}]")


if __name__ == "__main__":
    main()
