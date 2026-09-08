"""
test_ocr_lyrics.py — unit tests for scripts/ocr_lyrics.py
Author: Vishal Gattani
Created: 2026-09-07

Pure-logic tests (clean_text, _color_distance) need no OCR binary and always
run. The end-to-end extract_entry test needs the real tesseract binary — no
meaningful way to mock pixel-level OCR — so it's skipped (not failed) when
tesseract isn't installed. It uses a bundled fixture image (not an absolute
path into the vault) so it actually runs in CI, not just locally.
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ocr_lyrics as ocr  # noqa: E402

HAS_TESSERACT = shutil.which("tesseract") is not None
SAMPLE_IMAGE = Path(__file__).resolve().parent / "fixtures" / "good-girls-sample.jpg"


def test_clean_text_fixes_standalone_pipe():
    assert ocr.clean_text("| wanna hold your hand") == "I wanna hold your hand"


def test_clean_text_leaves_word_internal_pipe_alone():
    # not a real case in lyrics, but proves the regex only strips a STANDALONE
    # pipe, not one embedded in a word — guards against over-aggressive matching
    assert ocr.clean_text("a|b") == "a|b"


def test_clean_text_strips_surrounding_whitespace():
    assert ocr.clean_text("  hello world  ") == "hello world"


def test_color_distance_identical_is_zero():
    assert ocr._color_distance("#6b81c9", "#6b81c9") == 0


def test_color_distance_is_positive_for_different_colors():
    assert ocr._color_distance("#000000", "#ffffff") > 0


@pytest.mark.skipif(
    not (HAS_TESSERACT and SAMPLE_IMAGE.exists()),
    reason="needs the real tesseract binary and the local vault's sample image",
)
def test_extract_entry_on_known_good_sample():
    # "Good Girls" — LANY, one of the cleanest cards in the ground-truth set;
    # a real end-to-end regression check that the OCR + parsing pipeline
    # still produces a fully correct entry, not just that it runs without
    # crashing
    entry = ocr.extract_entry(SAMPLE_IMAGE)
    assert entry is not None
    assert entry["title"] == "Good Girls"
    assert entry["artist"] == "LANY"
    assert "California" in entry["lyric"]
    assert entry["color"] in ocr.PALETTE
