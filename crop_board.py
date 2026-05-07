#!/usr/bin/env python3
"""Crop Yobi's Basic Spelling Tricks screenshots to the main game board.

Removes:
  - Left UI panel (wizard, MAP, RESTART buttons)  x < 296
  - Right outer border                             x >= 1256
  - Bottom text/sentence bar                       y >= 914
"""

import argparse
from pathlib import Path
from PIL import Image

# Determined by diffing multiple screenshots to find the static vs dynamic regions.
CROP_BOX = (296, 0, 1256, 914)  # (left, upper, right, lower)


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
