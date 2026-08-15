"""Command-line interface for the ASCII art converter.

Usage:
    python -m ascii_art.cli <image_path> <output_md> [width] [--small]
    ascii-art <image_path> <output_md> [width] [--small]

Options:
    width       Output width in characters (default: 100)
    --small     Render the art with <sub> tags so it displays ~30% smaller
                (GitHub strips style="font-size", but allows <sub>/<sup>)
    --aspect X  Character width/height ratio (default: measured from the
                best available system monospace font, e.g. 0.53 Consolas)
"""

import sys

from . import markdown
from .converter import HAS_ASCII_MAGIC, char_ratio, image_to_ascii


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = [a for a in argv if not a.startswith("--")]
    flags = [a for a in argv if a.startswith("--")]
    small = "--small" in flags

    if len(args) < 2:
        print(__doc__)
        return 1

    image_path = args[0]
    md_path = args[1]
    width = int(args[2]) if len(args) > 2 else 100

    if "--aspect" in argv:
        i = argv.index("--aspect")
        aspect = float(argv[i + 1])
    else:
        aspect = char_ratio()  # measure the viewer's monospace font

    ascii_art = image_to_ascii(image_path, width, aspect_ratio=aspect)
    block = markdown.render_block(ascii_art, small=small)
    markdown.update_markdown(md_path, block, marker="ascii-art")
    engine = "ascii_magic" if HAS_ASCII_MAGIC else "Pillow"
    print(f"ASCII art ({'small' if small else 'normal'} render, {engine}) written to {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
