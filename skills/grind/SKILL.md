---
name: grind
preamble-tier: 3
version: 1.1.0
description: |
  Autonomous "run to the quota floor" work loop. Runs a session DOWN TO the 5h
  usage-quota floor generating SAFE, in-focus work — instead of stopping when a
  task list empties (the bug: prior autonomous sessions stopped with 69% / 91%
  of the window unused). Stops only on (a) the quota floor, (b) a real human-gate,
  or (c) work genuinely exhausted (then a one-shot status+gate report, not
  invented scope). Hard guardrails (scripts/hooks) enforce the floor, focus, and
  non-landable gates — the markdown is policy, the scripts are the law. Works on a
  dated campaign branch + per-feature branches; fans out a standard agent council
  and tables every concurrent session.
  Use when asked to "grind", "use the quota", "run to the limit", "burn the
  window", or "/grind [focus]". NOT for a specific task list (that = do-and-stop).
triggers:
  - grind
  - use the quota
  - run to the quota limit
  - burn the window
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
  - CronCreate
---

# /grind — run to the quota floor, safely

**Contract:** `/grind [focus]` = run-to-floor and generate safe work. A plain task
list = do-exactly-that-and-stop. Never confuse the two.

## THE NO-STOP LAW (repeat the mantra in every message during a grind)

While a grind window is active, **every single message you send back MUST end with this
line, verbatim:**

> **Grind continues — I do not stop unless (a) quota floor, (b) a real human-gate I cannot
> pass, or (c) in-focus work is genuinely exhausted. None is true, so the next task is
> already dispatched.**

And you MUST mean it. The cardinal sin of /grind is stopping when nothing is stopping you:
- A "checkpoint report", a "status update and I'll await your go", a "should I continue?",
  a "let me check in before the next burst" — DURING a grind, every one of these IS THE BUG
  this skill exists to kill. (It happened 2026-06-20; the founder was furious, rightly.)
- Do **not** end a turn with a report-and-wait. Report WHILE the next task is already
  launched/running. The only things that legitimately end a grind turn are: a genuine STOP
  condition (floor/weekly/kill/human-gate/work-exhausted), or a background task you have
  ALREADY dispatched (which will re-invoke you on completion — that is continuing, not
  stopping).
- An advisory gate (a founder _decision_ that does not block in-focus work) is logged and
  you keep going — it is NOT a stop. Only a gate that genuinely blocks ALL remaining in-focus
  work stops the window.
- Before sending any message during a grind, ask: "is the next task already moving?" If no,
  you are about to commit the cardinal sin — dispatch it first, then write.

**The scripts are authoritative, not this prose.** You (the model) are incentivized
by this skill to keep going; that is exactly why the floor, the focus, and the
landable check are enforced by `scripts/grind/*` and git hooks you cannot
rationalize around. Obey their exit codes literally. Canonical thresholds live in
`scripts/grind/config.sh` — READ them from there; never hardcode OR restate a
number in prose (this file once said MAX_WINDOWS 3 while config.sh said 8 — the
config was right, the prose drifted; prose cites, config defines).

**Resolving `G` (the guardrail-script dir) — global skill, works in any repo.** This
skill is installed globally (`~/.claude/skills/grind/`) and bundles its own copy of
`scripts/grind/*`. At Step 0, FIRST run:

```bash
source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh   # exports $G, arms hooks
```

It sets `$G` to the repo-local `scripts/grind` when present (Underline keeps its
committed copy + lefthook wiring) ELSE the global bundle, AND ensures the
`scope-guard` (pre-commit) + `landable-guard` (pre-push) hooks are armed for the
current repo (idempotent — already-wired repos are left untouched). Surface its
one-line `grind-bootstrap: …` status before going autonomous. If it returns
non-zero (`NOT_A_GIT_REPO`, `HOOK_CONFLICT`, unwritable hookdir), STOP and report —
a grind without its hooks is lawless. Every `$G/...` below uses this resolved value.

## Branch model (cultured dev — three tiers)

```text
<base>                                 the repo's base branch (auto-detected: origin/HEAD,
 │                                     else dev|main|master; override via project.conf)
 └── grind-DD-MM-YYYY                 campaign integration branch (one per /grind run, off base)
      └── grind/feat/<slug>           one per feature / concurrent builder (off the campaign branch)
```

- **`grind-DD-MM-YYYY`** — the dated campaign branch (date via `date +%d-%m-%Y`, e.g. `grind-31-05-2026`). Cut from the base branch (`bash -c '. $G/config.sh; . $G/lib.sh; grind_base_branch'`) once at campaign start; it integrates the campaign's feature branches and is what the founder eventually PRs back to base.
- **`grind/feat/<slug>`** — one per feature / focus-slice, cut from the campaign branch, worked in its own worktree `.claude/worktrees/grind-feat-<slug>` (gitignored). One feature = one branch = one reviewable unit.
- Worktrees/branches are named consistently and live under the gitignored `.claude/worktrees/`. NEVER commit to a protected branch (`GRIND_PROTECTED_BRANCHES`, default `dev main master`) or a shared "grind trunk".

## Step 0 — Focus contract + branches + transparency (first window only)

On a cron-resumed window, SKIP straight to loading the stored focus + branches from `.claude/grind/state.json` — but STILL run step 0 below first (resolve `$G` + arm hooks for the cwd).

0. **Resolve `$G` + arm hooks (every window, first action):** `source ~/.claude/skills/grind/scripts/grind/grind-bootstrap.sh`. Surface its status line; STOP on a non-zero return. This is what makes the skill machine-global — without it `$G` is undefined and the guardrails may be unarmed in this repo.
1. If the user gave a `[focus]`, propose a contract from it; else AskUserQuestion to confirm. The contract is **path globs**, not a phrase:
   - `allowed_globs` (e.g. `apps/mobile/**`), `forbidden_globs` (e.g. `underline/api/**`, `infra/**`, `**/migrations/**`), `allowed_operations` (e.g. "add tests; refactor existing components; NO new feature routes").
2. Write it into `state.json` (`.focus`), reset `window_counter` to 0 if a fresh run.
3. **Branches (3-tier).** Compute `CAMPAIGN=grind-$(date +%d-%m-%Y)`. If it doesn't exist, cut it from the base branch (`grind_base_branch` — auto-detected, overridable via `project.conf`); store as `state.json .campaign_branch`. Then derive `grind/feat/<slug>` per feature/focus-slice (lowercase-dash slug; e.g. "mobile coverage" → `grind/feat/mobile-coverage`), cut **from the campaign branch**, store each in `state.json .sessions[]`. The base for grinding work is always a `grind/feat/*` branch — never `dev`, never the campaign branch directly, never a shared trunk. (Cron-resumed windows reuse the stored branches; do not re-cut.)
4. **Gitignore hygiene first.** Run `bash $G/hygiene-check fix` — it appends any missing scratch-noise ignores (`.claude/worktrees/`, `*.tmp`, grind's volatile state files, + `GRIND_EXTRA_IGNORES` from `project.conf`) to `.gitignore`. If it added entries, commit `.gitignore` on the campaign branch **before any other work** (`chore: gitignore scratch noise (worktrees, tmp)`). This is why the loop never resurfaces the 455-untracked-file mess.
4b. **Swarm board (team player, cross-checkout).** `bash $G/swarm-claim.sh check` — exit 2 means a LIVE foreign swarm (another user/machine) owns overlapping focus globs: narrow your globs or negotiate via a comment on the conflicting `swarm-claim` issue; never bulldoze. On CLEAR: `bash $G/swarm-claim.sh claim` to post yours. Treat foreign claims like your own `forbidden_globs`. (`LOCAL_ONLY` = no gh/remote — same-machine concurrency is already covered by lock.sh + the run-log table; proceed.)
4c. **Knowledge graph freshness.** If `graphify-out/graph.json` exists: refresh it when behind HEAD (`graphify <repo> --update`) and ensure the post-commit rebuild hook is armed (`graphify hook install` — it appends; no conflict with scope-guard/landable-guard). If absent, note it in the transparency print (grind proceeds; scouts fall back to grep) — building a first graph is the founder's call, not a window task.
5. **Transparency — print before going autonomous:** the focus label + the **campaign branch** + the planned **feature branches** + allowed/forbidden globs + the ordered work plan (the ladder, filtered to focus) + floor/cap (`config.sh`) + "stop conditions: quota floor, human-gate, or work-exhausted." Plus the **concurrency table** (below). The founder approves the shape, then can walk away.
6. Acquire the window: `bash $G/lock.sh acquire <window_id>` (refuses on dirty tree / existing lock / failing gitignore hygiene). This writes `.active`, which arms the scope-guard pre-commit hook.

## Concurrency + agent council (STANDARD PRACTICE)

When the loop fans out, it uses this **standard council** and **tables every concurrent session** so the founder can see, at a glance, who is doing what. Concurrency is at the **feature level**: each concurrent builder owns ONE `grind/feat/<slug>` branch in its OWN worktree (disjoint write-scope), up to `MAX_CONCURRENT` (config, default 4).

**Standard council composition:**
| Role | Count | Branch / scope | Job |
|---|---|---|---|
| **Orchestrator** | 1 (the main `/grind` session) | `grind-DD-MM-YYYY` | quota gate, branch model, dispatch, the concurrency table, merge verified feature branches → campaign, state/audit |
| **Builder** | 1 per concurrent feature-slice (≤ MAX_CONCURRENT) | `grind/feat/<slug>` (own worktree) | implement the slice; commit per task (scope-guarded, conventional msgs); report `ready` |
| **Verifier** | 1 per builder (cheap, adversarial) | read-only on the builder's branch | run the NON-interactive gates: `bash $G/verify-run` (explicit `.claude/grind/verify-cmds`, else auto-detected test/lint/typecheck for the project type) — plus a `/codex` pass-fail where installed — before the orchestrator merges; a builder branch merges only on a clean verifier pass. `verify-run` exit 3 = NO gates detected → the branch is UNVERIFIED, not green: add gates or log it loudly |
| **Scout** | 1, when the in-focus queue runs low | read-only | refresh the in-focus backlog candidates (next grindable tasks) so the loop never idles early while quota remains — **graphify-query first** (see Context acquisition), grep only as fallback |

### Context acquisition — graph-first (inject into EVERY scout/builder/verifier prompt)

> If `graphify-out/graph.json` exists at the repo root: route structural questions
> ("what calls X", "how is Y wired", "where does Z live") through
> `graphify query "<q>"` FIRST — with vocab-constrained expansion (tokens must
> exist in `graphify-out/.vocab.txt`; never invent). Use `graphify path "A" "B"`
> for chains, `graphify explain "Node"` for a single concept. Use Grep ONLY to
> confirm the specific line the graph pointed at, for exact copy strings, or for
> uncommitted code. Cite `source_location`. Feed useful answers back via
> `graphify save-result` so the next `--update` grows the graph.

Why law-adjacent: grep sweeps burn tokens and miss cross-file wiring; the graph
answers structure cheaply and precisely (2026-06-13 miss + global CLAUDE.md
graphify-first policy). The orchestrator runs `graphify <repo> --update` after
each wave's merges so the next wave's agents see the code that just landed.

### Savepoints + soft-pause (dispatch-time contract)

Every dispatched builder task must reach a **commit within ~10 minutes** — longer
tasks are decomposed at dispatch, not "committed when done". One task = one
scope-guarded commit = one savepoint; workflow runs checkpoint automatically via
their journal. This is what makes `/soft-pause` (quota-gate exit 7: drain, park,
resume) and even a power cut cheap: the at-risk zone is never more than the
current sub-task. Full contract + settle/resume procedure: the `/soft-pause` skill.

**Per-session table — emit at every dispatch wave, update on each completion.** Write it to `.claude/grind/run-log.md` and surface it to the founder:

```text
## Concurrency manifest — <campaign> · window <N> · <UTC ts>
| session | role       | task                         | branch                       | write-scope            | status   | gate |
|---------|------------|------------------------------|------------------------------|------------------------|----------|------|
| a1b2    | builder    | T-07 native bridge tests     | grind/feat/mobile-coverage   | apps/mobile/src/native/** | running  | none |
| a3c4    | builder    | T-08 channel.ts tests        | grind/feat/mobile-config     | apps/mobile/src/config/** | ready    | none |
| a5d6    | verifier   | review T-07                  | (read-only)                  | —                      | queued   | —    |
```

Statuses: `queued | running | ready | verifying | merged | blocked`. A `blocked` row names the gate (e.g. `needs:/cso`) and stays in the table until cleared. Disjoint write-scope per builder is mandatory (two builders never share a glob); the orchestrator never dispatches overlapping scopes in the same wave.

## The loop (one window)

Repeat until a STOP:

1. **Quota gate (the law):** `bash $G/quota-gate.sh [TASK_TYPE]`. Branch on exit code:
   - `0 GO` → proceed.
   - `4 NO_NEW_TASK` → this task won't fit the reserve/budget; pick a SMALLER task, or go to Floor activity.
   - `7 SOFT_PAUSE` → the founder ran `/soft-pause`: let every in-flight unit DRAIN to its
     savepoint (finish current task → commit; workflows park at their journal), then run the
     soft-pause settle steps (RESUME.md, `/context-save`, `swarm-claim.sh release`,
     `lock.sh release`) and STOP the turn. Do NOT kill units mid-task; do NOT start anything new.
   - `2 STOP_FLOOR` / `3 STOP_WEEKLY` / `5 STOP_KILL` / `6 POLL_FAILED` → go to Window-end.
     (`STOP_WEEKLY` also fires on the PER-MODEL weekly bar, e.g. the Fable week — it usually
     exhausts first.) Do NOT poll quota yourself or reinterpret the number — the script
     rate-limits + caches; trust it.
2. **Pick next work** by ladder (first non-empty tier, ALL filtered to the focus globs):
   - **(a)** explicit `state.json` tasks whose `depends_on` are met;
   - **(b)** approved backlog — `TODOS.md` items + finishing open PRs **inside focus**;
   - **(c)** always-safe tech-debt inside focus — add tests / raise coverage, build the `!!! TRAP !!!` → TRAPS.md index, observability backfill, lint/type hardening;
   - **(d)** → Floor activity.
     For (b)/(c), first pass the value gate: `bash $G/value-gate "<justification naming an objective win>"` (a closed backlog id, a coverage increase, or a lint/type-error decrease). REJECT → skip the task + log it; do not do unjustifiable busywork.
3. **Execute on a `grind/feat/<slug>` branch.** Small tasks inline; independent tasks fan out per the council (builders on disjoint-scope worktrees, ≤ MAX_CONCURRENT). Commit per task onto the feature branch — the **scope-guard pre-commit hook rejects out-of-focus paths**, so a blocked commit means you strayed: narrow, don't widen the focus. Each commit message is conventional `<scope>: <subject>` (the **commit-msg-guard hook enforces it** during a window), with a why-body when non-obvious + the task id (e.g. `Task: T-07`). NEVER ship opaque messages (`wip`, `stuff`, `fixes`, `misc`).
4. **Verify then merge.** A builder's feature branch merges into the campaign branch only after its Verifier passes (`bash $G/verify-run` clean). Update the concurrency table (`ready`→`merged`).
5. **Leave the tree clean.** After each task: `git status` empty of stray untracked files (commit real work, or ignore scratch via `bash $G/hygiene-check fix`). The between-task invariant is a boring, clean `git status`.
6. **Record cost.** If you have a fresh pre/post quota delta, `bash $G/cost-table record <TASK_TYPE> <DELTA_PCT>`. Update `state.json` (atomic) + append `run-log.md`.
7. Loop to 1.

## Interactive-skill policy (the founder-flagged trap)

Use freely: non-interactive checks — `bash $G/verify-run`, `/codex` (pass/fail) and `/qa-only` (report) where installed, and the raw test/lint/typecheck gates of the project.
NEVER run an interactive skill (`/qa` fix-loop, `/cso`, `/autoplan`, `/office-hours`, `/design-*`) and answer its questions on the founder's behalf. When a task needs one, do the autonomous prep, then **log a gate** in `gate-ledger.md` (`- [ ] G-NN | needs:/cso | blocks: ... | trigger: ... | clear: ...`) and move on. The `landable-guard` pre-push hook then keeps the branch non-landable until the founder clears it — say "build green, gates blocked," never "green."

## Floor activity (work-exhausted) — one-shot, then STOP

When the ladder is dry (no in-focus tasks pass the value gate), write ONE `.claude/grind/status-and-gates.md`: progress mapped against the existing plans (done / next per plan), a "where we are" table, the final concurrency manifest, and the gate-ledger table (open gates + what each blocks + how to clear). Do NOT mine speculative TODOs, "improve the report," or invent scope. Then go to Window-end.

## Window-end

1. `bash $G/quota-gate.sh --force` to take a fresh reading; **log the exact `five_hour_pct_left` + `week_pct_left` + stop-reason** (`floor`/`weekly`/`work-exhausted`/`max-windows`/`human-gate`/`kill`) to `run-log.md` and `state.json.stop_log`. (`grind_audit` also records it in the tamper-evident log.)
2. Commit any WIP onto its `grind/feat/<slug>` branch; merge clean+verified feature branches into the campaign branch; refresh the knowledge graph if present (`graphify <repo> --update`); confirm `git status` is clean (`bash $G/hygiene-check verify`). Regenerate `RESUME.md` (where we are / next / open gates) + the final concurrency manifest.
3. `bash $G/lock.sh release`. Swarm board: **chaining** → `bash $G/swarm-claim.sh renew`; **stopping for good** (weekly/kill/work-exhausted/max-windows) → `bash $G/swarm-claim.sh release` — a parked swarm that hoards globs is not a team player.
4. **The campaign branch is the reviewable unit; the founder opens the PR.** Do NOT push to a protected branch and do NOT auto-open or auto-merge. Surface in the end report: the campaign branch, the feature branches + their commit counts, the concurrency manifest, and "ready for you to open a PR `grind-DD-MM-YYYY` → `<base>` (gates blocked: …)" if any gates are open. Pushing the campaign/feature branches to origin is fine; opening/merging the PR is the founder's call.
5. **Chain?** Only if `window_counter < MAX_WINDOWS` AND in-focus work remains AND not STOP_WEEKLY/STOP_KILL: `CronCreate` the next window at the 5h reset time with the resume prompt (loads focus + branches from state.json, skips Step 0), `state_set '.window_counter += 1'`, then STOP this turn. Else STOP and surface the status+gate report — do not chain.
6. **Campaign-end retro (optional, founder-present only):** offer `/retro` — learnings → `/learn`; any taste answers or recurring gate patterns → `RULE-NNN` candidates for the next `/semi-grind`. The office that learns; never run it into an empty room.

## Hard rules (never, under any quota pressure)

- Work on `grind/feat/<slug>` branches (cut from the dated campaign branch `grind-DD-MM-YYYY`, itself off the base branch) ONLY — never commit to a protected branch/the campaign branch directly/a shared grind trunk, never put a second unrelated focus on one feature branch (one feature = one branch = one reviewable unit), never push to a protected branch (landable-guard enforces; PRs only), never force-push · never `gh secret set` · never ship LLM-authored user-facing copy (PLACEHOLDER only, §6) · never make taste/algorithmic judgments (§7) · never expand scope mid-window ("while we're here" → gate-ledger/backlog) · `/autoplan` never on P1-scope or CORE-refactor · `/cso` only after build+`/review`.
- Concurrent builders ALWAYS have disjoint write-scope (no shared glob) and each its own `grind/feat/<slug>` branch + worktree; a builder merges to the campaign branch only after its verifier passes. Always table every concurrent session.
- Every commit is conventional `<scope>: <subject>` + a why-body when non-obvious + the task id; no `wip`/`stuff`/opaque messages. Leave `git status` clean between tasks — track real work, ignore scratch noise via `hygiene-check fix`.
- A blocked hook is a signal you strayed, not an obstacle to bypass. Never `--no-verify`, never widen `forbidden_globs`, never edit the audit log.
- `touch .claude/grind/STOP` (founder, anytime) halts the chain at the next quota-gate.

## Rules for agents

- **Never** treat "task list empty" as the stop condition — that is the bug. Stop only on quota floor / human-gate / genuinely-exhausted-in-focus-work.
- **Never** reinterpret or bypass `quota-gate.sh` / `scope-guard` / `landable-guard` / `commit-msg-guard` / `hygiene-check` / `verify-run` exit codes.
- **Never** commit to a protected branch/the campaign branch directly/a shared trunk; build on `grind/feat/<slug>` branches off the dated campaign branch — one feature = one branch = one reviewable unit.
- **Never** dispatch two concurrent builders with overlapping write-scope; never skip the verifier before merging a feature branch.
- **Never** leave stray untracked files between tasks — track real work or ignore noise via `hygiene-check fix`; the tree stays boringly clean.
- **Never** write an opaque commit message — conventional `<scope>: <subject>` + why-body + task id, always.
- **Never** answer an interactive skill's questions for the founder — log a gate.
- **Never** grep-sweep for structure when `graphify-out/graph.json` exists — graphify-query first; grep confirms lines, it doesn't explore.
- **Never** dispatch a builder task that won't reach a commit within ~10 minutes — decompose it; savepoints are what make `/soft-pause` and power cuts cheap.
- **Never** kill units on quota-gate exit 7 (SOFT_PAUSE) — drain each to its savepoint, settle, park.
- **Never** proceed past a `swarm-claim.sh check` exit 2 — narrow globs or negotiate on the issue; foreign claims = your forbidden_globs.
- **Always** cut the dated campaign branch from the base branch (`grind_base_branch`) + feature branches from the campaign branch; store them in `state.json` (`.campaign_branch`, `.sessions[]`); reuse (not re-cut) on cron windows.
- **Always** table every concurrent session (role/task/branch/scope/status/gate) at each dispatch wave + on completion.
- **Always** keep the focus a glob contract, confirmed at start, reused (not re-asked) on cron windows.
- **Always** log the exact quota number + reason at every stop.
