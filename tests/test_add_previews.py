"""
test_add_previews.py — unit tests for scripts/add_previews.py
Author: Vishal Gattani
Created: 2026-09-07

Pure-logic tests (primary_artist, artist_matches, pick_match) run with no
network access. find_preview's control flow (search -> catalog fallback ->
null) is tested with _get_json mocked out, so the suite never hits the real
iTunes API.
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


def test_artist_matches_exact():
    assert add_previews.artist_matches("Bazzi", "Bazzi")


def test_artist_matches_substring_in_multi_artist_credit():
    assert add_previews.artist_matches("Sultan + Shepard & Shallou", "Sultan + Shepard, Shallou")


def test_artist_matches_is_case_insensitive():
    assert add_previews.artist_matches("BAZZI", "bazzi")


def test_artist_matches_rejects_unrelated_artist():
    # the actual bug this guards against: a same-titled track by a
    # completely different artist must not be treated as a match
    assert not add_previews.artist_matches("Poolside & NEIL FRANCES", "The 1975")


def test_pick_match_exact_hit():
    results = [
        {"trackName": "you! - live from The Forum", "artistName": "LANY", "previewUrl": "live.m4a"},
        {"trackName": "you!", "artistName": "LANY", "previewUrl": "studio.m4a"},
    ]
    assert add_previews.pick_match(results, "you!", "LANY") == "studio.m4a"


def test_pick_match_is_case_insensitive():
    results = [{"trackName": "HEAVEN", "artistName": "Bazzi", "previewUrl": "heaven.m4a"}]
    assert add_previews.pick_match(results, "heaven", "Bazzi") == "heaven.m4a"


def test_pick_match_no_title_hit_returns_none():
    results = [{"trackName": "Something Else", "artistName": "Bazzi", "previewUrl": "x.m4a"}]
    assert add_previews.pick_match(results, "Heaven", "Bazzi") is None


def test_pick_match_skips_result_missing_preview_url():
    results = [{"trackName": "Heaven", "artistName": "Bazzi"}]  # no previewUrl field
    assert add_previews.pick_match(results, "Heaven", "Bazzi") is None


def test_pick_match_rejects_title_match_from_wrong_artist():
    # regression test: "I'm In Love With You" is a real song by both The 1975
    # and Poolside & NEIL FRANCES — matching on title alone previously picked
    # whichever ranked first in iTunes' search results, regardless of artist
    results = [
        {
            "trackName": "I'm in Love with You",
            "artistName": "Poolside & NEIL FRANCES",
            "previewUrl": "wrong.m4a",
        },
        {"trackName": "I'm In Love With You", "artistName": "The 1975", "previewUrl": "right.m4a"},
    ]
    assert add_previews.pick_match(results, "I'm In Love With You", "The 1975") == "right.m4a"


def test_find_preview_hits_on_first_search():
    search_response = {
        "results": [{"trackName": "Heaven", "artistName": "Bazzi", "previewUrl": "heaven.m4a"}]
    }
    with patch.object(add_previews, "_get_json", return_value=search_response) as mock_get:
        result = add_previews.find_preview("Heaven", "Bazzi")
    assert result == "heaven.m4a"
    mock_get.assert_called_once()  # never needed the catalog fallback


def test_find_preview_falls_back_to_artist_catalog():
    empty_search = {"results": []}
    artist_lookup = {"results": [{"artistId": 12345}]}
    catalog = {
        "results": [
            {
                "wrapperType": "track",
                "trackName": "Deep Cut",
                "artistName": "The 1975",
                "previewUrl": "deepcut.m4a",
            }
        ]
    }

    with patch.object(
        add_previews, "_get_json", side_effect=[empty_search, artist_lookup, catalog]
    ):
        result = add_previews.find_preview("Deep Cut", "The 1975")
    assert result == "deepcut.m4a"


def test_find_preview_falls_back_when_search_hits_are_all_wrong_artist():
    # search returns a title match, but for the wrong artist — must fall
    # through to the catalog lookup rather than accepting it
    wrong_artist_search = {
        "results": [
            {"trackName": "Deep Cut", "artistName": "Someone Else", "previewUrl": "wrong.m4a"}
        ]
    }
    artist_lookup = {"results": [{"artistId": 12345}]}
    catalog = {
        "results": [
            {
                "wrapperType": "track",
                "trackName": "Deep Cut",
                "artistName": "The 1975",
                "previewUrl": "right.m4a",
            }
        ]
    }

    with patch.object(
        add_previews, "_get_json", side_effect=[wrong_artist_search, artist_lookup, catalog]
    ):
        result = add_previews.find_preview("Deep Cut", "The 1975")
    assert result == "right.m4a"


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
