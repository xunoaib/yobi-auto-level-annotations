#!/usr/bin/env python3
"""Classify the terrain type of every tile in a level.

Strategy:
  1. Exact cluster lookup  — if the tile's MD5 matches a labeled cluster, use it.
  2. Dominant-colour fallback — for unlabeled clusters (edge/transition tiles),
     classify by the most prevalent colour family in the tile.

Usage:
    python3 classify_terrain.py tiles/001_first/
    python3 classify_terrain.py tiles/*/
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

CLUSTER_JSON   = Path("clusters/tile_clusters.json")
LABEL_JSON     = Path("terrain_labels.json")

# ---------------------------------------------------------------------------
# Colour-family fallback thresholds (RGB)
# ---------------------------------------------------------------------------
def _dominant_colour(arr: np.ndarray) -> str:
    r = arr[:, :, 0].astype(float)
    g = arr[:, :, 1].astype(float)
    b = arr[:, :, 2].astype(float)

    votes = {
        "water":  int(((b > 150) & (b > r * 1.5) & (b > g * 1.2)).sum()),
        "forest": int(((g > 80)  & (g > r * 1.4) & (g > b * 1.4) & (r < 100)).sum()),
        "grass":  int(((g > 200) & (g > r * 1.5) & (g > b * 1.5)).sum()),
        "sand":   int(((r > 200) & (g > 200) & (b > 100) & (b < 210)
                       & (np.abs(r - g) < 40)).sum()),
        "rock":   int(((np.abs(r - g) < 25) & (np.abs(g - b) < 25)
                       & (r > 80) & (r < 200)).sum()),
        "mud":    int(((r > 80) & (r < 180) & (g < 80) & (b < 60)
                       & (r > g * 1.5)).sum()),
        "embers": int(((r > 180) & (g > 100) & (g < 200) & (b < 80)).sum()),
    }
    return max(votes, key=lambda k: votes[k])


# ---------------------------------------------------------------------------
# Build lookup: tile MD5 -> label
# ---------------------------------------------------------------------------
def _build_lookup() -> dict[str, str]:
    with open(CLUSTER_JSON) as f:
        cluster_index = json.load(f)
    with open(LABEL_JSON) as f:
        label_list = json.load(f)

    cid_to_label = {entry["cluster_id"]: entry["label"] for entry in label_list}

    # We need tile-hash → label, but cluster_index stores path → cluster_id.
    # Build cluster_id → one representative path first.
    cid_to_path: dict[int, str] = {}
    for path_str, info in cluster_index.items():
        cid = info["cluster_id"]
        if cid not in cid_to_path:
            cid_to_path[cid] = path_str

    # Hash each representative tile once to get hash → label.
    lookup: dict[str, str] = {}
    for cid, path_str in cid_to_path.items():
        if cid not in cid_to_label:
            continue
        arr = np.array(Image.open(path_str).convert("RGB"))
        h = hashlib.md5(arr.tobytes()).hexdigest()
        lookup[h] = cid_to_label[cid]

    return lookup


def _tile_hash(arr: np.ndarray) -> str:
    return hashlib.md5(arr.tobytes()).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def classify_tile(arr: np.ndarray, lookup: dict[str, str]) -> tuple[str, str]:
    """Return (label, method) where method is 'lookup' or 'colour'."""
    h = _tile_hash(arr)
    if h in lookup:
        return lookup[h], "lookup"
    return _dominant_colour(arr), "colour"


def classify_level(tile_dir: Path, lookup: dict[str, str]) -> dict[str, str]:
    """Return {tile_stem: label} for every tile in tile_dir."""
    results = {}
    for tile_path in sorted(tile_dir.glob("r??_c??.png")):
        arr = np.array(Image.open(tile_path).convert("RGB"))
        label, _ = classify_tile(arr, lookup)
        results[tile_path.stem] = label
    return results


def results_as_grid(results: dict[str, str], rows: int = 12, cols: int = 15) -> list[list[str]]:
    grid = [["?" ] * cols for _ in range(rows)]
    for stem, label in results.items():
        row, col = int(stem[1:3]), int(stem[5:7])
        grid[row][col] = label
    return grid


def print_grid(grid: list[list[str]], col_width: int = 8) -> None:
    for row in grid:
        print(" ".join(cell.ljust(col_width) for cell in row))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Classify terrain in Yobi tile directories")
    parser.add_argument("dirs", nargs="+", type=Path)
    args = parser.parse_args()

    print("Building lookup table...", flush=True)
    lookup = _build_lookup()
    print(f"  {len(lookup)} labeled tile hashes loaded\n")

    for level_dir in args.dirs:
        results = classify_level(level_dir, lookup)
        grid = results_as_grid(results)

        print(f"=== {level_dir.name} ===")
        print_grid(grid)
        print()


if __name__ == "__main__":
    main()
