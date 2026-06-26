<!--
Paste this block into the repo's CLAUDE.md (or AGENTS.md). It is the per-repo
knowledge protocol: write-after-change + graph-first reading. Adjust the owner name.
-->

## Knowledge protocol (wiki + code graph)

This repo carries its own knowledge wiki (`docs/wiki/`, schema in `docs/wiki/SCHEMA.md`)
and a queryable code graph (`graphify-out/`). Treat both as first-class.

**Reading — graph first.** For any question about architecture, relationships, call
paths, or blast-radius: query the graph BEFORE grepping.
- `python3 graphify/gquery.py blast "<symbol|slug>" --depth 2`  (impact, spans code↔wiki)
- `python3 graphify/gquery.py path "A" "B"` · `neighbors "X"`
- Check freshness (`built_at_commit` in `graphify-out/GRAPH_REPORT.md` vs `git rev-parse HEAD`);
  if stale, rebuild (free, local): `python3 graphify/build.py --repo . --manifest docs/wiki/manifest.json --owner <owner> --wiki-dir docs/wiki`.
- Natural-language "how does X work" you answer yourself from the graph + sources
  (your session = the LLM; **never** an API token).

**Writing — at the end of a documentable change, you write the wiki yourself.** Invoke
the `wiki` skill: slice into atomic typed units, anchor each to a real commit hash +
path (+ symbol; prefer a symbol over `null`), write/MUTATE in place under the slug
(supersede, don't overwrite), set `[[slug]]` links + `entities`, then
`python3 docs/wiki/wiki-lint docs/wiki/` and commit **in the same PR as the code**.
There is no separate docs agent and no cross-repo PR — you are author and committer.

**Locked:** one fact one page (link, don't repeat) · in place under slug · supersede
not overwrite · prune orphans · never invent a hash/path/symbol · `verified`/
`primary-source` units are annotated, never overwritten. The CI lint gate enforces the
schema; the GitHub Wiki is published automatically on merge (do not edit the wiki UI).
