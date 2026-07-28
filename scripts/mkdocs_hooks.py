"""MkDocs hooks for assembled assembly-docs."""

from __future__ import annotations

import re

H2_SPLIT_RE = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.IGNORECASE | re.DOTALL)
OL_RE = re.compile(r"<ol(?![^>]*\sstart=)([^>]*)>(.*?)</ol>", re.IGNORECASE | re.DOTALL)


def on_page_content(html: str, *, page, config, files) -> str:  # noqa: ARG001
    if page.file.src_path.endswith("assembly-guide.md"):
        return fix_section_numbering(html)
    return html


def fix_section_numbering(html: str) -> str:
    parts = H2_SPLIT_RE.split(html)
    if len(parts) == 1:
        return html

    out: list[str] = []
    for part in parts:
        if part.lower().startswith("<h2"):
            out.append(part)
            continue
        out.append(renumber_ols(part))
    return "".join(out)


def renumber_ols(section_html: str) -> str:
    start = 1

    def repl(match: re.Match[str]) -> str:
        nonlocal start
        attrs = match.group(1)
        body = match.group(2)
        item_count = count_top_level_items(body)
        rendered = f'<ol start="{start}"{attrs}>{body}</ol>'
        start += item_count
        return rendered

    return OL_RE.sub(repl, section_html)


def count_top_level_items(ol_body: str) -> int:
    """Count only direct <li> children; ignore nested list items."""
    cleaned = re.sub(r"<ul\b.*?</ul>", "", ol_body, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<ol\b.*?</ol>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return len(re.findall(r"<li\b", cleaned, flags=re.IGNORECASE))
