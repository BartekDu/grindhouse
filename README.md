# grindhouse

The GRIND ENGINE and its works — canonical home of the guardrail law scripts and
the seven-skill family that turns a Claude Code machine into a virtual
development office.

```
GRIND ENGINE (scripts/grind/* law, .claude/grind/ per-repo state, 5h windows, audit chain)
 ├ /grind        burn mode — fill the window, stop at the quota floor
 ├ /semi-grind   supervised standardization — quiz-gated taste forks
 └ /sprint       scope-bound delivery — clarity gate → quiz → plan+codex →
                 team manifest → waves in worktrees → DONE = STOP
supporting cast
 ├ /soft-pause   drain-to-savepoint pause; power-cut recovery (quota-gate exit 7)
 ├ /quota        usage reader (5h / week / per-model week) + PAUSE precaution
 ├ /grind-office read-only dashboard — the office at a glance
 └ /culture      the development-culture framework (seed + audit)
```

## Layout

| Path | What |
|---|---|
| `scripts/grind/` | **The law.** quota-gate (floor/weekly/model-weekly/reserve/kill/PAUSE), scope-guard (focus globs + worktree law, pre-commit), landable-guard (pre-push), commit-msg-guard (commit-msg, conventional messages), value-gate, verify-run (per-repo `verify-cmds`, else auto-detected gates), lock, hygiene-check, cost-table, audit-verify (hash chain), swarm-claim (gh-issue ownership board), selftest (the whole matrix, no network/auth), grindjson.py, grind-bootstrap.sh, **the contribution law**: mirror-guard + mirror-hook (live install is read-only), anon-guard (added-lines-only leak scan), contribute (the one command that ships an improvement as a PR) |
| `skills/<name>/` | The seven skills (SKILL.md policy files + helpers; `skills/quota/` carries the `claude_usage.py` backup) |
| `install.sh` | Sync this repo → `~/.claude/skills` (the live install) |

## Per-repo configuration (all optional)

The law bundle is **project-agnostic**; anything project-specific lives in the
target repo, never in the scripts:

- `<repo>/.claude/grind/project.conf` — shell vars sourced by `config.sh`:
  `GRIND_BASE_BRANCH`, `GRIND_PROTECTED_BRANCHES`, `GRIND_EXTRA_IGNORES`,
  `GRIND_VALUE_EXTRA_RE`. Example for Underline:
  `docs/examples/underline.project.conf`.
- `<repo>/.claude/grind/verify-cmds` — one verification command per line
  (`#` comments). When absent, `verify-run` auto-detects gates from the project
  type (npm/yarn/pnpm scripts, pytest/ruff/mypy, cargo, go, manage.py,
  `make test`); when NOTHING is detectable it exits 3 (= UNVERIFIED, not green).

Prove the law after any change: `bash scripts/grind/selftest` (no network, no
Claude auth — quota-gate runs against a faked cache). CI runs the same matrix
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
- **Back-pressure (the contribution law):** the sync is one-way, so the live
  install is **read-only**. `mirror-hook` (a `PreToolUse` hook) denies edits
  under `~/.claude/skills`; `mirror-guard check|import` detects and rescues
  drift; `anon-guard` scans the outgoing diff's ADDED lines for client names,
  machine paths and secrets; `contribute` runs all of it and opens the PR.
  Commercial use of this engine is licensed against contributing improvements
  back, anonymized — full rationale and the daily shape in
  [`docs/contribution-law.md`](docs/contribution-law.md).
- **Quota tool:** `skills/quota/claude_usage.py` IS the executed tool —
  `install.sh` ships it to `~/.claude/skills/quota/`, grind's `config.sh`
  auto-resolves `GRIND_QUOTA_TOOL` (repo-vendored copy wins, else the installed
  skill; env/project.conf override), and the background loggers (Linux systemd
  timer in `skills/quota/systemd/`, Windows `ClaudeQuotaLog` task) invoke the
  installed copy. The old 4-place desktop-path coupling is dead.

## Constitution (from /culture — applies to this repo too)

1. Every rule cites the incident that created it.
2. Rules die when they stop paying rent (collapse pass).
3. Enforcement lives in scripts and stable-ID registers, not prose.
4. Knowledge is promoted to durable artifacts before compaction eats it.

Born 2026-07-10 from the grind-engine-v2 plan. History before that date lives in
the Underline repo (`feature/grind-skill`, PR #117) and `~/.claude` snapshots.
