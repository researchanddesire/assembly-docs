# assembly-docs

RAD unified assembly docs — GitHub Pages now, `ohai.researchanddesire.com` at cutover.

Aggregates each hardware product's `assembly-docs/` folder into a single
MkDocs Material site, following the same architecture as
[dev-docs](https://github.com/researchanddesire/dev-docs).

## How it works

- Each Ohai product repo opts in with the GitHub topic `ohai-assembly-docs` and
  keeps its assembly package in `assembly-docs/` at the repo root: markdown
  pages, an `assets/` folder of images, `site.yml` metadata, and a `nav.yml`
  (`site_name` + `nav`) describing page order.
- `scripts/assemble-docs.sh` discovers eligible product repos, shallow-clones
  them, stages each `assembly-docs/` package, and replaces `docs/{product}/`
  only after that product assembles successfully.
- `.github/workflows/deploy.yml` assembles, builds, and deploys to GitHub
  Pages on:
  - pushes to `main` touching `docs/**`, `mkdocs.yml`, or `scripts/**`
  - `repository_dispatch` events of type `assembly-docs-rebuild`, sent by each
    product repo's `trigger-assembly-docs.yml` workflow when its
    `assembly-docs/**`, BOM, PCB, or cable-source changes
  - manual `workflow_dispatch`

## Products

Products are discovered from non-archived `researchanddesire/*` repositories
with the `ohai-assembly-docs` topic and valid `assembly-docs/site.yml`
metadata. Template repos and repos with unreplaced placeholders are skipped.

Products whose repos don't yet have an `assembly-docs/` folder are skipped
with a warning at assemble time.

## Local development

```bash
pip install -r requirements.txt

# Assemble from local checkouts (skips cloning):
ASSEMBLE_LOCAL="$HOME/Github" ./scripts/assemble-docs.sh

mkdocs serve
```

Without `ASSEMBLE_LOCAL`, the script discovers topic-tagged repos through the
GitHub API and clones them: via a per-repo read-only deploy key when
`ASSEMBLE_SSH_DIR` contains one, via `ASSEMBLE_GITHUB_TOKEN` if set, otherwise
over anonymous HTTPS (sufficient once the repos are public at cutover).

## Secrets

While product repos are private, CI needs an `ASSEMBLE_GITHUB_TOKEN` secret with
read access to the product repos so discovery can see topic-tagged private
repos. Per-repo read-only deploy keys are still supported as a transition path.

Each product repo's `trigger-assembly-docs.yml` needs a `DOCS_DISPATCH_TOKEN`
secret — a fine-grained PAT (or org secret) with `contents: write` on this
repo, since the default `GITHUB_TOKEN` cannot send cross-repo dispatches.

## Bill of Materials rendering

Each product's `hardware/bom.csv` is rendered into a polished, colour-coded HTML
Bill of Materials and embedded in that product's assembly-docs `bom.md` page.
The rendered BOM belongs to the **assembly docs only** — never to developer
docs. (Developer docs may document this workflow, as here, but must not embed
the rendered BOM.)

### Where things live

| Thing | Path |
| ----- | ---- |
| BOM data (source of truth, per product repo) | `hardware/bom.csv` |
| Renderer | `scripts/render_bom.py` |
| Category code → label → colour map (single source) | `scripts/bom_categories.py` |
| Chip / table structure + focus styles | `docs/stylesheets/assembly.css` |
| BOM page (per product repo, carries the markers) | `assembly-docs/bom.md` |
| Generated block markers | `<!-- BEGIN GENERATED BOM -->` … `<!-- END GENERATED BOM -->` |
| PCB page / KiCanvas viewer assembly | `scripts/split_pcb_design_assets.py` + `scripts/insert_kicanvas_pcb.py` |
| Cable harness source files | Product repo `hardware/cables/` |

The renderer is **read-only** on `hardware/bom.csv` and validates its header
against the canonical [BOM schema](https://dev.researchanddesire.com/meta/bom-standard/)
(`dev-docs`); it never changes the schema.

### How it runs

Rendering happens **at assemble time**, so the embedded block is never committed
per-product and can never go stale:

- `scripts/assemble-docs.sh` clones each product repo and, for each, renders
  `hardware/bom.csv` into the assembled `docs/{product}/bom.md` between the
  markers. Commit SHA (used for commit-pinned source links) and release status
  are auto-detected from the product checkout's git.
- Product assembly packages carry `pcb-overview.md` and `cable-harnesses.md`.
  Legacy `## PCB design assets` sections from BOM pages are still moved into the
  standalone PCB page during assembly for migration safety.
- If `hardware/pcb/` contains KiCad board files (`**/*.kicad_pcb`), assembly
  copies those board files into the assembled site, preserving their relative
  subfolders, and embeds KiCanvas viewer previews. Non-KiCad PCB sources get
  the standalone page without a KiCanvas render.
- If a product's `bom.md` has no markers, or its `bom.csv` is a header-only
  template, the page is left untouched.
- Cable harnesses are product-level BOM assemblies. Detailed child cable BOMs
  belong to Wireviz-generated artifacts such as `.bom.tsv`, linked from the
  assembly cable page.

A self-contained **Lockbox BOM demo** (`demo/lockbox/`) validates the workflow
end-to-end without depending on a cloned repo or fabricating real product data.
Disable it with `ASSEMBLE_BOM_DEMO=0`.

### Run it locally

```bash
pip install -r requirements.txt

# Render the demo BOM into the assembled site and preview:
ASSEMBLE_LOCAL="$HOME/Github" ./scripts/assemble-docs.sh
mkdocs serve

# Render a single product's BOM into a page directly (read-only on the CSV):
python3 scripts/render_bom.py \
  --bom path/to/hardware/bom.csv \
  --page path/to/assembly-docs/bom.md \
  --repo-url https://github.com/researchanddesire/Lockbox \
  --require-markers
```

### When CI runs

- The site rebuilds when a product repo's `assembly-docs/**`, BOM CSVs,
  `hardware/pcb/**`, or `hardware/cables/**` changes
  (`templates/trigger-assembly-docs.yml` →
  `repository_dispatch` → `deploy.yml`), and on pushes to this repo's
  `docs/**` / `mkdocs.yml` / `scripts/**`.
- On a tagged product release, `templates/generate-bom-release.yml` (a caller in
  the product repo) invokes the reusable `.github/workflows/bom-release.yml`
  here, which renders a standalone `bom.html` and publishes it as a GitHub
  Actions artifact + Release asset — unless the repo already commits a
  `bom.html`.

### Troubleshooting

- **Page didn't update:** confirm `assembly-docs/bom.md` has both markers and
  that `hardware/bom.csv` has data rows (a header-only template is skipped).
- **`BOM header does not match the canonical RAD BOM schema`:** the CSV header
  drifted; fix `hardware/bom.csv` to match the 12-column schema exactly. The
  renderer will not change the schema.

## Cutover

At OSS cutover, add the `ohai-assembly-docs` topic to the canonical public
product repos, remove it from superseded private forks, set `site_url` in
`mkdocs.yml` to `https://ohai.researchanddesire.com/`, and configure the custom
domain in the Pages settings.
