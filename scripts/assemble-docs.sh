#!/usr/bin/env bash
# Assemble topic-discovered product assembly-docs into docs/{product}/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "${ROOT}/scripts/assemble_docs.py"
