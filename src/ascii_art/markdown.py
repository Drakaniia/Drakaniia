"""Render ASCII art into markdown blocks and update .md files."""

import html
import os


def render_block(ascii_art, small=False):
    """Wrap ASCII art in markdown that renders at normal or smaller size."""
    if small:
        # Each line in its own <sub>: GitHub renders it smaller (~30%),
        # and <pre> keeps the newlines and monospace intact. Escape the
        # art so ramp chars like < > & aren't parsed as HTML tags.
        esc = html.escape(ascii_art)
        subbed = "\n".join(f"<sub>{line}</sub>" for line in esc.split("\n"))
        return f"<pre>\n{subbed}\n</pre>"
    return f"```text\n{ascii_art}\n```"


def update_markdown(md_path, block, marker="ascii-art"):
    """Insert or replace a marked block in the markdown file.

    The block is wrapped in ``<!-- {marker}:start -->`` /
    ``<!-- {marker}:end -->`` comments; an existing block with the same
    marker is replaced in place, otherwise the block is appended.
    """
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    wrapped = f"{start}\n{block}\n{end}\n"

    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""  # create the file if it doesn't exist yet

    if start in content and end in content:
        content = content[:content.index(start)] + wrapped + content[content.index(end) + len(end):]
    else:
        content = content.rstrip() + "\n\n" + wrapped

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
