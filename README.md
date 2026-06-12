# assembly-docs

RAD unified assembly docs — GitHub Pages now, `ohai.researchanddesire.com` at cutover.

Aggregates each hardware product's `assembly-docs/` folder into a single
MkDocs Material site, following the same architecture as
[dev-docs](https://github.com/researchanddesire/dev-docs).

## How it works

- Each product repo keeps its assembly package in `assembly-docs/` at the repo
  root: markdown pages, an `assets/` folder of images, and a `nav.yml`
  (`site_name` + `nav`) describing page order.
- `scripts/assemble-docs.sh` shallow-clones each product repo, copies
  `assembly-docs/` into `docs/{product}/`, and translates its `nav.yml` into a
  `.pages` file for `mkdocs-awesome-pages-plugin`.
- `.github/workflows/deploy.yml` assembles, builds, and deploys to GitHub
  Pages on:
  - pushes to `main` touching `docs/**`, `mkdocs.yml`, or `scripts/**`
  - `repository_dispatch` events of type `assembly-docs-rebuild`, sent by each
    product repo's `trigger-assembly-docs.yml` workflow when its
    `assembly-docs/**` changes
  - manual `workflow_dispatch`

## Products

| Product | Source repo | Site section |
| --- | --- | --- |
| Deepthroat Trainer | `DT_Trainer-OSS` | `docs/dtt/` |
| Lockbox | `Lockbox-OSS` | `docs/lockbox/` |
| OSSM | `ossm` | `docs/ossm/` |

Products whose repos don't yet have an `assembly-docs/` folder are skipped
with a warning at assemble time.

## Local development

```bash
pip install -r requirements.txt

# Assemble from local checkouts (skips cloning):
ASSEMBLE_LOCAL="$HOME/Github" ./scripts/assemble-docs.sh

mkdocs serve
```

Without `ASSEMBLE_LOCAL`, the script clones each repo: via a per-repo
read-only deploy key when `ASSEMBLE_SSH_DIR` contains one, via
`ASSEMBLE_GITHUB_TOKEN` if set, otherwise over anonymous HTTPS (sufficient
once the repos are public at cutover).

## Secrets

While the `*-OSS` forks are private, CI needs one read-only deploy key per
private repo, stored as repository secrets:

- `ASSEMBLE_SSH_KEY_DTT`
- `ASSEMBLE_SSH_KEY_LOCKBOX`
- `ASSEMBLE_SSH_KEY_OSSM` (only if `ossm` is private)

Each product repo's `trigger-assembly-docs.yml` needs a `DOCS_DISPATCH_TOKEN`
secret — a fine-grained PAT (or org secret) with `contents: write` on this
repo, since the default `GITHUB_TOKEN` cannot send cross-repo dispatches.

## Cutover

At OSS cutover, repoint the source repos via env vars in `deploy.yml`
(e.g. `LOCKBOX_REPO=Lockbox`), set `site_url` in `mkdocs.yml` to
`https://ohai.researchanddesire.com/`, and configure the custom domain in the
Pages settings.
