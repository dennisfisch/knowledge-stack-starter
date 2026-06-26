# Wiki Unit — Frontmatter Schema v1

One atomic, typed knowledge unit per file. **The filename (minus `.md`) is the
stable slug = the unit's identity.** Update a unit *in place* under the same slug;
git holds the history. Don't spin a new slug per revision.

```yaml
---
title: <concise, unique title>
type: reference | howto | tutorial | explanation | decision   # Diátaxis + decision (ADR)
owner: <team or area, e.g. payments, platform, web>
status: draft | active | stale | superseded                   # draft → active on merge
provenance_tier: agent-compacted | verified | primary-source
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
last_verified: <YYYY-MM-DD>
source:                                  # REQUIRED for reference/howto/tutorial
  - repo: <repo name>
    path: <file/in/repo OR ticket/ADR ref>
    symbol: <function|section|null>      # prefer a real symbol over null — see note
    provenance: <commit hash (hex ≥7) for code types | ticket/ADR ref otherwise>
entities: [<knowledge-graph nodes, e.g. auth, billing>]   # blast-radius edges
relates: [<slug>, ...]                   # sibling links; rendered as [[slug]]
supersedes: <slug>                       # predecessor in a supersession chain
superseded_by: <slug>                    # successor (REQUIRED when status: superseded)
superseded_at: <YYYY-MM-DD>
review_after: <YYYY-MM-DD>               # for explanation/decision (review-based freshness)
confidence: <float 0.0–1.0>              # optional; read-time staleness decay
half_life_kind: static | versioned | event   # optional; decay class
---
```

## Types (Diátaxis + decision)

- `reference` — factual, code-derived knowledge.
- `howto` — procedural steps.
- `tutorial` — narrative, teaching.
- `explanation` — conceptual "why" (not code-derived).
- `decision` — an ADR; append-only, supersession chains.

## Provenance is the anti-rot contract

- **Code types** (`reference`/`howto`/`tutorial`) MUST carry a `source` with a real
  **commit hash** + path (+ ideally a symbol). This is what the Graphify bridge and
  the drift check key on.
- `explanation`/`decision` anchor to a ticket/ADR ref (review-based, not hash-checked).
- `provenance_tier`: `primary-source`/`verified` are **never overwritten**, only
  annotated. `agent-compacted` is a synthesis claim — negotiable on drift.

## Why prefer a real `symbol` over `null`

The bridge resolves `source.symbol` to an exact code node (precise blast-radius).
`symbol: null` falls back to file-level (coarse on big files). Symbol anchors are
still symbol-level, **not** line-level — so they don't rot. Win/win: precision now,
better drift detection later.

## Mutation discipline

- **In place under the slug.** One fact, one page. Other pages link here (`[[slug]]`),
  they don't repeat the logic.
- **Supersede, don't overwrite.** Old unit gets `status: superseded` + `superseded_by`
  + `superseded_at`; new unit gets `supersedes`. Both stay; git holds the trail.
- **Prune orphans.** A unit whose source symbol is gone should be retired — accretion
  is itself rot.
