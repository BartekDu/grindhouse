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

# --- the contribution law needs a way back home ----------------------------
# mirror-guard/mirror-hook run from the MIRROR (that is where the hook points),
# so they cannot find the clone by looking upward. Record it once, here, instead
# of hardcoding a machine path in a tracked script (same law as GRIND_QUOTA_TOOL).
CONF="${GRINDHOUSE_CONF:-$HOME/.claude/grindhouse.conf}"
mkdir -p "$(dirname "$CONF")"
printf '# written by grindhouse install.sh — the canonical clone on this machine\nGRINDHOUSE_ROOT=%s\n' "$HERE" > "$CONF"
echo "  conf:  $CONF (GRINDHOUSE_ROOT=$HERE)"

# The anonymization denylist is machine-local and confidential (it enumerates
# your clients) — never tracked. Seed it once from the template.
ANON="${GRIND_ANON_TERMS:-$HOME/.claude/grindhouse.anon-terms}"
if [ ! -f "$ANON" ]; then
  cp "$HERE/scripts/grind/anon-terms.example" "$ANON"
  echo "  anon:  $ANON (seeded from template — ADD YOUR CLIENT NAMES)"
fi

# The read-only-mirror hook is what makes the law preventive instead of
# forensic. install.sh does not edit settings.json (it is the user's file);
# it tells you when the guard is missing.
SETTINGS="$HOME/.claude/settings.json"
if ! grep -q 'mirror-hook' "$SETTINGS" 2>/dev/null; then
  cat <<EOF

grindhouse: the mirror is NOT write-protected yet. Add to $SETTINGS:

  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [ { "type": "command",
                     "command": "bash '$DEST/grind/scripts/grind/mirror-hook'" } ] }
    ]
  }

Without it, edits to $DEST are silently destroyed by the next install.sh
and never reach a PR. Prove the law any time:  bash "$HERE/scripts/grind/mirror-guard" check
EOF
fi
