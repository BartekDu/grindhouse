---
name: semi-grind
preamble-tier: 3
version: 2.0.0
description: |
  Semi-supervised standardization campaign loop — the THIRD mode, between
  interactive (user prompts every step; too slow) and /grind (autonomous to
  the quota floor; LOGS gates and moves on; too unsupervised for taste). Runs
  agentic cross-cutting DISCOVERY + autonomous MECHANICAL fixes, but BLOCKS on a
  user AskUserQuestion quiz for every real taste / product / design fork, then
  ratifies the answer as a RULE-NNN and proceeds. Governed by a living waved
  register (TC clusters + CF-NNN findings, stable never-renumbered ids,
  sha-stamped status) + a living rulebook (RULE-NNN). REUSES every /grind
  guardrail script + hook verbatim (scripts/grind/*) — it does NOT reimplement
  them; /grind itself is untouched and stays unattended-only. The delta over
  /grind is the quiz-surface + the register/rulebook governors.
  Use when asked to "semi-grind", "semi-supervised grind", "standardize",
  "consistency campaign", "/semi-grind [focus]". NOT for a specific task list
  (do-and-stop) and NOT for a fully-unsupervised burn (that = /grind).
triggers:
  - semi-grind
  - semi-supervised grind
  - standardize
  - consistency campaign
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Agent
  - Workflow
  - AskUserQuestion
  - Skill
  - TaskCreate
  - TaskUpdate
  - CronCreate
---

# /semi-grind — semi-supervised cross-cutting standardization

**Contract:** `/semi-grind [focus]` = autonomously discover cross-cutting problems,
cluster them, and drive the fix loop — running MECHANICAL fixes silently and
**BLOCKING on an `AskUserQuestion` quiz for every genuine taste / product / design fork**,
then ratifying the answer as a `RULE-NNN` and proceeding. A plain task list =
do-exactly-that-and-stop (not this). A fully-unsupervised burn that only logs gates
and never asks = `/grind` (not this).

**The scripts are authoritative, not this prose.** This loop REUSES `/grind`'s hard
guardrails verbatim — `scripts/grind/*` + the installed git hooks — because the model
is incentivized to keep going. **It does NOT reimplement any of them.** The ONLY thing
this skill adds over `/grind` is the **quiz-surface**: where `/grind` logs a gate to
`gate-ledger.md` and moves on, this skill blocks on a user `AskUserQuestion`, gets
the decision, ratifies it as a `RULE-NNN`, and continues — plus the **living waved
register** and the **rulebook governor**. Obey the script exit codes literally.
Canonical thresholds live in `scripts/grind/config.sh` (floor 10% / weekly 10% /
model-weekly 10% / reserve 5% / MAX_WINDOWS / MAX_CONCURRENT) — never hardcode a
different number.

The working rules learned from past campaigns apply here too and live in ONE place,
`$G/profile.md`: the orchestrator runs at `/effort high` + `/autocompact 200k` (the
`Agent` tool inherits the session's effort), every builder/verifier brief carries
`.claude/grind/rules.md` (`bash $G/rules-init`) and a UTC deadline, checks fail closed
with a control case.

**Resolving `G` — global skill, works in any repo.** Both skills install globally and
share ONE guardrail bundle. At Step 0, FIRST run
`source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh` — it exports `$G`
(repo-local `scripts/grind` if present, else the global bundle) and arms the
`scope-guard` / `landable-guard` / `commit-msg-guard` hooks for the cwd (idempotent).
STOP on a non-zero return. Every `$G/...` below uses that value. `/grind`
(`~/.claude/skills/grind/SKILL.md`) stays untouched and unattended-only; this is its
sibling, not a mode of it.

## When to use / when NOT

**Use when:**

- A cross-cutting quality problem spans multiple screens / modules / packages that a
  per-unit audit is structurally blind to (an affordance or pattern present in one
  place, missing in its mirror; three competing conventions for the same thing).
- The fixes are a MIX of mechanical (token swaps, dead-code removal, missing
  registration, naming alignment) and taste/design (which pattern wins, whether a
  stub becomes a feature).
- The user is **semi-present**: reachable to answer a handful of pros/cons quizzes,
  but not to prompt every step.

**Do NOT use when:**

- It's a closed task list → just do those tasks and stop.
- It's a fully away-from-keyboard burn with no taste forks, or a cron-resumed window with
  nobody at the keyboard → `/grind` (it logs gates and never hangs). **`/semi-grind` must
  not be cron-resumed into an empty room expecting a quiz answer** — its absent-user
  fallback (below) degrades to grind's log-a-gate-and-continue so it never hangs.
- It's a single PR / one-line change → a normal review.
- It's plan-level architecture → a user-present planning session.

## Inputs

1. **`[focus]`** → a **path-glob contract** (NOT a phrase), same shape as `/grind` Step 0:
   `allowed_globs`, `forbidden_globs`, `allowed_operations`. Plus the **dimensions** to
   audit (see Discovery).
2. **Register dir** — default `docs/consistency-<YYYY-MM-DD>/` in the repo (create at
   Step 0 if absent; the user may name a different one). Holds the waved register
   `consistency-findings.md`, the `decisions-ledger.md`, and per-feature design sub-dirs.
3. **Rulebook** — `RULEBOOK.md` at the repo top level (create at first ratification if
   absent). The living `RULE-NNN` ledger; the consolidator role is the sole writer.
4. **Authority order** for every ruling — resolve conflicts by rank; confirm/adjust with
   the user at Step 0 if the repo has its own docs hierarchy:
   design docs / specs / mockups FIRST → the current code (what exists, how organized) →
   derived config (design tokens, lint config, schemas) → written copy/docs → anything
   deprecated (hint only).

## On-disk state (reads / writes)

| File                                     | Owner        | Role                                                                                                                                                    |
| ---------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<register-dir>/consistency-findings.md` | consolidator | **The waved register.** `## Triage clusters` (TC-1..N, each a candidate fix wave with a progress line) + `## CF findings register` (CF-NNN). Bidirectional anchor links. sha-stamped status lifecycle. |
| `RULEBOOK.md`                            | consolidator | **The rulebook.** `RULE-NNN \| domain \| <rule> \| source: <cite>`. Stable, never renumbered; retired rules marked `**Status: retired**`.                |
| `<register-dir>/decisions-ledger.md`     | consolidator | `DD-NNN` decision queue (a fork surfaced / answered / deferred).                                                                                          |
| `.claude/grind/state.json`               | orchestrator | focus globs, campaign+feature branches, window_counter, stop_log. (Reused from `/grind` verbatim — the hooks key off `.claude/grind/.active`, not the skill name.) |
| `.claude/grind/run-log.md`               | orchestrator | append-only timestamped events + the concurrency manifest table.                                                                                          |
| `.claude/grind/gate-ledger.md`           | orchestrator | open NON-quiz **ops** gates (external checks the user must run) that `landable-guard` enforces. **Quiz/DD-NNN gates resolve in-thread, NOT here** (see conventions). |
| `.claude/grind/audit.log`                | grind_audit  | hash-chained tamper-evident log (`audit-verify`). Never edited.                                                                                           |
| `<register-dir>/<feature>-<date>/`       | bg workflow  | an EVOLVED cluster's own design sub-tree.                                                                                                                 |

The live **task list** (TaskCreate/TaskUpdate) is the glanceable sprint board — mirror the
register's progress line into it so the user sees "done / here / next" at a glance.

## Branch model (reused from /grind, three tiers)

```text
<base>                                the repo's base branch (grind_base_branch)
 └── grind-DD-MM-YYYY                campaign integration branch (one per run, off base)
      └── grind/feat/<slug>          one per fix wave / concurrent builder (off campaign)
```

**Reuse the `grind-DD-MM-YYYY` prefix** — the scope-guard / landable-guard hooks key off
`.claude/grind/.active`, NOT the branch name, so a distinct `std-` prefix would buy
nothing but a second convention. The campaign accumulates onto ONE PR. The user
opens/merges the PR; the loop never pushes to a protected branch.

## Step 0 — Focus + branches + transparency (first window only)

On a cron-resumed window, SKIP to loading focus + branches from `state.json`, then re-run
the quota gate (convention 5, below) — but STILL run step 0 below first (resolve `$G` + arm hooks).

0. **Resolve `$G` + arm hooks (every window, first action):**
   `source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh`. Surface its status;
   STOP on non-zero. This is what makes the skill machine-global.
1. Turn `[focus]` into the glob contract + the dimension list. **The contract MUST also
   cover the campaign's own write surfaces:** append `RULEBOOK.md` and `<register-dir>/**`
   to `allowed_globs` — the scope-guard pre-commit hook rejects any staged path outside
   the globs, so without these two the consolidator's register/rulebook commits are
   REJECTED mid-window. (`.claude/grind/**`, `scripts/grind/**` and `.gitignore` are
   already always-allowed by scope-guard itself.) Write to `state.json .focus`.
   If no `[focus]`, AskUserQuestion to confirm the contract before going autonomous.
2. **Branches:** `CAMPAIGN=grind-$(date +%d-%m-%Y)`; cut from the base branch
   (`grind_base_branch`) if absent; store as `state.json .campaign_branch`. Derive
   `grind/feat/<slug>` per fix wave from the campaign branch.
3. `bash $G/hygiene-check fix` (gitignore scratch noise); commit `.gitignore` if changed.
4. **Print before going autonomous:** focus label + campaign/feature branches +
   allowed/forbidden globs + the dimension list + floor/cap + the stop conditions + the
   concurrency table shape. The user approves the SHAPE, then can step away — **but stays
   reachable for quizzes** (the difference from `/grind`).
5. `bash $G/lock.sh acquire <window_id>` (refuses on dirty tree / existing lock / failing
   gitignore hygiene; writes `.active`, which arms the scope-guard pre-commit hook).

## Discovery fan-out (Wave 1 — DISCOVERY ONLY, zero code)

Run as **background subagents / a Workflow** (a subagent CANNOT prompt the user; keep the
main thread free as the quiz surface). Fan out **one read-only lens per dimension** across
the whole focus area.

**Dimensions** — pick per project type (the user can add/remove at Step 0):

- *Code repos:* `naming / structure / error-handling / api-shape / config-drift /
  docs-vs-code / test-consistency / dead-code`
- *UI repos, additionally:* `parity` (feature present in one screen-family, missing in the
  mirror) `/ ia` (information architecture) `/ header-layout / interaction / state-handling
  / a11y`

**Lens prompt template** (inline — spawn a general-purpose subagent per dimension):

```text
You are a read-only consistency lens for dimension: <dimension>.
Audit ALL of <allowed_globs> — never edit anything.
Find cross-cutting divergences: the same concept done ≥2 different ways, an
affordance/pattern present in one unit and missing in its mirror, a convention
followed in N places and broken in M.
Emit findings as:  CF-candidate | severity P0-P3 | dimension | file:line on BOTH
sides of the divergence | a fix-DIRECTION (not a decision) | a rule-candidate.
Cap: max 15 findings; prioritize, don't dump nits. NEVER tag a finding AUTO —
classification is the consolidator's call.
```

Then **consolidate (single atomic writer — the "consolidator" role, run in the main
thread or ONE subagent):** de-dupe raw CFs into **triage clusters TC-N** by theme, assign
final `CF-NNN` ids, rank by severity, cross-link (cluster→CFs, CF→cluster; a CF may belong
to >1 cluster), write the register + the top progress line.

## The main loop (per cluster, priority order)

Repeat until a STOP:

1. **Quota gate (the law):** `bash $G/quota-gate.sh [TASK_TYPE]`. Branch on exit:
   `0 GO`→proceed · `4 NO_NEW_TASK`→pick a SMALLER cluster/CF, else go to Window-end
   (Work-exhausted, stop condition 3) · `7 SOFT_PAUSE`→the user ran `/soft-pause`: let
   in-flight units DRAIN to their savepoint (finish current fix → commit), then park —
   never kill mid-task; settle + resume per the `/soft-pause` skill · `6 POLL_FAILED`→no
   fresh statusline reading: one ordinary turn, then the gate once more; a second
   `POLL_FAILED`→Window-end · `2/3/5`→Window-end.
   Never read quota yourself or reinterpret the number — trust the script.
   Before each fix wave, `bash $G/wave-brief` (advisory; /grind loop step 1b).
2. **Pick the next cluster** by the register's priority line, respecting `depends_on`
   (residual scope reassigned across clusters).
3. **Classify the fix (AUTO vs GATE vs internal-convention)** via the boundary below.
4. **If GATE → QUIZ-GATE step (below). BLOCK.** Get the user's decision (or, if the user
   is absent, the graceful fallback below — never hang).
5. **If AUTO → just do it** (no quiz). e.g. remove a dead cast, register a missing route in
   both places, hardcoded literal → shared constant/token. First pass
   `bash $G/value-gate "<objective win>"` (a closed CF, a coverage/lint-count drop).
6. **If internal-convention → the agent decides + documents it** (no quiz — see below).
7. **Build on a `grind/feat/<slug>` branch,** reusing shared components, grounded in the
   authority order. scope-guard pre-commit REJECTS out-of-focus paths — a blocked commit
   means you strayed; narrow, don't widen.
8. **Verify:** `bash $G/verify-run` (explicit `.claude/grind/verify-cmds`, else
   auto-detected project gates). Restate results honestly ("785/786; the 1 is a
   pre-existing env artifact, not my change"), never round up to "green." Exit 3
   (no gates) = UNVERIFIED — say so loudly.
9. **Commit + push.** Conventional `<scope>: <subject>` + why-body + the CF/TC id
   (commit-msg-guard enforces the shape). Accumulate onto the ONE campaign PR.
10. **Ratify + mark (consolidator, atomic):** the user's decision → a `RULE-NNN` in
    `RULEBOOK.md` (cite TC + CF + quiz date + live files); mark the CFs + the cluster
    status in the register, sha-stamped (`closed` / `partial → TC-x` / `✅ COMPLETED` /
    `🔄 EVOLVED`). Update the task list + register progress line.
11. Loop to 1.

## QUIZ-GATE step (the crux — what this adds over /grind)

When a cluster is GATE, the **orchestrator** (only the main thread can prompt — a subagent
CANNOT call `AskUserQuestion`) surfaces ONE quiz. Build it like this:

1. **Preamble** (prose, ABOVE the quiz), exactly four parts:
   - **Impact** — the user-facing harm this fixes (cite the P0/P1 + the CF ids).
   - **Scope** — which screens/modules/files change.
   - **A key insight** — the one non-obvious thing discovery surfaced.
   - **An explicit recommendation** — `Recommendation: <option> — because <one-line why>`.
     The recommendation lives in the **prose**, not folded into an option description.
2. **Options (2-4)**, each with:
   - pros AND cons in the description,
   - a **preview** where the choice is visual/structural (ASCII mockup, code snippet —
     show the shapes being chosen between, don't just name them),
   - the recommended option FIRST, tagged "(Recommended)".
3. User picks → proceed with that option. User clarifies/pushes back → **REFRAME and
   re-ask** (don't guess; silence ≠ approval). User defers, OR is absent →
   log a `DD-NNN` and move to the next unblocked cluster (do NOT answer on their behalf).
   See the graceful fallback below.

### Example skeleton

```text
PREAMBLE
  Impact:  P0 — users of module A get retry-on-failure; the mirror module B silently
           drops the operation (CF-001/019).
  Scope:   both modules' request layers; consolidates two ad-hoc retry helpers.
  Insight: module B's "retry" flag exists but is dead code — a worse bug than the
           missing affordance (CF-051, a 2nd P0).
  Recommendation: A (one shared retry helper) — one implementation, both call sites,
           kills the dead flag.

ASKUSERQUESTION  "Retry handling — which shape for both modules?"
  ┌ A (Recommended) one shared helper, both modules call it
  │   pro: single implementation, consistent semantics   con: touches both modules now
  ├ B  port module A's helper into B as a copy
  │   pro: no shared dep   con: two implementations drift again — the original bug
  └ C  keep per-module behavior, document the difference
      pro: least churn   con: the inconsistency this campaign exists to kill
```

## AUTO vs GATE decision rule (the safety boundary)

For every proposed fix, the consolidator stamps **exactly one** of these. This boundary
keeps an autonomous run inside safe limits. **When unsure → GATE** (demoting a wrongly-
AUTO'd taste fix after it ships is expensive).

- **AUTO** = objective, mechanical, behavior-preserving, reduces a measurable count:
  hardcoded literal → shared constant/token; off-convention naming → the documented
  convention; missing a11y attribute → added; dead cast/flag/import removed; a route or
  registration present on one side wired on the other (mechanical wiring, no taste fork);
  a banned word → its **documented** preferred swap. A builder applies it; `value-gate`
  passes on the count drop. **No quiz.**
- **GATE** = anything needing judgment: layout/flow/hierarchy/API-surface restructure; a
  change to what a feature DOES or that risks downgrading it; any NEW user-facing copy
  (never invented inline — mark PLACEHOLDER + quiz); a RULE candidate encoding taste.
  **Surfaces a quiz** (or a `DD-NNN`).
- **Internal convention ≠ GATE.** An engineering convention with **zero user-facing
  impact** is the agent's call: it decides it, documents it as a convention, ratifies a
  RULE — **without a quiz**, because there is nothing for the user to have taste about.
  Example shape: three back-navigation patterns flagged as a divergence, but the
  resolution is an engineering decoupling call — document pattern X as canonical and KEEP
  a justified exception where forcing uniformity would couple deliberately-decoupled,
  standalone-testable units (a downgrade). **NOT quizzed** — quizzing it is hand-holding;
  reserve pauses for real forks.

## Background-workflow fan-out (discovery + feature-design)

Two distinct fan-outs, both as **background subagents / Workflows** (keep the main thread
as the quiz surface — a subagent CANNOT prompt the user):

1. **Discovery** — one lens per dimension (Wave 1, above).
2. **Feature design (the EVOLVE path)** — when a cluster's answer OUTGROWS a fix and
   becomes a NEW FEATURE, spin its own design workflow into the cluster's own
   `<register-dir>/<feature>-<date>/` sub-tree, plus a **deep review pass**
   (`/code-review` at high effort, or a cross-model review if available) — because this is
   now plan-level. The mechanical honesty baseline (wire the fake affordance to the real
   thing or delete it) is AUTO and ships now; the feature is GATE-pending before any
   build; the cluster is marked `🔄 EVOLVED → in design`, **NOT closed**. It closes only
   when the feature lands AND the baseline is wired.

A subagent merges to the campaign branch only after its Verifier passes; the orchestrator
owns the merge + the concurrency table (reuse the `/grind` council: Orchestrator / Builder
/ Verifier / Scout, ≤ MAX_CONCURRENT, disjoint write-scope per builder).

**Deep-review cadence:** deep review fires on the **EVOLVE branch ONLY** — when a cluster
becomes a real feature with its own design workflow. It is **OFF for routine per-cluster
mechanical fixes** (the campaign accumulates onto ONE PR reviewed by the verifier's
non-interactive gates). Do not run a deep review per AUTO fix.

## Guardrail reuse (verbatim from /grind — the scripts are the law; do NOT reimplement)

Cite these exact paths; never fork or re-derive their logic:

- **`$G/quota-gate.sh`** — canonical floor + reserve, on the newest statusline reading. The terminal
  condition. Trust its exit codes (`0 GO` / `2 STOP_FLOOR` / `3 STOP_WEEKLY` — fires on
  the all-models AND the per-model weekly bar / `4 NO_NEW_TASK` / `5 STOP_KILL` /
  `6 POLL_FAILED` / `7 SOFT_PAUSE` — drain to savepoint + park, never kill).
- **`$G/scope-guard`** (pre-commit hook) — focus is a path-glob contract; out-of-focus
  commits are REJECTED. A blocked commit means you strayed — narrow, don't widen.
- **`$G/landable-guard`** (pre-push hook) — a deferred **ops** gate (logged to
  `gate-ledger.md`) makes the branch non-landable; direct pushes to protected branches are
  refused. Say "build green, gates blocked," never "green." **Quiz/DD-NNN gates are NOT
  wired into landable-guard** — they resolve in-thread; only ops gates block landing.
- **`$G/commit-msg-guard`** (commit-msg hook) — conventional `<scope>: <subject>`, no
  opaque messages, enforced only while a window is active.
- **`$G/value-gate`** — every AUTO/backlog fix needs an objective win (a closed CF, a
  coverage increase, a lint/type-error decrease). REJECT → skip + log.
- **`$G/verify-run`** — the non-interactive verification gate (explicit per-repo
  `verify-cmds`, else auto-detect). Exit 3 = UNVERIFIED, never "green".
- **`$G/lock.sh`** — single-run + dirty-tree preflight; writes `.active` (arms scope-guard).
- **`$G/hygiene-check`** — gitignore scratch-noise; `git status` stays boringly clean
  between tasks.
- **`$G/audit-verify`** (verifier) over **`.claude/grind/audit.log`** — hash-chained
  tamper-evident event log. Never edit it.
- **`$G/config.sh`** — canonical thresholds + optional per-repo `project.conf` overrides.
  Never hardcode a different number. (`lib.sh`, `grindjson.py`, `cost-table` are the
  shared helpers — skill-agnostic, reused as-is.)
- **Kill switch:** `touch .claude/grind/STOP` (the user, anytime) halts at the next
  quota-gate.

These scripts are a **shared guardrail library**, not grind-private: `/semi-grind` reuses
them by calling them; `/grind` does not depend on `/semi-grind`. Neither skill may make a
script grind-private without updating the other.

## Stop conditions (any one → Window-end)

1. **Quota floor** — `quota-gate.sh` returns `2 STOP_FLOOR` / `3 STOP_WEEKLY` /
   `5 STOP_KILL` / `6 POLL_FAILED`. The PRIMARY terminal condition.
2. **User decision pending (user PRESENT)** — a GATE cluster's quiz is unanswered /
   deferred to a `DD-NNN`, AND no other in-focus cluster can proceed without it. Log it,
   surface it, and (if quota remains + other clusters are unblocked) keep going on those;
   only the blocked cluster waits. A whole-campaign block (all remaining clusters
   GATE-pending) → Window-end with the status+gate report. **If the user is ABSENT, this
   is NOT a stop** — the fallback below takes over (log every GATE as a `DD-NNN`, keep
   doing AUTO work, window-end only on quota floor or work-exhausted).
3. **Work exhausted** — no in-focus cluster passes the value gate. Write ONE
   `status-and-gates.md` (progress per cluster, the "where we are" table, the final
   concurrency manifest, the gate-ledger + open `DD-NNN` quizzes). Do NOT invent scope.

### Absent-user graceful fallback (never hang)

If a GATE is reached but the user is away (or it's a cron-resumed window), **degrade to
grind's log-a-gate-and-continue**: do the AUTO work, defer every GATE to a `DD-NNN` in
`decisions-ledger.md` (and a non-quiz marker so it's visible at window-end), keep building
the unblocked clusters, and leave the branch non-landable. **Never block the loop waiting
on an `AskUserQuestion` with nobody present** — the hooks + ledger already exist for
exactly this. This is the explicit "no user present" mode; `/semi-grind` is never a hang
risk.

## Window-end

1. `bash $G/quota-gate.sh`; log exact `five_hour_pct_left` + `week_pct_left` +
   stop-reason to `run-log.md` + `state.json.stop_log` (also in the audit log).
2. Commit WIP onto its `grind/feat/<slug>` branch; merge clean+verified feature branches →
   campaign; `bash $G/hygiene-check verify`. Regenerate `RESUME.md` + the register
   progress line + the final concurrency manifest.
3. `bash $G/lock.sh release`.
4. **The campaign branch is the reviewable unit; the user opens the PR.** Surface:
   campaign branch, feature branches + commit counts, the concurrency manifest, the
   answered quizzes (RULE-NNN ratified), and — **loudly** — the open `DD-NNN` quizzes
   still awaiting a decision (they don't block landing, but they MUST be flagged at
   window-end), plus any ops gates that DO block landing. Then "ready for you to open PR
   `grind-DD-MM-YYYY` → `<base>` (gates blocked: …; open decisions: DD-NNN …)". Pushing
   branches is fine; opening/merging is the user's call.
5. **Chain?** Only if `window_counter < MAX_WINDOWS` AND in-focus work remains AND not
   STOP_WEEKLY/STOP_KILL AND no whole-campaign quiz block AND `bash $G/quota-gate.sh
   --next-window` answers `CHAIN …`: `CronCreate` the next window at that time with a
   resume prompt that starts with `[grind-resume]` (cc-pause-guard blocks unmarked cron
   prompts) and reads RESUME.md + state.json, then runs the gate (convention 5), then
   `wave-brief` — the /grind Window-end template. `state_set '.window_counter += 1'`,
   STOP this turn. Else STOP + status report.

### Re-poll on every post-quiz resume (convention 5)

A blocking `AskUserQuestion` burns the 5h **wall-clock** window even though no tokens flow
(the window is wall-clock, not work-clock; it cannot be paused). So **on every post-quiz
resume — and on every cron-resumed window — re-run `bash $G/quota-gate.sh` BEFORE
the next task**, and stop if the user's think-time pushed us under the floor. Never assume
the pre-quiz reading still holds.

## Rules for agents

- **Never** answer a GATE quiz on the user's behalf — surface an `AskUserQuestion` (or, if
  the user is absent, log a `DD-NNN` and proceed on other clusters via the graceful
  fallback). This is the ONE thing `/grind` does NOT do; it is the entire point of this
  skill.
- **Never** classify a taste / design / feature-affecting / new-copy fix as AUTO — when
  unsure, GATE.
- **Never** quiz the user on a zero-user-impact engineering convention (the third
  category — agent decides + documents it); quizzing it is hand-holding.
- **Never** treat "all clusters processed" as a stop reason while quota + unblocked
  clusters remain — stop only on quota floor / whole-campaign quiz block / value-gate-dry.
- **Never** reimplement, reinterpret, or bypass any `scripts/grind/*` script — call them;
  obey their exit codes; never `--no-verify`; never widen `forbidden_globs`; never edit
  the audit log.
- **Never** wire a `DD-NNN`/quiz gate into `landable-guard` — quizzes resolve in-thread;
  only ops gates block landing. But flag open `DD-NNN`s loudly at window-end.
- **Never** run a deep review on a routine per-cluster mechanical fix — it fires on the
  EVOLVE branch only (plan-level).
- **Never** let a subagent call `AskUserQuestion` — only the orchestrator (main thread)
  has the user surface. Discovery + feature-design run as background workflows that hand
  the fork up.
- **Never** renumber or delete a `CF-NNN` / `TC-N` / `RULE-NNN` / `DD-NNN` — mark
  `closed` / `partial → TC-x` / `🔄 EVOLVED` / `✅ COMPLETED`, sha-stamped.
- **Never** ratify a `RULE-NNN` with no source in the authority order — draft it as a
  `DD-NNN` candidate and quiz it.
- **Never** write the rulebook or register concurrently from two sessions — the
  consolidator is the single atomic writer.
- **Never** commit to a protected branch/the campaign branch directly — build on
  `grind/feat/<slug>` off the dated campaign branch; one fix wave = one branch = one
  reviewable unit; never push to a protected branch.
- **Never** close an EVOLVED cluster — it stays `🔄 EVOLVED → in design` until its new
  feature lands AND its mechanical baseline is wired.
- **Never** cron-resume `/semi-grind` into an empty room expecting a quiz answer — the
  absent-user fallback degrades to log-a-gate-and-continue so it never hangs.
- **Always** write the QUIZ preamble with impact · scope · key-insight · an explicit
  "Recommendation: X — because Y" + a visual preview per option where the choice is
  visual + the recommended option first.
- **Always** verify with `bash $G/verify-run` and restate results honestly — "green
  except X, here's why X isn't mine," never a rounded "green."
- **Always** re-run `quota-gate.sh` on every post-quiz resume + every cron
  window (convention 5) before the next task.
- **Always** keep the focus a glob contract, confirmed at Step 0, reused (not re-asked)
  on cron windows.
- **Always** mirror the register progress line into the live task list so the user can
  glance "done / here / next" without holding state.
