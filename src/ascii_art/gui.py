"""GUI for the ASCII art converter — tune settings in real time and write the
result into a markdown file (e.g. README.md).

Usage:
    python -m ascii_art.gui [image_path] [output_md]
    ascii-art-gui [image_path] [output_md]

Every slider re-renders the preview live (debounced), so you can dial in
exactly how you want the final art to look before writing it to the README.
"""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk

from PIL import Image

from . import converter as ac

# Preset character ramps (darkest -> lightest, unless Invert is checked).
CHARSETS = {
    "Standard": ac.CHARS,
    "Blocks": "\u2588\u2589\u258a\u258b\u258c\u258d\u258e\u258f ",
    "Minimal": "@%#*+=-:. ",
    "Dense ASCII": "WMB#&%@$8*+=-:. ",
}

PREVIEW_FONTS = ["Consolas", "Courier New", "DejaVu Sans Mono", "Menlo", "Monaco"]


class AsciiGUI:
    def __init__(self, root, image_path=None, md_path="README.md"):
        self.root = root
        root.title("ASCII Art Converter - live tweaks")
        root.geometry("920x780")
        root.minsize(720, 600)

        self.image_path = tk.StringVar(value=image_path or "")
        self.md_path = tk.StringVar(value=md_path)

        self.width = tk.IntVar(value=100)
        self.aspect = tk.DoubleVar(value=0.53)
        self.aspect_auto = tk.BooleanVar(value=True)
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.invert = tk.BooleanVar(value=False)
        self.small = tk.BooleanVar(value=False)
        self.charset = tk.StringVar(value="Standard")
        self.status = tk.StringVar(value="Pick an image to start.")

        self.orig_image = None
        self._job = None  # debounce timer id

        # Best available system monospace font => default aspect ratio.
        try:
            self.measured_aspect = ac.char_ratio()
        except Exception:
            self.measured_aspect = 0.53
        self.aspect.set(self.measured_aspect)

        self._build()
        self._wire_traces()
        self.aspect_scale.state(["disabled"])  # auto aspect is on by default

        if image_path and os.path.exists(image_path):
            self.load_image()

    # ------------------------------------------------------------- UI setup

    def _build(self):
        pad = dict(padx=8, pady=4)

        # --- file rows
        f = ttk.LabelFrame(self.root, text="Files")
        f.pack(fill="x", **pad)
        ttk.Label(f, text="Image:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(f, textvariable=self.image_path).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(f, text="Browse...", command=self.browse_image).grid(row=0, column=2, padx=8)
        ttk.Label(f, text="Output .md:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(f, textvariable=self.md_path).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(f, text="Browse...", command=self.browse_md).grid(row=1, column=2, padx=8)
        f.columnconfigure(1, weight=1)

        # --- settings sliders
        s = ttk.LabelFrame(self.root, text="Settings (preview updates as you drag)")
        s.pack(fill="x", **pad)
        s.columnconfigure(1, weight=1)

        self._add_slider(s, 0, "Width", self.width, 20, 220, "{} chars")
        self.aspect_scale = self._add_slider(s, 1, "Aspect", self.aspect, 0.25, 0.9,
                                             "{:.2f}", extra=self._aspect_row_extra(s))
        self._add_slider(s, 2, "Brightness", self.brightness, 0.2, 2.5, "{:.2f}x")
        self._add_slider(s, 3, "Contrast", self.contrast, 0.2, 2.5, "{:.2f}x")

        row = 4
        ttk.Label(s, text="Charset:").grid(row=row, column=0, sticky="e", padx=8, pady=4)
        ttk.Combobox(s, textvariable=self.charset, values=list(CHARSETS),
                     state="readonly", width=14).grid(row=row, column=1, sticky="w", pady=4)
        ttk.Checkbutton(s, text="Invert (bright -> dense glyphs)",
                        variable=self.invert).grid(row=row, column=2, sticky="w", padx=8)
        ttk.Checkbutton(s, text="Small render (<sub>, ~30% smaller on GitHub)",
                        variable=self.small).grid(row=row + 1, column=1, sticky="w", pady=4)

        # --- action buttons
        b = ttk.Frame(self.root)
        b.pack(fill="x", **pad)
        ttk.Button(b, text="Write to README", command=self.write_readme).pack(side="left")
        ttk.Button(b, text="Copy art", command=self.copy_art).pack(side="left", padx=8)

        # --- preview
        p = ttk.LabelFrame(self.root, text="Preview (monospace, as it will render)")
        p.pack(fill="both", expand=True, **pad)
        self.mono_font = self._pick_mono_font()
        self.preview = tk.Text(p, wrap="none", font=self.mono_font, state="disabled",
                               bg="#0d1117", fg="#e6edf3", insertbackground="#e6edf3",
                               padx=10, pady=10)
        vsb = ttk.Scrollbar(p, orient="vertical", command=self.preview.yview)
        hsb = ttk.Scrollbar(p, orient="horizontal", command=self.preview.xview)
        self.preview.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.preview.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        p.rowconfigure(0, weight=1)
        p.columnconfigure(0, weight=1)

        ttk.Label(self.root, textvariable=self.status, anchor="w",
                  relief="sunken").pack(fill="x", side="bottom")

    def _aspect_row_extra(self, parent):
        """Auto aspect checkbox that locks the slider to the measured ratio."""
        self.aspect_auto_btn = ttk.Checkbutton(
            parent, text="Auto (measured)", variable=self.aspect_auto,
            command=self.on_aspect_auto)
        return self.aspect_auto_btn

    def _add_slider(self, parent, row, label, var, from_, to, fmt, extra=None):
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="e", padx=8, pady=4)
        scale = ttk.Scale(parent, from_=from_, to=to, variable=var,
                          orient="horizontal")
        scale.grid(row=row, column=1, sticky="ew", pady=4)
        val = ttk.Label(parent, text="", width=14, anchor="w")
        val.grid(row=row, column=2, sticky="w", padx=8)

        def fmt_var(*_):
            val.config(text=fmt.format(var.get()))
        var.trace_add("write", fmt_var)
        fmt_var()

        if extra is not None:
            extra.grid(row=row, column=3, sticky="w", padx=8)
        return scale

    def _pick_mono_font(self):
        for name in PREVIEW_FONTS:
            f = tkfont.Font(family=name, size=9)
            if f.actual("family") == name:
                return (name, 9)
        return "TkFixedFont"

    def _wire_traces(self):
        for var in (self.width, self.aspect, self.brightness, self.contrast,
                    self.invert, self.small, self.charset):
            var.trace_add("write", self.schedule_update)

    # ------------------------------------------------------------ callbacks

    def browse_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")])
        if path:
            self.image_path.set(path)
            self.load_image()

    def browse_md(self):
        path = filedialog.asksaveasfilename(title="Choose markdown file", defaultextension=".md",
                                            filetypes=[("Markdown", "*.md"), ("All files", "*.*")])
        if path:
            self.md_path.set(path)

    def load_image(self):
        path = self.image_path.get()
        if not path or not os.path.exists(path):
            self.status.set(f"Image not found: {path}")
            self.orig_image = None
            return
        try:
            self.orig_image = Image.open(path).convert("RGB")
            self.status.set(f"Loaded {os.path.basename(path)}")
            self.update_preview()
        except Exception as e:
            self.status.set(f"Could not load image: {e}")
            self.orig_image = None

    def on_aspect_auto(self):
        self.aspect_scale.state(["disabled"] if self.aspect_auto.get() else ["!disabled"])
        self.schedule_update()

    # ------------------------------------------------------ live re-rendering

    def schedule_update(self, *_):
        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(60, self.update_preview)

    def convert(self):
        ramp = CHARSETS[self.charset.get()]
        aspect = self.measured_aspect if self.aspect_auto.get() else self.aspect.get()
        return ac.image_to_ascii_pillow(
            self.orig_image,
            width=self.width.get(),
            aspect_ratio=aspect,
            brightness=self.brightness.get(),
            contrast=self.contrast.get(),
            invert=self.invert.get(),
            charset=ramp,
        )

    def update_preview(self):
        self._job = None
        if self.orig_image is None:
            return
        try:
            art = self.convert()
        except Exception as e:
            self.status.set(f"Error: {e}")
            return
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", art)
        self.preview.config(state="disabled")
        rows = art.count("\n") + 1
        mode = "small (<sub>)" if self.small.get() else "code block"
        self.status.set(
            f"{rows} rows x {self.width.get()} cols | {mode} | -> {self.md_path.get()}")

    # ------------------------------------------------------------- actions

    def write_readme(self):
        if self.orig_image is None:
            self.status.set("Load an image first.")
            return
        try:
            art = self.convert()
        except Exception as e:
            self.status.set(f"Error: {e}")
            return
        block = ac.render_block(art, small=self.small.get())
        ac.update_markdown(self.md_path.get(), block, marker="ascii-art")
        self.status.set(f"Written to {self.md_path.get()}")

    def copy_art(self):
        if self.orig_image is None:
            self.status.set("Load an image first.")
            return
        try:
            art = self.convert()
        except Exception as e:
            self.status.set(f"Error: {e}")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(art)
        self.status.set("Art copied to clipboard.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = [a for a in argv if not a.startswith("-")]
    image = args[0] if len(args) > 0 else None
    md = args[1] if len(args) > 1 else "README.md"
    root = tk.Tk()
    AsciiGUI(root, image, md)
    root.mainloop()


if __name__ == "__main__":
    main()
