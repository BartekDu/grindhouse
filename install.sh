#!/usr/bin/env bash
# install.sh — sync grindhouse (canonical) → ~/.claude/skills (the live install).
#
# Idempotent. Copies every skill dir + composes the guardrail library into
# skills/grind/scripts/grind (where grind-bootstrap.sh expects the global
# bundle). Run after every change in this repo.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
BACKUPS="${CLAUDE_BACKUPS_DIR:-$HOME/.claude/backups}"

echo "grindhouse install → $DEST"
for s in grind semi-grind sprint soft-pause culture grind-office; do
  mkdir -p "$DEST/$s"
  cp -rf "$HERE/skills/$s/." "$DEST/$s/"
  echo "  skill: $s"
done

# The /quota skill (nested `claude /usage` poller) is retired: quota-gate reads
# the statusline readings now. Remove an old install, but only after a verified
# backup.
if [ -d "$DEST/quota" ]; then
  mkdir -p "$BACKUPS"
  bk="$BACKUPS/quota-skill-$(date +%Y%m%d-%H%M%S).tgz"
  tar czf "$bk" -C "$DEST" quota
  # list into a variable first: `tar | grep -q` under pipefail fails on SIGPIPE
  listing="$(tar tzf "$bk" 2>/dev/null || true)"
  if printf '%s\n' "$listing" | grep -x 'quota/SKILL.md' >/dev/null; then
    rm -rf "$DEST/quota"
    echo "  retired: quota (backup $bk)"
  else
    echo "grindhouse install: quota backup unreadable ($bk); quota left in place" >&2; exit 1
  fi
fi

# the law bundle lives inside the grind skill dir (grind-bootstrap.sh contract);
# files only (a stray __pycache__/ dir would make cp fail under set -e), and
# files no longer in the repo are pruned so retired scripts do not linger
mkdir -p "$DEST/grind/scripts/grind"
for f in "$HERE/scripts/grind/"*; do
  [ -f "$f" ] && cp -f "$f" "$DEST/grind/scripts/grind/"
done
for f in "$DEST/grind/scripts/grind/"*; do
  [ -f "$f" ] && [ ! -e "$HERE/scripts/grind/${f##*/}" ] && rm -f "$f" && echo "  pruned: ${f##*/}"
done
echo "  law:   scripts/grind ($(find "$HERE/scripts/grind" -maxdepth 1 -type f | wc -l | tr -d ' ') files)"

# sanity: the live install must diff clean against canonical
if diff -rq -x __pycache__ "$HERE/scripts/grind" "$DEST/grind/scripts/grind" >/dev/null; then
  echo "grindhouse install: OK (mirror clean)"
else
  echo "grindhouse install: WARNING — mirror differs after copy" >&2; exit 1
fi
