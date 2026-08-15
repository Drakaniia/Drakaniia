"""Convert images to ASCII art and render it in markdown (e.g. GitHub READMEs).

Public API:
    char_ratio()                measure the viewer's monospace font ratio
    image_to_ascii(path, ...)   convert an image file to ASCII art
    image_to_ascii_pillow(...)  Pillow-only conversion (live re-renders)
    render_block(art, ...)      wrap art in a markdown/HTML block
    update_markdown(path, ...)  insert/replace the art in a .md file
"""

from .converter import (
    CHARS,
    HAS_ASCII_MAGIC,
    MONO_FONTS,
    char_ratio,
    image_to_ascii,
    image_to_ascii_ascii_magic,
    image_to_ascii_pillow,
)
from .markdown import render_block, update_markdown

__all__ = [
    "CHARS",
    "HAS_ASCII_MAGIC",
    "MONO_FONTS",
    "char_ratio",
    "image_to_ascii",
    "image_to_ascii_ascii_magic",
    "image_to_ascii_pillow",
    "render_block",
    "update_markdown",
]

__version__ = "1.0.0"
