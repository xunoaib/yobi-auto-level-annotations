#!/usr/bin/env python3
"""Extract sprite templates from multiple tile instances.

For each sprite type, collects all detected instances, finds pixels
that are IDENTICAL across every instance (those are the sprite itself),
and saves an RGBA PNG where alpha=255 marks sprite pixels and alpha=0
marks background.  Works because pixel-art sprites have zero variation
between instances; only the background differs.

Usage:
    python3 extract_sprites.py                   # extract all known sprites
    python3 extract_sprites.py hippo zebra        # specific types
    python3 extract_sprites.py --min-instances 5  # require at least N instances
    python3 extract_sprites.py --show             # also save a visual contact sheet
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_instances(sprite_type: str, levels_dir: Path, tiles_dir: Path) -> list[np.ndarray]:
    arrays = []
    for level_path in sorted(levels_dir.glob("*.json")):
        data = json.loads(level_path.read_text())
        level = level_path.stem
        for r, row in enumerate(data["grid"]):
            for c, tile in enumerate(row):
                for obj in tile["objects"]:
                    if obj["type"] == "sprite" and obj["value"] == sprite_type:
                        p = tiles_dir / level / f"r{r:02d}_c{c:02d}.png"
                        if p.exists():
                            arrays.append(np.array(Image.open(p).convert("RGB")))
    return arrays


def extract_template(instances: list[np.ndarray]) -> np.ndarray:
    """Return RGBA array: sprite pixels have alpha=255, background alpha=0."""
    stack = np.stack(instances)           # (N, 64, 64, 3)
    ref   = stack[0]
    # A pixel is a sprite pixel if it has the SAME value in every instance
    same  = np.all(stack == ref, axis=0)  # (64, 64, 3)
    sprite_mask = same.all(axis=2)        # (64, 64) — True where all channels match

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)
    rgba[:, :, :3] = ref
    rgba[:, :, 3]  = np.where(sprite_mask, 255, 0)
    return rgba


def sprite_contact_sheet(templates: dict[str, np.ndarray], out_path: Path) -> None:
    """Save a visual sheet showing each sprite template against a grey background."""
    n = len(templates)
    cols = min(n, 8)
    rows = (n + cols - 1) // cols
    cell = 80
    canvas = Image.new("RGBA", (cols * cell, rows * cell), (80, 80, 80, 255))
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 9)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    bg = Image.new("RGBA", (64, 64), (80, 80, 80, 255))
    for i, (name, rgba) in enumerate(sorted(templates.items())):
        cx = (i % cols) * cell
        cy = (i // cols) * cell
        sprite = Image.fromarray(rgba, "RGBA")
        composite = Image.alpha_composite(bg.copy(), sprite)
        canvas.paste(composite, (cx, cy))
        pixel_count = (rgba[:, :, 3] > 0).sum()
        draw.text((cx + 1, cy + 65), f"{name}\n{pixel_count}px",
                  fill=(220, 220, 220, 255), font=font)
    canvas.convert("RGB").save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract sprite templates from tile instances")
    parser.add_argument("sprites", nargs="*",
                        help="Sprite types to extract (default: all detected)")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("sprites"),
                        help="Output directory for RGBA PNGs (default: sprites/)")
    parser.add_argument("--levels", type=Path, default=Path("levels"))
    parser.add_argument("--tiles",  type=Path, default=Path("tiles"))
    parser.add_argument("--min-instances", type=int, default=2,
                        help="Skip sprite types with fewer instances (default: 2)")
    parser.add_argument("--show", action="store_true",
                        help="Also save a contact sheet sprite_sheet.png")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    # Discover all sprite types if none specified
    if args.sprites:
        sprite_types = args.sprites
    else:
        sprite_types = set()
        for lp in args.levels.glob("*.json"):
            data = json.loads(lp.read_text())
            for row in data["grid"]:
                for tile in row:
                    for obj in tile["objects"]:
                        if obj["type"] == "sprite":
                            sprite_types.add(obj["value"])
        sprite_types = sorted(sprite_types)

    templates: dict[str, np.ndarray] = {}

    for stype in sprite_types:
        instances = load_instances(stype, args.levels, args.tiles)
        if len(instances) < args.min_instances:
            print(f"SKIP {stype}: only {len(instances)} instance(s)")
            continue

        rgba = extract_template(instances)
        sprite_pixels = int((rgba[:, :, 3] > 0).sum())
        out = args.outdir / f"{stype}.png"
        Image.fromarray(rgba, "RGBA").save(out)
        templates[stype] = rgba
        print(f"{stype:15s}: {len(instances):3d} instances → {sprite_pixels:4d} sprite pixels → {out}")

    if args.show and templates:
        sheet = args.outdir / "sprite_sheet.png"
        sprite_contact_sheet(templates, sheet)
        print(f"\nContact sheet: {sheet}")


if __name__ == "__main__":
    main()
