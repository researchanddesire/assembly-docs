#!/usr/bin/env bash
# Assemble product assembly-docs into docs/{product}/ for unified MkDocs build.
#
# Unlike dev-docs (developer-docs/docs/ + .pages), assembly docs live directly
# in each product repo's assembly-docs/ folder alongside an assets/ directory
# and a nav.yml (site_name + nav). We copy the whole folder and translate
# nav.yml into a .pages file for mkdocs-awesome-pages-plugin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${ROOT}/.assemble-work"
rm -rf "$WORK"
mkdir -p "$WORK"

copy_assembly_docs() {
  local src=$1
  local dest=$2
  local repo=$3
  local branch=$4
  mkdir -p "$dest"
  cp -R "$src/." "$dest/"
  # Translate the product's nav.yml (site_name + nav) into an awesome-pages
  # .pages file (title + nav), then drop nav.yml from the built site.
  if [ -f "$dest/nav.yml" ]; then
    sed 's/^site_name:/title:/' "$dest/nav.yml" > "$dest/.pages"
    rm -f "$dest/nav.yml"
  fi
  # Render the product's hardware/bom.csv into its bom.md (read-only on the CSV;
  # writes only the copied page between the BOM markers). See render_bom_into.
  render_bom_into "$src" "$dest" "$repo"
  # Repo-relative links (../hardware/...) only work inside the product repo.
  # Rewrite them to GitHub tree/blob URLs for the unified site.
  python3 "${ROOT}/scripts/rewrite_product_links.py" "$dest" "$repo" "$branch"
}

# Render a product's hardware/bom.csv into the copied bom.md, between the
# stable BOM markers. Safe by design:
#   * no hardware/bom.csv          -> skip (warn)
#   * no bom.md                    -> skip (warn)
#   * bom.md has no BOM markers    -> leave the page as-is (--require-markers)
#   * bom.csv is a header template -> skip (renderer no-ops on empty data)
# The CSV is never modified; only the assembled copy of bom.md is written.
render_bom_into() {
  local src=$1
  local dest=$2
  local repo=$3
  local bom page product license
  bom="$(cd "$src/.." && pwd)/hardware/bom.csv"
  page="$dest/bom.md"
  if [ ! -f "$bom" ]; then
    echo "note: no hardware/bom.csv in ${repo} — skipping BOM render"
    return
  fi
  if [ ! -f "$page" ]; then
    echo "note: no bom.md in ${repo}/assembly-docs — skipping BOM render"
    return
  fi
  product="$(sed -n 's/^title:[[:space:]]*//p' "$dest/.pages" 2>/dev/null | head -1)"
  [ -z "$product" ] && product="$repo"
  case "$repo" in
    Lockbox*|DT_Trainer*) license="CERN-OHL-S v2 (hardware) / MPL-2.0 (firmware)" ;;
    *) license="CERN-OHL-S v2" ;;
  esac
  # Commit + release status auto-detected from the product checkout's git.
  # source paths in bom.csv are written relative to hardware/ (where the BOM
  # lives), so resolve commit-pinned links against that prefix.
  python3 "${ROOT}/scripts/render_bom.py" \
    --bom "$bom" --page "$page" \
    --repo-url "https://github.com/researchanddesire/${repo}" \
    --product "$product" --license "$license" \
    --source-prefix hardware \
    --require-markers
}

# Self-contained synthetic BOM rendering demo. The real Lockbox BOM now renders
# from researchanddesire/Lockbox-OSS, so this fixture is off by default and kept
# only as a standalone validation target. Enable with ASSEMBLE_BOM_DEMO=1.
assemble_demo() {
  local name=$1
  local src_root=$2
  local dest="${ROOT}/docs/${name}"
  echo "Assembling BOM demo -> docs/${name}"
  mkdir -p "$dest"
  cp -R "${src_root}/assembly-docs/." "$dest/"
  if [ -f "$dest/nav.yml" ]; then
    sed 's/^site_name:/title:/' "$dest/nav.yml" > "$dest/.pages"
    rm -f "$dest/nav.yml"
  fi
  # Pinned commit + not-released so the demo output is deterministic and shows
  # the preview/reference banner.
  python3 "${ROOT}/scripts/render_bom.py" \
    --bom "${src_root}/hardware/bom.csv" --page "$dest/bom.md" \
    --repo-url "https://github.com/researchanddesire/Lockbox" \
    --commit 7f3c1a9e2b4d6f8a0c2e4b6d8f0a1c3e5d7b9f10 --not-released \
    --product "Chastity Lockbox (BOM demo)" \
    --license "CERN-OHL-S v2 (hardware) / MPL-2.0 (firmware)" \
    --source-prefix hardware
}

clone_or_copy() {
  local repo=$1
  local branch=${2:-main}
  local dest=$3
  if [ -n "${ASSEMBLE_LOCAL:-}" ] && [ -d "${ASSEMBLE_LOCAL}/${repo}" ]; then
    if [ -d "${ASSEMBLE_LOCAL}/${repo}/assembly-docs" ]; then
      echo "Using local ${ASSEMBLE_LOCAL}/${repo}/assembly-docs"
      copy_assembly_docs "${ASSEMBLE_LOCAL}/${repo}/assembly-docs" "$dest" "$repo" "$branch"
    else
      echo "WARN: no assembly-docs/ in local ${repo} — skipping"
    fi
    return
  fi
  echo "Cloning researchanddesire/${repo}@${branch}"
  # Preferred: per-repo read-only deploy key (SSH). The CI workflow writes one
  # key file per repo into ASSEMBLE_SSH_DIR. Falls back to a token, then to
  # anonymous HTTPS (works once repos are public at cutover).
  local key="${ASSEMBLE_SSH_DIR:-}/${repo}"
  if [ -n "${ASSEMBLE_SSH_DIR:-}" ] && [ -s "$key" ]; then
    GIT_SSH_COMMAND="ssh -i '$key' -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
      git clone --depth 1 --branch "$branch" "git@github.com:researchanddesire/${repo}.git" "$WORK/$repo"
  else
    local clone_url="https://github.com/researchanddesire/${repo}.git"
    if [ -n "${ASSEMBLE_GITHUB_TOKEN:-}" ]; then
      clone_url="https://x-access-token:${ASSEMBLE_GITHUB_TOKEN}@github.com/researchanddesire/${repo}.git"
    fi
    git clone --depth 1 --branch "$branch" "$clone_url" "$WORK/$repo"
  fi
  if [ -d "$WORK/$repo/assembly-docs" ]; then
    copy_assembly_docs "$WORK/$repo/assembly-docs" "$dest" "$repo" "$branch"
  else
    echo "WARN: no assembly-docs/ in ${repo} — skipping"
  fi
}

LOCKBOX_REPO="${LOCKBOX_REPO:-Lockbox-OSS}"
DTT_REPO="${DTT_REPO:-DT_Trainer-OSS}"
RADR_REPO="${RADR_REPO:-RADR-OSS}"
OSSM_REPO="${OSSM_REPO:-ossm}"

# During OSS prep, assemble from the *-OSS forks. At cutover, set
# LOCKBOX_REPO=Lockbox etc. to point at the canonical public repos.
LOCKBOX_BRANCH="${LOCKBOX_BRANCH:-main}"
DTT_BRANCH="${DTT_BRANCH:-main}"
RADR_BRANCH="${RADR_BRANCH:-main}"
OSSM_BRANCH="${OSSM_BRANCH:-main}"

clone_or_copy "$DTT_REPO" "$DTT_BRANCH" "${ROOT}/docs/dtt"
clone_or_copy "$LOCKBOX_REPO" "$LOCKBOX_BRANCH" "${ROOT}/docs/lockbox"
clone_or_copy "$RADR_REPO" "$RADR_BRANCH" "${ROOT}/docs/radr"
clone_or_copy "$OSSM_REPO" "$OSSM_BRANCH" "${ROOT}/docs/ossm"

if [ "${ASSEMBLE_BOM_DEMO:-0}" = "1" ]; then
  assemble_demo "lockbox-demo" "${ROOT}/demo/lockbox"
fi

echo "Assembled product assembly docs into docs/{dtt,lockbox,radr,ossm}"
