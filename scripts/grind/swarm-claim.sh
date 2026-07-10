#!/usr/bin/env bash
# swarm-claim.sh — cross-swarm backlog-ownership law. When TWO agent swarms (this
# machine + a teammate's, or two founders) work the same repo, local locks can't
# see each other — the coordination medium is GitHub: one open issue per live
# swarm, labeled `swarm-claim`, declaring WHO owns WHICH focus globs until WHEN.
#
# Same-machine concurrency is already covered by lock.sh + the run-log table;
# this script only matters across checkouts/users. Design seed: Fable's
# suggestion to coordinate swarms through gh issues as an ownership board.
#
# Usage:
#   swarm-claim.sh claim              — post/refresh MY claim (globs from state.json focus)
#   swarm-claim.sh check              — any LIVE foreign claim overlap my globs? exit 2 if so
#   swarm-claim.sh renew              — bump my claim's window_end (call at window chaining)
#   swarm-claim.sh release            — close my claim issue (campaign end / soft-pause)
#
# Exit codes:
#   0  OK / LOCAL_ONLY (no gh, no remote, no issue perms — degrade, never block)
#   1  usage / unexpected error
#   2  CLAIM_CONFLICT — a live foreign claim overlaps my focus globs; narrow scope
#      or negotiate via a comment on the conflicting issue before proceeding.
#
# Team-player duties (prompt-side, but restated here): check before claiming;
# treat foreign globs like your own forbidden_globs; comment before reclaiming a
# stale claim; release promptly — a swarm that hoards globs it isn't working is
# not a team player.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"; cd "$ROOT" || exit 1
. "$HERE/config.sh"; . "$HERE/lib.sh"

CMD="${1:-}"
[ -z "$CMD" ] && { echo "usage: swarm-claim.sh {claim|check|renew|release}" >&2; exit 1; }

LABEL="swarm-claim"
STALE_GRACE_SEC=$(( 6 * 3600 ))   # claim whose window_end passed > this ago = stale/reclaimable

# --- graceful degradation: no gh / no remote / no issue access → LOCAL_ONLY ---
if ! command -v gh >/dev/null 2>&1; then
  grind_audit "swarm_claim" "LOCAL_ONLY (no gh CLI) cmd=$CMD"
  echo "LOCAL_ONLY no-gh"; exit 0
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  grind_audit "swarm_claim" "LOCAL_ONLY (no origin remote) cmd=$CMD"
  echo "LOCAL_ONLY no-remote"; exit 0
fi
if ! gh issue list --label "$LABEL" --state open --json number --limit 1 >/dev/null 2>&1; then
  # covers: no issues perms, label queries forbidden, offline. Fail OPEN — a
  # private solo repo must never be blocked by the team-coordination layer.
  grind_audit "swarm_claim" "LOCAL_ONLY (gh issue list failed) cmd=$CMD"
  echo "LOCAL_ONLY gh-unreachable"; exit 0
fi

session_id="$(grind_state_get swarm.session_id)"
if [ -z "$session_id" ]; then
  session_id="swarm-$(hostname 2>/dev/null || echo host)-$$-$(grind_now)"
  grind_state_set swarm.session_id "\"$session_id\""
fi
my_issue="$(grind_state_get swarm.claim_issue)"
campaign="$(grind_state_get campaign_branch)"
my_globs="$(grind_gj focus-globs "$GRIND_STATE" allowed)"

claim_body() {
  # machine-parseable body; window_end = now + 5h (one window) unless renewing longer
  local wend
  wend="$(( $(grind_now) + 5*3600 ))"
  printf '%s\n' \
    '<!-- swarm-claim v1 — machine-parseable; edit via swarm-claim.sh only -->' \
    "session: ${session_id}" \
    "machine: $(hostname 2>/dev/null || echo unknown)" \
    "branch: ${campaign:-unknown}" \
    "window_end_epoch: ${wend}" \
    'globs:' \
    "$(printf '%s\n' "$my_globs" | sed 's/^/- /')"
}

case "$CMD" in
  claim|renew)
    if [ -n "$my_issue" ] && gh issue view "$my_issue" --json state -q .state 2>/dev/null | grep -qi open; then
      gh issue edit "$my_issue" --body "$(claim_body)" >/dev/null 2>&1 || true
      grind_audit "swarm_claim" "RENEWED issue=#$my_issue session=$session_id"
      echo "RENEWED #$my_issue"; exit 0
    fi
    # ensure the label exists (create fails otherwise); --force = idempotent
    gh label create "$LABEL" --description "live agent-swarm backlog-ownership claim (swarm-claim.sh)" \
      --color FBCA04 --force >/dev/null 2>&1 || true
    url="$(gh issue create --title "[swarm-claim] ${session_id}" --label "$LABEL" \
          --body "$(claim_body)" 2>/dev/null)" || {
      grind_audit "swarm_claim" "LOCAL_ONLY (issue create failed)"
      echo "LOCAL_ONLY create-failed"; exit 0
    }
    num="${url##*/}"
    grind_state_set swarm.claim_issue "\"$num\""
    grind_audit "swarm_claim" "CLAIMED issue=#$num session=$session_id branch=${campaign:-unknown}"
    echo "CLAIMED #$num"; exit 0
    ;;

  release)
    if [ -n "$my_issue" ]; then
      gh issue close "$my_issue" --comment "swarm-claim released (campaign end / soft-pause)." >/dev/null 2>&1 || true
      grind_state_set swarm.claim_issue '""'
      grind_audit "swarm_claim" "RELEASED issue=#$my_issue session=$session_id"
      echo "RELEASED #$my_issue"
    else
      echo "RELEASED none"
    fi
    exit 0
    ;;

  check)
    foreign="$(gh issue list --label "$LABEL" --state open \
      --json number,title,body --limit 50 2>/dev/null)" || { echo "LOCAL_ONLY list-failed"; exit 0; }
    # overlap = my glob prefix (up to first wildcard) nests with a foreign one,
    # either direction. Conservative: prefix containment, not full glob algebra.
    # program from heredoc on stdin; DATA via argv — never mix the two on stdin
    # (same trap scope-guard documents).
    result="$("$GRIND_PYTHON" - "$session_id" "$my_globs" "$(grind_now)" "$STALE_GRACE_SEC" "$foreign" <<'PY'
import json, sys
session, my_raw, now, grace = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
issues = json.loads(sys.argv[5] or "[]")
def prefix(g):  # glob → literal prefix before first wildcard, dir-normalized
    for i, c in enumerate(g):
        if c in "*?[":
            return g[:i].rstrip("/")
    return g.rstrip("/")
def overlap(a, b):
    pa, pb = prefix(a), prefix(b)
    return pa.startswith(pb) or pb.startswith(pa)
mine = [g for g in my_raw.splitlines() if g.strip()]
conflicts, stale = [], []
for it in issues:
    body = it.get("body") or ""
    if f"session: {session}" in body:
        continue  # my own claim
    theirs, wend = [], 0
    for ln in body.splitlines():
        ln = ln.strip()
        if ln.startswith("- "):
            theirs.append(ln[2:].strip())
        elif ln.startswith("window_end_epoch:"):
            try: wend = int(ln.split(":", 1)[1])
            except ValueError: pass
    if wend and now - wend > grace:
        stale.append(it["number"]); continue  # stale → reclaimable, not blocking
    for m in mine:
        for t in theirs:
            if overlap(m, t):
                conflicts.append(f"#{it['number']} glob={t} vs mine={m}")
print("CONFLICT " + "; ".join(conflicts) if conflicts else "CLEAR", end="")
if stale: print(f" stale_reclaimable={','.join(map(str, stale))}", end="")
PY
)"
    case "$result" in
      CONFLICT*)
        grind_audit "swarm_claim" "CONFLICT $result"
        echo "$result" >&2
        echo "Fix: narrow focus globs, or negotiate via a comment on the conflicting issue." >&2
        exit 2
        ;;
      *)
        grind_audit "swarm_claim" "CLEAR $result"
        echo "$result"; exit 0
        ;;
    esac
    ;;

  *)
    echo "usage: swarm-claim.sh {claim|check|renew|release}" >&2; exit 1
    ;;
esac
