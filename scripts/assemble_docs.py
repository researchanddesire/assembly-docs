#!/usr/bin/env python3
"""Assemble topic-discovered product assembly docs into the MkDocs site."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WORK = ROOT / ".assemble-work"
ORG = os.environ.get("ASSEMBLE_GITHUB_ORG", "researchanddesire")
TOPIC = os.environ.get("ASSEMBLE_TOPIC", "ohai-assembly-docs")
PLACEHOLDERS = ("PRODUCT_NAME", "PRODUCT_REPO", "PRODUCT_SLUG", "PRODUCT_LICENSE")
REQUIRED_ASSEMBLY_FILES = (
    "site.yml",
    "nav.yml",
    "index.md",
    "pcb-overview.md",
    "cable-harnesses.md",
    "bom.md",
    "assembly-guide.md",
)
REQUIRED_HARDWARE_PATHS = (
    "hardware/bom.csv",
    "hardware/cad",
    "hardware/pcb",
    "hardware/cables",
)


@dataclass
class Product:
    repo: str
    branch: str
    root: Path
    source: Path
    slug: str
    title: str
    license: str
    nav_order: int
    url: str


class AssemblyWarning(RuntimeError):
    """Warning-level assembly issue for a single product."""


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise AssemblyWarning(detail or f"command failed: {' '.join(cmd)}")
    return proc.stdout.strip()


def parse_flat_yaml(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("'\"")
        data[key.strip()] = value
    return data


def has_placeholder(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(marker in text for marker in PLACEHOLDERS)


def read_site(product_root: Path) -> dict[str, str]:
    site = product_root / "assembly-docs" / "site.yml"
    if not site.exists():
        raise AssemblyWarning("missing assembly-docs/site.yml")
    if has_placeholder(site):
        raise AssemblyWarning("assembly-docs/site.yml still contains template placeholders")
    data = parse_flat_yaml(site)
    missing = [key for key in ("slug", "title", "license", "nav_order") if not data.get(key)]
    if missing:
        raise AssemblyWarning(f"assembly-docs/site.yml missing required keys: {', '.join(missing)}")
    try:
        int(data["nav_order"])
    except ValueError as exc:
        raise AssemblyWarning("assembly-docs/site.yml nav_order must be an integer") from exc
    return data


def validate_product_root(product_root: Path) -> None:
    assembly = product_root / "assembly-docs"
    if not assembly.is_dir():
        raise AssemblyWarning("missing assembly-docs/")
    for name in REQUIRED_ASSEMBLY_FILES:
        path = assembly / name
        if not path.is_file():
            raise AssemblyWarning(f"missing assembly-docs/{name}")
        if has_placeholder(path):
            raise AssemblyWarning(f"assembly-docs/{name} still contains template placeholders")

    nav = assembly / "nav.yml"
    if not any(line.startswith("site_name:") for line in nav.read_text(encoding="utf-8").splitlines()):
        raise AssemblyWarning("assembly-docs/nav.yml must include site_name")

    for rel in REQUIRED_HARDWARE_PATHS:
        path = product_root / rel
        if not path.exists():
            raise AssemblyWarning(f"missing {rel}")

    trigger = product_root / ".github" / "workflows" / "trigger-assembly-docs.yml"
    if not trigger.is_file():
        raise AssemblyWarning("missing .github/workflows/trigger-assembly-docs.yml")


def product_from_root(repo: str, branch: str, product_root: Path, url: str) -> Product:
    validate_product_root(product_root)
    site = read_site(product_root)
    return Product(
        repo=repo,
        branch=branch,
        root=product_root,
        source=product_root / "assembly-docs",
        slug=site["slug"],
        title=site["title"],
        license=site["license"],
        nav_order=int(site["nav_order"]),
        url=url,
    )


def detect_branch(product_root: Path) -> str:
    try:
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=product_root)
    except AssemblyWarning:
        return "main"
    return branch if branch and branch != "HEAD" else "main"


def discover_local() -> tuple[list[Product], list[str]]:
    base = os.environ.get("ASSEMBLE_LOCAL")
    if not base:
        return [], []
    products: list[Product] = []
    warnings: list[str] = []
    for assembly in sorted(Path(base).glob("*/assembly-docs/site.yml")):
        product_root = assembly.parent.parent
        repo = product_root.name
        branch = detect_branch(product_root)
        url = f"https://github.com/{ORG}/{repo}"
        try:
            product = product_from_root(repo, branch, product_root, url)
        except AssemblyWarning as exc:
            if "placeholder" in str(exc):
                continue
            warnings.append(f"{repo}: skipped local candidate: {exc}")
            continue
        products.append(product)
    return sorted_products(products), warnings


def github_token() -> str:
    return os.environ.get("ASSEMBLE_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def github_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "assembly-docs-assembler",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_remote() -> tuple[list[Product], list[str]]:
    if not github_token():
        return [], [
            "ASSEMBLE_GITHUB_TOKEN is not set; skipped remote topic discovery "
            "to avoid assembling only public products"
        ]
    query = urllib.parse.quote(f"org:{ORG} topic:{TOPIC} archived:false")
    url = f"https://api.github.com/search/repositories?q={query}&per_page=100"
    try:
        payload = github_json(url)
    except Exception as exc:  # noqa: BLE001
        return [], [f"remote discovery failed for topic {TOPIC}: {exc}"]

    products: list[Product] = []
    warnings: list[str] = []
    for repo in sorted(payload.get("items", []), key=lambda item: item.get("name", "")):
        name = repo["name"]
        branch = repo.get("default_branch") or "main"
        try:
            product_root = clone_repo(name, branch, repo)
            product = product_from_root(name, branch, product_root, repo["html_url"])
        except AssemblyWarning as exc:
            warnings.append(f"{name}: skipped discovered repo: {exc}")
            continue
        products.append(product)
    return sorted_products(products), warnings


def clone_repo(name: str, branch: str, repo_payload: dict) -> Path:
    target = WORK / "repos" / name
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    key = Path(os.environ.get("ASSEMBLE_SSH_DIR", "")) / name
    if key.is_file() and key.stat().st_size > 0:
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i '{key}' -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        )
        url = f"git@github.com:{ORG}/{name}.git"
        run(["git", "clone", "--depth", "1", "--branch", branch, url, str(target)], env=env)
        return target

    url = repo_payload.get("clone_url") or f"https://github.com/{ORG}/{name}.git"
    token = github_token()
    if token and url.startswith("https://github.com/"):
        url = url.replace("https://github.com/", f"https://x-access-token:{token}@github.com/", 1)
    run(["git", "clone", "--depth", "1", "--branch", branch, url, str(target)])
    return target


def sorted_products(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda product: (product.nav_order, product.title.lower(), product.slug))


def translate_nav(source_nav: Path, dest_pages: Path) -> None:
    text = source_nav.read_text(encoding="utf-8")
    lines = ["title:" + line.split(":", 1)[1] if line.startswith("site_name:") else line for line in text.splitlines()]
    dest_pages.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_bom(product: Product, dest: Path) -> None:
    bom = product.root / "hardware" / "bom.csv"
    page = dest / "bom.md"
    if not bom.is_file():
        raise AssemblyWarning("missing hardware/bom.csv")
    if not page.is_file():
        raise AssemblyWarning("missing assembly-docs/bom.md")
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "render_bom.py"),
        "--bom",
        str(bom),
        "--page",
        str(page),
        "--repo-url",
        product.url,
        "--product",
        product.title,
        "--license",
        product.license,
        "--source-prefix",
        "hardware",
        "--require-markers",
    ]
    log(run(cmd))


def split_pcb(dest: Path) -> None:
    log(run([sys.executable, str(ROOT / "scripts" / "split_pcb_design_assets.py"), "--dest", str(dest)]))


def insert_kicanvas(product: Product, dest: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "insert_kicanvas_pcb.py"),
        "--page",
        str(dest / "pcb-overview.md"),
        "--pcb-dir",
        str(product.root / "hardware" / "pcb"),
        "--asset-dir",
        str(dest / "assets" / "kicanvas"),
    ]
    log(run(cmd))


def rewrite_links(product: Product, dest: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "rewrite_product_links.py"),
        str(dest),
        product.repo,
        product.branch,
    ]
    output = run(cmd)
    if output:
        log(output)


def assemble_product(product: Product, stage_root: Path) -> Path:
    stage_dest = stage_root / product.slug
    if stage_dest.exists():
        shutil.rmtree(stage_dest)
    shutil.copytree(product.source, stage_dest)
    nav = stage_dest / "nav.yml"
    if nav.exists():
        translate_nav(nav, stage_dest / ".pages")
        nav.unlink()
    (stage_dest / "site.yml").unlink(missing_ok=True)
    render_bom(product, stage_dest)
    split_pcb(stage_dest)
    insert_kicanvas(product, stage_dest)
    rewrite_links(product, stage_dest)
    return stage_dest


def publish_product(product: Product, stage_dest: Path) -> None:
    dest = DOCS / product.slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(stage_dest), str(dest))


def generate_top_level(products: list[Product]) -> None:
    if not products:
        return
    nav_lines = ["nav:", "  - index.md"]
    if (DOCS / "how-this-site-works.md").exists():
        nav_lines.append("  - How This Site Works: how-this-site-works.md")
    for product in products:
        nav_lines.append(f"  - {product.slug}")
    (DOCS / ".pages").write_text("\n".join(nav_lines) + "\n", encoding="utf-8")

    product_lines = "\n".join(
        f"- **{product.title.replace(' Assembly Docs', '')}** — assembled from "
        f"`{product.repo}/assembly-docs/`"
        for product in products
    )
    text = f"""# Research and Desire - Assembly Docs

Unified assembly documentation for Research and Desire hardware products.

Each product's assembly package (bill of materials, assembly guide, cable
harness notes, PCB overview, and supporting images) is maintained in its own
repository under `assembly-docs/` and assembled into this site automatically on
every update.

## Products

{product_lines}

## Contributing

To change a product's assembly docs, edit the `assembly-docs/` folder in that
product's repository. Cross-product pages like this one live in this repository.

For the full assembly pipeline, CI flow, BOM rendering rules, and contribution
boundaries, see [How This Site Works](how-this-site-works.md).
"""
    (DOCS / "index.md").write_text(text, encoding="utf-8")


def write_summary(successes: list[Product], warnings: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["## Assembly docs product assembly", ""]
    if successes:
        lines.extend(["### Published products", ""])
        lines.extend(f"- `{product.slug}` from `{product.repo}`" for product in successes)
        lines.append("")
    if warnings:
        lines.extend(["### Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    text = "\n".join(lines)
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    log(text)


def discover_products() -> tuple[list[Product], list[str]]:
    local_products, local_warnings = discover_local()
    if local_products:
        return local_products, local_warnings
    remote_products, remote_warnings = discover_remote()
    return remote_products, local_warnings + remote_warnings


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    products, warnings = discover_products()
    if not products:
        warnings.append(f"no products discovered with topic {TOPIC}; leaving existing product docs/nav untouched")
        write_summary([], warnings)
        return 0

    published: list[Product] = []
    with tempfile.TemporaryDirectory(prefix="assembly-docs-stage-") as tmp:
        stage_root = Path(tmp)
        for product in products:
            log(f"Assembling {product.repo}@{product.branch} -> docs/{product.slug}")
            try:
                stage_dest = assemble_product(product, stage_root)
                publish_product(product, stage_dest)
            except AssemblyWarning as exc:
                warnings.append(f"{product.repo}: {exc}")
                if (DOCS / product.slug).exists():
                    published.append(product)
                continue
            published.append(product)

    generate_top_level(published)
    write_summary(published, warnings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
