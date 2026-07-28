#!/usr/bin/env python3
"""Rewrite repo-relative links in assembled assembly-docs to GitHub URLs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\((\.\./|\./)([^)]+)\)")


def normalize_path(raw: str) -> str:
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def github_url(org: str, repo: str, branch: str, path: str) -> str:
    path = normalize_path(path)
    name = path.rstrip("/").split("/")[-1]
    is_dir = path.endswith("/") or "." not in name
    kind = "tree" if is_dir else "blob"
    return f"https://github.com/{org}/{repo}/{kind}/{branch}/{path}"


def rewrite_text(text: str, org: str, repo: str, branch: str) -> str:
    def repl(match: re.Match[str]) -> str:
        rel = match.group(1) + match.group(2)
        return f"]({github_url(org, repo, branch, rel)})"

    return LINK_RE.sub(repl, text)


def rewrite_dir(dest: Path, org: str, repo: str, branch: str) -> None:
    for path in dest.rglob("*.md"):
        original = path.read_text(encoding="utf-8")
        updated = rewrite_text(original, org, repo, branch)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"Rewrote repo links in {path.relative_to(dest.parent)}")


def main() -> None:
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} DEST REPO BRANCH", file=sys.stderr)
        sys.exit(1)

    dest = Path(sys.argv[1])
    rewrite_dir(dest, "researchanddesire", sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
