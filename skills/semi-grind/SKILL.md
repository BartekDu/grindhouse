---
name: semi-grind
preamble-tier: 3
version: 1.0.0
description: |
  Semi-supervised standardization campaign loop — the THIRD mode, between
  interactive (founder prompts every step; too slow) and /grind (autonomous to
  the quota floor; LOGS gates and moves on; too unsupervised for taste). Runs
  agentic cross-cutting DISCOVERY + autonomous MECHANICAL fixes, but BLOCKS on a
  founder AskUserQuestion quiz for every real taste / product / IA fork, then
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
  - AskUserQuestion
  - Skill
  - TaskCreate
  - TaskUpdate
  - CronCreate
---

# /semi-grind — semi-supervised cross-cutting standardization

**Contract:** `/semi-grind [focus]` = autonomously discover cross-cutting problems,
cluster them, and drive the fix loop — running MECHANICAL fixes silently and
**BLOCKING on an `AskUserQuestion` quiz for every genuine taste / product / IA fork**,
then ratifying the answer as a `RULE-NNN` and proceeding. A plain task list =
do-exactly-that-and-stop (not this). A fully-unsupervised burn that only logs gates
and never asks = `/grind` (not this).

**The scripts are authoritative, not this prose.** This loop REUSES `/grind`'s hard
guardrails verbatim — `scripts/grind/*` + the installed git hooks — because the model
is incentivized to keep going. **It does NOT reimplement any of them.** The ONLY thing
this skill adds over `/grind` is the **quiz-surface**: where `/grind` logs a gate to
`gate-ledger.md` and moves on, this skill blocks on a founder `AskUserQuestion`, gets
the decision, ratifies it as a `RULE-NNN`, and continues — plus the **living waved
register** and the **rulebook governor**. Obey the script exit codes literally.
Canonical thresholds live in `scripts/grind/config.sh` — READ them from there; never
hardcode OR restate a number in prose (prose drifts; the config is the law).

**Resolving `G` — global skill, works in any repo.** Both skills install globally and
share ONE guardrail bundle. At Step 0, FIRST run
`source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh` — it exports `$G`
(repo-local `scripts/grind` if present, else the global bundle) and arms the
`scope-guard`/`landable-guard` hooks for the cwd (idempotent). STOP on a non-zero
return. Every `$G/...` below uses that value. `/grind`
(`~/.claude/skills/grind/SKILL.md`) stays untouched and unattended-only; this is its
sibling, not a mode of it (see
`docs/process/semi-supervised-standardization-2026-06-09/GRIND-INTEGRATION.md`, Option C).

## When to use / when NOT

**Use when:**

- A cross-cutting quality problem spans multiple screens/wedges/modules that a per-unit
  audit is structurally blind to (e.g. an affordance present in one wedge, missing in
  the mirror — the tattoo wedge-switch-on-every-root vs piercing-on-one-root case that
  seeded this, CF-001/RULE-038).
- The fixes are a MIX of mechanical (token swaps, route registration, dead-cast removal)
  and taste/IA (which header shape wins, whether a stub becomes a feature).
- The founder is **semi-present**: reachable to answer a handful of pros/cons quizzes,
  but not to prompt every step.

**Do NOT use when:**

- It's a closed task list → just do those tasks and stop.
- It's a fully away-from-keyboard burn with no taste forks, or a cron-resumed window with
  nobody at the keyboard → `/grind` (it logs gates and never hangs). **`/semi-grind` must
  not be cron-resumed into an empty room expecting a quiz answer** — its absent-founder
  fallback (below) degrades to grind's log-a-gate-and-continue so it never hangs.
- It's a single PR / one-line change → `/review`.
- It's plan-level architecture → `/autoplan` + manual reviews (CLAUDE.md §3).

## Inputs

1. **`[focus]`** → a **path-glob contract** (NOT a phrase), same shape as `/grind` Step 0:
   `allowed_globs` (e.g. `apps/mobile/**`), `forbidden_globs` (e.g. `underline/api/**`,
   `infra/**`, `**/migrations/**`), `allowed_operations`. Plus the **dimensions** to audit
   (see Discovery).
2. **Register dir** (CLAUDE.md §15.2 state tree). Reference instance:
   `docs/design/standardization-2026-06-08/`. Holds the waved register
   `consistency-findings.md`, the `decisions-ledger.md`, the state files, and per-feature
   design sub-dirs.
3. **Rulebook** — `DESIGN_RULEBOOK.md` (repo top level). The living `RULE-NNN` ledger;
   `chief-stylist` is the sole writer. RULE-038..042 were ratified by the seed campaign.
4. **Lens agents** — `.claude/agents/{consistency-lens,style-lens,ux-lens,chief-stylist}.md`.
5. **Authority order** for every ruling (from `chief-stylist.md`): Claude-Design mockups
   (`docs/design/underline-mobile-claude-design-2026-06-08/`) FIRST → current app
   (`apps/mobile/src/`) for what-exists/how-organized → derived `tokens.ts` → copy/voice
   (`docs/copy-review/`, CLAUDE.md §6) → deprecated flow docs (hint only).
6. **Spec** — `docs/process/semi-supervised-standardization-2026-06-09/PROCESS.md` is the
   runnable playbook this skill operationalizes; read it once per cold start.

## On-disk state (reads / writes)

| File                                     | Owner         | Role                                                                                                                                                                                                   |
| ---------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `<register-dir>/consistency-findings.md` | chief-stylist | **The waved register.** `## Triage clusters` (TC-1..N, each a candidate fix wave with a progress line) + `## CF findings register` (CF-NNN). Bidirectional anchor links. sha-stamped status lifecycle. |
| `DESIGN_RULEBOOK.md`                     | chief-stylist | **The rulebook.** `RULE-NNN \| domain \| <rule> \| source: <cite>`. Stable, never renumbered; retired rules marked `**Status: retired**`.                                                              |
| `<register-dir>/decisions-ledger.md`     | chief-stylist | `DD-NNN` decision queue (a fork surfaced / answered / deferred).                                                                                                                                       |
| `.claude/grind/state.json`               | orchestrator  | focus globs, campaign+feature branches, window_counter, stop_log. (Reused from `/grind` verbatim — the hooks key off `.claude/grind/.active`, not the skill name.)                                     |
| `.claude/grind/run-log.md`               | orchestrator  | append-only timestamped events + the concurrency manifest table.                                                                                                                                       |
| `.claude/grind/gate-ledger.md`           | orchestrator  | open NON-quiz **ops** gates (`needs:/cso`, `needs:/qa`) that `landable-guard` enforces. **Quiz/DD-NNN gates resolve in-thread, NOT here** (see convention 2).                                          |
| `.claude/grind/audit.log`                | grind_audit   | hash-chained tamper-evident log (`audit-verify`). Never edited.                                                                                                                                        |
| `<register-dir>/<feature>-<date>/`       | bg workflow   | an EVOLVED cluster's own design sub-tree (e.g. `waiting-for-it-2026-06-09/`).                                                                                                                          |

The live **task list** (TaskCreate/TaskUpdate) is the glanceable sprint board — mirror the
register's progress line into it so the founder sees "done / here / next" (MEMORY:
`feedback_visible_timeline`).

## Branch model (reused from /grind, three tiers)

```text
dev
 └── grind-DD-MM-YYYY                campaign integration branch (one per run, off dev)
      └── grind/feat/<slug>          one per fix wave / concurrent builder (off campaign)
```

**Reuse the `grind-DD-MM-YYYY` prefix** (locked convention 4) — the scope-guard /
landable-guard hooks key off `.claude/grind/.active`, NOT the branch name, so a distinct
`std-` prefix would buy nothing but a second convention. The campaign accumulates onto ONE
PR (reference run = PR #64 on `grind-09-06-2026`). The founder opens/merges the PR; the
loop never pushes to `dev`/`main`.

## Step 0 — Focus + branches + transparency (first window only)

On a cron-resumed window, SKIP to loading focus + branches from `state.json`, then re-poll
quota (convention 5, below) — but STILL run step 0 below first (resolve `$G` + arm hooks).

0. **Resolve `$G` + arm hooks (every window, first action):**
   `source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh`. Surface its status; STOP
   on non-zero. This is what makes the skill machine-global.
1. Turn `[focus]` into the glob contract + the dimension list. Write to `state.json .focus`.
   If no `[focus]`, AskUserQuestion to confirm the contract before going autonomous.
2. **Branches:** `CAMPAIGN=grind-$(date +%d-%m-%Y)`; cut from `dev` if absent; store as
   `state.json .campaign_branch`. Derive `grind/feat/<slug>` per fix wave from the campaign
   branch.
3. `bash $G/hygiene-check fix` (gitignore scratch noise); commit `.gitignore` if changed.
3b. **Swarm board:** `bash $G/swarm-claim.sh check` — exit 2 = a live foreign swarm owns
   overlapping globs: narrow or negotiate on the `swarm-claim` issue, never bulldoze. On
   CLEAR: `bash $G/swarm-claim.sh claim`. (`LOCAL_ONLY` → proceed; lock.sh covers same-machine.)
3c. **Knowledge graph:** if `graphify-out/graph.json` exists, refresh when behind HEAD
   (`graphify <repo> --update`) + ensure the post-commit hook (`graphify hook install`).
   Lenses then query the graph first (see Discovery).
4. **Print before going autonomous:** focus label + campaign/feature branches +
   allowed/forbidden globs + the dimension list + floor/cap + the stop conditions + the
   concurrency table shape. Founder approves the SHAPE, then can step away — **but stays
   reachable for quizzes** (the difference from `/grind`).
5. `bash $G/lock.sh acquire <window_id>` (refuses on dirty tree / existing lock / failing
   gitignore hygiene; writes `.active`, which arms the scope-guard pre-commit hook).

## Discovery fan-out (Wave 1 — DISCOVERY ONLY, zero code)

Run as a **background workflow** (a subagent CANNOT prompt the founder; keep the main thread
free as the quiz surface). Fan out **one `consistency-lens` per dimension**, across BOTH
wedges, READ-ONLY. **Inject the graph-first block into every lens prompt** (see
`/grind` SKILL.md "Context acquisition — graph-first"): when `graphify-out/graph.json`
exists, structural questions route through `graphify query` first; Grep only confirms
the specific `file:line` the graph pointed at. Lenses that grep-sweep burn the token
budget discovery is supposed to conserve.

- dimensions (per `consistency-lens.md`): `parity / ia / header / interaction / state /
naming / ux-nightmare`.
- per-screen lenses (`style-lens` for visual-vs-mockup → `DF-NNN`, `ux-lens` for user-path →
  `UP-NNN`) fan out the same way when the campaign is per-screen rather than cross-cutting.
- each lens emits `CF-NNN` candidates: severity P0-P3, dimension tag, screens + exact
  `file:line` on BOTH sides of a divergence, a fix-DIRECTION, a `rule-candidate`. Caps per
  CLAUDE.md §15.3 (≤ findings per category; prioritize, don't dump nits). Every consistency
  fix the lens proposes is GATE — the lens never tags one AUTO (that is chief-stylist's call).

Then **consolidate (chief-stylist, single atomic writer):** de-dupe raw CFs into **triage
clusters TC-N** by theme, rank by severity, cross-link (cluster→CFs, CF→cluster, a CF may
belong to >1 cluster), write the register + the top progress line. The reference run = 58
CFs → 8 clusters (TC-1..TC-8).

## The main loop (per cluster, priority order)

Repeat until a STOP:

1. **Quota gate (the law):** `bash $G/quota-gate.sh [TASK_TYPE]`. Branch on exit:
   `0 GO`→proceed · `4 NO_NEW_TASK`→pick a SMALLER cluster/CF, else go to Window-end
   (Work-exhausted, stop condition 3) · `7 SOFT_PAUSE`→`/soft-pause` was invoked: drain every
   in-flight unit to its savepoint (finish current fix → commit; workflows park at their
   journal), run the settle steps (RESUME.md, `/context-save`, `swarm-claim.sh release`,
   `lock.sh release`), STOP the turn · `2/3/5/6`→Window-end (`STOP_WEEKLY` also fires on the
   PER-MODEL weekly bar, e.g. the Fable week — usually first to exhaust). Never poll quota
   yourself or reinterpret the number — the script rate-limits + caches.
2. **Pick the next cluster** by the register's priority line (e.g. "TC-1 then TC-2 first"),
   respecting `depends_on` (residual scope reassigned across clusters — e.g. TC-1's CF-019
   residual → TC-5).
3. **Classify the fix (AUTO vs GATE vs internal-convention)** via `chief-stylist`'s boundary
   (see below).
4. **If GATE → QUIZ-GATE step (below). BLOCK.** Get the founder decision (or, if the founder
   is absent, the graceful fallback below — never hang).
5. **If AUTO → just do it** (no quiz). e.g. drop a dead `as never` cast (CF-004), register a
   cross-domain route in both navigators (TC-4), hex→token. First pass
   `bash $G/value-gate "<objective win>"` (a closed CF, a coverage/lint-count drop).
6. **If internal-convention → the agent decides + documents it** (no quiz — see below).
7. **Build on a `grind/feat/<slug>` branch,** reusing shared components, grounded in the
   authority order. scope-guard pre-commit REJECTS out-of-focus paths — a blocked commit
   means you strayed; narrow, don't widen.
8. **Verify:** `tsc --noEmit` + `yarn jest --forceExit` (NEVER bare `npx jest` — Windows
   open-handle hang, MEMORY `feedback_no_bare_jest`; prefer `tsc` as the primary gate).
   Restate results honestly ("785/786; the 1 is a pre-existing env artifact, not my change"),
   never round up to "green."
9. **Commit + push** (lefthook: scope-guard / markdownlint / prettier / conventional /
   landable-guard). Conventional `<scope>: <subject>` + why-body + the CF/TC id. Accumulate
   onto the ONE campaign PR.
10. **Ratify + mark (chief-stylist, atomic):** the founder decision → a `RULE-NNN` in
    `DESIGN_RULEBOOK.md` (cite TC + CF + quiz date + live files); mark the CFs + the cluster
    status in the register, sha-stamped (`closed` / `partial → TC-x` / `✅ COMPLETED` /
    `🔄 EVOLVED`). Update the task list + register progress line.
11. Loop to 1.

## QUIZ-GATE step (the crux — what this adds over /grind)

When a cluster is GATE, the **orchestrator** (only the main thread can prompt — a subagent
CANNOT call `AskUserQuestion`) surfaces ONE quiz. Build it like this (MEMORY:
`feedback_ask_user_question_format` + the founder is visual):

1. **Preamble** (prose, ABOVE the quiz), exactly four parts:
   - **Impact** — the user-facing harm this fixes (cite the P0/P1 + the CF ids).
   - **Scope** — which screens/wedges/files change.
   - **A key insight** — the one non-obvious thing discovery surfaced.
   - **An explicit recommendation** — `Recommendation: <option> — because <one-line why>`.
     The recommendation lives in the **prose**, not folded into an option description.
2. **Options (2-4)**, each with:
   - pros AND cons in the description,
   - an **ASCII preview** (the founder is visual — show the layouts being chosen between,
     don't just name them),
   - the recommended option FIRST, tagged "(Recommended)".
3. Founder picks → proceed with that option. Founder clarifies/pushes back → **REFRAME and
   re-ask** (don't guess; CLAUDE.md §8: silence ≠ approval). Founder defers, OR is absent →
   log a `DD-NNN` and move to the next unblocked cluster (do NOT answer on their behalf —
   CLAUDE.md §7 / §3 interactive-skill policy). See the graceful fallback below.

### Example skeleton (the shape TC-1 used)

```text
PREAMBLE
  Impact:  P0 — piercing strands the user; no way to reach tattoo from 4 of 5 roots (CF-001/019/026).
  Scope:   both navigators' tab-root headers; consolidates IntentHeaderChip + PortHint.
  Insight: the Settings-based switch may not re-root the stack (CF-051, a 2nd P0) — a "switch"
           that doesn't re-root is a worse bug than the missing affordance.
  Recommendation: A (recessed PortHint on every root) — one component, always visible, always
           re-roots; the chip's active-tab-only placement is exactly what stranded users.

ASKUSERQUESTION  "Cross-wedge switch — which affordance on every tab root?"
  ┌ A (Recommended) recessed PortHint everywhere
  │   pro: one component both wedges; persistent; re-roots via RootRouter container swap
  │   con: lower visual prominence than a segmented chip
  │   preview:  [ ‹ port ›  today  piercings  jewelry  …  ]   ← pill left of action row, every root
  ├ B  promote IntentHeaderChip into a full header on every root
  │   pro: high prominence   con: 44px chrome on every root, no title room, two switch UIs
  └ C  keep per-wedge (chip on piercing, pill on tattoo)
      pro: least churn   con: the bug — two switch models; the discovery gap persists
```

## AUTO vs GATE decision rule (the safety boundary — from `chief-stylist.md`)

For every proposed fix, chief-stylist stamps **exactly one** of these. This boundary keeps an
autonomous run inside CLAUDE.md §7/§8. **When unsure → GATE** (demoting a wrongly-AUTO'd taste
fix after it ships is expensive).

- **AUTO** = objective, mechanical, behavior-preserving, reduces a measurable count: hardcoded
  hex / magic literal → theme token; off-scale spacing/radius/type → nearest scale; missing
  `accessibilityRole`/`Label` → added; reduce-motion not gated → gated; a banned copy word →
  its **documented** preferred swap; a dead `as never` cast removed (CF-004); a cross-domain
  route registered in both navigators (TC-4, mechanical wiring, no taste fork). A builder
  applies it; `value-gate` passes on the count drop. **No quiz.**
- **GATE** = anything needing judgment: layout/flow/hierarchy/IA restructure; a change to what a
  feature DOES or that risks downgrading it; any NEW user-facing copy (routes through
  `docs/copy-review/`, never invented inline — CLAUDE.md §6); a RULE candidate encoding taste.
  **Surfaces a quiz** (or a `DD-NNN`). (Reference: TC-1 wedge-switch IA → quiz → RULE-038;
  TC-3 settings parity → 3 quizzes → RULE-039/040/041.)
- **Internal convention ≠ GATE.** An engineering convention with **zero user-facing impact** is
  the agent's call: it decides it, documents it as a convention, ratifies a RULE — **without a
  quiz**, because there is nothing for the founder to have taste about. **Canonical example —
  TC-4 / CF-012, the `onBack` prop:** the consistency-lens flagged three back-link patterns as a
  divergence, but the resolution was an engineering decoupling call — the agent documented inline
  `useNavigation().goBack()` as canonical and KEPT the `onBack` prop on ExportData/DeleteAccount
  as the documented exception (forcing uniformity would couple deliberately-decoupled,
  standalone-testable screens — a downgrade). Folded into RULE-042. **NOT quizzed** — quizzing it
  would violate "don't hand-hold / reserve pauses for real forks" (MEMORY `feedback_dont_handhold`).

## Background-workflow fan-out (discovery + feature-design)

Two distinct fan-outs, both as **background workflows** (keep the main thread as the quiz
surface — a subagent CANNOT prompt the founder):

1. **Discovery** — one `consistency-lens` per dimension (Wave 1, above).
2. **Feature design (the EVOLVE path)** — when a cluster's answer OUTGROWS a fix and becomes a
   NEW FEATURE, spin its own design workflow: the 4-lens fan-out (style/ux + synthesis) into the
   cluster's own `<register-dir>/<feature>-<date>/` sub-tree, **plus a `codex exec` cross-model
   review + `finops-lens`** (CLAUDE.md §3, because this is now plan-level). **Reference: TC-2
   "stubs that lie" → founder chose to build "Waiting for it"**
   (`docs/design/waiting-for-it-2026-06-09/`) — an honest in-context placeholder + demand signal.
   The mechanical honesty baseline (wire the fake bell → real Notifications, delete the fake
   unread badge) is AUTO and ships now; the feature is GATE-pending before any build; the cluster
   is marked `🔄 EVOLVED → in design`, **NOT closed**. TC-2 closes only when the feature lands AND
   the honesty baseline is wired.

A subagent merges to the campaign branch only after its Verifier passes; the orchestrator owns
the merge + the concurrency table (reuse the `/grind` council: Orchestrator / Builder / Verifier
/ Scout, ≤ MAX_CONCURRENT, disjoint write-scope per builder).

### Codex / finops cadence (locked convention 1)

`codex exec` + `finops-lens` fire on the **EVOLVE branch ONLY** — when a cluster becomes a real
feature with its own design workflow, that plan goes through codex + finops before any build.
They are **OFF for routine per-cluster mechanical fixes** (CLAUDE.md §3 keeps codex off "routine
code-level PRs"; the campaign accumulates onto ONE PR reviewed by the verifier's non-interactive
gates). Do not run codex per AUTO fix.

## Guardrail reuse (verbatim from /grind — the scripts are the law; do NOT reimplement)

Cite these exact paths; never fork or re-derive their logic:

- **`scripts/grind/quota-gate.sh`** — canonical floor + reserve + rate-limited poll. The
  terminal condition. Trust its exit codes (`0 GO` / `2 STOP_FLOOR` / `3 STOP_WEEKLY` —
  incl. the per-model weekly bar / `4 NO_NEW_TASK` / `5 STOP_KILL` / `6 POLL_FAILED` /
  `7 SOFT_PAUSE` — drain to savepoint + park, see `/soft-pause`).
- **`scripts/grind/scope-guard`** (pre-commit hook) — focus is a path-glob contract; out-of-focus
  commits are REJECTED. A blocked commit means you strayed — narrow, don't widen. Also the
  **worktree law**: builder commits on `grind/feat/*` are refused outside `.claude/worktrees/`.
- **`scripts/grind/swarm-claim.sh`** — cross-swarm backlog-ownership board (gh issues labeled
  `swarm-claim`). `check` exit 2 = live foreign claim overlaps your globs (negotiate, don't
  bulldoze); degrades to LOCAL_ONLY without gh/remote.
- **`scripts/grind/landable-guard`** (pre-push hook) — a deferred **ops** `/qa` or `/cso` (logged
  to `gate-ledger.md`) makes the branch non-landable. Say "build green, gates blocked," never
  "green." **Quiz/DD-NNN gates are NOT wired into landable-guard** (convention 2) — they resolve
  in-thread; only ops gates block landing.
- **`scripts/grind/value-gate`** — every AUTO/backlog fix needs an objective win (a closed CF, a
  coverage increase, a lint/type-error decrease). REJECT → skip + log.
- **`scripts/grind/lock.sh`** — single-run + dirty-tree preflight; writes `.active` (arms
  scope-guard).
- **`scripts/grind/hygiene-check`** — gitignore scratch-noise; `git status` stays boringly clean
  between tasks.
- **`scripts/grind/audit-verify`** (verifier) over **`.claude/grind/audit.log`** (the
  `GRIND_DIR/audit.log` data file, NOT under `scripts/grind/`) — hash-chained tamper-evident event
  log. Never edit it.
- **`scripts/grind/config.sh`** — canonical thresholds (floor/weekly/reserve/MAX_WINDOWS/
  MAX_CONCURRENT). Never hardcode a different number. (`lib.sh`, `grindjson.py`, `cost-table` are
  the shared helpers — skill-agnostic, reused as-is.)
- **Kill switch:** `touch .claude/grind/STOP` (founder, anytime) halts at the next quota-gate.

These scripts are a **shared guardrail library**, not grind-private: `/semi-grind` reuses them by
calling them; `/grind` does not depend on `/semi-grind`. Neither skill may make a script
grind-private without updating the other (CLAUDE.md §13.3 cross-layer discipline).

## Stop conditions (any one → Window-end)

1. **Quota floor** — `quota-gate.sh` returns `2 STOP_FLOOR` / `3 STOP_WEEKLY` / `5 STOP_KILL` /
   `6 POLL_FAILED`. The PRIMARY terminal condition.
2. **Founder decision pending (founder PRESENT)** — a GATE cluster's quiz is unanswered / deferred
   to a `DD-NNN`, AND no other in-focus cluster can proceed without it. Log it, surface it, and (if
   quota remains + other clusters are unblocked) keep going on those; only the blocked cluster
   waits. A whole-campaign block (all remaining clusters GATE-pending) → Window-end with the
   status+gate report. **If the founder is ABSENT, this is NOT a stop** — the convention-3 fallback
   below takes over (log every GATE as a `DD-NNN`, keep doing AUTO work, window-end only on quota
   floor or work-exhausted). Stop-2 is the founder-present path; the fallback is the absent path.
3. **Work exhausted** — no in-focus cluster passes the value gate. Write ONE `status-and-gates.md`
   (progress per cluster, the "where we are" table, the final concurrency manifest, the
   gate-ledger + open `DD-NNN` quizzes). Do NOT invent scope.

### Absent-founder graceful fallback (locked convention 3 — never hang)

If a GATE is reached but the founder is away (or it's a cron-resumed window), **degrade to
grind's log-a-gate-and-continue**: do the AUTO work, defer every GATE to a `DD-NNN` in
`decisions-ledger.md` (and a non-quiz marker so it's visible at window-end), keep building the
unblocked clusters, and leave the branch non-landable. **Never block the loop waiting on an
`AskUserQuestion` with nobody present** — the hooks + ledger already exist for exactly this. This
is the explicit "no founder present" mode; `/semi-grind` is never a hang risk.

## Window-end

1. `bash $G/quota-gate.sh --force`; log exact `five_hour_pct_left` + `week_pct_left` + stop-reason
   to `run-log.md` + `state.json.stop_log` (also in the audit log).
2. Commit WIP onto its `grind/feat/<slug>` branch; merge clean+verified feature branches →
   campaign; refresh the knowledge graph if present (`graphify <repo> --update`);
   `bash $G/hygiene-check verify`. Regenerate `RESUME.md` + the register progress line +
   the final concurrency manifest.
3. `bash $G/lock.sh release`. Swarm board: chaining → `bash $G/swarm-claim.sh renew`;
   stopping for good → `bash $G/swarm-claim.sh release`.
4. **The campaign branch is the reviewable unit; the founder opens the PR.** Surface: campaign
   branch, feature branches + commit counts, the concurrency manifest, the answered quizzes
   (RULE-NNN ratified), and — **loudly** — the open `DD-NNN` quizzes still awaiting a founder
   decision (convention 2: they don't block landing, but they MUST be flagged at window-end), plus
   any ops gates (`needs:/cso` / `needs:/qa`) that DO block landing. Then "ready for you to open PR
   `grind-DD-MM-YYYY` → `dev` (gates blocked: …; open decisions: DD-NNN …)". Pushing branches is
   fine; opening/merging is the founder's call.
5. **Chain?** Only if `window_counter < MAX_WINDOWS` AND in-focus work remains AND not
   STOP_WEEKLY/STOP_KILL AND no whole-campaign quiz block: `CronCreate` the next window at the 5h
   reset with a resume prompt (loads focus+branches from state.json, skips Step 0, **re-polls
   quota** — convention 5), `state_set '.window_counter += 1'`, STOP this turn. Else STOP + status
   report.
6. **Campaign-end retro (optional, founder-present only):** offer `/retro` — learnings →
   `/learn`; ratified quiz answers already live as `RULE-NNN`s; recurring DD-NNN themes are the
   retro's first agenda item.

### Re-poll on every post-quiz resume (locked convention 5)

A blocking `AskUserQuestion` burns the 5h **wall-clock** window even though no tokens flow (the
window is wall-clock, not work-clock; it cannot be paused). So **on every post-quiz resume — and
on every cron-resumed window — re-poll `bash $G/quota-gate.sh --force` BEFORE the next task**, and
stop if the founder's think-time pushed us under the floor. Never assume the pre-quiz reading
still holds.

## Rules for agents

- **Never** answer a GATE quiz on the founder's behalf — surface an `AskUserQuestion` (or, if the
  founder is absent, log a `DD-NNN` and proceed on other clusters via the graceful fallback). This
  is the ONE thing `/grind` does NOT do; it is the entire point of this skill.
- **Never** classify a taste / IA / feature-affecting / new-copy fix as AUTO — when unsure, GATE.
  (Per `chief-stylist.md` + CLAUDE.md §7.)
- **Never** quiz the founder on a zero-user-impact engineering convention (the third category —
  agent decides + documents it; reference CF-012/`onBack`); quizzing it violates `feedback_dont_handhold`.
- **Never** treat "all clusters processed" as a stop reason while quota + unblocked clusters
  remain — stop only on quota floor / whole-campaign quiz block / value-gate-dry.
- **Never** reimplement, reinterpret, or bypass any `scripts/grind/*` script — call them; obey
  their exit codes; never `--no-verify`; never widen `forbidden_globs`; never edit the audit log.
- **Never** wire a `DD-NNN`/quiz gate into `landable-guard` (convention 2) — quizzes resolve
  in-thread; only ops gates (`/qa`, `/cso`) block landing. But flag open `DD-NNN`s loudly at
  window-end.
- **Never** run `codex` / `finops-lens` on a routine per-cluster mechanical fix (convention 1) —
  they fire on the EVOLVE branch only (plan-level, CLAUDE.md §3).
- **Never** let a subagent call `AskUserQuestion` — only the orchestrator (main thread) has the
  founder surface. Discovery + feature-design run as background workflows that hand the fork up.
- **Never** renumber or delete a `CF-NNN` / `TC-N` / `RULE-NNN` / `DD-NNN` — mark `closed` /
  `partial → TC-x` / `🔄 EVOLVED` / `✅ COMPLETED`, sha-stamped (CLAUDE.md §15.2).
- **Never** ratify a `RULE-NNN` with no source in the authority order — draft it as a `DD-NNN`
  candidate and quiz it.
- **Never** write the rulebook or register concurrently from two sessions — chief-stylist is the
  single atomic writer (CLAUDE.md §15.2).
- **Never** commit to `dev`/`main`/the campaign branch directly — build on `grind/feat/<slug>` off
  the dated campaign branch; one fix wave = one branch = one reviewable unit; never push to
  `dev`/`main`.
- **Never** close an EVOLVED cluster — it stays `🔄 EVOLVED → in design` until its new feature
  lands AND its mechanical baseline is wired (reference: TC-2).
- **Never** cron-resume `/semi-grind` into an empty room expecting a quiz answer — the
  absent-founder fallback degrades to log-a-gate-and-continue so it never hangs.
- **Never** grep-sweep for structure when `graphify-out/graph.json` exists — graphify-query
  first (lenses included); grep confirms lines, it doesn't explore.
- **Never** dispatch a builder fix that won't reach a commit within ~10 minutes — decompose;
  savepoints make `/soft-pause` and power cuts cheap.
- **Never** kill units on quota-gate exit 7 — drain each to its savepoint, settle, park.
- **Never** proceed past `swarm-claim.sh check` exit 2 — narrow globs or negotiate on the issue.
- **Always** write the QUIZ preamble with impact · scope · key-insight · an explicit
  "Recommendation: X — because Y" + an ASCII preview per option + the recommended option first
  (MEMORY `feedback_ask_user_question_format`: the founder is visual, wants the recommendation in
  prose).
- **Always** verify with `tsc --noEmit` + `yarn jest --forceExit` (NEVER bare `npx jest`) and
  restate results honestly — "green except X, here's why X isn't mine," never a rounded "green."
- **Always** re-poll `quota-gate.sh --force` on every post-quiz resume + every cron window
  (convention 5) before the next task.
- **Always** keep the focus a glob contract, confirmed at Step 0, reused (not re-asked) on cron
  windows.
- **Always** mirror the register progress line into the live task list so the founder can glance
  "done / here / next" without holding state.
