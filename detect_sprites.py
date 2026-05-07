#!/usr/bin/env python3
"""Detect sprites/objects in Yobi tile images using pixel-colour signatures.

Each detector returns the fraction of tile pixels matching the sprite's
characteristic colour. A threshold converts that to a yes/no decision.

Detection priority order (highest confidence first):
  cloud_demon → hippo → fire_demon → player → zebra → stone → rhino →
  apple → bridge

Usage:
    from detect_sprites import detect_sprite
    objects = detect_sprite(arr)   # arr = np.array of RGB tile
"""

import numpy as np


# ---------------------------------------------------------------------------
# Individual colour-signature detectors
# ---------------------------------------------------------------------------

def _f(arr: np.ndarray):
    """Return (r, g, b, total) float arrays for a tile."""
    r = arr[:, :, 0].astype(float)
    g = arr[:, :, 1].astype(float)
    b = arr[:, :, 2].astype(float)
    return r, g, b, float(r.size)


def _cloud_demon(arr: np.ndarray) -> float:
    """Blue-grey fluffy blob. Very high signal (~0.69 in ref tile)."""
    r, g, b, t = _f(arr)
    return ((b > 120) & (b > r) & (b > g) & (r > 60) & (g > 80) & (r < 170)).sum() / t


def _hippo(arr: np.ndarray) -> float:
    """True purple: B very high, R also high, G distinctly lower than both.
    Pixel colours: (219,81,255), (219,134,255), (178,0,219) etc.
    Excludes water (r<80), cloud demon (b not >> r), player (scores ~0.05).
    """
    r, g, b, t = _f(arr)
    return ((b > 160) & (r > 80) & (g < b - 60) & (g < r)).sum() / t


def _fire_demon(arr: np.ndarray) -> float:
    """Hot-red core pixels (r>200, g<60, b<60) that are absent from embers
    terrain (which is orange, not pure red) but present in fire demon sprites.
    Apples also have some red but score ~0.08, below the 0.10 threshold.
    """
    r, g, b, t = _f(arr)
    return ((r > 200) & (g < 60) & (b < 60)).sum() / t


def _player(arr: np.ndarray) -> float:
    """Gold halo + dark robe combo. Both must be present.
    Disqualified when neutral-grey pixels dominate (rock walls, stone).
    """
    r, g, b, t = _f(arr)
    # Rock walls have 55–70% neutral grey; the player has 0%
    grey = ((np.abs(r - g) < 25) & (np.abs(g - b) < 25) & (r > 80) & (r < 220)).sum() / t
    if grey > 0.20:
        return 0.0
    gold = ((r > 160) & (g > 100) & (g < 200) & (b < 100) & (r > g) & (g > b * 1.5)).sum() / t
    dark = ((r < 80) & (g < 60) & (b < 80)).sum() / t
    return min(gold, dark) * 8


def _zebra(arr: np.ndarray) -> float:
    """Black stripes + pure-white stripes (both must be present).
    Uses r/g/b > 220 for white to exclude rhino's grey body.
    """
    r, g, b, t = _f(arr)
    black = ((r < 60) & (g < 60) & (b < 60)).sum() / t
    white = ((r > 220) & (g > 220) & (b > 200) & (np.abs(r - g) < 20)).sum() / t
    return min(black, white) * 5  # both required


def _stone(arr: np.ndarray) -> float:
    """Pushable stone: very high near-neutral grey purity (>0.70 in ref)."""
    r, g, b, t = _f(arr)
    return ((np.abs(r - g) < 20) & (np.abs(g - b) < 20) & (r > 80) & (r < 200)).sum() / t


def _rhino(arr: np.ndarray) -> float:
    """Grey animal body with darker shadow areas (lower grey purity than stone).
    Rock walls also have grey+dark but include golden mortar pixels (gold>0.02).
    Rhinos have no gold — used as disqualifier.
    """
    r, g, b, t = _f(arr)
    # Rock walls have golden/orange mortar between stones; rhinos have none
    gold = ((r > 160) & (g > 100) & (g < 200) & (b < 100) & (r > g) & (g > b * 1.5)).sum() / t
    if gold > 0.02:
        return 0.0
    grey = ((np.abs(r - g) < 20) & (np.abs(g - b) < 20) & (r > 80) & (r < 200)).sum() / t
    dark = ((r < 60) & (g < 60) & (b < 60)).sum() / t
    if dark < 0.07:
        return 0.0
    return grey


def _apple(arr: np.ndarray) -> float:
    """Red round body + green star-leaf crown. Both must be present.
    Fire demons have no green leaves; bridges have no pure-red pixels.
    Returns min(red, leaf) scaled so threshold 0.03 requires both > ~0.04.
    """
    r, g, b, t = _f(arr)
    red  = ((r > 160) & (g < 60) & (b < 100) & (r > g * 2)).sum() / t
    leaf = ((g > 100) & (g < 220) & (r < 80) & (b < 80) & (g > r * 2)).sum() / t
    return min(red, leaf)


def _bridge(arr: np.ndarray) -> float:
    """Parallel brown/orange planks on a non-embers background.
    Planks: warm orange-brown (178,81,0) style.
    Background must include grass or sand (not pure embers).
    """
    r, g, b, t = _f(arr)
    # r < 220 excludes bright apple/flame orange (255,134,0); bridge planks are (178,81,0)
    # Pit-edge grass tiles have dark near-black pixels; real bridges have none
    pit = ((r < 30) & (g < 30) & (b < 60)).sum() / t
    if pit > 0.05:
        return 0.0
    plank = ((r > 130) & (r < 220) & (g > 30) & (g < 145) & (b < 30) & (r > g * 1.4)).sum() / t
    # Require non-embers background (grass, sand, or water present)
    bright_green = ((g > 175) & (r < 60) & (b < 60)).sum() / t
    sand         = ((r > 200) & (g > 200) & (b > 100) & (b < 210) & (np.abs(r - g) < 40)).sum() / t
    water        = ((b > 150) & (b > r * 1.5) & (b > g * 1.2)).sum() / t
    background   = bright_green + sand + water
    return plank if background > 0.15 else 0.0


# ---------------------------------------------------------------------------
# Dispatch table: (detector_fn, threshold, label)
# Ordered highest-confidence first.
# ---------------------------------------------------------------------------
_DETECTORS = [
    (_cloud_demon, 0.25, "cloud_demon"),
    (_hippo,       0.15, "hippo"),
    (_fire_demon,  0.10, "fire_demon"),  # hot-red core: embers=0.00, fire_demon=0.12, apple=0.08
    (_player,      0.30, "player"),
    (_zebra,       0.30, "zebra"),
    (_stone,       0.70, "stone"),
    (_rhino,       0.35, "rhino"),
    (_bridge,      0.07, "bridge"),
    (_apple,       0.03, "apple"),  # min(red, leaf): apple~0.042, fire_demon~0, bridge~0
]


def detect_sprite(arr: np.ndarray) -> list[dict]:
    """Return the highest-priority sprite object detected on this tile, if any.

    Detectors are checked in priority order; the first match wins so that
    lower-priority detectors cannot false-positive on a higher-priority sprite's
    distinctive pixels (e.g., apple filter triggering on fire demon red pixels).

    Returns a single-element list [{"type": "sprite", "value": <name>}]
    or [] if nothing is detected.
    """
    for fn, threshold, label in _DETECTORS:
        if fn(arr) >= threshold:
            return [{"type": "sprite", "value": label}]
    return []
