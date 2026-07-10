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
| `scripts/grind/` | **The law.** quota-gate (floor/weekly/model-weekly/reserve/kill/PAUSE), scope-guard (focus globs + worktree law, pre-commit), landable-guard (pre-push), value-gate, lock, hygiene-check, cost-table, audit-verify (hash chain), swarm-claim (gh-issue ownership board), grindjson.py, grind-bootstrap.sh |
| `skills/<name>/` | The seven skills (SKILL.md policy files + helpers; `skills/quota/` carries the `claude_usage.py` backup) |
| `install.sh` | Sync this repo → `~/.claude/skills` (the live install) |

## Sync model (canonical → mirrors)

- **Canonical:** this repo. Every change lands here first.
- **Live install:** `bash install.sh` → `~/.claude/skills/` (what sessions run).
- **Vendored downstream:** product repos that commit their own `scripts/grind/`
  copy for lefthook wiring (Underline: PR #117) — re-vendor with
  `cp -f scripts/grind/* <repo>/scripts/grind/`, but NEVER copy
  `grind-bootstrap.sh` into a product repo (it is the global entrypoint that
  RESOLVES repo-local vs global; inside a repo it has no meaning).
- **Live quota tool:** `C:/Users/b/Desktop/CF_domains/claude_usage.py` is what
  callers execute (4-place path coupling — see `skills/quota/DEPENDENCIES.md`);
  `skills/quota/claude_usage.py` is the tracked byte-identical backup.

## Constitution (from /culture — applies to this repo too)

1. Every rule cites the incident that created it.
2. Rules die when they stop paying rent (collapse pass).
3. Enforcement lives in scripts and stable-ID registers, not prose.
4. Knowledge is promoted to durable artifacts before compaction eats it.

Born 2026-07-10 from the grind-engine-v2 plan. History before that date lives in
the Underline repo (`feature/grind-skill`, PR #117) and `~/.claude` snapshots.
