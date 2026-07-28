# AGENTS.md

Guidance for future agents working in the `assembly-docs` aggregator repo,
especially on BOM rendering.

## Ohai product inclusion is topic-gated

- The public Ohai assembly site includes product repos discovered under the
  `researchanddesire` org with the GitHub topic `ohai-assembly-docs`.
- Never include template repos or repos with unreplaced placeholders such as
  `PRODUCT_NAME`, `PRODUCT_REPO`, `PRODUCT_SLUG`, or `PRODUCT_LICENSE`.
- An Ohai-eligible product repo must have a real `assembly-docs/site.yml` with
  `slug`, `title`, `license`, and integer `nav_order`.
- Do not add the `ohai-assembly-docs` topic to a product repo until its
  assembly package has real metadata and local assembly/build checks pass.

## Product hardware source contract

Product repos use these hardware source folders:

- `hardware/cad/` for mechanical source files and release exports.
- `hardware/pcb/` for PCB source files, fabrication notes, and production
  exports.
- `hardware/cables/` for Wireviz harness source files.

Assembly docs should expose PCB and cable/harness source artifacts when they
exist. Do not treat `hardware/cables/` as OSSM-only.

## BOM rendering is assembly-docs only

The rendered HTML Bill of Materials belongs **only** in the product
**assembly-docs** site this repo builds (`ohai.researchanddesire.com`). Do
**not** add a rendered BOM page, table, or embed to developer docs (dev-docs /
product `developer-docs/`). Developer docs may *document* the BOM generation
workflow (see the README), but must not contain the rendered BOM itself.

## `hardware/bom.csv` is the source

- Each product repo's `hardware/bom.csv` is the single source of truth for BOM
  data and is **human-owned**.
- Rendering is **read-only**: `scripts/render_bom.py` never mutates
  `hardware/bom.csv`. It only writes the assembled copy of `bom.md` (and
  standalone `bom.html` release artifacts).

## Rendering happens at assemble time

- `scripts/assemble-docs.sh` clones each product repo and renders its
  `hardware/bom.csv` into the assembled `docs/{product}/bom.md` between stable
  markers. Because the block is generated at build time and never committed
  per-product, it cannot go stale.
- `docs/{dtt,lockbox,ossm,...}/` are **CI-assembled** — never hand-edit them.
- Product assembly must stage output first and only replace `docs/{product}/`
  after that product assembles successfully. If a product fails, warn and keep
  the existing published copy rather than deleting it.

## Generated BOM blocks use stable markers

- The renderer replaces only the content between
  `<!-- BEGIN GENERATED BOM -->` and `<!-- END GENERATED BOM -->`.
- A product's `assembly-docs/bom.md` must contain these markers where the BOM
  belongs. If they are absent, the renderer leaves the page untouched
  (`--require-markers`), so hand-written BOM pages are safe until migrated.
- A header-only `hardware/bom.csv` (no data rows) is skipped — the page is left
  as-is rather than blanked.

## The renderer must not change the BOM schema

- The canonical BOM schema (fixed 12-column header + closed category-code enum)
  is owned by `dev-docs` (`docs/meta/bom-standard.md` + `schemas/bom.schema.json`).
- `scripts/render_bom.py` **validates** the header and refuses to render a
  non-conforming BOM. It must also reject unknown category codes. Do not invent,
  rename, reorder, or drop fields.
- The category code → label → colour map lives in **one** reusable source,
  `scripts/bom_categories.py`. Chip colours are emitted inline from there; the
  matching structure/focus CSS lives in `docs/stylesheets/assembly.css`. Do not
  duplicate the colour map in CSS.

## Cable BOMs stay Wireviz-owned

- Product-level `hardware/bom.csv` lists cable harnesses as top-level assembly
  line items.
- A harness BOM `Source` should point to the Wireviz source, for example
  `cables/OSSM-Motor-Control-Harness.yml`, relative to `hardware/`.
- Detailed cable BOMs belong to Wireviz-generated output such as `.bom.tsv`
  artifacts. Link those artifacts from assembly docs; do not copy child cable
  BOM rows into the product-level BOM or rendered assembly prose.

## CI / triggers

- The site rebuilds via `.github/workflows/deploy.yml` (push to `docs/**`,
  `mkdocs.yml`, `scripts/**`; `repository_dispatch`; manual; scheduled).
- Product repos trigger a rebuild on `assembly-docs/**`, BOM CSVs,
  `hardware/pcb/**`, and `hardware/cables/**` changes via
  `templates/trigger-assembly-docs.yml`.
- On tagged product releases, `templates/generate-bom-release.yml` (caller) +
  `.github/workflows/bom-release.yml` (reusable) produce a standalone `bom.html`
  artifact when no committed `bom.html` exists.
- Output is deterministic (no timestamps, stable ordering).

## Do not auto-commit

Leave changes reviewable. Do not create commits unless explicitly asked.
