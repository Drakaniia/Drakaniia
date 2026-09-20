#!/usr/bin/env python3
"""
scripts/compress-images.py

Compress images in place with visually lossless settings.
Keeps the same quality, drastically smaller files.

- PNG (RGBA, large): quantize to 256 colors (Octree palette) + optimize level 9.
  Preserves transparency. Saves ~90% on banners like main.png.
- PNG (other): lossless optimize (compress_level=9).
- JPEG/JPG: recompress as progressive JPEG with high quality (default 90),
  4:4:4 subsampling, optimize=True.
- GIF: lossless optimize (no resize; Pillow inflates animated GIFs).
- Optionally generates .webp alongside each image (q90 method 6).

Usage:
  python scripts/compress-images.py                          # compress images/ + assets/
  python scripts/compress-images.py images assets            # explicit dirs
  python scripts/compress-images.py --webp --quality 90      # custom quality + webp copies
  python scripts/compress-images.py --dry-run                # show savings without writing
  python scripts/compress-images.py --no-webp images/main.png  # single file, no webp

Requires: Pillow  (pip install Pillow)
"""

from __future__ import annotations

import argparse
import io
import pathlib
import shutil
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow not found. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DIRS = [PROJECT_ROOT / "images", PROJECT_ROOT / "assets"]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def compress_png(im: Image.Image, path: pathlib.Path, *, dry_run: bool) -> tuple[int, int]:
    orig = path.stat().st_size
    # Large RGBA PNGs benefit hugely from palette quantization
    if im.mode == "RGBA" and orig > 100 * 1024:
        # Octree (method=2) is the only palette method that handles alpha in Pillow
        im_q = im.quantize(colors=256, method=2)
        buf = io.BytesIO()
        im_q.save(buf, format="PNG", optimize=True, compress_level=9)
        data = buf.getvalue()
        # Only use quantized if actually smaller and palette has transparency
        if len(data) >= orig:
            buf2 = io.BytesIO()
            im.save(buf2, format="PNG", optimize=True, compress_level=9)
            data = buf2.getvalue()
    else:
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True, compress_level=9)
        data = buf.getvalue()

    new_size = len(data)
    if new_size < orig and not dry_run:
        # keep backup on first run if caller wants it (we don't create .bak here)
        path.write_bytes(data)
    return orig, new_size


def compress_jpeg(im: Image.Image, path: pathlib.Path, quality: int, *, dry_run: bool) -> tuple[int, int]:
    orig = path.stat().st_size
    rgb = im.convert("RGB") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True, subsampling=0)
    data = buf.getvalue()
    new_size = len(data)
    # Pillow's JPEG may be larger on tiny/thumbnail images — keep original then
    if new_size < orig and not dry_run:
        path.write_bytes(data)
        # If file was misnamed .png content with .jpg extension, we now wrote valid JPEG
    elif new_size >= orig:
        new_size = orig
    return orig, new_size


def compress_gif(im: Image.Image, path: pathlib.Path, *, dry_run: bool) -> tuple[int, int]:
    orig = path.stat().st_size
    # Animated GIFs often inflate when round-tripped through Pillow, so only
    # optimize single-frame GIFs; leave animated ones as-is.
    if getattr(im, "is_animated", False):
        return orig, orig
    buf = io.BytesIO()
    im.save(buf, format="GIF", optimize=True)
    data = buf.getvalue()
    new_size = len(data)
    if new_size < orig and not dry_run:
        path.write_bytes(data)
    elif new_size >= orig:
        new_size = orig
    return orig, new_size


def maybe_generate_webp(im: Image.Image, src_path: pathlib.Path, quality: int, *, dry_run: bool) -> int | None:
    if src_path.suffix.lower() == ".webp":
        return None
    if getattr(im, "is_animated", False):
        return None  # keep animated GIFs as-is; single-frame WEBP would lose animation
    # Skip webp generation for tiny paletted PNGs where WEBP inflates (e.g. ascii previews)
    if src_path.suffix.lower() == ".png":
        try:
            if src_path.stat().st_size < 80 * 1024:
                return None
        except Exception:
            pass
    webp_path = src_path.with_suffix(".webp")
    buf = io.BytesIO()
    try:
        im.save(buf, format="WEBP", quality=quality, method=6)
    except Exception:
        return None
    data = buf.getvalue()
    # Only keep webp if it's actually smaller than the source (avoid 51KB PNG -> 330KB WEBP)
    try:
        if len(data) >= src_path.stat().st_size:
            return None
    except Exception:
        pass
    if not dry_run:
        webp_path.write_bytes(data)
    return len(data)


def collect_images(targets: list[pathlib.Path]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for t in targets:
        if t.is_file() and t.suffix.lower() in IMAGE_EXTS:
            out.append(t)
        elif t.is_dir():
            for p in t.rglob("*"):
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS and ".bak" not in p.suffixes:
                    out.append(p)
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Compress images visually losslessly.")
    ap.add_argument("targets", nargs="*", help="Files or dirs to compress (default: images/ assets/)")
    ap.add_argument("--quality", type=int, default=90, help="JPEG/WEBP quality 1-100 (default 90, JPEG uses 92 if --quality 90 for photo safety)")
    ap.add_argument("--webp", action="store_true", default=True, help="Also generate .webp alongside each image (default on)")
    ap.add_argument("--no-webp", dest="webp", action="store_false", help="Disable webp generation")
    ap.add_argument("--dry-run", action="store_true", help="Show savings without writing files")
    args = ap.parse_args()

    if args.targets:
        targets = [pathlib.Path(t) if pathlib.Path(t).is_absolute() else PROJECT_ROOT / t for t in args.targets]
        # also handle relative from CWD
        targets = [p if p.exists() else pathlib.Path(t) for p, t in zip(targets, args.targets)]
    else:
        targets = [p for p in DEFAULT_DIRS if p.exists()]
        if not targets:
            print(f"No default dirs found ({', '.join(str(p) for p in DEFAULT_DIRS)}), pass a target.", file=sys.stderr)
            sys.exit(1)

    images = collect_images(targets)
    if not images:
        print("No images found.", file=sys.stderr)
        sys.exit(0)

    total_orig = 0
    total_new = 0
    # For total we track actual file sizes after run (or hypothetical if dry-run)
    jpeg_quality = 92 if args.quality == 90 else args.quality

    print(f"Found {len(images)} image(s). quality={args.quality} webp={args.webp} dry_run={args.dry_run}\n")
    for p in images:
        try:
            im = Image.open(p)
        except Exception as e:
            print(f"SKIP {p.relative_to(PROJECT_ROOT) if p.is_relative_to(PROJECT_ROOT) else p}: {e}")
            continue
        fmt = (im.format or p.suffix).upper()
        orig = p.stat().st_size
        # Dispatch
        if fmt == "PNG" or p.suffix.lower() == ".png":
            o, n = compress_png(im, p, dry_run=args.dry_run)
        elif fmt in ("JPEG", "JPG") or p.suffix.lower() in (".jpg", ".jpeg"):
            # Handle misnamed PNG content with .jpg/.jpeg extension (common)
            # Pillow will report PNG format even with .jpeg suffix — treat as JPEG target
            o, n = compress_jpeg(im, p, jpeg_quality, dry_run=args.dry_run)
        elif fmt == "GIF":
            o, n = compress_gif(im, p, dry_run=args.dry_run)
        elif fmt == "WEBP":
            # Re-optimize webp in place
            buf = io.BytesIO()
            im.save(buf, format="WEBP", quality=args.quality, method=6)
            n = len(buf.getvalue())
            o = orig
            if n < orig and not args.dry_run:
                p.write_bytes(buf.getvalue())
            elif n >= orig:
                n = orig
        else:
            # Fallback: try lossless PNG optimize
            o, n = compress_png(im, p, dry_run=args.dry_run)

        saved = o - n if n < o else 0
        pct = (1 - n / o) * 100 if o else 0
        status = "OK" if n < o else "already optimal"
        print(f"{status:16} {p.relative_to(PROJECT_ROOT) if p.is_relative_to(PROJECT_ROOT) else p}  {o/1024:.1f} KB -> {n/1024:.1f} KB  ({pct:.1f}% saved)" if n < o else f"{status:16} {p.relative_to(PROJECT_ROOT) if p.is_relative_to(PROJECT_ROOT) else p}  {o/1024:.1f} KB")

        if args.webp and fmt != "WEBP":
            try:
                # Re-open original (before quantize) for best webp quality — use fresh open
                im2 = Image.open(p) if not args.dry_run else im
                # For PNG we want the original RGBA for webp, not the paletted version
                # so re-open the backup in memory is not possible; use im (original) captured above
                src_im = im  # original loaded before compression
                wsize = maybe_generate_webp(src_im, p, args.quality, dry_run=args.dry_run)
                if wsize is not None:
                    rel_webp = p.with_suffix(".webp")
                    rel = rel_webp.relative_to(PROJECT_ROOT) if rel_webp.is_relative_to(PROJECT_ROOT) else rel_webp
                    print(f"  -> {rel}  {wsize/1024:.1f} KB")
            except Exception as e:
                print(f"  webp failed for {p}: {e}", file=sys.stderr)

        total_orig += o
        total_new += n if n < o else o

    print(f"\nTotal: {total_orig/1024:.1f} KB -> {total_new/1024:.1f} KB  saved {(total_orig-total_new)/1024:.1f} KB ({(1-total_new/total_orig)*100:.1f}% reduction)")
    if args.dry_run:
        print("(dry-run — no files were written)")


if __name__ == "__main__":
    main()
