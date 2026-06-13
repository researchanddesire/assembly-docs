#!/usr/bin/env python3
"""Render a product ``hardware/bom.csv`` into a polished HTML Bill of Materials.

Reusable across every Research and Desire product (Lockbox, DT_Trainer, OSSM,
...). This lives in the assembly-docs aggregator repo and is invoked by
``scripts/assemble-docs.sh`` at build time: for each product it reads the
product's ``hardware/bom.csv`` and embeds an accessible, strongly colour-coded
HTML BOM table into that product's assembly-docs ``bom.md`` page, between stable
markers (``<!-- BEGIN GENERATED BOM -->`` / ``<!-- END GENERATED BOM -->``).

Because rendering happens at assemble time the embedded block is never committed
per-product, so it can never go stale. The same renderer can also:

  * ``--check``      verify an already-embedded block is up to date (exit 1 if
                     stale) -- for any repo that chooses to commit the block.
  * ``--standalone`` write a self-contained ``bom.html`` -- used on tagged
                     product releases when no committed ``bom.html`` exists.

Design rules (see AGENTS.md / dev-docs BOM standard §3a):
  * The BOM CSV is READ-ONLY. This tool never writes to it.
  * The BOM *schema* is fixed and owned by the canonical standard in dev-docs.
    This tool validates the header against that schema and refuses to render a
    BOM with a different schema -- it does not invent or rename fields.
  * Output is deterministic (no timestamps, stable ordering).
  * Rendering belongs to ASSEMBLY DOCS ONLY -- never to developer docs.
"""

from __future__ import annotations

import argparse
import csv
import html
import posixpath
import re
import subprocess
import sys
from pathlib import Path

from bom_categories import color_for, label_for, text_color_for

# --- Canonical schema (display headers, in order) -----------------------------
# Mirrors dev-docs schemas/bom.schema.json. Field names are the machine
# identifiers; HEADERS are what the CSV header row must contain, in this order.
FIELDS = [
    "line_item",
    "part_name",
    "category",
    "description",
    "qty",
    "unit_of_measure",
    "manufacturer",
    "mfg_part_number",
    "vendor",
    "vendor_part_number",
    "source",
    "notes",
]
HEADERS = [
    "#",
    "Part Name",
    "Category",
    "Description",
    "Qty",
    "UOM",
    "Manufacturer",
    "MFG PN",
    "Vendor",
    "Vendor PN",
    "Source",
    "Notes",
]
# Columns kept deliberately narrow / compact and on a single line.
NUMERIC_FIELDS = {"line_item", "qty", "unit_of_measure"}
# Text columns whose content is wrapped in a 2-line clamp (see .bom-clamp CSS)
# so a long value wraps to at most two lines instead of overrunning the next
# column. Everything except the numeric columns and the category chip.
CLAMP_FIELDS = set(FIELDS) - NUMERIC_FIELDS - {"category"}

BLANK_DISPLAY = "\u2013"  # en-dash for blank cells, per the BOM standard.
BEGIN_MARKER = "<!-- BEGIN GENERATED BOM -->"
END_MARKER = "<!-- END GENERATED BOM -->"

_URL_RE = re.compile(r"https?://[^\s<>\"')]+")


# --- Value rendering ----------------------------------------------------------
def is_blank(value: str) -> bool:
    return value.strip() in ("", BLANK_DISPLAY, "-")


def esc(value: str) -> str:
    """HTML-escape a raw CSV value (quotes included)."""
    return html.escape(value, quote=True)


def github_blob_url(repo_url: str, commit: str, path: str) -> str:
    base = repo_url.rstrip("/")
    return f"{base}/blob/{commit}/{path.lstrip('/')}"


def render_link(href: str, text: str) -> str:
    return (
        f'<a href="{esc(href)}" target="_blank" rel="noopener noreferrer">'
        f"{esc(text)}</a>"
    )


def linkify(value: str) -> str:
    """Escape text and turn any embedded http(s) URLs into links.

    Used for free-text columns (notes) that may carry prior notes plus vendor
    links. Non-URL text is HTML-escaped; URLs become anchors.
    """
    out: list[str] = []
    last = 0
    for m in _URL_RE.finditer(value):
        out.append(esc(value[last : m.start()]))
        url = m.group(0)
        out.append(render_link(url, url))
        last = m.end()
    out.append(esc(value[last:]))
    return "".join(out)


def render_source(value: str, repo_url: str, commit: str, prefix: str = "") -> str:
    """Render the ``source`` cell.

    * blank -> en-dash
    * external URL (incl. vendor links) -> preserved as a link
    * otherwise a source path -> commit-pinned GitHub blob link. ``prefix`` is
      the BOM file's directory relative to the repo root (e.g. ``hardware``),
      since source paths in bom.csv are written relative to the BOM file.
    """
    value = value.strip()
    if is_blank(value):
        return BLANK_DISPLAY
    if value.startswith("http://") or value.startswith("https://"):
        return render_link(value, value)
    repo_path = f"{prefix.strip('/')}/{value}" if prefix.strip("/") else value
    repo_path = posixpath.normpath(repo_path)
    href = github_blob_url(repo_url, commit, repo_path)
    return render_link(href, value)


def render_category_chip(code: str) -> str:
    code = code.strip().upper()
    label = label_for(code)
    bg = color_for(code)
    fg = text_color_for(bg)
    style = f"background:{bg};color:{fg}"
    # title -> mouse tooltip; aria-label -> screen readers; tabindex -> keyboard
    # focus; data-label -> CSS tooltip shown on hover AND focus.
    return (
        f'<span class="bom-cat" style="{style}" tabindex="0" '
        f'role="img" title="{esc(label)}" aria-label="Category: {esc(label)}" '
        f'data-label="{esc(label)}">{esc(code)}</span>'
    )


def render_cell(
    field: str, value: str, repo_url: str, commit: str, source_prefix: str = ""
) -> str:
    if field == "category":
        return render_category_chip(value) if not is_blank(value) else BLANK_DISPLAY
    if field == "source":
        return render_source(value, repo_url, commit, source_prefix)
    if field == "notes":
        return BLANK_DISPLAY if is_blank(value) else linkify(value)
    if is_blank(value):
        return BLANK_DISPLAY
    return esc(value)


# --- CSV loading & schema validation ------------------------------------------
def load_bom(bom_path: Path) -> list[dict[str, str]]:
    with bom_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(f"error: {bom_path} is empty")
        header = [h.strip() for h in header]
        if header != HEADERS:
            raise SystemExit(
                "error: BOM header does not match the canonical RAD BOM schema.\n"
                "This renderer must not change the schema -- fix hardware/bom.csv\n"
                f"  expected: {HEADERS}\n"
                f"  found:    {header}"
            )
        rows: list[dict[str, str]] = []
        for raw in reader:
            if not any(cell.strip() for cell in raw):
                continue  # skip blank lines
            if len(raw) != len(FIELDS):
                raise SystemExit(
                    f"error: row has {len(raw)} columns, expected {len(FIELDS)}:\n"
                    f"  {raw}"
                )
            rows.append(dict(zip(FIELDS, raw)))
    return rows


# --- Git helpers (deterministic auto-detection) -------------------------------
def git(repo_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_dir), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def detect_commit(repo_dir: Path, bom_path: Path) -> str:
    """Commit that last touched the BOM, so the pin only moves when data does."""
    sha = git(repo_dir, "log", "-n", "1", "--format=%H", "--", str(bom_path.resolve()))
    return sha or git(repo_dir, "rev-parse", "HEAD") or "HEAD"


def detect_released(repo_dir: Path, commit: str) -> bool:
    tags = git(repo_dir, "tag", "--contains", commit)
    return bool(tags)


# --- HTML assembly ------------------------------------------------------------
def render_table(
    rows: list[dict[str, str]], repo_url: str, commit: str, source_prefix: str = ""
) -> str:
    head_cells = "".join(
        f'      <th class="bom-col-{field}" scope="col">{esc(header)}</th>\n'
        for field, header in zip(FIELDS, HEADERS)
    )
    body_rows: list[str] = []
    for row in rows:
        cells: list[str] = []
        for field in FIELDS:
            classes = [f"bom-col-{field}"]
            if field in NUMERIC_FIELDS:
                classes.append("bom-num")
            raw = row.get(field, "")
            rendered = render_cell(field, raw, repo_url, commit, source_prefix)
            if field in CLAMP_FIELDS:
                # title carries the full value so the 2-line clamp never hides
                # information — hovering reveals anything truncated.
                title = "" if is_blank(raw) else f' title="{esc(raw.strip())}"'
                rendered = f'<div class="bom-clamp"{title}>{rendered}</div>'
            cells.append(f'      <td class="{" ".join(classes)}">{rendered}</td>')
        body_rows.append("    <tr>\n" + "\n".join(cells) + "\n    </tr>")
    body = "\n".join(body_rows)
    return (
        '<div class="bom-table-frame" role="region" aria-label="Bill of Materials table" tabindex="0">\n'
        '  <table class="bom-table">\n'
        "    <thead>\n    <tr>\n" + head_cells + "    </tr>\n    </thead>\n"
        "    <tbody>\n" + body + "\n    </tbody>\n"
        "  </table>\n"
        "</div>"
    )


def render_status(released: bool) -> str:
    if released:
        return (
            '<p class="bom-status bom-status-released">'
            "<strong>Released for production.</strong> This BOM corresponds to a "
            "tagged hardware release.</p>"
        )
    return (
        '<p class="bom-status bom-status-preview">'
        "<strong>Not a tagged release.</strong> This BOM is rendered from the "
        "current <code>main</code> and is preview / reference material, not a "
        "production release snapshot.</p>"
    )


def render_meta(repo_url: str, commit: str, released: bool) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    commit_url = f"{repo_url.rstrip('/')}/commit/{commit}"
    short = commit[:7]
    return (
        '<dl class="bom-meta">\n'
        f"  <dt>Repository</dt><dd>{render_link(repo_url, repo_name)}</dd>\n"
        f"  <dt>Source commit</dt><dd>{render_link(commit_url, short)} "
        f'<span class="bom-sha-full">({esc(commit)})</span></dd>\n'
        "</dl>\n" + render_status(released)
    )


def render_footer(repo_url: str, license_name: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    return (
        '<footer class="bom-footer">\n'
        "  <p>Bill of Materials generated from <code>hardware/bom.csv</code> by "
        "Research and Desire BOM tooling.</p>\n"
        f"  <p>License: {esc(license_name)}.</p>\n"
        f"  <p>Source: {render_link(repo_url, repo_name + ' on GitHub')}.</p>\n"
        "  <p>&copy; Research and Desire.</p>\n"
        "</footer>"
    )


def render_block(
    rows: list[dict[str, str]],
    repo_url: str,
    commit: str,
    released: bool,
    license_name: str,
    source_prefix: str = "",
) -> str:
    """The full generated content placed between the BOM markers."""
    parts = [
        BEGIN_MARKER,
        '<section class="bom" markdown="0">',
        render_meta(repo_url, commit, released),
        render_table(rows, repo_url, commit, source_prefix),
        render_footer(repo_url, license_name),
        "</section>",
        END_MARKER,
    ]
    return "\n".join(parts) + "\n"


def render_standalone(block: str, product: str) -> str:
    """A self-contained HTML document for release artifacts."""
    title = f"{esc(product)} - Bill of Materials"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{title}</title>\n"
        "  <style>\n" + standalone_css() + "  </style>\n"
        "</head>\n<body>\n"
        f"  <h1>{title}</h1>\n"
        + block
        + "</body>\n</html>\n"
    )


def standalone_css() -> str:
    """Minimal embedded CSS for the standalone artifact (no external deps)."""
    return """    body { font-family: system-ui, sans-serif; margin: 2rem; color: #1b1b1b; }
    .bom-table-frame { overflow-x: auto; border: 1px solid #d0d7de; border-radius: 6px; }
    table.bom-table { border-collapse: collapse; width: auto; font-size: 0.85rem; }
    .bom-table th, .bom-table td { border: 1px solid #d0d7de; padding: 4px 8px; vertical-align: top; text-align: left; }
    .bom-table thead th { background: #f0f3f6; position: sticky; top: 0; }
    .bom-num { text-align: right; white-space: nowrap; }
    .bom-col-description { max-width: 24rem; }
    .bom-col-source { max-width: 22rem; }
    .bom-col-notes { max-width: 20rem; }
    .bom-col-part_name { max-width: 14rem; }
    .bom-col-manufacturer, .bom-col-vendor { max-width: 11rem; }
    .bom-col-mfg_part_number, .bom-col-vendor_part_number { max-width: 12rem; }
    .bom-clamp { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow: hidden; white-space: normal; word-break: break-word; overflow-wrap: anywhere; }
    .bom-clamp[title] { cursor: help; }
    .bom-cat { display: inline-block; padding: 1px 8px; border-radius: 999px; font-weight: 700; font-size: 0.75rem; }
    .bom-status-preview { background: #fff3bf; padding: 8px 12px; border-radius: 6px; }
    .bom-status-released { background: #d3f9d8; padding: 8px 12px; border-radius: 6px; }
    .bom-footer { margin-top: 1.5rem; font-size: 0.8rem; color: #57606a; }
"""


# --- Page embedding -----------------------------------------------------------
def has_markers(page_text: str) -> bool:
    return BEGIN_MARKER in page_text and END_MARKER in page_text


def replace_block(page_text: str, block: str) -> str:
    if has_markers(page_text):
        pre = page_text.split(BEGIN_MARKER)[0]
        post = page_text.split(END_MARKER, 1)[1]
        return pre + block + post
    sep = "" if page_text.endswith("\n") else "\n"
    return page_text + sep + "\n" + block


def extract_block(page_text: str) -> str | None:
    if not has_markers(page_text):
        return None
    start = page_text.index(BEGIN_MARKER)
    end = page_text.index(END_MARKER) + len(END_MARKER)
    return page_text[start:end] + "\n"


# --- CLI ----------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render hardware/bom.csv to HTML BOM.")
    p.add_argument("--bom", required=True, type=Path, help="path to hardware/bom.csv")
    p.add_argument("--page", type=Path, help="assembly-docs bom.md to embed BOM into")
    p.add_argument("--standalone", type=Path, help="write a standalone bom.html here")
    p.add_argument("--repo-url", required=True, help="product GitHub repo URL")
    p.add_argument("--commit", help="source commit SHA (default: auto-detect from git)")
    p.add_argument("--product", default="Product", help="product display name")
    p.add_argument("--license", default="CERN-OHL-S v2", help="applicable license")
    p.add_argument(
        "--source-prefix",
        default="",
        help="repo-root-relative dir of the BOM file (e.g. 'hardware'); "
        "source paths in bom.csv are resolved relative to it for blob links",
    )
    rel = p.add_mutually_exclusive_group()
    rel.add_argument("--released", dest="released", action="store_true")
    rel.add_argument("--not-released", dest="released", action="store_false")
    p.set_defaults(released=None)
    p.add_argument(
        "--check",
        action="store_true",
        help="verify the embedded block is up to date; exit 1 if stale",
    )
    p.add_argument(
        "--require-markers",
        action="store_true",
        help="when embedding, skip (no-op + warn) if the page has no BOM markers",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    bom_path: Path = args.bom
    if not bom_path.exists():
        raise SystemExit(f"error: {bom_path} not found")

    repo_dir = bom_path.resolve().parent
    rows = load_bom(bom_path)

    # A header-only template has no data: skip embedding so we never blank out a
    # hand-written page before the BOM is populated.
    if not rows and args.page and not args.check:
        print(f"note: {bom_path} has no data rows yet — skipping BOM render")
        return 0

    commit = args.commit or detect_commit(repo_dir, bom_path)
    if args.released is None:
        released = detect_released(repo_dir, commit) if args.commit is None else False
    else:
        released = args.released

    block = render_block(
        rows, args.repo_url, commit, released, args.license, args.source_prefix
    )

    if args.standalone:
        args.standalone.parent.mkdir(parents=True, exist_ok=True)
        args.standalone.write_text(render_standalone(block, args.product), "utf-8")
        print(f"wrote standalone BOM -> {args.standalone}")

    if args.page:
        if not args.page.exists():
            raise SystemExit(f"error: page {args.page} not found")
        page_text = args.page.read_text("utf-8")

        if args.require_markers and not has_markers(page_text):
            print(
                f"note: {args.page} has no BOM markers — leaving page as-is. "
                "Add the markers where the BOM belongs to enable rendering:\n"
                f"  {BEGIN_MARKER}\n  {END_MARKER}"
            )
            return 0

        if args.check:
            current = extract_block(page_text)
            if current is None:
                print(
                    f"error: no generated BOM block found in {args.page}.",
                    file=sys.stderr,
                )
                return 1
            if current.strip() != block.strip():
                print(
                    f"error: generated BOM in {args.page} is STALE.\n"
                    "hardware/bom.csv (or the renderer) changed but the embedded\n"
                    "BOM was not regenerated. Re-run the BOM render and commit it.",
                    file=sys.stderr,
                )
                return 1
            print(f"ok: generated BOM in {args.page} is up to date")
            return 0

        new_text = replace_block(page_text, block)
        if new_text != page_text:
            args.page.write_text(new_text, "utf-8")
            print(f"embedded generated BOM block in {args.page}")
        else:
            print(f"generated BOM block already current in {args.page}")

    if not args.page and not args.standalone:
        sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
