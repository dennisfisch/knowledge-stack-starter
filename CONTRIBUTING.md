# Working with the knowledge wiki — team cheat sheet

One page. The wiki (`docs/wiki/`) is the team's durable "why"; the code graph
(`graphify-out/`) is the mechanical "what connects to what". You maintain the wiki as a
side effect of normal work — there is no docs team.

## The loop (per ticket)

1. **Read graph-first.** Architecture / "what does changing X affect?" → query the
   graph before grepping:
   ```bash
   python3 graphify/gquery.py blast "<symbol-or-slug>"     # needs no venv
   ```
2. **Do the work** in your worktree / feature branch.
3. **Write-after-change.** If this established durable truth, run **`/wiki`**: it writes
   or mutates atomic units in `docs/wiki/`, in the **same PR** as the code.
4. **Commit.** The pre-commit hook runs `wiki-lint` + `wiki-verify` automatically.
5. **PR.** CI gates schema + anchor drift. Merge → the GitHub Wiki updates itself.

## What is "durable truth" (worth a unit)?

A decision, a non-obvious mechanism, a gotcha, a public contract — anything a teammate
(or an AI agent) would waste time rediscovering. **Not** every change. Not a restatement
of the code.

## Writing units (the rules that matter)

- **One fact, one page.** Other pages link (`[[slug]]`), they don't repeat.
- **The filename is the identity** (kebab-case slug). Change a fact → edit that file
  **in place**. Don't spin a new slug.
- **Supersede, don't overwrite.** A replaced decision: old gets `status: superseded` +
  `superseded_by`; new gets `supersedes`. Both stay.
- **Anchor to real code.** `source:` = real path + a real **symbol** (prefer a symbol
  over `null` — it makes the graph precise and drift sharp) + the commit hash.
- **Prune.** Delete units whose source is gone. Accretion is rot.
- Schema: `docs/wiki/SCHEMA.md`.

## Gates (same tools, three places)

| When | Where | Checks |
|---|---|---|
| commit | `.githooks/pre-commit` | `wiki-lint` + `wiki-verify` (local, instant) |
| PR | GitHub Action `lint` | same, authoritative |
| merge | Action `publish-wiki` | renders → GitHub Wiki |

Enable the hook once per clone: `git config core.hooksPath .githooks`.
Emergency bypass: `git commit --no-verify` (CI still gates).

## Refresh the code graph (when you want to query it)

```bash
graphify/setup-venv.sh                                          # once per machine
python3 docs/wiki/wiki-manifest docs/wiki --repo "$(basename "$PWD")"
graphify/run build.py --repo . --manifest docs/wiki/manifest.json --owner "$(basename "$PWD")" --wiki-dir docs/wiki
```
The graph is derived + gitignored — rebuilt on demand, never committed.

## Keeping the tooling current

```bash
/path/to/knowledge-stack-starter/install.sh . --update
```
Pulls the latest kit and refreshes the tooling/skills/workflow/hook. **Never touches
your wiki units or CLAUDE.md.** Your repo's version is in `.knowledge-stack-version`.
