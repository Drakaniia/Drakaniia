"""Image -> ASCII conversion engine.

Two backends are supported:

- ``ascii_magic`` (preferred; used automatically when installed)
- a pure Pillow fallback (always available)
"""

import os

from PIL import Image, ImageEnhance, ImageFont

try:
    import ascii_magic
    HAS_ASCII_MAGIC = True
except ImportError:
    HAS_ASCII_MAGIC = False

# Characters ordered from darkest (most dense) to lightest (least dense).
# ~70 levels give smooth gradients instead of the banding of a 10-char ramp.
CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

# Common monospace fonts, best first, per platform.
MONO_FONTS = [
    r"C:\Windows\Fonts\consola.ttf",   # Windows (GitHub uses this)
    r"C:\Windows\Fonts\cour.ttf",      # Windows fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",  # Linux
    "/System/Library/Fonts/Menlo.ttc",  # macOS
    "/System/Library/Fonts/Monaco.ttf",  # macOS
]


def char_ratio():
    """Measure the width/height ratio of the best available monospace font."""
    for path in MONO_FONTS:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 14)
            char_w = font.getlength("M" * 100) / 100
            ascent, descent = font.getmetrics()
            ratio = char_w / (ascent + descent)
            print(f"Measured char ratio {ratio:.4f} from {path}")
            return ratio
    print("No system monospace font found; using 0.5")
    return 0.5


def image_to_ascii_ascii_magic(image_path, width=100, aspect_ratio=0.5):
    """Convert an image to ASCII using the ascii_magic library."""
    art = ascii_magic.from_image(image_path)
    # ascii_magic's width_ratio is height/width of a char cell; convert our
    # measured width/height ratio and enhance contrast/sharpness for detail.
    width_ratio = 1.0 / aspect_ratio if aspect_ratio > 0 else 2.2
    return art.to_ascii(columns=width, width_ratio=width_ratio, enhance_image=True)


def image_to_ascii_pillow(image, width=100, aspect_ratio=0.5, brightness=1.0,
                          contrast=1.0, invert=False, charset=None):
    """Fallback: convert a PIL image (or image path) to ASCII with Pillow directly.

    brightness/contrast: multipliers applied before grayscaling.
    invert:              flip the ramp so bright pixels map to dense glyphs.
    charset:             character ramp (defaults to CHARS).
    """
    if charset is None:
        charset = CHARS
    ramp = charset[::-1] if invert else charset

    # Accept either a PIL Image (GUI keeps one loaded for fast re-renders)
    # or a path to an image file.
    close_after = not hasattr(image, "convert")
    if close_after:
        image = Image.open(image)
    try:
        im = image.convert("RGB")
        if brightness != 1.0:
            im = ImageEnhance.Brightness(im).enhance(brightness)
        if contrast != 1.0:
            im = ImageEnhance.Contrast(im).enhance(contrast)
        im = im.convert("L")  # grayscale

        # Scale height by the character cell ratio so the rendered text
        # keeps the image's aspect ratio (e.g. 0.53 for Consolas).
        aspect = im.height / im.width
        height = max(1, int(width * aspect * aspect_ratio))
        im = im.resize((width, height))

        pixels = im.tobytes()  # one byte per pixel for grayscale
        step = 255 / (len(ramp) - 1)

        lines = []
        for y in range(height):
            row = pixels[y * width:(y + 1) * width]
            lines.append("".join(ramp[min(int(p / step), len(ramp) - 1)] for p in row))
        return "\n".join(lines)
    finally:
        if close_after:
            image.close()


def image_to_ascii(image_path, width=100, aspect_ratio=0.5):
    """Convert an image file to ASCII art, picking the best available backend."""
    if HAS_ASCII_MAGIC:
        return image_to_ascii_ascii_magic(image_path, width, aspect_ratio)
    print("ascii_magic not installed; using Pillow fallback")
    return image_to_ascii_pillow(image_path, width, aspect_ratio)
