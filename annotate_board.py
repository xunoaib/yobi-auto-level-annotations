#!/usr/bin/env python3
"""Overlay terrain classifications and/or object detections on a cropped board image.

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

# Axis label margins (pixels added outside the tile grid)
MARGIN_LEFT = 36
MARGIN_TOP  = 28

GRID_LINE   = (255, 255, 255, 60)
AXIS_COLOR  = (220, 220, 220, 255)

LETTER_BG = (220, 50, 50, 200)
LETTER_FG = (255, 255, 255, 255)

# Sprite category → badge colour
SPRITE_COLORS: dict[str, tuple] = {
    # Player
    "player":       (230, 160,   0, 210),   # gold
    # Water enemies
    "hippo":        (160,  40, 200, 210),   # purple
    "alligator":    ( 20, 140,  20, 210),   # dark green
    # Land animals
    "zebra":        ( 50,  50,  50, 210),   # near-black
    "rhino":        (120, 120, 120, 210),   # grey
    "gazelle":      (160, 100,  20, 210),   # brown
    "elephant":     ( 90,  90, 110, 210),   # blue-grey
    "lion":         (200, 140,  20, 210),   # golden-brown
    "tiger":        (200,  80,   0, 210),   # orange
    # Demons
    "fire_demon":   (220,  40,   0, 210),   # red
    "cloud_demon":  (100, 150, 220, 210),   # light blue
    "arrow_demon":  (180,  60, 180, 210),   # purple
    "wind_demon":   (100, 200, 200, 210),   # cyan
    # Items
    "apple":        (200,  30,  30, 210),   # red
    "bridge":       (140,  80,  20, 210),   # brown
    "stone":        (150, 150, 150, 210),   # grey
    "token":        (220, 190,   0, 210),   # gold
    "potion_water": ( 30, 100, 220, 210),   # blue
    "potion_fire":  (220,  80,   0, 210),   # orange
    "potion_arrow": ( 80, 160,  40, 210),   # green
    "potion_wind":  ( 80, 200, 200, 210),   # cyan
    "potion_time":  (120,  30, 180, 210),   # purple
    # Vehicles
    "jeep":         ( 30, 160,  30, 210),   # green
}
SPRITE_FG_DEFAULT = (255, 255, 255, 255)

# Terrain label → badge colour
TERRAIN_COLORS: dict[str, tuple] = {
    "sand":   (210, 180,  80, 160),
    "water":  ( 50, 120, 220, 160),
    "forest": ( 30, 110,  30, 160),
    "grass":  (100, 200,  50, 160),
    "rock":   (130, 130, 130, 160),
    "mud":    (120,  70,  30, 160),
    "embers": (230, 120,  20, 160),
    "pit":    ( 20,  20,  20, 180),
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
                pad: int = 4, anchor_bottom: bool = False) -> None:
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x + (TILE_SIZE - tw) // 2 - bbox[0]
    if anchor_bottom:
        ty = y + TILE_SIZE - th - pad * 2 - bbox[1]
    else:
        ty = y + (TILE_SIZE - th) // 2 - bbox[1]
    bx0, by0 = tx - pad, ty - pad
    bx1, by1 = tx + tw + pad, ty + th + pad
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4, fill=bg)
    draw.text((tx, ty), text, fill=fg, font=font)


def annotate(board_path: Path, tile_dir: Path,
             letter_refs: dict, terrain_lookup: dict,
             show: str, out_path: Path) -> None:

    board_raw = Image.open(board_path).convert("RGBA")
    # Add margins for axis labels
    w = MARGIN_LEFT + COLS * TILE_SIZE
    h = MARGIN_TOP  + ROWS * TILE_SIZE
    board = Image.new("RGBA", (w, h), (30, 30, 30, 255))
    board.paste(board_raw, (MARGIN_LEFT, MARGIN_TOP))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_terrain = _load_font(11)
    font_letter  = _load_font(26)
    font_sprite  = _load_font(10)
    font_axis    = _load_font(13)

    # Grid lines (offset into tile area)
    for col in range(COLS + 1):
        x = MARGIN_LEFT + col * TILE_SIZE
        draw.line([(x, MARGIN_TOP), (x, MARGIN_TOP + ROWS * TILE_SIZE)],
                  fill=GRID_LINE, width=1)
    for row in range(ROWS + 1):
        y = MARGIN_TOP + row * TILE_SIZE
        draw.line([(MARGIN_LEFT, y), (MARGIN_LEFT + COLS * TILE_SIZE, y)],
                  fill=GRID_LINE, width=1)

    # Column numbers along the top axis
    for col in range(COLS):
        label = str(col)
        bbox = font_axis.getbbox(label)
        tw = bbox[2] - bbox[0]
        cx = MARGIN_LEFT + col * TILE_SIZE + TILE_SIZE // 2
        cy = MARGIN_TOP // 2
        draw.text((cx - tw // 2 - bbox[0], cy - (bbox[3] - bbox[1]) // 2 - bbox[1]),
                  label, fill=AXIS_COLOR, font=font_axis)

    # Row numbers along the left axis
    for row in range(ROWS):
        label = str(row)
        bbox = font_axis.getbbox(label)
        tw = bbox[2] - bbox[0]
        cx = MARGIN_LEFT // 2
        cy = MARGIN_TOP + row * TILE_SIZE + TILE_SIZE // 2
        draw.text((cx - tw // 2 - bbox[0], cy - (bbox[3] - bbox[1]) // 2 - bbox[1]),
                  label, fill=AXIS_COLOR, font=font_axis)

    # Load the pre-parsed level JSON (sprites + background terrain already computed)
    level_json = Path("levels") / f"{tile_dir.name}.json"
    level_data = json.loads(level_json.read_text()) if level_json.exists() else None

    # Terrain badges
    if show in ("terrain", "both"):
        terrain_map = classify_level(tile_dir, terrain_lookup)
        for stem, label in terrain_map.items():
            row, col = int(stem[1:3]), int(stem[5:7])
            x = MARGIN_LEFT + col * TILE_SIZE
            y = MARGIN_TOP  + row * TILE_SIZE

            # For object tiles, show the background terrain from the JSON
            if level_data:
                tile = level_data["grid"][row][col]
                if tile["objects"]:
                    label = tile["terrain"]   # background terrain (may be "unknown")

            bg = TERRAIN_COLORS.get(label, TERRAIN_DEFAULT_COLOR)
            _draw_badge(draw, x, y, label, bg, (255, 255, 255, 220), font_terrain, pad=3)

    # Sprite badges (drawn above terrain, anchored to bottom of tile)
    if show in ("letters", "both") and level_data:
        for row, grid_row in enumerate(level_data["grid"]):
            for col, tile in enumerate(grid_row):
                sprite_objs = [o for o in tile["objects"] if o["type"] == "sprite"]
                if sprite_objs:
                    name = sprite_objs[0]["value"]
                    x = MARGIN_LEFT + col * TILE_SIZE
                    y = MARGIN_TOP  + row * TILE_SIZE
                    bg = SPRITE_COLORS.get(name, (40, 40, 180, 210))
                    _draw_badge(draw, x, y, name, bg, SPRITE_FG_DEFAULT,
                                font_sprite, pad=3, anchor_bottom=True)

    # Letter badges (centred, drawn on top of everything)
    if show in ("letters", "both"):
        letters = detect_letters(tile_dir, letter_refs)
        for stem, letter in letters.items():
            row, col = int(stem[1:3]), int(stem[5:7])
            x = MARGIN_LEFT + col * TILE_SIZE
            y = MARGIN_TOP  + row * TILE_SIZE
            _draw_badge(draw, x, y, letter, LETTER_BG, LETTER_FG, font_letter, pad=5)

    result = Image.alpha_composite(board, overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path)


def _level_summary(level_data: dict) -> str:
    if not level_data:
        return ""
    letters = [(r, c, o["value"])
               for r, row in enumerate(level_data["grid"])
               for c, tile in enumerate(row)
               for o in tile["objects"] if o["type"] == "letter"]
    sprites = [(r, c, o["value"])
               for r, row in enumerate(level_data["grid"])
               for c, tile in enumerate(row)
               for o in tile["objects"] if o["type"] == "sprite"]
    letter_str = "".join(f"r{r}c{c}={v}" for r, c, v in letters)
    sprite_str = ", ".join(f"{v}@r{r}c{c}" for r, c, v in sprites)
    return (f"word={level_data['word']}  "
            f"letters=[{letter_str}]  "
            f"sprites=[{sprite_str}]")


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

        level_json = Path("levels") / f"{tile_dir.name}.json"
        level_data = json.loads(level_json.read_text()) if level_json.exists() else None
        summary = _level_summary(level_data)

        annotate(board_path, tile_dir, letter_refs, terrain_lookup, args.show, out_path)
        print(f"{board_path.stem}  {summary}")
        print(f"  -> {out_path}")


if __name__ == "__main__":
    main()
