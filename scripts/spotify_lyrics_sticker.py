"""
spotify_lyrics_sticker.py — crop Spotify lyric-share screenshots down to just the inner rounded card
Author: Vishal Gattani
Created: 2026-09-03

Detects the rounded lyric card in each screenshot (the box holding the track art,
lyric text, and Spotify logo) by diffing each row against its own left-edge
background color, then crops to the card's bounding box.

Usage:
    python spotify_lyrics_sticker.py [input_dir] [output_dir]
    python spotify_lyrics_sticker.py \
        /Users/vishalgattani/Desktop/my-brain-in-logseq/stickers/lyrics \
        /Users/vishalgattani/Desktop/my-brain-in-logseq/stickers

Files already present in output_dir are skipped (no regen).
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_INPUT = Path("/Users/vishalgattani/Desktop/my-brain-in-logseq/stickers/lyrics")
DEFAULT_OUTPUT = Path("/Users/vishalgattani/Desktop/my-brain-in-logseq/stickers")
DIFF_THRESHOLD = 18  # per-channel-summed color distance from row's background reference


def find_card_bbox(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w = arr.shape[:2]
    bg_ref = arr[:, 2:6, :3].mean(axis=1)  # per-row background sample from near left edge
    diff = np.abs(arr[:, :, :3].astype(int) - bg_ref[:, None, :].astype(int)).sum(axis=2)
    mask = diff > DIFF_THRESHOLD

    rows = np.where(mask.any(axis=1))[0]
    if rows.size == 0:
        return None
    cols = np.where(mask.any(axis=0))[0]
    if cols.size == 0:
        return None

    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def process_image(src: Path, dst: Path) -> bool:
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    bbox = find_card_bbox(arr)
    if bbox is None:
        print(f"skip (no card detected): {src.name}")
        return False
    img.crop(bbox).save(dst)
    print(f"cropped {src.name} -> {dst.name} {bbox}")
    return True


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    output_dir.mkdir(parents=True, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png"}
    for src in sorted(input_dir.iterdir()):
        if src.suffix.lower() not in exts:
            continue
        dst = output_dir / src.name
        if dst.exists():
            print(f"exists, skipping: {dst.name}")
            continue
        process_image(src, dst)


if __name__ == "__main__":
    main()
