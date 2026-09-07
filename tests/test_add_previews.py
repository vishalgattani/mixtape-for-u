"""
test_add_previews.py — unit tests for scripts/add_previews.py
Author: Vishal Gattani
Created: 2026-09-07

Pure-logic tests (primary_artist, pick_match) run with no network access.
find_preview's control flow (search -> catalog fallback -> null) is tested
with _get_json mocked out, so the suite never hits the real iTunes API.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import add_previews  # noqa: E402


def test_primary_artist_single():
    assert add_previews.primary_artist("Bazzi") == "Bazzi"


def test_primary_artist_comma_joined():
    assert add_previews.primary_artist("Vansire, FLOOR CRY") == "Vansire"


def test_primary_artist_plus_joined():
    assert add_previews.primary_artist("Sultan + Shepard, Shallou") == "Sultan"


def test_pick_match_exact_hit():
    results = [
        {"trackName": "you! - live from The Forum", "previewUrl": "live.m4a"},
        {"trackName": "you!", "previewUrl": "studio.m4a"},
    ]
    assert add_previews.pick_match(results, "you!") == "studio.m4a"


def test_pick_match_is_case_insensitive():
    results = [{"trackName": "HEAVEN", "previewUrl": "heaven.m4a"}]
    assert add_previews.pick_match(results, "heaven") == "heaven.m4a"


def test_pick_match_no_hit_returns_none():
    results = [{"trackName": "Something Else", "previewUrl": "x.m4a"}]
    assert add_previews.pick_match(results, "Heaven") is None


def test_pick_match_skips_result_missing_preview_url():
    results = [{"trackName": "Heaven"}]  # no previewUrl field
    assert add_previews.pick_match(results, "Heaven") is None


def test_find_preview_hits_on_first_search():
    search_response = {"results": [{"trackName": "Heaven", "previewUrl": "heaven.m4a"}]}
    with patch.object(add_previews, "_get_json", return_value=search_response) as mock_get:
        result = add_previews.find_preview("Heaven", "Bazzi")
    assert result == "heaven.m4a"
    mock_get.assert_called_once()  # never needed the catalog fallback


def test_find_preview_falls_back_to_artist_catalog():
    empty_search = {"results": []}
    artist_lookup = {"results": [{"artistId": 12345}]}
    catalog = {
        "results": [{"wrapperType": "track", "trackName": "Deep Cut", "previewUrl": "deepcut.m4a"}]
    }

    with patch.object(
        add_previews, "_get_json", side_effect=[empty_search, artist_lookup, catalog]
    ):
        result = add_previews.find_preview("Deep Cut", "The 1975")
    assert result == "deepcut.m4a"


def test_find_preview_returns_none_when_artist_not_found():
    empty_search = {"results": []}
    empty_artist_lookup = {"results": []}

    with patch.object(add_previews, "_get_json", side_effect=[empty_search, empty_artist_lookup]):
        result = add_previews.find_preview("Nonexistent Song", "Nonexistent Artist")
    assert result is None


LYRICS_PATH = Path(__file__).resolve().parent.parent / "lyrics.json"


def test_lyrics_json_is_valid_and_well_formed():
    entries = json.loads(LYRICS_PATH.read_text())
    assert isinstance(entries, list)
    assert len(entries) > 0
    required = {"title", "artist", "lyric", "color"}
    for entry in entries:
        assert required.issubset(entry.keys()), entry
        assert isinstance(entry["title"], str) and entry["title"]
        assert isinstance(entry["artist"], str) and entry["artist"]
        assert isinstance(entry["lyric"], str) and entry["lyric"]
        assert entry["color"].startswith("#")
        if "preview" in entry and entry["preview"] is not None:
            assert entry["preview"].startswith("https://")
