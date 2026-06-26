#!/usr/bin/env bash
# install.sh — drop the knowledge stack into a target repo (or update it in place).
#
#   ./install.sh /path/to/target-repo            # full install
#   ./install.sh /path/to/target-repo --update   # pull latest kit, refresh tooling only
#
# Always overwrites the TOOLING (skills, docs/wiki tools, graphify rig, hook, workflow)
# and stamps .knowledge-stack-version. NEVER touches your wiki units, and never clobbers
# an existing CLAUDE.md block, PR template, or CONTRIBUTING.md.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"

TARGET=""; UPDATE=0
for arg in "$@"; do
  case "$arg" in
    --update) UPDATE=1 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || { echo "usage: ./install.sh /path/to/target-repo [--update]"; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"

# --update: refresh the kit itself first (best-effort), so a single command pulls fixes.
if [ "$UPDATE" = 1 ] && git -C "$KIT" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$KIT" pull --ff-only 2>&1 | tail -1 || echo "note: could not fast-forward kit; using local copy."
fi
VERSION="$(cat "$KIT/VERSION" 2>/dev/null || echo "?")"
KIT_COMMIT="$(git -C "$KIT" rev-parse --short HEAD 2>/dev/null || echo nogit)"

mkdir -p "$TARGET"/.claude/skills "$TARGET"/docs/wiki "$TARGET"/graphify \
         "$TARGET"/.github/workflows "$TARGET"/.githooks

# --- tooling (always overwritten = the update surface) ---
cp -R "$KIT/skills/wiki" "$KIT/skills/code-graph" "$TARGET/.claude/skills/"
cp "$KIT/tools/SCHEMA.md" "$KIT/tools/wiki-lint" "$KIT/tools/wiki-render" \
   "$KIT/tools/wiki-manifest" "$KIT/tools/wiki-verify" "$TARGET/docs/wiki/"
chmod +x "$TARGET"/docs/wiki/wiki-{lint,render,manifest,verify}
cp "$KIT"/graphify/{setup-venv.sh,run,build.py,wiki-bridge.py,gquery.py} "$TARGET/graphify/"
chmod +x "$TARGET/graphify/setup-venv.sh" "$TARGET/graphify/run"
cp "$KIT/tools/hooks/pre-commit" "$TARGET/.githooks/pre-commit"
chmod +x "$TARGET/.githooks/pre-commit"
cp "$KIT/.github/workflows/knowledge.yml" "$TARGET/.github/workflows/"
echo "$VERSION ($KIT_COMMIT)" > "$TARGET/.knowledge-stack-version"

# --- enable the pre-commit hook (don't clobber an existing hooks path, e.g. husky) ---
if [ -z "$(git -C "$TARGET" config --get core.hooksPath || true)" ]; then
  git -C "$TARGET" config core.hooksPath .githooks
  echo "enabled pre-commit hook (core.hooksPath=.githooks)"
else
  echo "note: core.hooksPath already set ($(git -C "$TARGET" config --get core.hooksPath)) — "\
"call .githooks/pre-commit from your existing hook to enable wiki checks."
fi

# --- gitignore the derived/local bits ---
touch "$TARGET/.gitignore"
for line in "graphify-out/" "graphify/.venv/" ".wiki-build/" "docs/wiki/manifest.json"; do
  grep -qxF "$line" "$TARGET/.gitignore" || echo "$line" >> "$TARGET/.gitignore"
done

# --- non-tooling files: create only if absent (never clobber team content) ---
CL="$TARGET/CLAUDE.md"; touch "$CL"
if ! grep -q "Knowledge protocol (wiki + code graph)" "$CL"; then
  { echo; sed '/^<!--/,/-->/d' "$KIT/CLAUDE.snippet.md"; } >> "$CL"
  echo "appended knowledge block to CLAUDE.md"
fi
if [ ! -f "$TARGET/CONTRIBUTING.md" ]; then
  cp "$KIT/CONTRIBUTING.md" "$TARGET/CONTRIBUTING.md"
  echo "added CONTRIBUTING.md"
fi
if [ ! -f "$TARGET/.github/pull_request_template.md" ]; then
  cp "$KIT/.github/pull_request_template.md" "$TARGET/.github/pull_request_template.md"
  echo "added .github/pull_request_template.md"
else
  echo "note: PR template exists — paste the 'Knowledge (wiki)' block from the kit's into it."
fi

if [ "$UPDATE" = 1 ]; then
  echo "updated knowledge stack in $TARGET to v$VERSION ($KIT_COMMIT) — units & CLAUDE.md untouched"
else
  echo "installed knowledge stack v$VERSION into $TARGET"
  echo "next: see COLD-START.md (init the GitHub Wiki once, seed the first unit, build the graph)"
fi
