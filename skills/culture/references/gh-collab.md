# GH-issue collaboration — the human↔swarm bridge

**Origin:** ratified 2026-07-11. Audit found every human surface of the grind engine was
session/shell-bound (focus-contract approval + AskUserQuestion = session owner only;
gate-ledger.md = repo file; STOP/PAUSE = shell sentinels; grind-office = Claude session).
A non-technical teammate with only github.com web access could neither feed work, see gates,
nor answer them. GitHub issues fix all three — no VS Code, no shell, no Claude session needed.

## TODO intake (humans → swarm)

- Humans file issues from the GitHub web UI. Label **`grind-ok`** marks an issue as
  swarm-consumable (an unlabeled issue is a discussion, not a task).
- Agents read the queue via `gh issue list --label grind-ok --state open` (best-effort —
  skip silently without gh/remote, same degradation as the swarm board).
- One issue = one task. The agent comments progress on the issue and closes it with the
  landing commit / PR ref. In /grind, `grind-ok` issues are ladder tier (b) backlog and
  `closes issue #N` passes the value-gate.

## Human-gate mirroring (swarm → humans)

- When a run hits a human-gate, besides the gate-ledger row it files
  `gh issue create --label human-gate` (best-effort, degrade silently).
- Answers come as issue comments. **Only repo-collaborator comments count as clearance.**
  Taste/GATE-class decisions remain founder-only per the constitution — a collaborator
  comment can clear an operational gate, never ratify a RULE-NNN.
- At window start / post-quiz resume, the orchestrator reads open `human-gate` issues +
  fresh comments (one `gh issue list` call) and folds clearances into the gate-ledger.

## Etiquette

- Agents NEVER close a human-opened issue without a linking comment (what landed, where).
- The **`swarm-claim`** label stays reserved for the agent↔agent ownership board
  (`scripts/grind/swarm-claim.sh`) — never reuse it for TODOs or gates.
- Humans can request a pause by commenting **`PAUSE`** on the live swarm-claim issue; the
  orchestrator polls for it at each quota-gate poll (rate-limited by
  `GRIND_POLL_MIN_INTERVAL_SEC`) and treats it like the PAUSE sentinel (drain to savepoint,
  park — see /soft-pause).
