# Staffing — difficulty → model × effort (engine-wide)

Canonical matrix for ALL graded modes (/grind, /semi-grind, /sprint). Moved here from
sprint's SKILL.md (2026-07-11) so grind/semi-grind councils staff the same way. Wired into
`Agent` / Workflow `agent()` via `opts.model` + `opts.effort`.

**Guiding principle (owner, 2026-07-11): match on the OUTPUT QUALITY the task needs, not on
burn.** Cost is a constraint (the quota gate + the downgrade rule below), never the objective.

## The matrix

| Work | Model | Effort |
|---|---|---|
| web/repo/doc scouting, log trawls | sonnet | medium |
| mechanical bulk edits, formatting, chunk extraction | haiku | low |
| build/verify runs, test authoring | sonnet | high |
| architecture, taste, merge conflicts, orchestration, GATE-class judgment | opus/fable | high/max |

Tie-break when unsure between tiers: the cheaper one for read-only roles, the stronger one for
anything that writes code the founder will review.

**Never:** opus/fable on mechanical scouting; haiku on architecture.

## Council defaults (/grind, /semi-grind)

| Role | Model | Effort | Why |
|---|---|---|---|
| Orchestrator | session model | session | main thread; only it may quiz the founder |
| Builder | sonnet | high | opus/fable for architecture-class slices |
| Verifier | haiku–sonnet | low–medium | cheap adversarial, 1 per builder |
| Scout | sonnet | medium | read-only backlog refresh |

semi-grind fan-outs: consistency-lens = sonnet/medium; EVOLVE 4-lens = opus/high;
mechanical fix builders = haiku–sonnet per the matrix.

## Quota-aware downgrade (limits ↔ staffing coupling)

Before staffing a wave, read `.claude/grind/.quota-cache.json` (written by `quota-gate.sh`,
fresh within `GRIND_POLL_MIN_INTERVAL_SEC`). If the binding per-model weekly bar has
`<= GRIND_MODEL_DOWNGRADE_PCT`% left (threshold in `config.sh` — do not restate the number):

- **non-GATE roles** drop one tier (opus→sonnet→haiku), OR staff onto a model whose weekly
  bar is healthier;
- **GATE-class judgment is NEVER downgraded** — defer the wave to the next weekly cycle
  instead, and log the deferral to the run log.

Record actual per-task quota deltas via `bash $G/cost-table record` so the matching gets
empirical over time.
