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

import numpy as np
from PIL import Image

from classify_terrain import classify_level, _build_lookup as build_terrain_lookup, background_terrain
from detect_letters import detect_letters, DEFAULT_REFS
from match_sprites import load_templates, detect_sprite_template
from detect_sprites import _player as player_score

ROWS = 12
COLS = 15

# Terrain labels that are actually objects on top of another terrain
OBJECT_TERRAIN_MAP: dict = {}  # terrain labels that encode an object (none currently)


def parse_level(tile_dir: Path, terrain_lookup: dict, letter_refs: dict,
                sprite_templates: "dict | None" = None) -> dict:
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

            # Sprite objects — template matching (colour fallback omitted)
            tile_path = tile_dir / f"{stem}.png"
            tile_arr = np.array(Image.open(tile_path).convert("RGB"))
            if sprite_templates:
                match = detect_sprite_template(tile_arr, sprite_templates)
                if match:
                    obj = {"type": "sprite", "value": match["value"]}
                    terrain = background_terrain(tile_arr, "sprite", obj["value"])
                    objects.append(obj)

            # Letter objects — infer background terrain from outer ring.
            if stem in letter_map:
                terrain = background_terrain(tile_arr, "letter", letter_map[stem])
                objects.append({"type": "letter", "value": letter_map[stem]})

            grid_row.append({"terrain": terrain, "objects": objects})
        grid.append(grid_row)

    # --- Player deduplication -------------------------------------------------
    # The player appears exactly once per level, always on a water tile.
    # 1. Collect every tile where "player" was detected.
    # 2. Among those on water, keep the highest-scoring one.
    # 3. Strip "player" from every other tile (water or not).
    all_player_rc = [
        (r, c)
        for r, row in enumerate(grid)
        for c, tile in enumerate(row)
        if any(obj.get("value") == "player" for obj in tile["objects"])
    ]
    def _ps(r: int, c: int) -> float:
        arr = np.array(Image.open(tile_dir / f"r{r:02d}_c{c:02d}.png").convert("RGB"))
        return player_score(arr)

    water_candidates = [
        (_ps(r, c), r, c)
        for r, c in all_player_rc
        if terrain_map.get(f"r{r:02d}_c{c:02d}", "") == "water"
    ]
    # Best candidate: highest-scoring water tile, or highest overall if none on water
    if water_candidates:
        _, best_r, best_c = max(water_candidates)
    elif all_player_rc:
        _, best_r, best_c = max((_ps(r, c), r, c) for r, c in all_player_rc)
    else:
        best_r, best_c = None, None

    for r, c in all_player_rc:
        if (r, c) != (best_r, best_c):
            grid[r][c]["objects"] = [
                o for o in grid[r][c]["objects"] if o.get("value") != "player"
            ]
            if not grid[r][c]["objects"]:
                grid[r][c]["terrain"] = terrain_map.get(f"r{r:02d}_c{c:02d}", "unknown")
    # --------------------------------------------------------------------------

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
    sprite_templates = load_templates()
    with open(args.refs) as f:
        letter_refs = json.load(f)

    for tile_dir in args.dirs:
        if not tile_dir.is_dir():
            continue
        level = parse_level(tile_dir, terrain_lookup, letter_refs, sprite_templates)

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
