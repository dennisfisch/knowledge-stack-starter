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
GRASPOLOGIC_VERSION="3.4.4"        # Leiden community detection (Python <3.13)
VENV="${GRAPHIFY_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/knowledge-graphify/venv}"

mkdir -p "$(dirname "$VENV")"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "graphifyy==${GRAPHIFY_VERSION}" pyyaml
"$VENV/bin/pip" install --quiet "graspologic==${GRASPOLOGIC_VERSION}" \
  || echo "WARN: graspologic not installed — clustering only via --no-cluster."

echo "OK: graphify $("$VENV/bin/graphify" --version 2>/dev/null || echo '?') in $VENV"
echo "Run builds via:  graphify/run build.py …   (queries need no venv: python3 graphify/gquery.py …)"
