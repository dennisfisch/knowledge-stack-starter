#!/usr/bin/env bash
# Graphify rig — pinned, SHARED venv (built once per machine, reused by all worktrees).
#
# The venv lives OUTSIDE any worktree (default under ~/.local/share), so opening a new
# worktree per ticket does NOT rebuild it. Override with GRAPHIFY_VENV to pin a
# different graphify version for a specific repo.
#
# IMPORTANT (locked): Graphify NEVER reads an Anthropic/OpenAI token. Code extraction
# is purely local (tree-sitter AST, zero API). Semantic extraction is done by the HOST
# (Claude Code) via subagents on the subscription — no key. So we install NO provider
# SDKs, only the local engine + Leiden clustering (+ pyyaml for the wiki tools).
set -euo pipefail

GRAPHIFY_VERSION="0.8.49"          # pinned (v8 line); upgrade deliberately only
GRASPOLOGIC_VERSION="3.4.4"        # Leiden community detection — requires Python <3.13
VENV="${GRAPHIFY_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/knowledge-graphify/venv}"

# Prefer a Python <3.13 so graspologic installs and clustering uses Leiden (best
# quality) — even when the machine's default python3 is 3.13. Fall back to any python3:
# graphify then uses its built-in Louvain clustering instead (slightly lower quality,
# still works). Either way the graph + blast-radius are unaffected.
PYBIN=""; FALLBACK=""
for c in python3.12 python3.11 python3.10 python3; do
  command -v "$c" >/dev/null 2>&1 || continue
  FALLBACK="${FALLBACK:-$c}"
  if "$c" -c 'import sys; sys.exit(0 if sys.version_info[:2] < (3,13) else 1)' 2>/dev/null; then
    PYBIN="$c"; break
  fi
done
PYBIN="${PYBIN:-$FALLBACK}"
[ -n "$PYBIN" ] || { echo "setup-venv: no python3 found"; exit 1; }

mkdir -p "$(dirname "$VENV")"
"$PYBIN" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "graphifyy==${GRAPHIFY_VERSION}" pyyaml

if "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info[:2] < (3,13) else 1)'; then
  "$VENV/bin/pip" install --quiet "graspologic==${GRASPOLOGIC_VERSION}" \
    || echo "WARN: graspologic failed — clustering falls back to Louvain (still works)."
else
  echo "note: venv Python is $("$VENV/bin/python" -V 2>&1) (>=3.13) — skipping graspologic;"
  echo "      clustering uses graphify's built-in Louvain fallback (graph + blast-radius work)."
  echo "      For best-quality Leiden clustering, install python3.12 and re-run:"
  echo "      rm -rf '$VENV'; graphify/setup-venv.sh"
fi

echo "OK: graphify $("$VENV/bin/graphify" --version 2>/dev/null || echo '?') ($("$VENV/bin/python" -V 2>&1)) in $VENV"
echo "Run builds via:  graphify/run build.py …   (queries need no venv: python3 graphify/gquery.py …)"
