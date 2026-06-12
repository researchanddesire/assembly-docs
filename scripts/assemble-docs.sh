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
  mkdir -p "$dest"
  cp -R "$src/." "$dest/"
  # Translate the product's nav.yml (site_name + nav) into an awesome-pages
  # .pages file (title + nav), then drop nav.yml from the built site.
  if [ -f "$dest/nav.yml" ]; then
    sed 's/^site_name:/title:/' "$dest/nav.yml" > "$dest/.pages"
    rm -f "$dest/nav.yml"
  fi
}

clone_or_copy() {
  local repo=$1
  local branch=${2:-main}
  local dest=$3
  if [ -n "${ASSEMBLE_LOCAL:-}" ] && [ -d "${ASSEMBLE_LOCAL}/${repo}/assembly-docs" ]; then
    echo "Using local ${ASSEMBLE_LOCAL}/${repo}/assembly-docs"
    copy_assembly_docs "${ASSEMBLE_LOCAL}/${repo}/assembly-docs" "$dest"
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
    copy_assembly_docs "$WORK/$repo/assembly-docs" "$dest"
  else
    echo "WARN: no assembly-docs/ in ${repo} — skipping"
  fi
}

LOCKBOX_REPO="${LOCKBOX_REPO:-Lockbox-OSS}"
DTT_REPO="${DTT_REPO:-DT_Trainer-OSS}"
OSSM_REPO="${OSSM_REPO:-ossm}"

# During OSS prep, assemble from the *-OSS forks. At cutover, set
# LOCKBOX_REPO=Lockbox etc. to point at the canonical public repos.
LOCKBOX_BRANCH="${LOCKBOX_BRANCH:-main}"
DTT_BRANCH="${DTT_BRANCH:-main}"
OSSM_BRANCH="${OSSM_BRANCH:-main}"

clone_or_copy "$DTT_REPO" "$DTT_BRANCH" "${ROOT}/docs/dtt"
clone_or_copy "$LOCKBOX_REPO" "$LOCKBOX_BRANCH" "${ROOT}/docs/lockbox"
clone_or_copy "$OSSM_REPO" "$OSSM_BRANCH" "${ROOT}/docs/ossm"

echo "Assembled product assembly docs into docs/{dtt,lockbox,ossm}"
