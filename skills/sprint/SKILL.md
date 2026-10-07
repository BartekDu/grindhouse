---
name: sprint
preamble-tier: 3
version: 1.0.0
description: |
  Scope-bound task/feature delivery on the GRIND ENGINE — the third mode.
  /grind = burn to the quota floor (open-ended). /semi-grind = quiz-gated
  standardization. /sprint = "here is a task or feature: clarify it, plan it
  with a top model, staff it with models matched to difficulty, execute it in
  parallel waves in worktrees across quota-separated 5h windows, and STOP WHEN
  IT IS DONE." Vague spec → founder quiz rounds until the clarity gate passes.
  Reuses every /grind guardrail script + hook verbatim (scripts/grind/*);
  the plan gets a MANDATORY codex cross-model pass before wave 1.
  Use when asked to "sprint", "sprint this", "deliver this feature",
  "/sprint <task or feature>". NOT an open-ended burn (that = /grind) and NOT
  a standardization campaign (that = /semi-grind).
triggers:
  - sprint
  - sprint this
  - deliver this feature
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - Skill
  - TaskCreate
  - TaskUpdate
  - CronCreate
  - Workflow
---

# /sprint — scope-bound delivery on the grind engine

**Contract:** `/sprint <task or feature description>` = clarity-gate the spec (quiz
the founder until it passes), plan at high effort, staff a team manifest with
models matched to difficulty, execute in parallel waves (each wave = one Workflow
run, builders in worktrees), chain 5h windows while work remains — and **STOP when
the task is DONE**. The terminal condition is scope-complete, not quota-floor:
that is the whole difference from `/grind`. The founder opens the PR; the loop
never merges to `dev`/`main`.

**Taxonomy:** GRIND is the *engine* — `scripts/grind/*` law, `.claude/grind/`
state, 5h window chaining, the hash-chained audit log. The "campaign branch"
(`grind-DD-MM-YYYY`) is the run container every mode cuts. `/sprint` is the
engine's delivery mode; it reuses every guardrail verbatim (the hooks key off
`.claude/grind/.active`, not the skill name) and adds only: the clarity gate,
the quiz loop, the high-effort plan + codex pass, the team manifest with model
matching, and the done-means-stop terminal.

**The scripts are the law.** Same as its siblings: obey `quota-gate.sh` /
`scope-guard` / `landable-guard` / `value-gate` / `lock.sh` / `hygiene-check` /
`swarm-claim.sh` exit codes literally; thresholds live in
`scripts/grind/config.sh` (read, never restate). Resolve `$G` at S0 via
`source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh`; STOP on
non-zero — a sprint without hooks is lawless.

## When to use / when NOT

- **Use:** a described task or feature that should be delivered end-to-end with
  parallel agents and window discipline — "sprint the payment-retry feature",
  "/sprint add CSV export to reports".
- **NOT:** open-ended "use up the window" (→ `/grind`); cross-cutting
  consistency (→ `/semi-grind`); a one-liner or single PR (just do it / `/review`);
  pure planning with no build intent (→ `/autoplan` or plan mode).

## S0 — Bootstrap (every window, first action)

1. `source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh` → `$G`, hooks
   armed. STOP on non-zero.
2. `bash $G/hygiene-check fix`; commit `.gitignore` if changed.
3. **Swarm board:** `bash $G/swarm-claim.sh check` (exit 2 → narrow globs or
   negotiate on the issue — foreign claims are your `forbidden_globs`), then
   `claim` on CLEAR. `LOCAL_ONLY` → proceed.
4. **Knowledge graph:** if `graphify-out/graph.json` exists, `--update` when
   behind HEAD + ensure `graphify hook install`. All sprint agents get the
   graph-first block (see `/grind` SKILL.md "Context acquisition — graph-first").
5. Branches (grind 3-tier): `CAMPAIGN=grind-$(date +%d-%m-%Y)` off `dev`;
   `grind/feat/<slug>` per wave item, each in its own worktree
   `.claude/worktrees/grind-feat-<slug>` (scope-guard's worktree law REFUSES
   builder commits outside `.claude/worktrees/`).
6. `bash $G/quota-gate.sh` — obey (incl. `7 SOFT_PAUSE` → drain + park per
   `/soft-pause`; `6 POLL_FAILED` → one turn, one retry, as in `/grind`). It reads the
   newest statusline reading. Print the `/effort high` + `/autocompact 200k` reminder;
   `bash $G/rules-init` (project rules for every brief; fill a fresh skeleton with the
   founder before going autonomous); read `$G/profile.md`.
7. `bash $G/lock.sh acquire <window_id>`.

On a cron-resumed window: run S0, then **SKIP S1–S4** (the charter is frozen —
never re-plan on resume) and continue at S5 with `state.json` waves/team.

## S1 — Clarity gate

Score the spec against this fixed checklist. ALL must be answerable from the
founder's description (or the repo) before planning:

| # | Question | Pass looks like |
|---|---|---|
| 1 | **Goal** | one sentence, testable ("users can X") |
| 2 | **Scope globs** | which paths change (`allowed_globs`) and which must not (`forbidden_globs`) |
| 3 | **Acceptance criteria** | 2–6 verifiable bullets ("CSV downloads with columns A,B,C") |
| 4 | **Non-goals** | at least one explicit exclusion (kills scope creep at the source) |
| 5 | **Risk/unknowns** | the one thing most likely to sink it, named |

PASS all 5 → S3. ANY fail → S2. Do not "charitably infer" a failing row — that
is how vague specs become wrong features.

## S2 — Quiz loop (vague spec → charter)

`AskUserQuestion` rounds in the house format (MEMORY
`feedback_ask_user_question_format`): preamble with **Impact / Scope / key
Insight / explicit `Recommendation: X — because Y`**; 2–4 options each with pros
AND cons and an **ASCII preview** (the founder is visual); recommended option
first, tagged "(Recommended)". One round per failing checklist row-cluster; loop
until S1 passes. Ratify every answer into the charter; flag taste answers as
`RULE-NNN` candidates for the rulebook.

Founder absent mid-quiz → do NOT hang: log the open fork as a `DD-NNN`, park the
sprint (this is a spec gate — unlike `/semi-grind` there is no unblocked AUTO
work before a plan exists), surface "sprint parked pending DD-NNN".

## S3 — Plan (high effort) + MANDATORY codex pass

1. Launch a **Plan agent at opus/fable, effort high/max** with: the charter, the
   graph-first block, and the repo's canonical docs. Output → `PLAN.md` in the
   sprint's register dir (`docs/sprints/<slug>-<date>/`): frozen charter,
   acceptance criteria, and a **wave decomposition** where every wave item has a
   DISJOINT write-scope glob (two builders never share a glob — the same law
   the orchestrator enforces at dispatch).
2. **Codex pass — mandatory, before wave 1** (ratified 2026-07-10; Underline
   data: a retroactive codex run on a shipped plan produced 15 findings, 4
   CRITICAL — cross-model catches Claude-blind error classes): `/codex` review
   of `PLAN.md`. Fold CRITICAL/HIGH findings into the plan; log the rest to the
   register. Routine per-item fixes during execution do NOT get codex (same
   cadence rule as `/semi-grind` convention 1).
3. Freeze: `state.json .sprint.plan = <path>`, waves + globs into
   `state.json .sprint.waves[]`. After freeze, scope changes are a founder quiz,
   never a silent widen.

## S4 — Team manifest (persona + model matching)

Write `state.json .sprint.team[]` + a run-log table. Per role:

- **Persona:** usual work → REUSE the existing `.claude/agents/<persona>.md`
  (promote-to-agent rule; agents are durable memory — additive updates only,
  never `persona-v2` forks). Novel role → write the persona file BEFORE
  dispatch, not inline.
- **Model matching (difficulty → model), wired into `Agent` / Workflow `agent()`
  `opts.model` + `opts.effort`:**

| Work | Model | Effort |
|---|---|---|
| web/repo/doc scouting, log trawls | sonnet | medium |
| mechanical bulk edits, formatting, chunk extraction | haiku | low |
| build/verify runs, test authoring | sonnet | high |
| architecture, taste, merge conflicts, orchestration, GATE-class judgment | opus/fable | high/max |

Every Workflow `agent()` call sets BOTH fields from the manifest. The `Agent`
tool takes only `model`: its agents inherit the orchestrator session's effort, so
the orchestrator runs at `/effort high` + `/autocompact 200k` (S0 prints it; the
founder types it). An agent at the inherited `max` was the failure: in session
`6c5ee3ea` (2026-09-27) about $240 of Sonnet agents ran at `max` with no better
first-pass rate than `high`. Working rules: `$G/profile.md`.

When unsure between tiers, take the cheaper one for read-only roles and the
stronger one for anything that writes code the founder will review. Record
actual per-task quota deltas via `bash $G/cost-table record` so the matching
gets empirical over time.

## S5 — Execute (waves on the Workflow engine)

Each wave = **ONE Workflow run**:

```
pipeline(waveItems,
  item => agent(buildPrompt(item),  {model: team[item.role].model,
                                     effort: team[item.role].effort,
                                     isolation: 'worktree', phase: 'Build'}),
  (res, item) => agent(verifyPrompt(item), {model: 'sonnet', effort: 'high',
                                            phase: 'Verify'}))
```

- `pipeline()` not `parallel()` — no barrier unless a stage genuinely needs ALL
  prior results (dedup/merge). Item A verifies while item B still builds.
- Builders in worktrees is LAW (scope-guard worktree law), disjoint write-scope
  per item is LAW at dispatch (from the frozen wave decomposition).
- Every builder prompt carries: the graph-first block, `.claude/grind/rules.md`
  verbatim, the savepoint contract with the absolute UTC deadline `wave-brief`
  printed, the focus globs, the conventional-commit format + task id, and the
  brief rules of `$G/profile.md` (fail-closed checks with a control case; the
  verifier also diffs changed documents).
- The Workflow journal is the wave's savepoint: on `/soft-pause` (quota-gate
  exit 7) or a crash, resume with `Workflow({scriptPath, resumeFromRunId})` —
  the unchanged prefix replays free.
- Between waves: `bash $G/quota-gate.sh [TASK_TYPE]` (obey 0/2/3/4/5/6/7), then
  `bash $G/wave-brief` (advisory: deadline, $ left, agents past 100 requests,
  re-read files);
  orchestrator merges verified branches → campaign branch; `graphify --update`;
  update the concurrency manifest in `run-log.md`
  (session/role/task/branch/write-scope/status/gate — the `/grind` table shape);
  mirror progress into TaskCreate/TaskUpdate so the founder can glance the board.
- Verifier gates are non-interactive only (`tsc --noEmit`, `yarn jest
  --forceExit` — never bare `npx jest`, `/codex` pass/fail, `manage.py check`).
  An interactive need (`/qa` fix-loop, `/cso`) → gate-ledger entry, branch stays
  non-landable, sprint continues on other items.

## S6 — Window-end (work remains, quota doesn't)

Exactly `/grind` Window-end: `quota-gate.sh` + log the number and
reason; commit WIP; merge verified; `graphify --update`; `hygiene-check verify`;
regenerate `RESUME.md`; `lock.sh release`; `swarm-claim.sh renew`. Chain via
`CronCreate` at the time `quota-gate.sh --next-window` prints (`CHAIN …`), with a
resume prompt that starts with `[grind-resume]` (cc-pause-guard blocks unmarked
cron prompts), reads `RESUME.md` + `state.json`, runs the gate, then `wave-brief`,
and **skips S1–S4** (frozen plan); `window_counter += 1`, STOP the turn. No chain on
STOP_WEEKLY / STOP_KILL / `NO_CHAIN` / `window_counter >= MAX_WINDOWS` (config.sh).

## S7 — DONE (the anti-grind terminal)

When every acceptance criterion is verified met:

1. Final verify across the campaign branch (full non-interactive gate suite).
2. `bash $G/swarm-claim.sh release`; `bash $G/lock.sh release`.
3. Final `status-and-gates.md`: acceptance criteria → evidence table, the final
   concurrency manifest, open gates/DD-NNNs (loudly), per-wave cost summary.
4. Optional `/retro` — learnings → `/learn`; taste answers → `RULE-NNN`
   candidates for the next `/semi-grind`.
5. Surface: "sprint DONE — ready for you to open PR `grind-DD-MM-YYYY` → `dev`
   (gates blocked: …)". **STOP.** Quota remaining is NOT a reason to continue —
   scope-complete is the terminal. (Founder wants the leftover window burned →
   they say `/grind`.)

## Rules for agents

- **Never** keep working past scope-complete because quota remains — DONE means
  STOP; inventing scope is `/grind`'s cardinal sin inverted.
- **Never** start building on a spec that fails the clarity gate — quiz, don't
  charitably infer.
- **Never** skip the codex pass on `PLAN.md` — it is mandatory before wave 1
  (and only there; not per-item).
- **Never** re-plan on a cron resume — the charter froze at S3; scope changes go
  through a founder quiz.
- **Never** dispatch two wave items with overlapping write-scope, a builder
  outside a worktree, or a task that won't commit within ~10 minutes.
- **Never** assign opus/fable to mechanical scouting or haiku to
  architecture — match the table; record real costs.
- **Never** reimplement or bypass a `scripts/grind/*` script; obey exit codes,
  including `7 SOFT_PAUSE` (drain to savepoint, park — never kill).
- **Never** grep-sweep for structure when `graphify-out/graph.json` exists —
  graph-first in every agent prompt.
- **Never** open or merge the PR — the founder does; pushing branches is fine.
- **Always** table every concurrent session per wave; mirror progress to the
  task board; log the exact quota numbers at every stop.
