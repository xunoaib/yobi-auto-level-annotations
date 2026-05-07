#!/usr/bin/env python3
"""Extract individual 64×64 tiles from cropped Yobi game board images.

Input images must be 960×768 (output of crop_board.py): 15 tiles wide × 12 tiles tall.
Each tile is saved as <outdir>/<level_stem>/r<row>_c<col>.png (0-indexed).
"""

import argparse
from pathlib import Path
from PIL import Image

TILE_SIZE = 64
COLS = 15
ROWS = 12


def extract_tiles(src: Path, outdir: Path) -> None:
    img = Image.open(src)
    if img.size != (COLS * TILE_SIZE, ROWS * TILE_SIZE):
        raise ValueError(f"{src}: expected {COLS*TILE_SIZE}×{ROWS*TILE_SIZE}, got {img.size[0]}×{img.size[1]}")

    tile_dir = outdir / src.stem
    tile_dir.mkdir(parents=True, exist_ok=True)

    for row in range(ROWS):
        for col in range(COLS):
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            tile = img.crop((x, y, x + TILE_SIZE, y + TILE_SIZE))
            tile.save(tile_dir / f"r{row:02d}_c{col:02d}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract tiles from cropped Yobi board images")
    parser.add_argument("inputs", nargs="+", type=Path, help="Cropped board PNG files")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("tiles"),
                        help="Output directory (default: ./tiles)")
    args = parser.parse_args()

    for src in args.inputs:
        extract_tiles(src, args.outdir)
        print(f"{src} -> {args.outdir / src.stem}/ ({ROWS*COLS} tiles)")


if __name__ == "__main__":
    main()
