#!/usr/bin/env python3
"""Ensure a product has an assembled PCB Design Assets page."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PCB_HEADING_RE = re.compile(r"^## PCB design assets\s*$", re.MULTILINE | re.IGNORECASE)
NEXT_H2_RE = re.compile(r"^## .+$", re.MULTILINE)
NAV_BOM_LINE_RE = re.compile(r"^(\s*)-\s+Bill of Materials:\s+bom\.md\s*$", re.MULTILINE)
NAV_PCB_LINE_RE = re.compile(r"^\s*-\s+PCB Design Assets:\s+pcb-design-assets\.md\s*$", re.MULTILINE)
PLACEHOLDER = "# PCB Design Assets\n\nPCB assets are awaiting migration.\n"


def split_pcb_section(bom_page: Path, pcb_page: Path) -> bool:
    content = bom_page.read_text(encoding="utf-8")
    match = PCB_HEADING_RE.search(content)
    if not match:
        return False

    next_match = NEXT_H2_RE.search(content, match.end())
    section_end = next_match.start() if next_match else len(content)
    section = content[match.start() : section_end].strip()

    updated_bom = f"{content[:match.start()].rstrip()}\n\n{content[section_end:].lstrip()}"
    pcb_content = PCB_HEADING_RE.sub("# PCB Design Assets", section, count=1)

    bom_page.write_text(updated_bom, encoding="utf-8")
    pcb_page.write_text(f"{pcb_content}\n", encoding="utf-8")
    return True


def ensure_pcb_page(bom_page: Path, pcb_page: Path) -> str:
    if bom_page.exists() and split_pcb_section(bom_page, pcb_page):
        return "split"

    if pcb_page.exists():
        return "existing"

    pcb_page.write_text(PLACEHOLDER, encoding="utf-8")
    return "placeholder"


def update_nav(pages_file: Path) -> None:
    if not pages_file.exists():
        return

    lines = pages_file.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if line.strip()]
    lines = [line for line in lines if not NAV_PCB_LINE_RE.match(line)]

    updated: list[str] = []
    inserted = False
    for line in lines:
        updated.append(line)
        match = NAV_BOM_LINE_RE.match(line)
        if match and not inserted:
            updated.append(f"{match.group(1)}- PCB Design Assets: pcb-design-assets.md")
            inserted = True

    pages_file.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ensure an assembled PCB Design Assets page and nav item."
    )
    parser.add_argument("--dest", required=True, type=Path, help="assembled product docs directory")
    args = parser.parse_args()

    dest = args.dest
    bom_page = dest / "bom.md"
    pcb_page = dest / "pcb-design-assets.md"

    result = ensure_pcb_page(bom_page, pcb_page)
    update_nav(dest / ".pages")
    if result == "split":
        print(f"Moved PCB design assets from {bom_page} to {pcb_page}")
    elif result == "existing":
        print(f"Using existing PCB design assets page at {pcb_page}")
    else:
        print(f"Created placeholder PCB design assets page at {pcb_page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
