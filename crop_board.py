#!/usr/bin/env python3
"""Crop Yobi's Basic Spelling Tricks screenshots to the main game board.

Removes:
  - Left UI panel (wizard, MAP, RESTART buttons)  x < 296
  - Right outer border                             x >= 1256
  - Top header/landscape graphic                   y < 146
  - Bottom text/sentence bar                       y >= 914

Result is exactly 960×768 px (15 tiles × 12 tiles at 64 px/tile).
"""

import argparse
from pathlib import Path
from PIL import Image

# Left/right from pixel-diff analysis; top derived from 15×12 tile grid at 64 px/tile.
CROP_BOX = (296, 146, 1256, 914)  # (left, upper, right, lower) → 960×768


def crop_screenshot(src: Path, dst: Path) -> None:
    img = Image.open(src)
    cropped = img.crop(CROP_BOX)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop game board from Yobi screenshots")
    parser.add_argument("inputs", nargs="+", type=Path, help="Input PNG files")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("cropped"),
                        help="Output directory (default: ./cropped)")
    args = parser.parse_args()

    for src in args.inputs:
        dst = args.outdir / src.name
        crop_screenshot(src, dst)
        print(f"{src} -> {dst}")


if __name__ == "__main__":
    main()
