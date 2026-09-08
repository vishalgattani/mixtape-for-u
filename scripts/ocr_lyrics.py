"""
ocr_lyrics.py — fully offline pipeline: cropped lyric card -> lyrics.json entry, no Claude needed
Author: Vishal Gattani
Created: 2026-09-07

Crops new screenshots from stickers/lyrics/ (reusing spotify_lyrics_sticker's own
crop logic), then runs each cropped card through Tesseract OCR to extract title,
artist, and lyric text, samples a background color, and appends a new entry to
lyrics.json — no manual transcription, no vision model, just pytesseract.

Requires the `tesseract` binary (macOS: `brew install tesseract`) and the
`pytesseract` package (`pip install pytesseract`).

READ THIS BEFORE TRUSTING THE OUTPUT: OCR on a bold display font has real,
systematic failure modes that this script mitigates but cannot fully eliminate:
  - capital "I" is frequently misread as "|" (this script fixes standalone "|"
    tokens back to "I", the one safe, unambiguous correction)
  - spaces between words occasionally get dropped ("Alll Need" instead of
    "All I Need") — not auto-fixable without a real spellchecker, left as-is
  - the small album-art thumbnail can bleed OCR noise into the title line —
    mitigated by ignoring any header-region word left of ~22% of the card
    width (past the thumbnail's right edge)
Always skim the printed summary after running and hand-fix anything that
looks wrong directly in lyrics.json — this replaces the *bulk* of manual
transcription, not a careful proofread.

Usage:
    python scripts/ocr_lyrics.py [lyrics_dir] [stickers_dir] [lyrics.json path]
    python scripts/ocr_lyrics.py \
        /Users/vishalgattani/Desktop/my-brain-in-logseq/stickers/lyrics \
        /Users/vishalgattani/Desktop/my-brain-in-logseq/stickers \
        lyrics.json

Tracks which source screenshot produced each entry via a "source" field, so
re-running only processes screenshots that don't have a matching entry yet —
same "already there, skip it" behavior as spotify_lyrics_sticker.py's crop step.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spotify_lyrics_sticker import find_card_bbox  # noqa: E402

MIN_CONFIDENCE = 15
THUMBNAIL_RIGHT_FRACTION = 0.17  # header words left of this (as a fraction of
# card width) are thumbnail-art OCR noise, not title/artist text
FOOTER_TEXT_PATTERN = re.compile(r"spotify", re.IGNORECASE)

# curated accent palette to assign new entries a color close to their actual
# card background — same set used for the manually-transcribed entries
PALETTE = ["#6b81c9", "#d9615f", "#8f8f90", "#3a86b8", "#7a87a8", "#9c8c8c", "#e0332f"]


def crop_new_screenshots(lyrics_dir: Path, stickers_dir: Path) -> list[Path]:
    """Crop any stickers/lyrics/* screenshot not already cropped into stickers_dir.
    Returns the list of newly-cropped file paths (empty if nothing new)."""
    stickers_dir.mkdir(parents=True, exist_ok=True)
    exts = {".jpg", ".jpeg", ".png"}
    newly_cropped = []
    for src in sorted(lyrics_dir.iterdir()):
        if src.suffix.lower() not in exts:
            continue
        dst = stickers_dir / src.name
        if dst.exists():
            continue
        img = Image.open(src).convert("RGB")
        bbox = find_card_bbox(np.array(img))
        if bbox is None:
            print(f"skip (no card detected): {src.name}")
            continue
        img.crop(bbox).save(dst)
        newly_cropped.append(dst)
        print(f"cropped {src.name}")
    return newly_cropped


def clean_text(text: str) -> str:
    """The one safe, unambiguous OCR correction: a standalone "|" is always a
    misread capital "I" in this font — never a real pipe character in lyrics."""
    return re.sub(r"(?<!\w)\|(?!\w)", "I", text).strip()


def ocr_lines(img: Image.Image) -> list[dict]:
    """Word-level OCR grouped into lines by Tesseract's own block/par/line
    numbering, which — empirically, on these cards — cleanly separates the
    header (title+artist), lyric body, and footer into different block_nums.
    Keeps each line's individual words (not just the joined text) so callers
    can drop specific noise words — e.g. thumbnail-art bleed sharing a line
    with real title text — without losing the rest of that line."""
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    grouped: dict[tuple, list[tuple]] = {}
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = int(data["conf"][i]) if data["conf"][i] != "-1" else -1
        if not text or conf < MIN_CONFIDENCE:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append((text, data["left"][i], data["top"][i], data["height"][i]))

    lines = []
    for key in sorted(grouped):
        words = grouped[key]
        lines.append(
            {
                "block": key[0],
                "left": min(w[1] for w in words),
                "top": min(w[2] for w in words),
                "height": sum(w[3] for w in words) / len(words),
                "words": [(w[0], w[1]) for w in words],
            }
        )
    return lines


def _line_text(line: dict, min_left: int = 0) -> str:
    """Rebuild a line's text from only the words at/after min_left."""
    return clean_text(" ".join(text for text, left in line["words"] if left >= min_left))


def extract_entry(img_path: Path) -> dict | None:
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    lines = ocr_lines(img)
    if not lines:
        return None

    thumbnail_edge = w * THUMBNAIL_RIGHT_FRACTION
    header_block = lines[0]["block"]
    header = []
    for ln in lines:
        if ln["block"] != header_block:
            continue
        text = _line_text(ln, thumbnail_edge)
        if re.search(r"[A-Za-z0-9]", text):  # drop lines that are pure noise/symbols
            header.append(text)
    if not header:
        return None
    title = header[0]
    artist = header[1] if len(header) > 1 else ""

    body_block_nums = sorted({ln["block"] for ln in lines if ln["block"] > header_block})
    if not body_block_nums:
        return None
    # the lyric is the first body block; later blocks (Spotify wordmark, stray
    # glyphs from the logo) are footer noise — drop anything mentioning it
    lyric_lines = [
        text
        for ln in lines
        if ln["block"] == body_block_nums[0]
        for text in [_line_text(ln)]
        if text and not FOOTER_TEXT_PATTERN.search(text)
    ]
    if not lyric_lines:
        return None
    lyric = "\n".join(lyric_lines)

    # background color: sample a small patch on the right-middle edge, safely
    # clear of the thumbnail (top-left) and the text (which is left-aligned)
    patch = img.crop((int(w * 0.92), int(h * 0.45), w - 2, int(h * 0.55)))
    avg = np.array(patch).reshape(-1, 3).mean(axis=0)
    color = "#%02x%02x%02x" % tuple(avg.astype(int))
    closest = min(PALETTE, key=lambda hexv: _color_distance(hexv, color))

    return {
        "title": title,
        "artist": artist,
        "lyric": lyric,
        "color": closest,
        "source": img_path.name,
    }


def _color_distance(hex_a: str, hex_b: str) -> float:
    a = tuple(int(hex_a[i : i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(hex_b[i : i + 2], 16) for i in (1, 3, 5))
    return sum((x - y) ** 2 for x, y in zip(a, b))


def main() -> None:
    lyrics_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../../stickers/lyrics")
    stickers_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("../../stickers")
    lyrics_json_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("lyrics.json")

    entries = json.loads(lyrics_json_path.read_text()) if lyrics_json_path.exists() else []
    known_sources = {e["source"] for e in entries if "source" in e}

    crop_new_screenshots(lyrics_dir, stickers_dir)

    to_process = [
        p
        for p in sorted(stickers_dir.glob("*.JPG"))
        if p.name not in known_sources
    ]
    if not to_process:
        print("nothing new to OCR")
        return

    for img_path in to_process:
        entry = extract_entry(img_path)
        if entry is None:
            print(f"OCR FAILED (no usable text found): {img_path.name}")
            continue
        entries.append(entry)
        print(f"OCR'd {img_path.name}:")
        print(f"  title:  {entry['title']!r}")
        print(f"  artist: {entry['artist']!r}")
        print(f"  lyric:  {entry['lyric']!r}")
        print(f"  color:  {entry['color']}")

    lyrics_json_path.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"\nwrote {len(to_process)} new entries to {lyrics_json_path}")
    print("^ skim the above output and hand-fix anything wrong directly in lyrics.json")
    print("  (common issues: dropped spaces, thumbnail-art bleeding into the title line)")


if __name__ == "__main__":
    main()
