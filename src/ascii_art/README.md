# ASCII Art Converter

Turn any image into ASCII art and drop it straight into markdown — the banner on
the root `README.md` (this repo's GitHub profile) was generated from
`images/ybanez1.jpg` by this very tool. Tune width, brightness, contrast, and
the character ramp, then render the result as a normal code block or as `<sub>`
text that displays ~30% smaller on GitHub.

## Install

```bash
pip install -e .[magic]     # installs the ascii-art / ascii-art-gui commands
# or, dependencies only (no console commands):
pip install -r requirements.txt
```

Requires Python 3.9+ and [Pillow](https://pypi.org/project/Pillow/).
[ascii-magic](https://pypi.org/project/ascii-magic/) is optional but gives
smoother gradients; without it the pure-Pillow backend is used automatically.

## Usage

### Command line

```bash
ascii-art images/ybanez1.jpg README.md 100 --small
# or, without installing (add src/ to PYTHONPATH):
PYTHONPATH=src python -m ascii_art.cli images/ybanez1.jpg README.md 100 --small
```

| Option     | Description                                                                 |
| ---------- | --------------------------------------------------------------------------- |
| `width`    | Output width in characters (default: 100)                                   |
| `--small`  | Render with `<sub>` tags so it displays ~30% smaller on GitHub              |
| `--aspect` | Character cell ratio (default: measured from your system monospace font)    |

The art is written between `<!-- ascii-art:start -->` / `<!-- ascii-art:end -->`
markers, so re-running always replaces the previous block in place.

### GUI

```bash
ascii-art-gui
ascii-art-gui images/ybanez1.jpg README.md
# or, without installing:
PYTHONPATH=src python -m ascii_art.gui images/ybanez1.jpg README.md
```

Drag the sliders to preview live, then **Write to README** or **Copy art**.

## Project layout

```
src/ascii_art/       package
  __init__.py        public API (char_ratio, image_to_ascii*, render_block, update_markdown)
  converter.py       conversion engine (charsets, font ratio, Pillow/ascii_magic backends)
  markdown.py        render <pre>/<sub> blocks and update .md files
  cli.py             command-line entry point
  gui.py             tkinter GUI with live preview
images/              sample source images and generated previews
assets/              README assets
README.md            this file (project docs)
```
