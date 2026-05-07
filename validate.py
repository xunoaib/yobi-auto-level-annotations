#!/usr/bin/env python3
"""Validate current tile detections against stored ground truth files.

Re-runs the full detection pipeline for each level that has a ground
truth file, then diffs the object lists. Reports three outcome types:

  MISSING  — object in ground truth but not detected   (regression)
  EXTRA    — object detected but not in ground truth   (new false positive)
  OK       — object matches ground truth exactly

Exit code 0 if all checked levels pass, 1 if any differences found.

Usage:
    python3 validate.py                          # validate all ground truth levels
    python3 validate.py 001_first 083_danger     # specific levels
    python3 validate.py --gt ground_truth/       # custom ground truth dir
    python3 validate.py --summary                # one line per level only
"""

import argparse
import json
import sys
from pathlib import Path

from classify_terrain import _build_lookup as build_terrain_lookup
from detect_letters import DEFAULT_REFS
from parse_level import parse_level


def load_ground_truth(gt_file: Path) -> dict[str, list]:
    return json.loads(gt_file.read_text())


def detect_objects(level_name: str, tiles_root: Path,
                   terrain_lookup: dict, letter_refs: dict) -> dict[str, list]:
    """Re-run the full pipeline; return {stem: [objects]} for non-empty tiles."""
    tile_dir = tiles_root / level_name
    if not tile_dir.exists():
        return {}
    data = parse_level(tile_dir, terrain_lookup, letter_refs)
    result: dict[str, list] = {}
    for r, row in enumerate(data["grid"]):
        for c, tile in enumerate(row):
            if tile["objects"]:
                result[f"r{r:02d}_c{c:02d}"] = tile["objects"]
    return result


def diff(detected: dict, truth: dict) -> tuple[list, list, list]:
    """Return (missing, extra, ok) lists of (stem, objects) tuples."""
    all_stems = set(detected) | set(truth)
    missing, extra, ok = [], [], []
    for stem in sorted(all_stems):
        d_objs = detected.get(stem, [])
        t_objs = truth.get(stem, [])
        if d_objs == t_objs:
            ok.append((stem, d_objs))
        elif not d_objs:
            missing.append((stem, t_objs))
        elif not t_objs:
            extra.append((stem, d_objs))
        else:
            # Present in both but different — report as both missing old and extra new
            missing.append((stem, t_objs))
            extra.append((stem, d_objs))
    return missing, extra, ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate detections against ground truth")
    parser.add_argument("levels", nargs="*",
                        help="Level stems to validate. Default: all ground truth files.")
    parser.add_argument("--gt", type=Path, default=Path("ground_truth"),
                        help="Ground truth directory (default: ground_truth/)")
    parser.add_argument("--tiles", type=Path, default=Path("tiles"),
                        help="Tiles root directory (default: tiles/)")
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    parser.add_argument("--summary", action="store_true",
                        help="Print one summary line per level only")
    args = parser.parse_args()

    with open(args.refs) as f:
        letter_refs = json.load(f)
    terrain_lookup = build_terrain_lookup()

    if args.levels:
        gt_files = [args.gt / f"{stem}.json" for stem in args.levels]
    else:
        gt_files = sorted(args.gt.glob("*.json"))

    if not gt_files:
        print(f"No ground truth files found in {args.gt}/")
        sys.exit(0)

    total_missing = total_extra = total_ok = 0
    failed_levels: list[str] = []

    for gt_file in gt_files:
        if not gt_file.exists():
            print(f"SKIP {gt_file.name}: ground truth file not found")
            continue

        level_name = gt_file.stem
        truth    = load_ground_truth(gt_file)
        detected = detect_objects(level_name, args.tiles, terrain_lookup, letter_refs)
        missing, extra, ok = diff(detected, truth)

        total_missing += len(missing)
        total_extra   += len(extra)
        total_ok      += len(ok)

        if missing or extra:
            failed_levels.append(level_name)
            if args.summary:
                print(f"FAIL  {level_name}  "
                      f"missing={len(missing)} extra={len(extra)} ok={len(ok)}")
            else:
                print(f"\n{'='*60}")
                print(f"FAIL  {level_name}")
                for stem, objs in missing:
                    print(f"  MISSING  {stem}: {objs}")
                for stem, objs in extra:
                    print(f"  EXTRA    {stem}: {objs}")
        else:
            if args.summary:
                print(f"ok    {level_name}  ({len(ok)} object tiles)")
            else:
                print(f"ok    {level_name}  ({len(ok)} object tiles)")

    print(f"\n{'='*60}")
    print(f"Levels checked : {len(gt_files)}")
    print(f"Levels passed  : {len(gt_files) - len(failed_levels)}")
    print(f"Levels failed  : {len(failed_levels)}")
    print(f"Object tiles   : {total_ok} ok / {total_missing} missing / {total_extra} extra")

    if failed_levels:
        print(f"\nFailed: {', '.join(failed_levels)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
