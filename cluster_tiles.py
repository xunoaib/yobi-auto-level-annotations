#!/usr/bin/env python3
"""Cluster all extracted tiles by exact pixel content and produce a review gallery.

For each unique tile appearance (identified by MD5 of raw pixels), outputs:
  - cluster_gallery.png  — grid of every unique tile, sorted by frequency
  - tile_clusters.json   — maps every tile file to its cluster_id

Usage:
    python3 cluster_tiles.py tiles/ [-o clusters/]
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TILE_SIZE = 64
GALLERY_COLS = 20        # tiles per row in the gallery
LABEL_HEIGHT = 14        # px of text below each tile in gallery
PAD = 2                  # px gap between tiles


def md5_of_image(path: Path) -> str:
    img = Image.open(path).convert("RGB")
    return hashlib.md5(img.tobytes()).hexdigest()


def build_clusters(tile_root: Path) -> tuple[dict, dict]:
    """Return (hash→[paths], path→hash) for every tile under tile_root."""
    hash_to_paths: dict[str, list[Path]] = defaultdict(list)
    path_to_hash: dict[str, str] = {}

    tile_files = sorted(tile_root.rglob("r??_c??.png"))
    total = len(tile_files)
    for i, path in enumerate(tile_files, 1):
        if i % 1000 == 0:
            print(f"  hashing {i}/{total}...")
        h = md5_of_image(path)
        hash_to_paths[h].append(path)
        path_to_hash[str(path)] = h

    return hash_to_paths, path_to_hash


def make_gallery(hash_to_paths: dict, outdir: Path) -> dict[str, int]:
    """Save gallery PNG; return hash→cluster_id mapping (sorted by frequency)."""
    sorted_clusters = sorted(hash_to_paths.items(), key=lambda x: -len(x[1]))
    n = len(sorted_clusters)
    hash_to_id = {h: i for i, (h, _) in enumerate(sorted_clusters)}

    cols = GALLERY_COLS
    rows = (n + cols - 1) // cols
    cell_w = TILE_SIZE + PAD
    cell_h = TILE_SIZE + LABEL_HEIGHT + PAD

    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (40, 40, 40))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 10)
    except OSError:
        font = ImageFont.load_default()

    for idx, (h, paths) in enumerate(sorted_clusters):
        col = idx % cols
        row = idx // cols
        x = col * cell_w
        y = row * cell_h

        tile = Image.open(paths[0]).convert("RGB")
        canvas.paste(tile, (x, y))

        label = f"#{idx} ×{len(paths)}"
        draw.text((x, y + TILE_SIZE + 1), label, fill=(200, 200, 200), font=font)

    out_path = outdir / "cluster_gallery.png"
    canvas.save(out_path)
    print(f"Gallery: {out_path}  ({n} clusters, {cols}×{rows} grid)")
    return hash_to_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster Yobi tiles by pixel content")
    parser.add_argument("tile_root", type=Path, help="Root tiles/ directory")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("clusters"),
                        help="Output directory (default: ./clusters)")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    print("Hashing tiles...")
    hash_to_paths, path_to_hash = build_clusters(args.tile_root)
    print(f"  {len(path_to_hash)} tiles → {len(hash_to_paths)} unique clusters")

    hash_to_id = make_gallery(hash_to_paths, args.outdir)

    # Build JSON index: relative path → {cluster_id, count}
    index = {}
    for path_str, h in path_to_hash.items():
        cluster_id = hash_to_id[h]
        index[path_str] = {
            "cluster_id": cluster_id,
            "cluster_size": len(hash_to_paths[h]),
        }

    json_path = args.outdir / "tile_clusters.json"
    with open(json_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Index:   {json_path}")


if __name__ == "__main__":
    main()
