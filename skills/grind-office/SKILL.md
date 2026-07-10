---
name: grind-office
preamble-tier: 3
version: 1.0.0
description: |
  Read-only status dashboard for the GRIND ENGINE (the virtual development
  office): quota bars (5h / week / per-model week), active mode + window, this
  swarm's council + waves, foreign swarm-claims, open gates and DD-NNN
  decisions, PAUSE/STOP/lock sentinels, RESUME freshness, and environment
  diagnostics (two-python trap, quota tool, hooks, mirror sync). One command =
  the whole office at a glance. ZERO mutations — it never writes, claims,
  releases, or edits anything. Named grind-office so its allegiance to the
  grind engine is explicit.
  Use when asked to "grind office", "office status", "what's the swarm doing",
  "show the board", or "/grind-office".
triggers:
  - grind office
  - office status
  - show the board
  - what's the swarm doing
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - TaskList
  - TaskGet
---

# /grind-office — the office at a glance (read-only)

**Contract:** render ONE dashboard from on-disk state + read-only queries.
NEVER mutate: no claims, no releases, no sentinel changes, no state writes, no
fresh quota poll that would double-spend (reuse `.quota-cache.json` / the CSV;
only poll if both are stale >10 min AND the founder asked for fresh numbers).

## Sources → panels

| Panel | Source |
|---|---|
| quota | `.claude/grind/.quota-cache.json` (fh/wk/wm) else newest row of `~/.claude/quota_log.csv`; flag which bar binds (the per-model week usually exhausts first) |
| mode/window | `.claude/grind/state.json` (`.focus.label`, `.campaign_branch`, `.window_counter`) + which skill's register dir exists |
| swarms | this session: `state.json .sessions[]` + run-log concurrency manifest; foreign: `gh issue list --label swarm-claim --state open` (read-only; skip silently if no gh/remote) |
| team/waves | `state.json .sprint.team[]` / `.sprint.waves[]` when present; register progress line (`consistency-findings.md`) for semi-grind; TaskList board |
| gates | `.claude/grind/gate-ledger.md` open `- [ ]` rows + `<register-dir>/decisions-ledger.md` open `DD-NNN`s |
| sentinels | `PAUSE` / `STOP` existence; `lock.sh status`; `.active` |
| resume | `RESUME.md` mtime + first heading |
| diag | `config.sh` pythons resolvable? `GRIND_QUOTA_TOOL` path exists? git hooks contain scope-guard/landable-guard markers? `diff -q` canonical `scripts/grind` vs `~/.claude/skills/grind/scripts/grind` (minus grind-bootstrap.sh) |

## Output shape (always this box; omit empty panels with a `·  none` line)

```text
┌─ GRIND OFFICE ── <DD-MM-YYYY HH:MM> ──────────────────────┐
│ quota   5h ██████░░ 62%   week 48%   fable-wk 34% ⚠ binds │
│ mode    /sprint "payment retries"  window 2/<cfg>          │
│ swarms  this: grind-10-07-2026 (4 builders, 1 verifier)    │
│         foreign claims: none live · 1 stale (#118)         │
│ team    sprint-pm(fable/max) 2×builder(sonnet) scout(sonnet)│
│ waves   W2 ███░ 3/4 merged · W3 queued                     │
│ gates   G-03 needs:/cso · DD-7 deferred                    │
│ sentinel PAUSE:no STOP:no  lock:held(pid 1234)  active:yes │
│ resume  .claude/grind/RESUME.md (fresh, 14:05)             │
│ diag    pythons OK · quota tool OK · hooks armed · mirror OK│
└────────────────────────────────────────────────────────────┘
```

Below the box: one short line per anomaly worth action (stale claim, mirror
drift, POLL_FAILED history in the audit tail, PAUSE present, RESUME stale >24h)
— each phrased as "finding → suggested command", never executed.

## Rules for agents

- **Never** mutate anything — this skill is the one place in the engine that is
  guaranteed safe to run mid-campaign, mid-pause, or mid-someone-else's-window.
- **Never** trigger a fresh ~13s quota poll when a cached reading <10 min
  exists — reuse; the dashboard is a glance, not an audit.
- **Never** silently omit a red panel — sentinels present, mirror drift, or a
  binding model-week bar are the headline, not a footnote.
- **Always** show which quota bar BINDS (min of 5h/week/model-week vs their
  thresholds in `config.sh`) — the founder decision is always "how much runway".
