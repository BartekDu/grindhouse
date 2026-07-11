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
                                # the gate was blind to it — a Fable grind could burn the model week
                                # while the all-models bar looked fine.
GRIND_RESERVE_BUFFER_PCT=5      # stop ACCEPTING new tasks at floor+buffer (15%)
GRIND_MAX_WINDOWS=8             # auto-chain cap: founder-authorized 2026-06-03 for the v0.5-mobile
                                # self-chaining campaign (was 3). Weekly hard-stop is the real brake.
GRIND_MAX_CONCURRENT=4         # fan-out cap: parallel feature-builders per window (disjoint scope each)
GRIND_POLL_MIN_INTERVAL_SEC=600 # rate-limit /quota polls; reuse cached reading within this window

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

# --- external tools ---
# !!! GRIND ENV TRAP !!! These scripts run under BOTH git-bash (python = Windows
# python, C:/ paths OK) and WSL bash (only python3 + python.exe interop exist).
# Two DIFFERENT pythons are needed:
#   GRIND_PYTHON       runs grindjson.py (a local-repo path) -> must be the
#                      current shell's native python (git-bash python / WSL python3).
#   GRIND_QUOTA_PYTHON runs the quota tool, which imports `pyte` -- installed in
#                      the WINDOWS python only -> git-bash python / WSL python.exe.
# Getting this wrong fails the gate closed (POLL_FAILED) and no grind can start.
# Full history: see commit that added this block + docs/grind-campaigns/v0.5-mobile/PLAN.md.
if [ -z "${GRIND_PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then GRIND_PYTHON="python"
  elif command -v python3 >/dev/null 2>&1; then GRIND_PYTHON="python3"
  else GRIND_PYTHON="python"; fi
fi
if [ -z "${GRIND_QUOTA_PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then GRIND_QUOTA_PYTHON="python"
  elif command -v python.exe >/dev/null 2>&1; then GRIND_QUOTA_PYTHON="python.exe"
  else GRIND_QUOTA_PYTHON="$GRIND_PYTHON"; fi
fi
# Windows pythons (python / python.exe) take C:/ paths -- keep the Windows-style default.
GRIND_QUOTA_TOOL="${GRIND_QUOTA_TOOL:-C:/Users/b/Desktop/CF_domains/claude_usage.py}"

# Local git-bash has python but NOT jq, so all JSON ops route through grindjson.py.
GRIND_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
grind_gj() { "$GRIND_PYTHON" "$GRIND_SCRIPTS/grindjson.py" "$@"; }

# Resolve to repo root so scripts work from any cwd.
grind_repo_root() { git rev-parse --show-toplevel 2>/dev/null; }
