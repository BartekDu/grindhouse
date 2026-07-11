#!/usr/bin/env bash
# !!! GRIND GLOBAL BOOTSTRAP !!! — makes /grind + /semi-grind work in ANY repo on
# this machine. Source it (don't exec) at Step 0 so it can export G into your shell:
#
#     source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh
#     echo "$G"            # -> resolved guardrail-script dir
#
# What it does:
#   1. Resolves G = the guardrail-script dir. Project-local `<repo>/scripts/grind`
#      WINS when present (a repo may keep its own committed, version-controlled
#      copy + lefthook wiring); otherwise the global bundle that ships with this
#      skill.
#   2. Ensures scope-guard (pre-commit) + landable-guard (pre-push) +
#      commit-msg-guard (commit-msg) are actually armed for THIS repo. The
#      guardrails are the law; a grind with no hooks is lawless. Idempotent:
#      already-wired repos (lefthook grind-* / a grind-marked git hook) are left
#      untouched; foreign hooks are never clobbered.
#
# Exit/return: sets G + GRIND_BOOTSTRAP_STATUS; prints a one-line status the model
# surfaces to the user before going autonomous. Returns non-zero only when it
# cannot find a repo or cannot write hooks (then the caller must stop).

GRIND_GLOBAL_BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_grind_repo_root() { git rev-parse --show-toplevel 2>/dev/null; }

grind_bootstrap() {
  local repo hookdir marker="!!! GRIND HOOK v2 !!!" legacy_marker="!!! GRIND HOOK !!!"
  repo="$(_grind_repo_root)"
  if [ -z "$repo" ]; then
    GRIND_BOOTSTRAP_STATUS="NOT_A_GIT_REPO"
    echo "grind-bootstrap: not inside a git repo — /grind needs one. Run from a repo." >&2
    return 2
  fi

  # 1. Resolve G: project-local copy wins, else the global bundle.
  if [ -x "$repo/scripts/grind/quota-gate.sh" ]; then
    G="$repo/scripts/grind"
    local g_origin="project"
  else
    G="$GRIND_GLOBAL_BUNDLE"
    local g_origin="global-bundle"
  fi
  export G
  mkdir -p "$repo/.claude/grind" 2>/dev/null || true   # state tree (lock.sh re-mkdirs; this lets pre-acquire audit appends not crash)

  # 2. Ensure the three guardrail hooks are armed for this repo.
  local wired="no"
  # 2a. lefthook wiring (repo manages its own hooks) — already managed, leave it.
  if [ -f "$repo/lefthook.yml" ] && grep -q 'grind-scope-guard' "$repo/lefthook.yml" 2>/dev/null; then
    wired="lefthook"
  fi
  hookdir="$(git rev-parse --git-path hooks 2>/dev/null)"
  [ -z "$hookdir" ] && hookdir="$repo/.git/hooks"

  if [ "$wired" = "no" ]; then
    mkdir -p "$hookdir" 2>/dev/null || { GRIND_BOOTSTRAP_STATUS="HOOKDIR_UNWRITABLE"; echo "grind-bootstrap: cannot write $hookdir" >&2; return 3; }
    # Two passes, ALL-OR-NOTHING: first classify every hook (v2 ok / v1 upgrade /
    # absent install / foreign conflict) WITHOUT writing; any conflict aborts the
    # whole install so a failed bootstrap never leaves the repo partially armed
    # (pre-fix, a pre-commit conflict still installed pre-push + commit-msg).
    local todo=() present=() conflict=() hook name state
    for hook in pre-commit:scope-guard pre-push:landable-guard commit-msg:commit-msg-guard; do
      name="${hook#*:}"; hook="${hook%%:*}"
      if grep -q "$marker" "$hookdir/$hook" 2>/dev/null; then
        present+=("$hook")
      elif grep -q "$legacy_marker" "$hookdir/$hook" 2>/dev/null; then
        todo+=("$hook:$name:upgrade")
      elif [ -f "$hookdir/$hook" ]; then
        conflict+=("$hook")
      else
        todo+=("$hook:$name:new")
      fi
    done
    if [ "${#conflict[@]}" -gt 0 ]; then
      GRIND_BOOTSTRAP_STATUS="HOOK_CONFLICT:${conflict[*]}"
      echo "grind-bootstrap: G=$G ($g_origin); existing non-grind hook(s) [${conflict[*]}] in $hookdir — NOT clobbered, NOTHING installed." >&2
      echo "  Add manually:  pre-commit -> 'bash $G/scope-guard'   pre-push -> 'bash $G/landable-guard'   commit-msg -> 'bash $G/commit-msg-guard'" >&2
      return 4
    fi
    local installed=() item
    for item in "${todo[@]}"; do
      hook="${item%%:*}"; name="${item#*:}"; state="${name#*:}"; name="${name%%:*}"
      _grind_write_hook "$hookdir/$hook" "$name" "$marker"
      installed+=("$hook($state)")
    done
    if [ "${#installed[@]}" -gt 0 ]; then
      wired="git-hook(${installed[*]})"
    else
      wired="git-hook"
    fi
  fi

  GRIND_BOOTSTRAP_STATUS="OK"
  echo "grind-bootstrap: G=$G ($g_origin) · guardrails armed via $wired · repo=$repo"
  return 0
}

# Write a grind guardrail git hook. The guardrail path is resolved at RUNTIME
# (v1 baked an absolute path — moving ~/.claude/skills bricked every armed repo
# with exit 127 on commit/push): repo-local scripts/grind wins (same order as
# the $G resolution above), else the global bundle via $HOME. Missing bundle:
# fail-CLOSED while a grind window is active (a window without its law must
# stop), fail-OPEN with a warning otherwise (the user's normal work is never
# held hostage by a moved directory). Caller has already resolved conflicts.
_grind_write_hook() {
  local path="$1" name="$2" marker="$3"
  cat > "$path" <<EOF
#!/usr/bin/env bash
# $marker  (installed by grind-bootstrap.sh; safe to delete to disarm)
# Resolves the guardrail at runtime: repo-local scripts/grind, else the global
# bundle. Missing bundle: fail-closed during an active grind window, else warn+skip.
root="\$(git rev-parse --show-toplevel 2>/dev/null)"
common="\$(git rev-parse --git-common-dir 2>/dev/null)"
case "\$common" in /*) main="\$(dirname "\$common")";; *) main="\$root";; esac
for d in "\$root/scripts/grind" "\$HOME/.claude/skills/grind/scripts/grind"; do
  [ -f "\$d/$name" ] && exec bash "\$d/$name" "\$@"
done
if [ -n "\$main" ] && [ -f "\$main/.claude/grind/.active" ]; then
  echo "grind hook ($name): guardrail bundle MISSING while a grind window is ACTIVE — failing closed" >&2
  exit 1
fi
echo "grind hook ($name): guardrail bundle not found (~/.claude/skills/grind moved?) — skipping; delete this hook to silence" >&2
exit 0
EOF
  chmod +x "$path" 2>/dev/null || true
  return 0
}

# Auto-run when sourced so callers just `source` and read \$G.
grind_bootstrap
