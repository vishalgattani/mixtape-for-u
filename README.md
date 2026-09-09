# mixtape_for_u

A browser-based "lyrics picker": a card pops up with a random lyric snippet
(title, artist, and a short line) over an animated p5.js background, with an
optional 30-second audio preview you can play/pause/rewind/forward through.

## Repo layout

```
index.html    page markup/layout
main.js       card + playback logic (fetches lyrics.json, drives the UI)
sketch.js     p5.js background animation
style.css     styling
lyrics.json   data source: one entry per {title, artist, lyric, color, preview}

scripts/
  add_previews.py            looks up an iTunes 30s preview URL for each lyrics.json entry
  spotify_lyrics_sticker.py  crops Spotify lyric-share screenshots to the inner card

tests/
  test_add_previews.py       pytest suite for scripts/add_previews.py
```

## Running the web page locally

The page fetches `lyrics.json` via `fetch()`, which most browsers block on
`file://` URLs, so serve the directory over HTTP instead of opening
`index.html` directly:

```bash
python -m http.server
```

Then open `http://localhost:8000` in a browser.

## Running the Python scripts

`add_previews.py` uses only the standard library:

```bash
python scripts/add_previews.py [path/to/lyrics.json]   # defaults to ./lyrics.json
```

`spotify_lyrics_sticker.py` additionally needs `numpy` and `Pillow`:

```bash
pip install numpy pillow
python scripts/spotify_lyrics_sticker.py [input_dir] [output_dir]
```

### Tests

```bash
pip install pytest
pytest
```

`test_add_previews.py` covers `add_previews.py`'s matching logic and control
flow with the network calls mocked out, plus a schema check on `lyrics.json`.

## Formatting

Python code is formatted with `black` and `isort` (both configured for a
100-character line length in `pyproject.toml`):

```bash
pip install black isort
black .
isort .
```
