#!/usr/bin/env python3
"""Template-based sprite detection using RGBA sprite masks.

For each sprite, an RGBA template in sprites/ encodes which pixels
belong to the sprite (alpha=255) versus background (alpha=0).
Detection works by checking whether a candidate tile's pixels match
the template's sprite pixels.  All four 90° rotations are tried
because animals can appear rotated.

Usage:
    from match_sprites import load_templates, detect_sprite_template

    templates = load_templates()
    result = detect_sprite_template(tile_arr, templates)
    # result: {"type": "sprite", "value": "zebra", "confidence": 0.94}
    # or None if nothing matches above the threshold
"""

from pathlib import Path

import numpy as np
from PIL import Image

SPRITES_DIR = Path(__file__).parent / "sprites"
MATCH_THRESHOLD = 0.65   # fraction of sprite pixels that must match exactly

# These sprites are symmetric / non-animated and only need to be checked
# at rotation=0.  Everything else (animals) gets all four rotations.
NO_ROTATION = {"player", "cloud_demon", "fire_demon", "bridge", "apple"}


def load_templates(sprites_dir: Path = SPRITES_DIR) -> dict[str, list[np.ndarray]]:
    """Return {sprite_name: [RGBA arrays]} for every PNG in sprites/.

    Multiple files sharing the same base name (e.g. lion.png, lion_2.png)
    are grouped under the same sprite so all variants are tried during
    detection.  The base name is the filename stem stripped of any trailing
    underscore-digit suffix (_2, _3, …).
    """
    import re
    templates: dict[str, list[np.ndarray]] = {}
    for p in sorted(sprites_dir.glob("*.png")):
        if p.stem == "sprite_sheet":
            continue
        arr = np.array(Image.open(p).convert("RGBA"), dtype=np.uint8)
        if arr.shape != (64, 64, 4):
            continue
        base = re.sub(r"_\d+$", "", p.stem)
        templates.setdefault(base, []).append(arr)
    return templates


def _match_score(tile: np.ndarray, template: np.ndarray) -> float:
    """Fraction of sprite pixels (alpha=255) in *template* that exactly
    match the corresponding pixels in *tile* (H×W×3, uint8)."""
    mask = template[:, :, 3] > 0
    n = int(mask.sum())
    if n == 0:
        return 0.0
    matches = np.all(tile[mask] == template[:, :, :3][mask], axis=1).sum()
    return float(matches) / n


def detect_sprite_template(
    tile_arr: np.ndarray,
    templates: "dict[str, list[np.ndarray]]",
    threshold: float = MATCH_THRESHOLD,
) -> "dict | None":
    """Return the best-matching sprite dict or None.

    tile_arr must be (64, 64, 3) uint8.
    Tries all four 90° CCW rotations for sprites that support it.
    Multiple template variants per sprite name are all tried.
    """
    best_name: str | None = None
    best_conf: float = 0.0
    best_template: "np.ndarray | None" = None

    for name, variant_list in templates.items():
        rotations = [0] if name in NO_ROTATION else [0, 1, 2, 3]
        for template in variant_list:
            for k in rotations:
                rotated = np.rot90(template, k=k, axes=(0, 1))
                score = _match_score(tile_arr, rotated)
                if score > best_conf:
                    best_conf = score
                    best_name = name
                    best_template = rotated

    if best_conf >= threshold and best_name is not None:
        return {
            "type": "sprite",
            "value": best_name,
            "confidence": round(best_conf, 3),
            "template": best_template,
        }
    return None
