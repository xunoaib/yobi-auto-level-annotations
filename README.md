> **Note:** Every line of code in this repository was written by an AI assistant through iterative prompting. Treat it accordingly.

# Yobi Level Extraction

Extracts structured tile data from screenshots of *Yobi's Basic Spelling Tricks* (1994 DOS edutainment game). Parses all 101 levels into JSON maps of terrain type and objects per tile.

## Output

Each level produces a `levels/<name>.json` file:

```json
{
  "level": "001_first",
  "word": "FIRST",
  "rows": 12,
  "cols": 15,
  "grid": [
    [
      { "terrain": "forest", "objects": [] },
      { "terrain": "water",  "objects": [{ "type": "sprite", "value": "player" }] },
      { "terrain": "sand",   "objects": [{ "type": "letter", "value": "F" }] }
    ]
  ]
}
```

**Terrain types:** `sand`, `water`, `grass`, `forest`, `rock`, `mud`, `embers`, `pit`

**Object types:**
- `letter` — A–Z collectible letters that spell the level's word
- `sprite` — all named game entities (see below)

**Sprite values:** `player`, `hippo`, `alligator`, `gazelle`, `lion`, `tiger`, `elephant`, `rhino`, `zebra`, `fire_demon`, `cloud_demon`, `arrow_demon`, `apple`, `bridge`, `stone`, `token`, `jeep`, `potion_water`, `potion_fire`, `potion_arrow`, `potion_wind`, `potion_time`

## Pipeline

```
level-screenshots/   Raw 1280×960 PNG screenshots
       │
crop_board.py        Crop to 960×768 game board  →  cropped/
       │
extract_tiles.py     Split into 180 64×64 tiles   →  tiles/<level>/
       │
parse_level.py       Classify terrain + detect     →  levels/<level>.json
                     letters + match sprites
       │
annotate_board.py    Overlay labels on board image →  annotated/
```

## Scripts

| Script | Purpose |
|--------|---------|
| `crop_board.py` | Crop screenshots to the 15×12 tile game board |
| `extract_tiles.py` | Split each board into 180 individual 64×64 tile PNGs |
| `cluster_tiles.py` | MD5-cluster tiles to find unique terrain patterns |
| `classify_terrain.py` | Classify terrain by cluster lookup + colour heuristics |
| `detect_letters.py` | Detect A–Z letter tiles by pixel-hash lookup |
| `match_sprites.py` | Template-match sprites using RGBA masks |
| `extract_sprites.py` | Extract RGBA sprite templates from tile instances |
| `parse_level.py` | Combine all detections into a level JSON (parallelised) |
| `annotate_board.py` | Render terrain/object labels onto board images (parallelised) |
| `export_ground_truth.py` | Export verified object detections as ground truth |
| `validate.py` | Diff current detections against ground truth (parallelised) |

## Technique

**Terrain** is classified by MD5 hash lookup against a hand-labelled cluster table, with a colour-priority fallback for unlabelled transition tiles. Priority order: forest → water → grass/sand/rock (largest pixel count wins) → mud.

**Letters** are detected by hashing a fixed 32×32 region within the tile. Each hash maps to a specific letter.

**Sprites** use RGBA template matching: each sprite's template PNG marks sprite pixels (alpha=255) vs background (alpha=0). A tile is matched if ≥65% of the template's sprite pixels match exactly. Animals support four 90° rotations; items and demons do not. Multiple template variants per sprite handle hand-drawn orientations (e.g. `lion.png` + `lion_2.png`).

**Background terrain** under sprites and letters is inferred by excluding the sprite's template pixels from terrain classification. Constraints prevent impossible results (e.g. stones and cloud demons cannot be on water).

## Running

```bash
# Full pipeline from scratch
python3 crop_board.py level-screenshots/*.png
python3 extract_tiles.py cropped/*.png
python3 parse_level.py tiles/*/ -o levels/
python3 annotate_board.py cropped/*.png -o annotated/

# Validate against ground truth
python3 validate.py --summary

# Rebuild and annotate specific levels
python3 parse_level.py tiles/042_though/ -o levels/
python3 annotate_board.py cropped/042_though.png -o annotated/
```

All three multi-level scripts run in parallel by default (`-j` to set worker count).

## Requirements

Python 3.10+, Pillow, NumPy.
