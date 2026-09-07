"""
add_previews.py — look up an iTunes 30s preview clip URL for each lyrics.json entry
Author: Vishal Gattani
Created: 2026-09-07

For each {title, artist, ...} entry in lyrics.json, queries the (unauthenticated)
iTunes Search API for a matching track and writes back entry["preview"] with its
previewUrl. Falls back to a full artist-catalog lookup when the fuzzy search
endpoint misses an exact title match (happens for some deep-cut tracks). Sets
preview to null (and leaves it that way) when no match is found — no auth, no
API key, nothing to configure.

Usage:
    python scripts/add_previews.py [lyrics.json path, default: ./lyrics.json]

Re-run any time lyrics.json gains new entries; existing "preview" fields are
left untouched unless you delete them first (so a stale/broken URL isn't
silently kept — remove the field and re-run to refresh it).
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"


def _get_json(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}", timeout=10) as resp:
        return json.load(resp)


def primary_artist(artist: str) -> str:
    """First-billed artist from a "feat."/"&"/"+"-joined credit string."""
    return artist.split(",")[0].split("+")[0].strip()


def pick_match(results: list[dict], title: str) -> str | None:
    """previewUrl of the first result whose trackName exactly matches title."""
    wanted = title.strip().lower()
    for r in results:
        if r.get("trackName", "").strip().lower() == wanted and r.get("previewUrl"):
            return r["previewUrl"]
    return None


def find_preview(title: str, artist: str) -> str | None:
    first_artist = primary_artist(artist)

    search_data = _get_json(
        SEARCH_URL, {"term": f"{title} {first_artist}", "entity": "song", "limit": 10}
    )
    match = pick_match(search_data.get("results", []), title)
    if match:
        return match

    # fuzzy search missed it (common for deep cuts) — pull the artist's full
    # catalog and match by exact track name instead.
    artist_data = _get_json(SEARCH_URL, {"term": first_artist, "entity": "musicArtist", "limit": 1})
    if not artist_data.get("results"):
        return None
    artist_id = artist_data["results"][0]["artistId"]

    catalog = _get_json(LOOKUP_URL, {"id": artist_id, "entity": "song", "limit": 200})
    tracks = [r for r in catalog.get("results", []) if r.get("wrapperType") == "track"]
    return pick_match(tracks, title)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("lyrics.json")
    entries = json.loads(path.read_text())

    for entry in entries:
        if "preview" in entry:
            continue
        preview = find_preview(entry["title"], entry["artist"])
        entry["preview"] = preview
        status = "found" if preview else "NOT FOUND — leaving null"
        print(f"{entry['title']} — {entry['artist']}: {status}")

    path.write_text(json.dumps(entries, indent=2) + "\n")


if __name__ == "__main__":
    main()
