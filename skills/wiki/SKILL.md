---
name: wiki
description: >
  Capture or mutate durable knowledge in this repo's wiki (docs/wiki/) DIRECTLY,
  while the change context is hot. Use at the END of a change that touched
  documentable truth — an architectural decision, a non-obvious mechanism, a
  how-to, a reference fact, a "why". Writes typed atomic units with schema-v1
  frontmatter and source anchors, supersedes rather than overwrites, sets links,
  and lints before commit. You author and commit it yourself, in the SAME PR as
  the code — there is no separate curator agent.
---

# /wiki — write knowledge directly, while context is hot

This repo carries its own knowledge wiki at `docs/wiki/` (one atomic, typed unit
per file; the filename minus `.md` is the stable **slug = identity**). You — the
working session — are the author AND the committer. The lossy handoff "someone else
writes the docs later from a commit summary" is exactly what kills docs; you have
the context now, so you write it now. The schema (`docs/wiki/SCHEMA.md`) and the CI
lint gate keep it consistent — not a dedicated agent.

## When to invoke

At the end of a change that touched **documentable truth**. Not every change. Ask:
"did this establish a decision, a non-obvious mechanism, a gotcha, a how-to, or a
reference fact that a future engineer (or agent) would waste time rediscovering?"
If yes → run this skill before you open/finish the PR.

## Steps

### 1. Fix the change context
Run `git diff`, `git log -1`, note the touched files and the real commit hash
(`git rev-parse --short HEAD` — use the actual hash, never invent one).

### 2. Slice into atomic units (1 change ≠ 1 doc)
Each independent fact/decision is its own unit. A refactor that also changed a
policy is (at least) two units: a `reference`/`howto` for the mechanism and a
`decision` for the policy. One fact, one page; other pages **link** (`[[slug]]`).

### 3. Pick the type honestly (provenance decides)
`reference`/`howto`/`tutorial` are **code-derived** → they MUST carry a `source`
with a real **commit hash** + path (+ a real `symbol` if you can — prefer a symbol
over `null`; it makes the Graphify bridge precise and drift sharper). `explanation`
and `decision` are the "why" → anchor to a ticket/ADR ref, not a hash. If you have
no code anchor, it is not a reference.

### 4. Write or MUTATE in place
- **New fact** → new file `docs/wiki/<slug>.md` with full schema-v1 frontmatter
  (see `docs/wiki/SCHEMA.md`) + dense prose.
- **Changed fact** → edit the EXISTING `<slug>.md` in place. Do not spin a new slug.
- **Replaced decision** → supersede, don't overwrite: old unit gets
  `status: superseded` + `superseded_by: <new>` + `superseded_at: <today>`; new unit
  gets `supersedes: <old>`. Both stay; git holds the trail.
- Set `entities:` (blast-radius nodes) and `relates:` (real `[[slug]]` links to units
  that exist or that you create in this same PR — no dangling links).
- `status: draft` on creation; flip to `active` when the PR is ready to merge.

### 5. Lint before commit (the gate, deterministic)
```bash
python3 docs/wiki/wiki-lint docs/wiki/        # corpus mode: schema + cross-refs
```
Fix every ERROR. The same lint runs in PR CI and will block the merge otherwise.

### 6. Commit with the code
Stage the unit(s) **in the same PR** as the code change. The wiki is published to
the GitHub Wiki automatically on merge (CI) — you do not touch the wiki UI.

## Rules (locked)

- **In place under the slug. Supersede, don't overwrite. Prune orphans.**
- **Never invent a commit hash, path, or symbol** — verify against the repo.
- **`primary-source`/`verified` units are never overwritten, only annotated.**
- One fact, one page; link instead of repeating.
- You write, you lint, you commit — no separate agent, no cross-repo PR.
