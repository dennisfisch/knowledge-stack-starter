#!/usr/bin/env bash
# Graphify rig — pinned venv, reproducible, never `latest`.
#
# IMPORTANT (locked): Graphify NEVER reads an Anthropic/OpenAI token. Code
# extraction is purely local (tree-sitter AST, zero API). Semantic extraction is
# done by the HOST (Claude Code) via subagents on the Claude Max subscription — no
# key. So we install NO provider SDKs, only the local engine + Leiden clustering.
set -euo pipefail

GRAPHIFY_VERSION="0.8.49"          # pinned (v8 line); upgrade deliberately only
GRASPOLOGIC_VERSION="3.4.4"        # Leiden community detection (Python <3.13)
VENV="$(cd "$(dirname "$0")" && pwd)/.venv"

python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
# Engine pinned (purely local, reads NO provider key). graspologic separately —
# graphifyy ships no extra for it; without graspologic, use --no-cluster only.
"$VENV/bin/pip" install --quiet "graphifyy==${GRAPHIFY_VERSION}"
"$VENV/bin/pip" install --quiet "graspologic==${GRASPOLOGIC_VERSION}" \
  || echo "WARN: graspologic not installed — clustering only via --no-cluster."

echo "OK: graphify $("$VENV/bin/graphify" --version 2>/dev/null || echo '?') in $VENV"
