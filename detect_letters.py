#!/usr/bin/env python3
"""Detect letter tiles in extracted Yobi tile directories.

Letter tiles are identified by their fixed gray box + pure-red glyph signature.
Each letter maps to a unique MD5 hash of its 32×32 box crop; the reference
map was built once by visual inspection of all 25 unique letter hashes and
is stored in letter_refs.json.

Usage:
    # Detect letters in one level directory:
    python3 detect_letters.py tiles/001_first/

    # Detect letters in all levels:
    python3 detect_letters.py tiles/*/
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

LETTER_BOX = (16, 16, 48, 48)   # pixel crop within a 64×64 tile
DEFAULT_REFS = Path(__file__).parent / "letter_refs.json"


def _arrays(arr: np.ndarray) -> tuple:
    return arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)


def is_letter_tile(arr: np.ndarray) -> bool:
    """True when the tile contains a letter box (gray border + red glyph)."""
    r, g, b = _arrays(arr)
    pure_red = (r > 100) & (g == 0) & (b == 0)
    gray = (np.abs(r - g) < 15) & (np.abs(g - b) < 15) & (r > 80) & (r < 245)
    return bool(pure_red.sum() > 20 and gray.sum() > 100 and pure_red.sum() < 350)


def box_hash(arr: np.ndarray) -> str:
    crop = np.array(Image.fromarray(arr).crop(LETTER_BOX))
    return hashlib.md5(crop.tobytes()).hexdigest()


def detect_letters(tile_dir: Path, refs: dict[str, str]) -> dict[str, str]:
    """Return {tile_stem: letter} for every letter tile in tile_dir."""
    results = {}
    for tile_path in sorted(tile_dir.glob("r??_c??.png")):
        arr = np.array(Image.open(tile_path).convert("RGB"))
        if is_letter_tile(arr):
            h = box_hash(arr)
            results[tile_path.stem] = refs.get(h, f"?{h[:6]}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect letter tiles in Yobi boards")
    parser.add_argument("dirs", nargs="+", type=Path, help="Tile level directories")
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS,
                        help=f"Letter reference JSON (default: {DEFAULT_REFS})")
    args = parser.parse_args()

    with open(args.refs) as f:
        refs = json.load(f)

    for level_dir in args.dirs:
        results = detect_letters(level_dir, refs)
        word_guess = "".join(sorted(set(results.values())))
        print(f"{level_dir.name}: {results}  → letters present: {word_guess}")


if __name__ == "__main__":
    main()
