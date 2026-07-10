---
name: soft-pause
preamble-tier: 3
version: 1.0.0
description: |
  Graceful pause for agent swarms and workflows WITHOUT burning paid progress.
  The old way (kill agents / touch STOP) threw away up to 30 minutes × N Fable
  agents of work. Soft-pause instead: sets the PAUSE sentinel, lets every unit
  DRAIN to its next savepoint (commit / workflow-journal write), parks it, and
  writes a resume bundle. `resume` picks everything back up — including after a
  power cut, because the savepoint contract makes crash recovery the same path.
  Use when asked to "soft pause", "pause the grind", "pause the swarm",
  "park the agents", "graceful pause", or "/soft-pause [--hard|resume|status]".
  NOT the kill switch (that = `touch .claude/grind/STOP` — immediate halt).
triggers:
  - soft pause
  - pause the grind
  - pause the swarm
  - park the agents
  - graceful pause
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - TaskList
  - TaskGet
  - TaskStop
  - Skill
---

# /soft-pause — drain to savepoint, park, resume without loss

**Contract:** `/soft-pause` = every running unit finishes its CURRENT task to the
next savepoint, then parks. Nothing is killed mid-flight; nothing paid for is
thrown away. `/soft-pause --hard` = stop NOW, losing only the delta since the
last savepoint (bounded by the contract below). `/soft-pause resume` = clear the
sentinel and pick everything back up. Also the crash-recovery path.

The sentinel + gate plumbing is LAW, not prose: `quota-gate.sh` exit `7 SOFT_PAUSE`
(see `scripts/grind/quota-gate.sh`) refuses to green-light any next task while
`.claude/grind/PAUSE` exists. This skill is the operator surface over that law.

## The savepoint contract (canonical statement)

This contract is what makes pausing — and power cuts — cheap. It is injected into
/grind, /semi-grind, and /sprint builder dispatch prompts; `/culture` carries the
reusable template (`references/savepoints.md`).

| Unit | Savepoint | Mechanism |
|---|---|---|
| Builder agent | one completed task = one scope-guarded commit | git (pre-commit hook enforced) |
| Workflow run | every `agent()` completion | `journal.jsonl` — automatic, harness-native; resume via `resumeFromRunId` (unchanged prefix replays free) |
| Orchestrator | `state.json` write + run-log row per wave event | `grindjson.py` atomic write |

- **No builder task may run longer than ~10 minutes without producing a commit.**
  Longer tasks MUST be decomposed at dispatch time. This line bounds the
  worst-case loss for `--hard` and for a power cut alike.
- Between savepoints = the at-risk zone. Keep it small; that is the whole rule.

## `/soft-pause` (default — drain)

1. **Set the sentinel + audit:** `mkdir -p .claude/grind && touch .claude/grind/PAUSE`,
   then `bash $G/quota-gate.sh` once to confirm it answers `SOFT_PAUSE` (exit 7)
   and to land the audit-chain entry. (`$G` per grind-bootstrap; outside a grind
   repo just create the sentinel — step 2 still works.)
2. **Enumerate live units:** `TaskList` for running agents/workflows; read
   `.claude/grind/run-log.md` concurrency manifest if present.
3. **Drain:** each builder finishes its current task to the commit, then parks
   (the orchestrator loop hits the gate's exit 7 and dispatches nothing new).
   Workflow runs park at their next `agent()` boundary — do NOT `TaskStop` them;
   their journal is already the savepoint. Typical settle: 2–10 min.
4. **Bundle for resume:** regenerate `RESUME.md` (grind window-end machinery),
   run `/context-save`, `bash $G/swarm-claim.sh release` (free the globs for
   other swarms while parked), `bash $G/lock.sh release`.
5. **Settle report — always surface this table:**

```text
## Soft-pause settle — <UTC ts>
| unit | role | savepoint reached | lost |
|------|------|-------------------|------|
| a1b2 | builder T-07 | commit 3f2a91c (task complete) | nothing |
| wf_x | workflow wave-2 | journal @ agent 7/9 | nothing |
```

The sentinel stays. The session may end; the machine may power off.

## `/soft-pause --hard` (stop NOW)

Same as above but step 3 is `TaskStop` on every unit immediately. Loss = work
since each unit's last savepoint — bounded to ~10 min per builder by the
contract. Use when the founder needs the machine NOW or a unit is misbehaving.
Report what was lost per unit in the settle table (never claim "nothing" unless
verified against the last commit/journal entry).

## `/soft-pause resume` (also the crash-recovery path)

1. `rm .claude/grind/PAUSE` (if present) + audit entry.
2. Reload `state.json`: focus globs, campaign + feature branches, team manifest,
   `window_counter`.
3. **Re-poll quota FIRST:** `bash $G/quota-gate.sh --force` — a pause burns
   wall-clock, not tokens; the 5h window did NOT pause with you. Obey the exit
   code (a resume straight into `STOP_FLOOR` parks again until the reset).
4. Re-claim the swarm board: `bash $G/swarm-claim.sh check` then `claim`
   (someone may have legitimately claimed your globs while you were parked —
   exit 2 means negotiate, not bulldoze).
5. Parked Workflow runs: relaunch with `Workflow({scriptPath, resumeFromRunId})`
   — the journal prefix replays free; only live work re-runs. Builders resume
   from their branches (`.claude/worktrees/*` + `state.json .sessions[]`).
6. `/context-restore` if the session is fresh; re-acquire `lock.sh`.

**After a power cut / crash** there is no PAUSE sentinel — detect via a stale
`.claude/grind/.lock` (lock.sh reclaims >6h or dead-PID locks) plus dirty
worktrees. Run the same steps 2–6; the loss is whatever sat between savepoints.

## Rules for agents

- **Never** kill a unit that is mid-task when a drain was requested — exit 7 means
  finish-to-savepoint, not abort. (`--hard` is the founder's explicit call.)
- **Never** `TaskStop` a Workflow run to pause it — its journal already
  checkpoints; parking at the next `agent()` boundary is free, killing is not.
- **Never** dispatch a builder task estimated >10 min without decomposing it —
  the savepoint contract is what makes every pause and every power cut cheap.
- **Never** resume without re-polling `quota-gate.sh --force` and re-checking
  `swarm-claim.sh check` — wall-clock moved and teammates may have claimed globs.
- **Never** report "nothing lost" without checking each unit's last savepoint.
- **Always** leave the settle table in the transcript AND in `RESUME.md`.
