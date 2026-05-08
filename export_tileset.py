#!/usr/bin/env python3
"""Export one representative 64×64 tile image per terrain type.

For each terrain label in terrain_labels.json, picks the cluster with the
most tile instances (the most common pure example of that terrain) and copies
its representative tile to tileset/<label>.png.  Also writes tileset.png,
a horizontal sprite sheet of all terrain types in a consistent order.

Usage:
    python3 export_tileset.py
    python3 export_tileset.py -o my_tileset/
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CLUSTER_JSON  = Path("clusters/tile_clusters.json")
LABEL_JSON    = Path("terrain_labels.json")
TILE_SIZE     = 64

TERRAIN_ORDER = ["sand", "grass", "forest", "water", "rock", "mud", "embers", "pit"]


def build_tileset(outdir: Path) -> dict[str, Path]:
    """Return {terrain_label: saved_png_path} for every labeled terrain type."""
    cluster_index = json.loads(CLUSTER_JSON.read_text())
    label_list    = json.loads(LABEL_JSON.read_text())

    cid_to_label: dict[int, str] = {e["cluster_id"]: e["label"] for e in label_list}

    # Count how many tiles belong to each cluster
    cluster_sizes: dict[int, int] = defaultdict(int)
    cluster_rep:   dict[int, str] = {}          # cluster_id → one tile path
    for path_str, info in cluster_index.items():
        cid = info["cluster_id"]
        cluster_sizes[cid] += 1
        if cid not in cluster_rep:
            cluster_rep[cid] = path_str

    # For each terrain label pick the largest (most-instances) labeled cluster
    label_to_best: dict[str, tuple[int, int]] = {}   # label → (size, cid)
    for cid, label in cid_to_label.items():
        size = cluster_sizes[cid]
        if label not in label_to_best or size > label_to_best[label][0]:
            label_to_best[label] = (size, cid)

    outdir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    for label, (size, cid) in sorted(label_to_best.items()):
        src = Path(cluster_rep[cid])
        arr = np.array(Image.open(src).convert("RGB"), dtype=np.uint8)
        dst = outdir / f"{label}.png"
        Image.fromarray(arr).save(dst)
        print(f"  {label:10s}: cluster {cid:4d}  ({size:4d} instances)  →  {dst}")
        saved[label] = dst

    return saved


def build_sheet(saved: dict[str, Path], outdir: Path) -> Path:
    """Save a horizontal sprite sheet with labels below each tile."""
    order  = [t for t in TERRAIN_ORDER if t in saved] + \
             [t for t in sorted(saved) if t not in TERRAIN_ORDER]
    n      = len(order)
    margin = 18
    canvas = Image.new("RGB", (n * TILE_SIZE, TILE_SIZE + margin), (30, 30, 30))
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 9)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)

    for i, label in enumerate(order):
        tile = Image.open(saved[label]).convert("RGB")
        canvas.paste(tile, (i * TILE_SIZE, 0))
        bbox = font.getbbox(label)
        tw   = bbox[2] - bbox[0]
        tx   = i * TILE_SIZE + (TILE_SIZE - tw) // 2 - bbox[0]
        draw.text((tx, TILE_SIZE + 2), label, fill=(200, 200, 200), font=font)

    sheet = outdir / "tileset.png"
    canvas.save(sheet)
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Export representative terrain tiles")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("tileset"),
                        help="Output directory (default: tileset/)")
    args = parser.parse_args()

    print("Building tileset …")
    saved = build_tileset(args.outdir)

    sheet = build_sheet(saved, args.outdir)
    print(f"\nSprite sheet → {sheet}")
    print(f"Individual tiles → {args.outdir}/")


if __name__ == "__main__":
    main()
