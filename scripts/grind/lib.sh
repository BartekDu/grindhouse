#!/usr/bin/env bash
# Shared helpers for /grind enforcement scripts. Source after config.sh.
# JSON ops route through grindjson.py (grind_gj) because local git-bash has no jq.

set -o pipefail

# GRIND_NOW (epoch seconds) pins "now" for tests; grindjson.py honours it too.
grind_now()       { if [ -n "${GRIND_NOW:-}" ]; then printf '%s\n' "${GRIND_NOW%%.*}"; else date +%s; fi; }
grind_now_iso()   { date -u +%Y-%m-%dT%H:%M:%SZ; }
grind_die()       { echo "grind: $*" >&2; exit 1; }

# Atomic write: content on stdin -> $1 (write-temp-then-rename). Prevents the
# §15.2 "concurrent state.json write" hazard from leaving a half-written file.
grind_atomic_write() {
  local dest="$1" tmp
  tmp="${dest}.tmp.$$"
  cat > "$tmp" && mv -f "$tmp" "$dest"
}

# state.json accessors (python-backed; no jq).
grind_state_get()  { grind_gj get "$GRIND_STATE" "$1"; }              # dotted.path
grind_state_set()  { grind_gj set "$GRIND_STATE" "$1" "$2"; }         # path, json-value
grind_state_incr() { grind_gj incr "$GRIND_STATE" "$1" "${2:-1}"; }   # path [by]

# Hash-chained audit line (tamper-evident; audit-verify checks the chain).
grind_audit() { grind_gj audit-append "$GRIND_AUDIT" "$1" "${2:-}"; }

# Append a timestamped line to the human run-log.
grind_runlog() { printf -- '- **%s** — %s\n' "$(grind_now_iso)" "$*" >> "$GRIND_RUNLOG"; }

grind_killed() { [ -f "$GRIND_STOP" ]; }     # kill switch present?
grind_active() { [ -f "$GRIND_ACTIVE" ]; }   # a window currently running?

# Base branch resolution (campaign branches are cut from + PR'd back to this).
# Order: explicit override (project.conf / env) > origin/HEAD > first existing
# of dev|main|master > current branch. Never guess a branch that doesn't exist.
# (Incident: the branch model hardcoded `dev`; repos whose base is main/master
# cut campaigns from a branch that didn't exist.)
grind_base_branch() {
  if [ -n "${GRIND_BASE_BRANCH:-}" ]; then printf '%s\n' "$GRIND_BASE_BRANCH"; return; fi
  local b
  b="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)"
  if [ -n "$b" ]; then printf '%s\n' "${b#origin/}"; return; fi
  for b in dev main master; do
    if git show-ref --verify --quiet "refs/heads/$b"; then printf '%s\n' "$b"; return; fi
  done
  git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main
}
