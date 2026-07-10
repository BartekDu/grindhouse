#!/usr/bin/env bash
# !!! GRIND GLOBAL BOOTSTRAP !!! — makes /grind + /semi-grind work in ANY repo on
# this machine. Source it (don't exec) at Step 0 so it can export G into your shell:
#
#     source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh
#     echo "$G"            # -> resolved guardrail-script dir
#
# What it does:
#   1. Resolves G = the guardrail-script dir. Project-local `<repo>/scripts/grind`
#      WINS when present (Underline keeps its committed, version-controlled copy +
#      lefthook wiring); otherwise the global bundle that ships with this skill.
#   2. Ensures scope-guard (pre-commit) + landable-guard (pre-push) are actually
#      armed for THIS repo. The guardrails are the law; a grind with no hooks is
#      lawless. Idempotent: already-wired repos (lefthook grind-* / a grind-marked
#      git hook) are left untouched.
#
# Exit/return: sets G + GRIND_BOOTSTRAP_STATUS; prints a one-line status the model
# surfaces to the founder before going autonomous. Returns non-zero only when it
# cannot find a repo or cannot write hooks (then the caller must stop).

GRIND_GLOBAL_BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_grind_repo_root() { git rev-parse --show-toplevel 2>/dev/null; }

grind_bootstrap() {
  local repo hookdir marker="!!! GRIND HOOK !!!"
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

  # 2. Ensure the two guardrail hooks are armed for this repo.
  local wired="no"
  # 2a. lefthook wiring (Underline path) — already managed, leave it.
  if [ -f "$repo/lefthook.yml" ] && grep -q 'grind-scope-guard' "$repo/lefthook.yml" 2>/dev/null; then
    wired="lefthook"
  fi
  hookdir="$(git rev-parse --git-path hooks 2>/dev/null)"
  [ -z "$hookdir" ] && hookdir="$repo/.git/hooks"
  # 2b. native git-hook wiring with our marker — already done.
  if [ "$wired" = "no" ] \
     && grep -ql "$marker" "$hookdir/pre-commit" 2>/dev/null \
     && grep -ql "$marker" "$hookdir/pre-push" 2>/dev/null; then
    wired="git-hook"
  fi

  if [ "$wired" = "no" ]; then
    mkdir -p "$hookdir" 2>/dev/null || { GRIND_BOOTSTRAP_STATUS="HOOKDIR_UNWRITABLE"; echo "grind-bootstrap: cannot write $hookdir" >&2; return 3; }
    local installed=() conflict=()
    _grind_install_hook "$hookdir/pre-commit"  "$G/scope-guard"    "$marker" && installed+=(pre-commit) || conflict+=(pre-commit)
    _grind_install_hook "$hookdir/pre-push"    "$G/landable-guard" "$marker" && installed+=(pre-push) || conflict+=(pre-push)
    if [ "${#conflict[@]}" -gt 0 ]; then
      wired="partial"
      GRIND_BOOTSTRAP_STATUS="HOOK_CONFLICT:${conflict[*]}"
      echo "grind-bootstrap: G=$G ($g_origin); existing non-grind hook(s) [${conflict[*]}] in $hookdir — NOT clobbered." >&2
      echo "  Add manually:  pre-commit -> 'bash $G/scope-guard'   pre-push -> 'bash $G/landable-guard'" >&2
      return 4
    fi
    wired="git-hook(new:${installed[*]})"
  fi

  GRIND_BOOTSTRAP_STATUS="OK"
  echo "grind-bootstrap: G=$G ($g_origin) · guardrails armed via $wired · repo=$repo"
  return 0
}

# Write a minimal git hook that execs a grind guardrail. Refuses (returns 1) if a
# foreign hook already exists, so we never clobber a user's own hook.
_grind_install_hook() {
  local path="$1" script="$2" marker="$3"
  if [ -f "$path" ] && ! grep -q "$marker" "$path" 2>/dev/null; then
    return 1   # foreign hook present — caller surfaces a manual-wire instruction
  fi
  cat > "$path" <<EOF
#!/usr/bin/env bash
# $marker  (installed by grind-bootstrap.sh; safe to delete to disarm)
exec bash "$script" "\$@"
EOF
  chmod +x "$path" 2>/dev/null || true
  return 0
}

# Auto-run when sourced so callers just `source` and read \$G.
grind_bootstrap
