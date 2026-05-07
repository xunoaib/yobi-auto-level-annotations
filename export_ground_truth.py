#!/usr/bin/env python3
"""Export current level object detections as per-level ground truth files.

Reads levels/*.json and writes one ground_truth/<level>.json per level,
containing only tiles that have objects (letters, sprites, items).
Terrain is excluded — it is noisier and harder to verify exhaustively.

Usage:
    python3 export_ground_truth.py                  # export all levels
    python3 export_ground_truth.py 001_first 083_danger  # specific levels
    python3 export_ground_truth.py -o my_gt/        # custom output dir
"""

import argparse
import json
from pathlib import Path


def export_level(level_json: Path, out_dir: Path) -> int:
    """Export object detections for one level. Returns number of object tiles."""
    data = json.loads(level_json.read_text())
    objects: dict[str, list] = {}
    for r, row in enumerate(data["grid"]):
        for c, tile in enumerate(row):
            if tile["objects"]:
                objects[f"r{r:02d}_c{c:02d}"] = tile["objects"]

    out_path = out_dir / level_json.name
    out_path.write_text(json.dumps(objects, indent=2))
    return len(objects)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export object detections as ground truth files"
    )
    parser.add_argument("levels", nargs="*",
                        help="Level stems to export (e.g. 001_first). "
                             "Default: all levels in levels/")
    parser.add_argument("-s", "--source", type=Path, default=Path("levels"),
                        help="Source levels directory (default: levels/)")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("ground_truth"),
                        help="Output directory (default: ground_truth/)")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    if args.levels:
        sources = [args.source / f"{stem}.json" for stem in args.levels]
    else:
        sources = sorted(args.source.glob("*.json"))

    total_tiles = 0
    for src in sources:
        if not src.exists():
            print(f"SKIP {src.name}: not found in {args.source}")
            continue
        n = export_level(src, args.outdir)
        total_tiles += n
        print(f"{src.stem}: {n} object tile(s) -> {args.outdir / src.name}")

    print(f"\nExported {len(sources)} levels, {total_tiles} object tiles total.")


if __name__ == "__main__":
    main()
