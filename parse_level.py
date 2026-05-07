#!/usr/bin/env python3
"""Parse a Yobi level into a structured JSON map.

Each tile is classified for terrain type and any objects on it (letters,
items). Output is a JSON document with a 2-D grid of tile descriptors.

Usage:
    python3 parse_level.py tiles/001_first/
    python3 parse_level.py tiles/*/  -o levels/
"""

import argparse
import json
from pathlib import Path

from classify_terrain import classify_level, _build_lookup as build_terrain_lookup
from detect_letters import detect_letters, DEFAULT_REFS

ROWS = 12
COLS = 15

# Terrain labels that are actually objects on top of another terrain
OBJECT_TERRAIN_MAP = {
    "tomato_on_sand": ("sand", {"type": "item", "value": "tomato"}),
}


def parse_level(tile_dir: Path, terrain_lookup: dict, letter_refs: dict) -> dict:
    """Return a structured level dict for one level directory."""
    word = tile_dir.name.split("_", 1)[1].upper()

    # Classify terrain for every tile
    terrain_map = classify_level(tile_dir, terrain_lookup)

    # Detect letter objects
    letter_map = detect_letters(tile_dir, letter_refs)

    # Build 2-D grid
    grid: list[list[dict]] = []
    for row in range(ROWS):
        grid_row = []
        for col in range(COLS):
            stem = f"r{row:02d}_c{col:02d}"
            raw_terrain = terrain_map.get(stem, "unknown")
            objects: list[dict] = []

            # Unpack composite terrain labels (e.g. tomato_on_sand)
            if raw_terrain in OBJECT_TERRAIN_MAP:
                terrain, obj = OBJECT_TERRAIN_MAP[raw_terrain]
                objects.append(obj)
            else:
                terrain = raw_terrain

            # Letter objects — the gray letter box obscures the underlying
            # terrain, so terrain is unreliable for these tiles.
            if stem in letter_map:
                terrain = "unknown"
                objects.append({"type": "letter", "value": letter_map[stem]})

            grid_row.append({"terrain": terrain, "objects": objects})
        grid.append(grid_row)

    return {
        "level": tile_dir.name,
        "word": word,
        "rows": ROWS,
        "cols": COLS,
        "grid": grid,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Yobi level tiles into JSON")
    parser.add_argument("dirs", nargs="+", type=Path, help="Tile level directories")
    parser.add_argument("-o", "--outdir", type=Path, default=None,
                        help="Write one JSON file per level to this directory "
                             "(default: print to stdout)")
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    args = parser.parse_args()

    terrain_lookup = build_terrain_lookup()
    with open(args.refs) as f:
        letter_refs = json.load(f)

    for tile_dir in args.dirs:
        if not tile_dir.is_dir():
            continue
        level = parse_level(tile_dir, terrain_lookup, letter_refs)

        if args.outdir:
            args.outdir.mkdir(parents=True, exist_ok=True)
            out = args.outdir / f"{tile_dir.name}.json"
            with open(out, "w") as f:
                json.dump(level, f, indent=2)
            # Print a compact summary
            letter_tiles = [
                f"r{r}c{c}={obj['value']}"
                for r, row in enumerate(level["grid"])
                for c, tile in enumerate(row)
                for obj in tile["objects"] if obj["type"] == "letter"
            ]
            print(f"{tile_dir.name}  word={level['word']}  letters={letter_tiles}")
        else:
            print(json.dumps(level, indent=2))


if __name__ == "__main__":
    main()
