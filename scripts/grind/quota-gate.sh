#!/usr/bin/env bash
# quota-gate.sh — THE single source of truth for "may /grind start another task?"
#
# The loop MUST consult this and obey the exit code. It is a script, not model
# judgment, precisely so the model cannot rationalize past the floor.
#
# Source: the newest reading in GRIND_QUOTA_READINGS (cc-ledger's
# cc-statusline.py records the 5h/week meters Claude Code hands the status
# line; cc-usage-probe.py records them from the /usage endpoint, source="oauth").
# With no fresh reading the gate first runs GRIND_QUOTA_PROBE once (see config.sh)
# and re-reads once. Optional adapter: GRIND_QUOTA_TOOL (a command printing
# {five_hour_pct_left, week_pct_left, week_model_pct_left} JSON).
#
# Usage:
#   quota-gate.sh [TASK_TYPE] [--force]
#     TASK_TYPE  optional; if given, also checks the measured p90 %-drop for that
#                task type fits in the headroom above the floor (reserve budgeting).
#     --force    accepted for old callers; a no-op (every call reads the newest reading).
#   quota-gate.sh --next-window
#     prints "CHAIN <epoch> <local-iso>" (exit 0) = when to schedule the next
#     window, or "NO_CHAIN <reason>" (exit 3) = do not chain (run_opts.chain
#     false, or the next window would start after the hard stop / week reset).
#
# Exit codes (the loop branches on these):
#   0  GO            — proceed; budget OK
#   2  STOP_FLOOR    — 5h-left <= floor; end the window
#   3  STOP_WEEKLY   — week-left OR model-week-left <= hard-stop, OR the campaign
#                      hard stop (GRIND_HARD_STOP_AT / run_opts.hard_stop_at /
#                      GRIND_STOP_BEFORE_WEEK_RESET_MIN) is reached; end + do NOT chain
#   4  NO_NEW_TASK   — within reserve buffer, OR this TASK_TYPE won't fit; pick smaller / go to floor activity
#   5  STOP_KILL     — kill switch present
#   6  POLL_FAILED   — no fresh reading (missing file / stale / from before the 5h
#                      reset) even after the one probe run; fail safe: treat as STOP.
#                      Caller: do one turn, retry once; a second POLL_FAILED = Window-end.
#   7  SOFT_PAUSE    — PAUSE sentinel present (/soft-pause): finish current task to its
#                      savepoint (commit / journal write), then PARK — do not kill agents,
#                      do not start anything new. Resume clears the sentinel.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"; cd "$ROOT" || exit 6
. "$HERE/config.sh"; . "$HERE/lib.sh"

TASK_TYPE=""; NEXT=0
for a in "$@"; do case "$a" in --force) ;; --next-window) NEXT=1;; *) TASK_TYPE="$a";; esac; done

# Effective hard stop: project.conf/env AND the run's --until (state.json
# .run_opts.hard_stop_at); grindjson takes the earliest of a comma list.
run_until="$(grind_state_get run_opts.hard_stop_at 2>/dev/null)"
HARD_STOP="${GRIND_HARD_STOP_AT}${run_until:+,$run_until}"; HARD_STOP="${HARD_STOP#,}"

if [ "$NEXT" = "1" ]; then
  case "$(grind_state_get run_opts.chain 2>/dev/null)" in False|false|0) no_chain=1;; *) no_chain=0;; esac
  if [ "$no_chain" = "1" ]; then
    grind_audit "quota_gate" "NO_CHAIN (run_opts.chain=false, --no-chain)"
    echo "NO_CHAIN --no-chain"; exit 3
  fi
  out="$(grind_gj next-window "$GRIND_QUOTA_READINGS" "$HARD_STOP" "$GRIND_STOP_BEFORE_WEEK_RESET_MIN")"; rc=$?
  grind_audit "quota_gate" "$out"
  echo "$out"; exit "$rc"
fi

if grind_killed; then grind_audit "quota_gate" "STOP_KILL (kill switch present)"; echo "STOP_KILL"; exit 5; fi

# Soft-pause: checked before any reading — pausing needs no quota. Drain
# semantics (finish current task to savepoint, park) are the CALLER's duty; this
# gate just refuses to green-light the next task while the sentinel exists.
if [ -f "$GRIND_PAUSE" ]; then
  grind_audit "quota_gate" "SOFT_PAUSE (PAUSE sentinel present; drain to savepoint and park)"
  echo "SOFT_PAUSE"; exit 7
fi

# --- read the meters ---
if [ -n "$GRIND_QUOTA_TOOL" ]; then
  src="tool"; age=0
  case "$GRIND_QUOTA_TOOL" in
    *.py) raw="$("$GRIND_PYTHON" "$GRIND_QUOTA_TOOL" --json 2>/dev/null)" || true ;;
    *)    raw="$("$GRIND_QUOTA_TOOL" --json 2>/dev/null)" || true ;;
  esac
  read -r fh wk wm < <(printf '%s' "$raw" | grind_gj quota-parse) || true
  if [ -z "${fh:-}" ] || [ -z "${wk:-}" ]; then
    grind_audit "quota_gate" "POLL_FAILED (src=tool $GRIND_QUOTA_TOOL unreadable; failing safe to STOP)"
    echo "POLL_FAILED src=tool"; exit 6
  fi
  hs="$(grind_gj hard-stop "$HARD_STOP")"
else
  src="statusline"
  read_meters() { out="$(grind_gj quota-read "$GRIND_QUOTA_READINGS" "$GRIND_READING_MAX_AGE_SEC" "$HARD_STOP" "$GRIND_STOP_BEFORE_WEEK_RESET_MIN")"; }
  read_meters; rc=$?
  probe_note=""
  if [ "$rc" -ne 0 ] && [ -n "$GRIND_QUOTA_PROBE" ]; then
    # no fresh reading: ask the probe ONCE (any failure is ignored), then re-read ONCE
    probe_script="${GRIND_QUOTA_PROBE%% --*}"; probe_args="${GRIND_QUOTA_PROBE#"$probe_script"}"
    if [ -f "$probe_script" ]; then
      case "$probe_script" in *.py) probe_cmd=("$GRIND_PYTHON" "$probe_script");; *) probe_cmd=("$probe_script");; esac
      command -v timeout >/dev/null 2>&1 && probe_cmd=(timeout 30 "${probe_cmd[@]}")
      # shellcheck disable=SC2086  # probe_args is a flag list, split on purpose
      perr="$("${probe_cmd[@]}" $probe_args --readings "$GRIND_QUOTA_READINGS" 2>&1 >/dev/null)"; prc=$?
      grind_audit "quota_probe" "rc=${prc} ${probe_script##*/}${perr:+ ($(printf '%s' "$perr" | head -n1 | cut -c1-120))}"
      probe_note="; probe rc=${prc}"
      read_meters; rc=$?
    fi
  fi
  if [ "$rc" -ne 0 ]; then
    grind_audit "quota_gate" "POLL_FAILED (src=statusline: ${out#FAIL }${probe_note}; failing safe to STOP)"
    echo "POLL_FAILED src=statusline ${out#FAIL }"; exit 6
  fi
  read -r fh wk wm age hs src <<< "$out"      # src = the record's own source: statusline | oauth
  src="${src:-statusline}"
fi
wm="${wm:--1}"; hs="${hs:-0}"
# grind-office reads this snapshot (no gate run needed to show the bars)
grind_gj cache-write "$GRIND_QUOTA_CACHE" "$fh" "$wk" "$wm" 2>/dev/null || true

# --- campaign hard stop: STOP_WEEKLY, so no further window is chained ---
if [ "$hs" != "0" ]; then
  grind_audit "quota_gate" "STOP_WEEKLY hard_stop=${hs} (${HARD_STOP:-week reset -${GRIND_STOP_BEFORE_WEEK_RESET_MIN}min}) src=${src}"
  echo "STOP_WEEKLY hard_stop=${hs}"; exit 3
fi

# --- thresholds (integer percent comparisons) ---
if [ "$wk" -le "$GRIND_HARD_STOP_WEEK_PCT" ]; then
  grind_audit "quota_gate" "STOP_WEEKLY week_left=${wk}% (<= ${GRIND_HARD_STOP_WEEK_PCT}) src=${src}"
  echo "STOP_WEEKLY week_left=${wk}"; exit 3
fi
# Per-model weekly bar (e.g. "Current week (Fable)") — usually the FIRST to
# exhaust. wm < 0 = the reading has no per-model bar; skip, don't guess.
if [ "$wm" -ge 0 ] && [ "$wm" -le "$GRIND_HARD_STOP_WEEK_MODEL_PCT" ]; then
  grind_audit "quota_gate" "STOP_WEEKLY week_model_left=${wm}% (<= ${GRIND_HARD_STOP_WEEK_MODEL_PCT}) src=${src}"
  echo "STOP_WEEKLY week_model_left=${wm}"; exit 3
fi
if [ "$fh" -le "$GRIND_FLOOR_5H_PCT" ]; then
  grind_audit "quota_gate" "STOP_FLOOR five_hour_left=${fh}% (<= ${GRIND_FLOOR_5H_PCT}) src=${src}"
  echo "STOP_FLOOR five_hour_left=${fh}"; exit 2
fi

buffer_floor=$(( GRIND_FLOOR_5H_PCT + GRIND_RESERVE_BUFFER_PCT ))
if [ "$fh" -le "$buffer_floor" ]; then
  grind_audit "quota_gate" "NO_NEW_TASK reserve-buffer five_hour_left=${fh}% (<= ${buffer_floor}) src=${src}"
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

# Keep this audit format: cc-ledger's cc-quota.py parses
# "five_hour_left=N% week_left=N% week_model_left=N%" (N may be -1).
grind_audit "quota_gate" "GO five_hour_left=${fh}% week_left=${wk}% week_model_left=${wm}% type=${TASK_TYPE:-none} src=${src} age=${age}s"
echo "GO five_hour_left=${fh} week_left=${wk} week_model_left=${wm} src=${src} age=${age}s"; exit 0
