#!/usr/bin/env bash
# !!! GRIND CANONICAL CONFIG !!! — single source of truth for /grind thresholds.
#
# The autonomy floor lived inconsistently across docs (20 / 15 / 25). This file
# is the ONE place it is defined; SKILL.md, quota-gate.sh, and every other grind
# script source it. Change a threshold here, nowhere else. See
# .claude/skills/grind/SKILL.md and docs plan jazzy-crunching-naur.md.

# --- thresholds (percent of limit REMAINING) ---
GRIND_FLOOR_5H_PCT=10            # stop the window when five_hour_pct_left <= this
GRIND_HARD_STOP_WEEK_PCT=10     # weekly hard-stop: do NOT chain another window
GRIND_HARD_STOP_WEEK_MODEL_PCT=10  # per-model weekly hard-stop (week_model_pct_left, e.g. "Current
                                # week (Fable)"). That bar usually exhausts FIRST; before 2026-07-10
                                # the gate was blind to it. DORMANT unless the reading carries the
                                # optional week_model_used field (the statusline does not always
                                # get it) — Step 0 has the operator check /usage by hand once.
GRIND_RESERVE_BUFFER_PCT=5      # stop ACCEPTING new tasks at floor+buffer (15%)
GRIND_MAX_WINDOWS=8             # auto-chain cap: founder-authorized 2026-06-03 for the v0.5-mobile
                                # self-chaining campaign (was 3). Weekly hard-stop is the real brake.
GRIND_MAX_CONCURRENT=4         # fan-out cap: parallel feature-builders per window (disjoint scope each)
GRIND_TASK_DEADLINE_MIN=10      # one builder task = one commit within this many minutes (savepoint);
                                # wave-brief prints the absolute UTC deadline for the briefs
GRIND_READING_MAX_AGE_SEC=900   # a reading older than this is stale (the gate runs GRIND_QUOTA_PROBE once, else POLL_FAILED);
                                # the statusline re-records unchanged meters every 5 min while it runs

# --- main-root anchor (define BEFORE the overrides + paths that use it) ---
# A campaign has ONE state tree, at the MAIN worktree root. Builders run in
# linked worktrees (.claude/worktrees/grind-feat-*), where `rev-parse
# --show-toplevel` points at the worktree — anchoring state there gave every
# builder an EMPTY state and silently DISARMED the guards (incident: an
# out-of-focus `wip` commit passed clean inside a builder worktree; the
# worktree law forces builders INTO worktrees, so the law must reach them
# there). dirname(--git-common-dir) is the main worktree root from anywhere;
# the common dir may print relative (".git") in the main root, so resolve
# via cd.
grind_main_root() {
  local common
  common="$(git rev-parse --git-common-dir 2>/dev/null)" || { pwd; return; }
  case "$common" in
    /*) dirname "$common" ;;
    *)  ( cd "$(dirname "$common")" 2>/dev/null && pwd ) || pwd ;;
  esac
}
GRIND_MAIN_ROOT="$(grind_main_root)"

# --- per-repo project overrides (optional) ---
# The bundle is project-AGNOSTIC: anything project-specific comes from an
# optional shell-var file  <repo>/.claude/grind/project.conf  sourced here.
# Read from the MAIN root: project.conf is typically untracked, so it does not
# exist inside a linked worktree's toplevel.
# (Incident: value-gate/hygiene/landable hardcoded one product's backlog ids,
# scratch dirs and branch names — the bundle rejected every other repo's work.)
# Recognized vars (all optional; sensible defaults / auto-detection otherwise):
#   GRIND_BASE_BRANCH="main"            # campaign branches cut from + PR'd to this
#                                       # (default: origin/HEAD, else dev|main|master)
#   GRIND_PROTECTED_BRANCHES="main dev" # landable-guard refuses direct pushes to these
#                                       # (enforced only while a grind window is active)
#   GRIND_EXTRA_IGNORES="db.sqlite3 out/cache/"   # extra hygiene-check .gitignore entries
#   GRIND_VALUE_EXTRA_RE='PROJ-[0-9]+'  # extra value-gate objective-win id regex
#   GRIND_HARD_STOP_AT="2026-10-05T17:55+02:00"  # campaign hard stop (ISO, or HH:MM = today);
#                                       # from then on the gate answers STOP_WEEKLY (no chain)
#   GRIND_STOP_BEFORE_WEEK_RESET_MIN=5  # STOP_WEEKLY this many minutes before the weekly reset
#   GRIND_QUOTA_READINGS=/path/x.jsonl  # statusline readings file (default below)
#   GRIND_QUOTA_PROBE="/path/probe.py --write"  # refresh a stale reading once (default: cc-usage-probe.py if
#                                       # installed; set empty to turn the probe off)
#   GRIND_QUOTA_TOOL=/path/tool.py      # optional adapter: a command printing the old
#                                       # {five_hour_pct_left, week_pct_left, week_model_pct_left} JSON
# Verification gates live in <repo>/.claude/grind/verify-cmds (see verify-run).
# Example conf for the Underline repo: docs/examples/underline.project.conf.
if [ -f "$GRIND_MAIN_ROOT/.claude/grind/project.conf" ]; then
  . "$GRIND_MAIN_ROOT/.claude/grind/project.conf"
fi
GRIND_PROTECTED_BRANCHES="${GRIND_PROTECTED_BRANCHES-dev main master}"   # set EMPTY in project.conf to disable the push block

# --- paths (anchored at the MAIN worktree root via GRIND_MAIN_ROOT, above) ---
GRIND_DIR="$GRIND_MAIN_ROOT/.claude/grind"
GRIND_STATE="${GRIND_DIR}/state.json"
GRIND_RUNLOG="${GRIND_DIR}/run-log.md"
GRIND_GATELEDGER="${GRIND_DIR}/gate-ledger.md"
GRIND_AUDIT="${GRIND_DIR}/audit.log"
GRIND_COST="${GRIND_DIR}/cost-history.jsonl"
GRIND_STOP="${GRIND_DIR}/STOP"             # kill switch: presence => immediate STOP
GRIND_PAUSE="${GRIND_DIR}/PAUSE"           # soft-pause sentinel (/soft-pause): drain to savepoint, then park
GRIND_ACTIVE="${GRIND_DIR}/.active"        # present only while a window is running
GRIND_LOCK="${GRIND_DIR}/.lock"            # single-run lock dir (mkdir is atomic)
GRIND_QUOTA_CACHE="${GRIND_DIR}/.quota-cache.json"

# --- quota source ---
# The gate reads the meters Claude Code hands the status line, as recorded by
# cc-ledger's cc-statusline.py (one JSON reading per line; contract in
# grindjson.py quota-read). No nested `claude /usage` poll any more: it needed
# a terminal-emulator module, a second python on Windows, and hung on the folder-trust dialog in new
# folders. Override per repo in project.conf.
GRIND_QUOTA_READINGS="${GRIND_QUOTA_READINGS:-$HOME/.claude/tools/cc-quota.readings.jsonl}"
GRIND_HARD_STOP_AT="${GRIND_HARD_STOP_AT:-}"                 # empty = no campaign hard stop
GRIND_STOP_BEFORE_WEEK_RESET_MIN="${GRIND_STOP_BEFORE_WEEK_RESET_MIN:-}"   # empty = off
GRIND_QUOTA_TOOL="${GRIND_QUOTA_TOOL:-}"                     # empty = statusline readings
# Probe: when the newest reading is missing / stale / from before the 5h reset (the case that
# fails safe to POLL_FAILED), the gate runs this ONCE, then re-reads the readings once. It is
# cc-ledger's cc-usage-probe.py, which asks the endpoint /usage uses and appends a source="oauth"
# reading (no quota spent; works headless and right after a 5h reset). "<script> --write": a
# script ending in .py runs with GRIND_PYTHON; the gate adds `--readings $GRIND_QUOTA_READINGS`
# (a custom probe must accept it) and ignores any failure. Unset = that script if it exists;
# set EMPTY (env or project.conf) = off.
if [ "${GRIND_QUOTA_PROBE+set}" != "set" ]; then
  GRIND_QUOTA_PROBE=""
  [ -f "$HOME/.claude/tools/cc-usage-probe.py" ] && GRIND_QUOTA_PROBE="$HOME/.claude/tools/cc-usage-probe.py --write"
fi

# --- python ---
# grindjson.py (stdlib only) runs on the current shell's native python:
# git-bash on Windows -> `python`, Linux/macOS/WSL -> `python3`.
if [ -z "${GRIND_PYTHON:-}" ]; then
  case "${OSTYPE:-$(uname -s 2>/dev/null)}" in
    msys*|cygwin*|MINGW*|MSYS*) _gp="python python3" ;;
    *)                          _gp="python3 python" ;;
  esac
  for _p in $_gp; do
    if command -v "$_p" >/dev/null 2>&1; then GRIND_PYTHON="$_p"; break; fi
  done
  GRIND_PYTHON="${GRIND_PYTHON:-python3}"; unset _gp _p
fi

# Local git-bash has python but NOT jq, so all JSON ops route through grindjson.py.
GRIND_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
grind_gj() { "$GRIND_PYTHON" "$GRIND_SCRIPTS/grindjson.py" "$@"; }

# Resolve to repo root so scripts work from any cwd.
grind_repo_root() { git rev-parse --show-toplevel 2>/dev/null; }
