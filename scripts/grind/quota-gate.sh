#!/usr/bin/env bash
# quota-gate.sh — THE single source of truth for "may /grind start another task?"
#
# The loop MUST consult this and obey the exit code. It is a script, not model
# judgment, precisely so the model cannot rationalize past the floor.
#
# Usage:
#   quota-gate.sh [TASK_TYPE] [--force]
#     TASK_TYPE  optional; if given, also checks the measured p90 %-drop for that
#                task type fits in the headroom above the floor (reserve budgeting).
#     --force    bypass the poll rate-limit and take a fresh reading (use at window-end).
#
# Exit codes (the loop branches on these):
#   0  GO            — proceed; budget OK
#   2  STOP_FLOOR    — 5h-left <= floor; end the window
#   3  STOP_WEEKLY   — week-left OR model-week-left <= hard-stop; end + do NOT chain
#   4  NO_NEW_TASK   — within reserve buffer, OR this TASK_TYPE won't fit; pick smaller / go to floor activity
#   5  STOP_KILL     — kill switch present
#   6  POLL_FAILED   — quota tool unreadable (fail safe: treat as STOP)
#   7  SOFT_PAUSE    — PAUSE sentinel present (/soft-pause): finish current task to its
#                      savepoint (commit / journal write), then PARK — do not kill agents,
#                      do not start anything new. Resume clears the sentinel.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"; cd "$ROOT" || exit 6
. "$HERE/config.sh"; . "$HERE/lib.sh"

TASK_TYPE=""; FORCE=0
for a in "$@"; do case "$a" in --force) FORCE=1;; *) TASK_TYPE="$a";; esac; done

if grind_killed; then grind_audit "quota_gate" "STOP_KILL (kill switch present)"; echo "STOP_KILL"; exit 5; fi

# Soft-pause: checked before any poll — pausing needs no quota reading. Drain
# semantics (finish current task to savepoint, park) are the CALLER's duty; this
# gate just refuses to green-light the next task while the sentinel exists.
if [ -f "$GRIND_PAUSE" ]; then
  grind_audit "quota_gate" "SOFT_PAUSE (PAUSE sentinel present; drain to savepoint and park)"
  echo "SOFT_PAUSE"; exit 7
fi

# --- rate-limited poll: reuse cached reading unless stale or --force ---
need_poll=1
if [ "$FORCE" = "0" ] && [ -f "$GRIND_QUOTA_CACHE" ]; then
  read -r _cfh _cwk _cwm cache_ts < <(grind_gj cache-read "$GRIND_QUOTA_CACHE")
  age=$(( $(grind_now) - ${cache_ts:-0} ))
  [ "$age" -lt "$GRIND_POLL_MIN_INTERVAL_SEC" ] && need_poll=0
fi

if [ "$need_poll" = "1" ]; then
  # !!! GRIND ENV TRAP !!! quota tool needs the WINDOWS python (pyte module) -- see config.sh
  raw="$("$GRIND_QUOTA_PYTHON" "$GRIND_QUOTA_TOOL" --json 2>/dev/null)" || true
  read -r fh wk wm < <(printf '%s' "$raw" | grind_gj quota-parse) || true
  if [ -z "${fh:-}" ] || [ -z "${wk:-}" ]; then
    grind_audit "quota_gate" "POLL_FAILED (tool unreadable; failing safe to STOP)"
    echo "POLL_FAILED"; exit 6
  fi
  grind_gj cache-write "$GRIND_QUOTA_CACHE" "$fh" "$wk" "${wm:--1}"
else
  read -r fh wk wm _ < <(grind_gj cache-read "$GRIND_QUOTA_CACHE")
fi
wm="${wm:--1}"

# --- thresholds (integer percent comparisons) ---
if [ "$wk" -le "$GRIND_HARD_STOP_WEEK_PCT" ]; then
  grind_audit "quota_gate" "STOP_WEEKLY week_left=${wk}% (<= ${GRIND_HARD_STOP_WEEK_PCT})"
  echo "STOP_WEEKLY week_left=${wk}"; exit 3
fi
# Per-model weekly bar (e.g. "Current week (Fable)") — usually the FIRST to
# exhaust. wm < 0 = tool didn't report it (older reading); skip, don't guess.
if [ "$wm" -ge 0 ] && [ "$wm" -le "$GRIND_HARD_STOP_WEEK_MODEL_PCT" ]; then
  grind_audit "quota_gate" "STOP_WEEKLY week_model_left=${wm}% (<= ${GRIND_HARD_STOP_WEEK_MODEL_PCT})"
  echo "STOP_WEEKLY week_model_left=${wm}"; exit 3
fi
if [ "$fh" -le "$GRIND_FLOOR_5H_PCT" ]; then
  grind_audit "quota_gate" "STOP_FLOOR five_hour_left=${fh}% (<= ${GRIND_FLOOR_5H_PCT})"
  echo "STOP_FLOOR five_hour_left=${fh}"; exit 2
fi

buffer_floor=$(( GRIND_FLOOR_5H_PCT + GRIND_RESERVE_BUFFER_PCT ))
if [ "$fh" -le "$buffer_floor" ]; then
  grind_audit "quota_gate" "NO_NEW_TASK reserve-buffer five_hour_left=${fh}% (<= ${buffer_floor})"
  echo "NO_NEW_TASK reserve five_hour_left=${fh}"; exit 4
fi

# --- reserve budgeting: does this task TYPE fit the headroom above the floor? ---
if [ -n "$TASK_TYPE" ]; then
  headroom=$(( fh - GRIND_FLOOR_5H_PCT ))
  need="$("$HERE/cost-table" p90 "$TASK_TYPE")"   # measured p90 %-drop (or conservative default)
  if [ "$headroom" -lt "$need" ]; then
    grind_audit "quota_gate" "NO_NEW_TASK type=${TASK_TYPE} need=${need}% headroom=${headroom}% (five_hour_left=${fh})"
    echo "NO_NEW_TASK type=${TASK_TYPE} need=${need} headroom=${headroom}"; exit 4
  fi
fi

grind_audit "quota_gate" "GO five_hour_left=${fh}% week_left=${wk}% week_model_left=${wm}% type=${TASK_TYPE:-none}"
echo "GO five_hour_left=${fh} week_left=${wk} week_model_left=${wm}"; exit 0
