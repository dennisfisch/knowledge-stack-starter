# Knowledge Stack Starter — wiki + code graph, per repo

A team-scalable knowledge layer that combines a **curated LLM-friendly wiki** with an
**automatic, queryable code graph** — designed so the **working Claude Code session
writes and mutates the wiki directly** (no dedicated curator agent), with consistency
enforced by a schema + CI gate.

## The model

| Layer | What | Source of truth |
|---|---|---|
| **Wiki** (`docs/wiki/`) | typed atomic units (Diátaxis + decision), schema-v1 frontmatter, source anchors, supersession | **per repo**, co-located with code |
| **Presentation** | **GitHub Wiki**, auto-published by a GitHub Action (no extra stack; private repo → private wiki) | derived mirror of `docs/wiki/` |
| **Code graph** (`graphify-out/`) | Graphify: AST nodes/edges, communities, god nodes, bridged to wiki via source anchors | derived, rebuildable |
| **Gate** | `wiki-lint` in PR CI + normal review | replaces a curator agent |

**Reading is graph-first** (architecture/blast-radius → query the graph before grep).
**Writing is session-direct** (the session that made the change writes the wiki unit,
same PR). The two are wired into the repo's `CLAUDE.md`.

## Why per-repo + federated (not one central docs repo)

Direct-write + repo-local Graphify both pull toward co-locating the wiki with the code:
the session is already in the repo, so writing is a local file in the same PR (no
cross-repo handoff — the very friction that kills docs). Org-wide discovery comes later
as a **read-only** harvested index, not a central write surface. Cross-cutting org
knowledge lives in its own repo's wiki. Mono-repo is the trivial unified case.

## Layout (what `install.sh` puts in a repo)

```
your-repo/
├── .claude/skills/{wiki,code-graph}/SKILL.md   # the two skills
├── .github/workflows/knowledge.yml             # PR lint gate + wiki publish
├── CLAUDE.md                                    # + knowledge protocol block
├── docs/wiki/
│   ├── SCHEMA.md  wiki-lint  wiki-verify  wiki-render  wiki-manifest
│   └── <slug>.md ...                            # the units
└── graphify/{setup-venv.sh,run,build.py,wiki-bridge.py,gquery.py}
```

## This kit

```
install.sh            # drop the stack into a target repo (one command)
COLD-START.md         # step-by-step: set up · onboard team · ingest · mutate
CLAUDE.snippet.md     # the knowledge block (install.sh appends it)
skills/               # wiki (write/mutate) · code-graph (read)
tools/                # SCHEMA.md · wiki-lint · wiki-verify · wiki-render · wiki-manifest
graphify/             # the repo-local code-graph rig (pinned)
.github/workflows/    # knowledge.yml
examples/             # a sample unit
```

## Guardrails (locked)

- **Subscription-only** — Graphify reads no provider API key; the LLM work is your
  session (code-graph skill) on your subscription. Code AST is local/zero-API.
- **Anti-rot** — symbol/file-level anchors (never line-level), drift via graph rebuild,
  read-time freshness badges, supersede-don't-overwrite, prune orphans.
- **Pinned** tooling, derived artifacts gitignored.

Start at **COLD-START.md**.
