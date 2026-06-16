#!/usr/bin/env python3
"""Insert KiCanvas PCB previews into an assembled product PCB overview page.

This runs on the assembled copy of a product's PCB overview page. The
product repo remains the source of truth; this script only copies selected
``hardware/pcb`` files into the generated site and updates the assembled page
between stable markers.
"""

from __future__ import annotations

import argparse
import html
import shutil
import re
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN KICANVAS PCB -->"
END_MARKER = "<!-- END KICANVAS PCB -->"
PCB_HEADING_RE = re.compile(
    r"^#{1,2} PCB (?:overview|design assets)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
PLACEHOLDER_TEXTS = (
    "PCB overview content is awaiting migration.",
    "PCB assets are awaiting migration.",
)
GENERATED_INTRO = "KiCanvas previews are generated from KiCad board files under `hardware/pcb/`."

def rel_url(path: Path, start: Path) -> str:
    return path.relative_to(start).as_posix()


def discover_boards(pcb_dir: Path) -> list[Path]:
    return sorted(path for path in pcb_dir.rglob("*.kicad_pcb") if path.is_file())


def copy_kicad_assets(sources: list[Path], targets: list[Path]) -> None:
    for source, target in zip(sources, targets, strict=True):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def choose_boards(boards: list[Path], preferred_name: str | None, pcb_dir: Path) -> list[Path]:
    if not boards:
        return []

    if preferred_name:
        for board in boards:
            rel = board.relative_to(pcb_dir).as_posix()
            if board.name == preferred_name or rel == preferred_name:
                return [board]

    return boards


def build_viewer(board_url: str, board_name: str, index: int, count: int) -> str:
    label = "KiCanvas PCB viewer" if count == 1 else f"KiCanvas PCB viewer {index}: {board_name}"
    escaped_label = html.escape(label)
    escaped_name = html.escape(board_name)
    escaped_url = html.escape(board_url, quote=True)
    return f"""\
<div class="pcb-kicanvas" markdown="0">
  <div class="pcb-kicanvas-head">
    <strong>{escaped_label}</strong>
    <div class="pcb-kicanvas-actions">
      <a href="{escaped_url}" download>{escaped_name}</a>
      <button class="pcb-kicanvas-full-window" type="button" aria-expanded="false">Full window</button>
    </div>
  </div>
  <kicanvas-embed class="pcb-kicanvas-viewer" src="{escaped_url}" controls="full"></kicanvas-embed>
</div>
"""


def build_block(boards: list[Path], page_dir: Path) -> str:
    viewers = [
        build_viewer(rel_url(board, page_dir), board.name, index, len(boards))
        for index, board in enumerate(boards, start=1)
    ]
    rendered_viewers = "\n".join(viewers)
    return f"""\
{BEGIN_MARKER}
{rendered_viewers}
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
        paragraph_end = len(content)

    paragraph = content[paragraph_start:paragraph_end].strip()
    if paragraph in PLACEHOLDER_TEXTS:
        prefix = f"{content[:heading.end()].rstrip()}\n\n{GENERATED_INTRO}"
        suffix = content[paragraph_end:].lstrip()
    else:
        insert_at = min(paragraph_end + 2, len(content))
        prefix = content[:insert_at].rstrip()
        suffix = content[insert_at:].lstrip()

    if suffix:
        return f"{prefix}\n\n{block.rstrip()}\n\n{suffix}"
    return f"{prefix}\n\n{block.rstrip()}\n"


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

    discovered = discover_boards(pcb_dir)
    boards = choose_boards(discovered, args.board, pcb_dir)
    if not boards:
        print(f"note: no .kicad_pcb files in {pcb_dir} - skipping KiCanvas PCB preview")
        return 0

    target_boards = [asset_dir / board.relative_to(pcb_dir) for board in boards]
    content = page.read_text(encoding="utf-8")
    block = build_block(target_boards, page.parent)
    updated = replace_or_insert(content, block)
    if updated is None:
        print(f"note: no PCB overview section in {page} - skipping KiCanvas PCB preview")
        return 0

    copy_kicad_assets(boards, target_boards)
    page.write_text(updated, encoding="utf-8")
    board_names = ", ".join(board.name for board in boards)
    print(f"Inserted KiCanvas PCB preview for {board_names} into {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
