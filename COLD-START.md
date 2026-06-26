# Cold Start — knowledge stack (wiki + code graph) in your org

A team-scalable knowledge layer with **no extra infrastructure to start**:
- **Wiki per repo** (`docs/wiki/`) — typed atomic units, the source of truth.
- **Presentation = GitHub Wiki**, auto-published by a GitHub Action (private repo →
  private wiki). No SSG, no hosting, no auth to run.
- **Code graph per repo** (Graphify) — queried *first* for architecture/blast-radius.
- **The working Claude Code session writes the wiki directly** — no curator agent.
  Consistency comes from a schema + a CI lint gate, not a person.

Architecture decisions baked in: wiki **per repo** (write-local; the session is
already in the repo), an optional **central read-only index** later for org-wide
search, and a **federated** model (cross-cutting org knowledge lives in its own repo's
wiki). See `README.md` for the why.

---

## Part A — Set up the first repo (~15 min)

**0. Prereqs:** `python3` + `pyyaml` (`pip install pyyaml`) for the wiki tools;
`git`; a GitHub repo. The code graph additionally needs the pinned venv (step A5).

**1. Install the stack:**
```bash
git clone <this-kit> knowledge-stack-starter
knowledge-stack-starter/install.sh /path/to/your-repo
```
This drops in `.claude/skills/{wiki,code-graph}`, `docs/wiki/` tools + `SCHEMA.md`,
the `graphify/` rig, `.github/workflows/knowledge.yml`, gitignores the derived bits,
and appends the knowledge block to `AGENTS.md`.

**2. Initialize the GitHub Wiki once (manual, one time):**
Repo → **Wiki** → **Create the first page** → save anything. This creates
`<repo>.wiki.git`; from now on the Action owns it. (A wiki can't be pushed to until
it exists.)

**Give the Action a way to push to the wiki.** Three options — the `publish-wiki` job
tries them in this order; pick whatever your org policy allows. Add secrets under repo
→ Settings → Secrets and variables → Actions → **New repository secret**.

- **`WIKI_SSH_KEY` — write Deploy Key (recommended for teams).** Repo-bound, **not tied
  to a personal user**, so it survives offboarding and needs no account PAT:
  ```bash
  ssh-keygen -t ed25519 -f wiki_deploy_key -N "" -C wiki-publish
  # wiki_deploy_key.pub → repo Settings → Deploy keys → Add → ✓ Allow write access
  # wiki_deploy_key (private) → Actions secret named WIKI_SSH_KEY
  ```
  A write deploy key on the repo can also push its `*.wiki.git`.
- **`WIKI_TOKEN` — a PAT.** Fine-grained (Repository access = this repo, Contents: RW)
  or classic (scope `repo`). **User-bound.** Use this when the Settings → Actions →
  General → Workflow permissions **Read and write** toggle is **greyed out** by org policy.
- **`GITHUB_TOKEN` (built-in).** Used automatically if you *can* set that toggle to
  Read and write. No secret needed.

Everything else (checkout, lint) only needs read, so a read-only default is fine.

**3. Write the first unit** (or backfill from a boilerplate repo — Part C). Easiest:
ask your Claude Code session, after any real change, to run the `wiki` skill. Or hand-write
`docs/wiki/<slug>.md` from `docs/wiki/SCHEMA.md`. See `examples/payments-idempotency-keys.md`.

**4. Verify the gate locally, then push:**
```bash
python3 docs/wiki/wiki-lint docs/wiki/        # must pass (0 errors)
git add docs/wiki .claude .github AGENTS.md graphify .gitignore
git commit -m "knowledge stack + first units" && git push
```
Open a PR → the **lint** job gates it. Merge to main → the **publish-wiki** job renders
and pushes to the GitHub Wiki. Visit repo → Wiki.

**5. Build the code graph (local, on demand — never committed):**
```bash
graphify/setup-venv.sh                                   # once per MACHINE (shared venv)
python3 docs/wiki/wiki-manifest docs/wiki --repo "$(basename "$PWD")"   # refresh anchors
graphify/run build.py --repo . --manifest docs/wiki/manifest.json \
        --owner "$(basename "$PWD")" --wiki-dir docs/wiki
python3 graphify/gquery.py blast "<some-symbol-or-slug>"   # queries need NO venv
```
The graph (`graphify-out/`) is **derived and gitignored** — rebuilt on demand in
whatever worktree you're in, so parallel devs/worktrees never conflict on a generated
file. CI does **not** build or store it; CI's graph role is the deterministic
**drift gate** (`wiki-verify`) in the lint job, which needs no venv.

---

## Part B — Onboard the team

Each engineer needs, per repo, only what `install.sh` already committed: the two
skills (`.claude/skills/`), the `AGENTS.md` block, the `docs/wiki/` tools. So a fresh
clone is ready. The team contract is two habits, both encoded in `AGENTS.md`:

1. **Read graph-first.** For "how does X work / what does changing Y affect", run
   `python3 graphify/gquery.py blast "X"` before grepping.
2. **Write-after-change.** At the end of a change that established durable truth, run
   the `wiki` skill — the unit ships **in the same PR** as the code. Review covers
   code + doc together; CI lint blocks schema violations.

No one is "the docs person." The curator role is the **schema + CI gate**. Pruning and
supersession are everyone's job (the skill makes them mechanical).

**Pre-commit hook (lint + verify locally).** A committed hook at `.githooks/pre-commit`
runs `wiki-lint` + `wiki-verify` whenever a commit touches `docs/wiki/`, so schema/drift
errors never reach CI. `install.sh` enables it for the installing clone; **every other
clone enables it once** (it's local git config, not committed):
```bash
git config core.hooksPath .githooks
```
If your repo already uses a hooks path (husky, pre-commit framework), don't override it —
instead call `.githooks/pre-commit` from your existing hook. Bypass in an emergency with
`git commit --no-verify`. Needs `python3` + `pyyaml` locally (skips with a note if absent).

Tips:
- PR template line: "If this changed durable truth, did you run `/wiki`?"
- Keep units atomic — reviewers reject 500-line "kitchen sink" units.

---

## Part C — Ingest a boilerplate / existing repo (initial backfill)

Don't try to document everything. The graph tells you **where the load-bearing parts
are**; capture those, let the write-after-change loop fill the rest.

1. **Build the graph** (Part A5). Read `graphify-out/GRAPH_REPORT.md`: **god nodes**
   (core abstractions), **communities** (modules), and rationale already extracted from
   `# WHY/# NOTE` comments.
2. **Backfill the load-bearing knowledge** in a single bounded pass. For each top god
   node / key module / known decision, have your session run the `wiki` skill to write
   one unit, anchored to the real symbol + commit hash. Aim for ~10–30 units, not 300.
   Prioritise: irreversible decisions, non-obvious mechanisms, gotchas, public contracts.
3. **Lint + PR + merge** → the wiki populates and the bridge links units to code
   (`gquery.py blast` now spans both).
4. Stop. The rest accretes naturally through normal work.

> Anti-pattern: auto-generating a unit per file. That recreates the code in prose and
> rots instantly. Units capture the **why** and the non-obvious — the graph already
> carries the **what**.

---

## Part D — Mutate over time (steady state)

- **New truth** → `wiki` skill writes/updates a unit in the same PR. `draft` → `active`.
- **Changed truth** → edit the unit **in place** under its slug (git keeps history).
- **Replaced decision** → supersede: old gets `status: superseded` + `superseded_by`;
  new gets `supersedes`. Both stay. The wiki renders a tombstone banner.
- **Drift** → when code moves, a unit's `source` anchor goes stale. Rebuild the graph
  (`build.py`, free); stale anchors surface. The next session touching that area
  re-anchors or rewrites the unit. Mark units `status: stale` honestly until fixed.
- **Prune** → delete units whose source symbol is gone. Accretion is rot.
- **Freshness is visible** → `status` badges + `last_verified` render on every wiki
  page; `built_at_commit` shows graph staleness.

### Later upgrades (when you outgrow the cold start)
- **Org-wide search:** a small harvester clones each repo's `docs/wiki/` read-only into
  a central index repo/site (the federated "read index"). Source of truth stays per repo.
- **Richer presentation:** swap the GitHub Wiki for an SSG (e.g. behind SSO) — same
  `docs/wiki/` source, different renderer.
- **Native graph queries/MCP:** expose `graphify` over MCP so agents call
  `blast`/`path`/`get_pr_impact` as tools.
