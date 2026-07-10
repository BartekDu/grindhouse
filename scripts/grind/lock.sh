#!/usr/bin/env bash
# lock.sh — single-run lock + dirty-tree preflight for /grind windows.
# Stops duplicate cron fires, overrun-concurrency, and starting on a dirty/mid-merge tree.
#
# Usage:
#   lock.sh acquire WINDOW_ID     exit 0 + write .active if acquired; non-zero if locked/dirty
#   lock.sh release               release the lock + remove .active
#   lock.sh status                print holder info
#
# Lock is a directory ($GRIND_LOCK) — mkdir is atomic across processes. Stale
# locks (holder PID dead, or older than 6h) are reclaimed.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"; cd "$ROOT" || exit 1
. "$HERE/config.sh"; . "$HERE/lib.sh"
mkdir -p "$GRIND_DIR"

STALE_SEC=$((6*3600))
pid_alive() { kill -0 "$1" 2>/dev/null; }

case "${1:-}" in
  acquire)
    win="${2:-?}"
    # reclaim stale lock
    if [ -d "$GRIND_LOCK" ]; then
      lpid="$(cat "$GRIND_LOCK/pid" 2>/dev/null || echo 0)"
      lts="$(cat "$GRIND_LOCK/ts" 2>/dev/null || echo 0)"
      age=$(( $(grind_now) - lts ))
      if pid_alive "$lpid" && [ "$age" -lt "$STALE_SEC" ]; then
        echo "LOCKED held by pid=$lpid window=$(cat "$GRIND_LOCK/window" 2>/dev/null) age=${age}s" >&2
        grind_audit "lock" "acquire DENIED (held pid=$lpid)"
        exit 1
      fi
      echo "lock.sh: reclaiming stale lock (pid=$lpid age=${age}s)" >&2
      rm -rf "$GRIND_LOCK"
    fi
    # dirty-tree preflight: refuse to start a window on a dirty / mid-merge tree
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      echo "!!! GRIND LOCK: working tree not clean — refusing to start a window. Commit/stash/resolve first." >&2
      grind_audit "lock" "acquire DENIED (dirty tree)"
      exit 2
    fi
    if [ -f "$GRIND_MERGE_HEAD" ] 2>/dev/null || [ -f ".git/MERGE_HEAD" ]; then
      echo "!!! GRIND LOCK: mid-merge — refusing to start." >&2
      grind_audit "lock" "acquire DENIED (mid-merge)"
      exit 2
    fi
    # gitignore hygiene preflight: scratch noise (.claude/worktrees/, db.sqlite3,
    # *.tmp) must be ignored before a window starts, or it accumulates as 100s of
    # untracked files (the founder-flagged "hot mess"). verify is fail-closed; the
    # loop runs `hygiene-check fix` + commits .gitignore on the feature branch first.
    if ! bash "$HERE/hygiene-check" verify >/dev/null 2>&1; then
      echo "!!! GRIND LOCK: gitignore hygiene failing — run 'bash $HERE/hygiene-check fix', commit .gitignore on the feature branch, then re-acquire." >&2
      bash "$HERE/hygiene-check" verify >&2
      grind_audit "lock" "acquire DENIED (hygiene)"
      exit 3
    fi
    mkdir "$GRIND_LOCK" 2>/dev/null || { echo "LOCKED (race)" >&2; exit 1; }
    echo "$$"                          > "$GRIND_LOCK/pid"
    echo "${CLAUDE_SESSION_ID:-$$}"    > "$GRIND_LOCK/session"
    echo "$win"                        > "$GRIND_LOCK/window"
    echo "$(grind_now)"                > "$GRIND_LOCK/ts"
    : > "$GRIND_ACTIVE"
    grind_audit "lock" "acquired window=$win pid=$$"
    echo "ACQUIRED window=$win"
    ;;
  release)
    rm -rf "$GRIND_LOCK"; rm -f "$GRIND_ACTIVE"
    grind_audit "lock" "released"
    echo "RELEASED"
    ;;
  status)
    if [ -d "$GRIND_LOCK" ]; then
      echo "held pid=$(cat "$GRIND_LOCK/pid" 2>/dev/null) window=$(cat "$GRIND_LOCK/window" 2>/dev/null) ts=$(cat "$GRIND_LOCK/ts" 2>/dev/null)"
    else echo "free"; fi
    ;;
  *) grind_die "usage: lock.sh {acquire WINDOW_ID|release|status}" ;;
esac
