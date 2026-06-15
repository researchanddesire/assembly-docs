#!/usr/bin/env python3
"""Insert a KiCanvas PCB preview into an assembled product PCB overview page.

This runs on the assembled copy of a product's ``assembly-docs/bom.md``. The
product repo remains the source of truth; this script only copies selected
``hardware/pcb`` files into the generated site and updates the assembled page
between stable markers.
"""

from __future__ import annotations

import argparse
import shutil
import re
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN KICANVAS PCB -->"
END_MARKER = "<!-- END KICANVAS PCB -->"
PCB_HEADING_RE = re.compile(
    r"^#{1,2} PCB (?:overview|design assets)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

COPY_PATTERNS = (
    "*.kicad_pcb",
)


def rel_url(path: Path, start: Path) -> str:
    return path.relative_to(start).as_posix()


def copy_kicad_assets(pcb_dir: Path, asset_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in COPY_PATTERNS:
        files.extend(sorted(pcb_dir.glob(pattern)))

    if not files:
        return []

    asset_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in files:
        target = asset_dir / source.name
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def choose_board(copied: list[Path], preferred_name: str | None) -> Path | None:
    boards = sorted(path for path in copied if path.suffix == ".kicad_pcb")
    if not boards:
        return None

    if preferred_name:
        for board in boards:
            if board.name == preferred_name:
                return board

    return boards[0]


def build_block(board_url: str, board_name: str) -> str:
    return f"""\
{BEGIN_MARKER}
<div class="pcb-kicanvas" markdown="0">
  <div class="pcb-kicanvas-head">
    <strong>KiCanvas PCB viewer</strong>
    <div class="pcb-kicanvas-actions">
      <a href="{board_url}" download>{board_name}</a>
      <button class="pcb-kicanvas-full-window" type="button" aria-expanded="false">Full window</button>
    </div>
  </div>
  <kicanvas-embed class="pcb-kicanvas-viewer" src="{board_url}" controls="full"></kicanvas-embed>
</div>
{END_MARKER}
"""


def replace_or_insert(content: str, block: str) -> str | None:
    begin = content.find(BEGIN_MARKER)
    end = content.find(END_MARKER)

    if begin != -1 and end != -1 and end > begin:
        end += len(END_MARKER)
        content = f"{content[:begin].rstrip()}\n\n{content[end:].lstrip()}"

    heading = PCB_HEADING_RE.search(content)
    if heading is None:
        return None

    paragraph_start = heading.end()
    while content[paragraph_start : paragraph_start + 1] == "\n":
        paragraph_start += 1

    paragraph_end = content.find("\n\n", paragraph_start)
    if paragraph_end == -1:
        return None

    insert_at = paragraph_end + 2
    return f"{content[:insert_at].rstrip()}\n\n{block.rstrip()}\n\n{content[insert_at:].lstrip()}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy KiCad PCB files and insert a KiCanvas preview into a PCB overview page."
    )
    parser.add_argument("--page", required=True, type=Path, help="assembled PCB overview page")
    parser.add_argument("--pcb-dir", required=True, type=Path, help="product hardware/pcb directory")
    parser.add_argument(
        "--asset-dir",
        required=True,
        type=Path,
        help="site asset directory where KiCad files should be copied",
    )
    parser.add_argument("--board", help="preferred .kicad_pcb filename")
    args = parser.parse_args()

    page = args.page
    pcb_dir = args.pcb_dir
    asset_dir = args.asset_dir

    if not page.exists():
        print(f"note: {page} not found - skipping KiCanvas PCB preview")
        return 0
    if not pcb_dir.is_dir():
        print(f"note: {pcb_dir} not found - skipping KiCanvas PCB preview")
        return 0

    copied = copy_kicad_assets(pcb_dir, asset_dir)
    board = choose_board(copied, args.board)
    if board is None:
        print(f"note: no .kicad_pcb files in {pcb_dir} - skipping KiCanvas PCB preview")
        return 0

    content = page.read_text(encoding="utf-8")
    board_url = rel_url(board, page.parent)
    block = build_block(board_url, board.name)
    updated = replace_or_insert(content, block)
    if updated is None:
        print(f"note: no PCB overview section in {page} - skipping KiCanvas PCB preview")
        return 0

    page.write_text(updated, encoding="utf-8")
    print(f"Inserted KiCanvas PCB preview for {board.name} into {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
