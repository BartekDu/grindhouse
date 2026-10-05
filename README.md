# grindhouse

The GRIND ENGINE and its works — canonical home of the guardrail law scripts and
the six-skill family that turns a Claude Code machine into a virtual
development office.

```
GRIND ENGINE (scripts/grind/* law, .claude/grind/ per-repo state, 5h windows, audit chain)
 ├ /grind        burn mode — fill the window, stop at the quota floor
 ├ /semi-grind   supervised standardization — quiz-gated taste forks
 └ /sprint       scope-bound delivery — clarity gate → quiz → plan+codex →
                 team manifest → waves in worktrees → DONE = STOP
supporting cast
 ├ /soft-pause   drain-to-savepoint pause; power-cut recovery (quota-gate exit 7)
 ├ /grind-office read-only dashboard — the office at a glance
 └ /culture      the development-culture framework (seed + audit)
```

## Layout

| Path | What |
|---|---|
| `scripts/grind/` | **The law.** quota-gate (statusline readings: floor/weekly/model-weekly/reserve/hard stop/kill/PAUSE), scope-guard (focus globs + worktree law, pre-commit), landable-guard (pre-push), commit-msg-guard (commit-msg, conventional messages), value-gate, verify-run (per-repo `verify-cmds`, else auto-detected gates), lock, hygiene-check, cost-table, audit-verify (hash chain), swarm-claim (gh-issue ownership board), run-opts (`/grind` quick-start flags in state.json), rules-init (per-repo `rules.md`), wave-brief (advisory budget brief from cc-ledger), profile.md (the learned working rules, one copy), selftest (the whole matrix, no network/auth), grindjson.py, grind-bootstrap.sh |
| `skills/<name>/` | The six skills (SKILL.md policy files + helpers) |
| `install.sh` | Sync this repo → `~/.claude/skills` (the live install) |

## Per-repo configuration (all optional)

The law bundle is **project-agnostic**; anything project-specific lives in the
target repo, never in the scripts:

- `<repo>/.claude/grind/project.conf` — shell vars sourced by `config.sh`:
  `GRIND_BASE_BRANCH`, `GRIND_PROTECTED_BRANCHES`, `GRIND_EXTRA_IGNORES`,
  `GRIND_VALUE_EXTRA_RE`, `GRIND_QUOTA_READINGS`, `GRIND_HARD_STOP_AT`,
  `GRIND_STOP_BEFORE_WEEK_RESET_MIN`, `GRIND_QUOTA_TOOL`. Example for Underline:
  `docs/examples/underline.project.conf`.
- `<repo>/.claude/grind/verify-cmds` — one verification command per line
  (`#` comments). When absent, `verify-run` auto-detects gates from the project
  type (npm/yarn/pnpm scripts, pytest/ruff/mypy, cargo, go, manage.py,
  `make test`); when NOTHING is detectable it exits 3 (= UNVERIFIED, not green).
- `<repo>/.claude/grind/rules.md` — the project's hard constraints (size limits,
  network exceptions, ...). The orchestrator pastes it into every builder and
  verifier brief; `/grind` Step 0 creates a skeleton when it is missing.

Prove the law after any change: `bash scripts/grind/selftest` (no network, no
Claude auth — quota-gate runs against fixture statusline readings). CI runs the same matrix
on every push/PR on ubuntu + windows git-bash
(`.github/workflows/selftest.yml`) — a fix that lands on one OS can no longer
silently regress the other.

## Sync model (canonical → mirrors)

- **Canonical:** this repo. Every change lands here first.
- **Live install:** `bash install.sh` → `~/.claude/skills/` (what sessions run).
- **Vendored downstream:** product repos that commit their own `scripts/grind/`
  copy for lefthook wiring (Underline: PR #117) — re-vendor with
  `cp -f scripts/grind/* <repo>/scripts/grind/`, but NEVER copy
  `grind-bootstrap.sh` into a product repo (it is the global entrypoint that
  RESOLVES repo-local vs global; inside a repo it has no meaning).
- **Quota source:** the statusline readings that cc-ledger's `cc-statusline.py`
  appends to `~/.claude/tools/cc-quota.readings.jsonl` (contract: cc-ledger
  `docs/READINGS.md`; parser: `grindjson.py quota-read`). Install cc-ledger's
  status line, or no grind can start (the gate fails closed with POLL_FAILED).
  There are no status line readings in headless `claude -p` runs, and the last one is stale
  after a 5h reset until the first API call: so when there is no fresh reading the gate runs
  `GRIND_QUOTA_PROBE` once (default: cc-ledger's `cc-usage-probe.py --write` if installed, which
  records a `source: "oauth"` reading from the `/usage` endpoint, no quota spent; empty = off)
  and re-reads once. A probe failure is ignored (still POLL_FAILED). `GRIND_QUOTA_TOOL` is an
  optional adapter for another source. The old `/quota` skill (nested
  `claude /usage` poll) is retired; `install.sh` backs up and removes an old
  install.

## Constitution (from /culture — applies to this repo too)

1. Every rule cites the incident that created it.
2. Rules die when they stop paying rent (collapse pass).
3. Enforcement lives in scripts and stable-ID registers, not prose.
4. Knowledge is promoted to durable artifacts before compaction eats it.

Born 2026-07-10 from the grind-engine-v2 plan. History before that date lives in
the Underline repo (`feature/grind-skill`, PR #117) and `~/.claude` snapshots.
