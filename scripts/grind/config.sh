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

# --- campaign key (grind assumed ONE campaign per repository; it no longer does) ---
# The state tree stays anchored at the main root — see grind_main_root above, and do
# NOT undo that: anchoring per-worktree gave builders an EMPTY state and silently
# disarmed the guards. What was actually wrong is narrower. The tree was keyed by
# REPOSITORY, so two concurrent campaigns shared one state.json, one focus, one PAUSE,
# one lock and one gate counter.
#
# Measured 2026-08-17, all three in a single afternoon: a QA session had the focus flip
# under it mid-run when a security campaign started, so its commits were refused by a
# contract it had never agreed to; its /soft-pause sentinel parked BOTH campaigns; and
# both minted a "G-13", because each independently computed max+1 over the same ledger.
# The two G-13s then merged CLEANLY — their rows sat in different sections — so nothing
# went red for a duplicate id. A shared counter between writers who cannot see each
# other has no solution; the fix is to stop sharing the counter.
#
# So: still the main root (the law reaches builders), now keyed by campaign (campaigns
# stop overwriting each other). A linked worktree resolves WHICH campaign owns it, so a
# builder still inherits its own campaign's focus and guards.
GRIND_ROOT_DIR="$GRIND_MAIN_ROOT/.claude/grind"     # shared by every campaign
GRIND_CAMPAIGNS_DIR="$GRIND_ROOT_DIR/campaigns"

# Resolution order. Each step is cheaper to be certain about than the next.
#   1. $GRIND_CAMPAIGN                    explicit; also settable in project.conf
#   2. <worktree>/.claude/grind-campaign  marker written when the worktree is created
#   3. exactly one campaign exists        unambiguous, so no marker is needed
#   4. no campaigns/ dir at all           legacy flat tree, behaviour unchanged
#   5. AMBIGUOUS                          several campaigns, no marker -> never guess
grind_resolve_campaign() {
  local wt marker n last d
  if [ -n "${GRIND_CAMPAIGN:-}" ]; then printf '%s' "$GRIND_CAMPAIGN"; return 0; fi

  wt="$(git rev-parse --show-toplevel 2>/dev/null)" || wt=""
  marker="$wt/.claude/grind-campaign"
  if [ -n "$wt" ] && [ -f "$marker" ]; then
    # tr -d '\r' because a marker written on Windows carries CRLF, and a campaign name
    # with a trailing CR names a directory that does not exist — indistinguishable from
    # "no campaign", which would fall through to the ambiguous branch for no reason.
    head -n 1 "$marker" | tr -d '\r\n'; return 0
  fi

  if [ -d "$GRIND_CAMPAIGNS_DIR" ]; then
    n=0; last=""
    for d in "$GRIND_CAMPAIGNS_DIR"/*/; do [ -d "$d" ] || continue; n=$((n+1)); last="$d"; done
    if [ "$n" = "1" ]; then basename "$last"; return 0; fi
    if [ "$n" = "0" ]; then printf ''; return 0; fi
    printf ''; return 2      # several, and nothing says which. The caller fails closed.
  fi
  printf ''                  # legacy: no campaigns/ dir, use the flat tree
}

GRIND_CAMPAIGN="$(grind_resolve_campaign)"; grind_campaign_rc=$?
# Reported here, ENFORCED by the guards, and the split is deliberate: config.sh is
# sourced by every hook, so exiting here would break unrelated commands. A guard that
# cannot tell which campaign's law applies must REFUSE — quietly picking one is how the
# disarmed-guard incident happened in the first place.
GRIND_CAMPAIGN_AMBIGUOUS=0
[ "$grind_campaign_rc" = "2" ] && GRIND_CAMPAIGN_AMBIGUOUS=1
unset grind_campaign_rc

# --- paths (anchored at the MAIN worktree root via GRIND_MAIN_ROOT, above) ---
if [ -n "$GRIND_CAMPAIGN" ]; then
  GRIND_DIR="$GRIND_CAMPAIGNS_DIR/$GRIND_CAMPAIGN"
else
  GRIND_DIR="$GRIND_ROOT_DIR"
fi
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
# !!! GRIND ENV TRAP !!! Two roles, resolved per-OS (override via env or
# project.conf for exotic setups — e.g. WSL driving a Windows-side claude
# needs GRIND_QUOTA_PYTHON=python.exe):
#   GRIND_PYTHON       runs grindjson.py -> the current shell's native python
#                      (git-bash `python`, Linux/macOS `python3`).
#   GRIND_QUOTA_PYTHON runs the quota tool (imports `pyte`) -> the python that
#                      has pyte installed. On Windows that was the Windows
#                      python only; on Linux one python3 serves both roles
#                      (`python3 -m pip install --user pyte`).
# Getting this wrong fails the gate closed (POLL_FAILED) and no grind can start.
case "${OSTYPE:-$(uname -s 2>/dev/null)}" in
  msys*|cygwin*|MINGW*|MSYS*)   # git-bash on Windows: `python` is the Windows python
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
    ;;
  *)                            # Linux / macOS / WSL shells: python3 first
    if [ -z "${GRIND_PYTHON:-}" ]; then
      if command -v python3 >/dev/null 2>&1; then GRIND_PYTHON="python3"
      elif command -v python >/dev/null 2>&1; then GRIND_PYTHON="python"
      else GRIND_PYTHON="python3"; fi
    fi
    if [ -z "${GRIND_QUOTA_PYTHON:-}" ]; then
      if command -v python3 >/dev/null 2>&1; then GRIND_QUOTA_PYTHON="python3"
      elif command -v python >/dev/null 2>&1; then GRIND_QUOTA_PYTHON="python"
      elif command -v python.exe >/dev/null 2>&1; then GRIND_QUOTA_PYTHON="python.exe"
      else GRIND_QUOTA_PYTHON="$GRIND_PYTHON"; fi
    fi
    ;;
esac
# Quota tool: repo-vendored copy wins (main root), else the installed skill —
# no machine-specific default path (the old C:/Users/... default was one
# machine's desktop; every other machine failed the gate closed). Override
# with GRIND_QUOTA_TOOL=... (env or project.conf) to point elsewhere.
if [ -z "${GRIND_QUOTA_TOOL:-}" ]; then
  if [ -f "$GRIND_MAIN_ROOT/.claude/skills/quota/claude_usage.py" ]; then
    GRIND_QUOTA_TOOL="$GRIND_MAIN_ROOT/.claude/skills/quota/claude_usage.py"
  else
    GRIND_QUOTA_TOOL="$HOME/.claude/skills/quota/claude_usage.py"
  fi
fi

# Local git-bash has python but NOT jq, so all JSON ops route through grindjson.py.
GRIND_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
grind_gj() { "$GRIND_PYTHON" "$GRIND_SCRIPTS/grindjson.py" "$@"; }

# Resolve to repo root so scripts work from any cwd.
grind_repo_root() { git rev-parse --show-toplevel 2>/dev/null; }
