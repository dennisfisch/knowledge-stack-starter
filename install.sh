#!/usr/bin/env bash
# install.sh — drop the knowledge stack into a target repo.
#
#   ./install.sh /path/to/target-repo
#
# Copies: .claude/skills/{wiki,code-graph}, docs/wiki/ tools + SCHEMA, graphify/ rig,
# the GitHub Action, and appends the CLAUDE.md knowledge block. Idempotent-ish:
# re-running overwrites the tools/skills/workflow but never your wiki units.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:?usage: ./install.sh /path/to/target-repo}"
TARGET="$(cd "$TARGET" && pwd)"

mkdir -p "$TARGET"/.claude/skills "$TARGET"/docs/wiki "$TARGET"/graphify "$TARGET"/.github/workflows "$TARGET"/.githooks

cp -R "$KIT/skills/wiki"       "$TARGET/.claude/skills/"
cp -R "$KIT/skills/code-graph" "$TARGET/.claude/skills/"
cp "$KIT/tools/SCHEMA.md" "$KIT/tools/wiki-lint" "$KIT/tools/wiki-render" "$KIT/tools/wiki-manifest" "$KIT/tools/wiki-verify" "$TARGET/docs/wiki/"
chmod +x "$TARGET"/docs/wiki/wiki-{lint,render,manifest,verify}
cp "$KIT"/graphify/{setup-venv.sh,run,build.py,wiki-bridge.py,gquery.py} "$TARGET/graphify/"
chmod +x "$TARGET/graphify/setup-venv.sh" "$TARGET/graphify/run"
cp "$KIT/tools/hooks/pre-commit" "$TARGET/.githooks/pre-commit"
chmod +x "$TARGET/.githooks/pre-commit"
cp "$KIT/.github/workflows/knowledge.yml" "$TARGET/.github/workflows/"

# Enable the committed pre-commit hook (lint+verify) — but never clobber an existing
# hooks path (e.g. husky). Each clone runs this once; install.sh does it for you here.
if [ -z "$(git -C "$TARGET" config --get core.hooksPath || true)" ]; then
  git -C "$TARGET" config core.hooksPath .githooks
  echo "enabled pre-commit hook (core.hooksPath=.githooks)"
else
  echo "note: core.hooksPath already set ($(git -C "$TARGET" config --get core.hooksPath)); "\
"add a call to .githooks/pre-commit from your existing hook to enable wiki checks."
fi

# gitignore the derived/local bits
touch "$TARGET/.gitignore"
for line in "graphify-out/" "graphify/.venv/" ".wiki-build/"; do
  grep -qxF "$line" "$TARGET/.gitignore" || echo "$line" >> "$TARGET/.gitignore"
done

# append the CLAUDE.md knowledge block once
CL="$TARGET/CLAUDE.md"; touch "$CL"
if ! grep -q "Knowledge protocol (wiki + code graph)" "$CL"; then
  { echo; sed '/^<!--/,/-->/d' "$KIT/CLAUDE.snippet.md"; } >> "$CL"
  echo "appended knowledge block to CLAUDE.md"
fi

echo "installed knowledge stack into $TARGET"
echo "next: see COLD-START.md (init the GitHub Wiki once, seed the first unit, build the graph)"
