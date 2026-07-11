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
GRIND_MODEL_DOWNGRADE_PCT=25    # staffing downgrade: when the binding per-model weekly bar has
                                # <= this % left, non-GATE roles drop one model tier
                                # (opus->sonnet->haiku); GATE-class judgment defers instead.
                                # See skills/grind/references/staffing.md (ratified 2026-07-11).
GRIND_MAX_WINDOWS=8             # auto-chain cap: founder-authorized 2026-06-03 for the v0.5-mobile
                                # self-chaining campaign (was 3). Weekly hard-stop is the real brake.
GRIND_MAX_CONCURRENT=4         # fan-out cap: parallel feature-builders per window (disjoint scope each)
GRIND_POLL_MIN_INTERVAL_SEC=600 # rate-limit /quota polls; reuse cached reading within this window

# --- paths (relative to repo root) ---
GRIND_DIR=".claude/grind"
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
