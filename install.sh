#!/usr/bin/env bash
# install.sh — sync grindhouse (canonical) → ~/.claude/skills (the live install).
#
# Idempotent. Copies every skill dir + composes the guardrail library into
# skills/grind/scripts/grind (where grind-bootstrap.sh expects the global
# bundle). Run after every change in this repo.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "grindhouse install → $DEST"
for s in grind semi-grind sprint soft-pause culture grind-office quota; do
  mkdir -p "$DEST/$s"
  cp -rf "$HERE/skills/$s/." "$DEST/$s/"
  echo "  skill: $s"
done

# the law bundle lives inside the grind skill dir (grind-bootstrap.sh contract)
mkdir -p "$DEST/grind/scripts/grind"
cp -f "$HERE/scripts/grind/"* "$DEST/grind/scripts/grind/"
echo "  law:   scripts/grind ($(ls "$HERE/scripts/grind" | wc -l | tr -d ' ') files)"

# sanity: the live install must diff clean against canonical
if diff -rq "$HERE/scripts/grind" "$DEST/grind/scripts/grind" >/dev/null; then
  echo "grindhouse install: OK (mirror clean)"
else
  echo "grindhouse install: WARNING — mirror differs after copy" >&2; exit 1
fi
