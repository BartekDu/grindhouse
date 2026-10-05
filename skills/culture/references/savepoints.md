# The savepoint contract

**Origin:** pausing a 20-agent Fable swarm used to mean killing it — 30 minutes
× 20 agents of paid work gone; a power cut meant the same with no warning.
Ratified 2026-07-10 with the `/soft-pause` skill and quota-gate exit 7.

**The contract** (inject into every builder dispatch prompt):

| Unit | Savepoint | Mechanism |
|---|---|---|
| Builder agent | one completed task = one commit | git (hook-enforced scope) |
| Workflow run | every `agent()` completion | `journal.jsonl` (automatic); resume via `resumeFromRunId` — unchanged prefix replays free |
| Orchestrator | `state.json` write + run-log row | atomic write |

- **No builder task runs >~10 minutes without producing a commit.** Longer
  tasks are decomposed AT DISPATCH — "commit when done" is the anti-pattern.
- Between savepoints = the at-risk zone; the rule exists to keep it small.
- Pause = drain to next savepoint, park (never kill mid-task); hard-stop and
  power cuts lose only the at-risk zone.
- Resume runs one turn, then the quota gate, before any new work — pauses
  burn wall-clock; the 5h window does not pause with you.

Full operator procedure: `~/.claude/skills/soft-pause/SKILL.md`.
