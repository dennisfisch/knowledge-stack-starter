---
name: code-graph
description: >
  Query this repo's Graphify code graph (graphify-out/) to answer questions about
  architecture, relationships, call paths, and blast-radius — including which wiki
  units/decisions a code change affects — BEFORE grepping or reading raw files.
  Also (re)builds the graph when it is missing or stale. The graph is repo-local
  and bridged to the wiki via deterministic source anchors.
---

# /code-graph — read the code graph first

This repo has a deterministic, queryable graph of its code + bridged wiki units
under `graphify-out/`. For questions about **architecture, relationships, call
paths, or blast-radius**, query the graph FIRST, then read the few relevant source
files. Don't blind-grep.

## Read (no LLM, no token — pure graph traversal)

```bash
# What is connected to X (code symbol OR wiki slug), incl. affected wiki units:
python3 graphify/gquery.py blast "<symbol|slug>" --depth 2
# Shortest path between two things:
python3 graphify/gquery.py path "A" "B"
# Direct neighbours:
python3 graphify/gquery.py neighbors "X"
```

Use `blast` for impact analysis ("I'm changing `create_charge` — what breaks, which
decisions/how-tos are in scope?"). It spans code↔wiki via the bridge.

## Natural-language questions

"How does X work / trace the data flow through Z" — answer it yourself from the
graph + the cited source files. That uses your session (subscription), **not** an
API token. Graphify never reads a provider key.

## Build / refresh (when missing or stale)

Check freshness: `built_at_commit` in `graphify-out/GRAPH_REPORT.md` vs
`git rev-parse HEAD`. If stale or absent (AST rebuild is free, local):

```bash
graphify/setup-venv.sh                                   # once per MACHINE (shared venv)
python3 docs/wiki/wiki-manifest docs/wiki --repo "$(basename "$PWD")"   # refresh anchors
graphify/run build.py --repo . --manifest docs/wiki/manifest.json \
  --owner "$(basename "$PWD")" --wiki-dir docs/wiki
```

`build.py` runs detect → AST → cluster → reuse community labels → wiki-bridge →
export, into `graphify-out/` in the current worktree (gitignored, never committed —
so parallel worktrees never conflict). Queries (`gquery.py`) need NO venv. The
semantic doc pass and one-time community naming are host/subscription steps — never an
API key.

## Rule

The graph is **navigation, not ground truth** — for line-level detail, open the
source. The wiki is the curated "why"; the graph is the mechanical "what connects
to what".
