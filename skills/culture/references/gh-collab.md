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

## Bug intake (manual testers → swarm)

- Testers file issues labeled **`bug`** from the web UI. Title = the symptom, imperative
  ("Login button dead after logout"). Body per the template below (installable as
  `.github/ISSUE_TEMPLATE/bug_report.md` by `/culture seed`):

```markdown
### Steps to reproduce
1. ...
2. ...

### Expected
...

### Actual
...

### Build / environment
version or commit sha, browser/device, account type

### Severity (reporter's guess)
blocker / major / minor / cosmetic

### Screenshot / recording
(attach if visual)
```

- **Agent pre-triage** (best-effort, e.g. the campaign scout): attempt the repro steps, dedup
  against open issues, comment findings on the issue. **Agents never add or remove
  `fix-accepted`** — acceptance is a human act.
- A human repo collaborator adds **`fix-accepted`** = green light to fix. From then on the
  issue is swarm-consumable exactly like `grind-ok`: ladder tier (b) in /grind,
  `closes issue #N` passes the value-gate, closed with the landing commit/PR ref + a linking
  comment.

## Bug-fix campaign (fix-accepted list → grind)

- A batch of triaged bugs = its own campaign: `/grind <focus globs covering the affected
  area>`. The ladder picks up in-focus `fix-accepted` issues; each bug = one builder task on
  a `grind/feat/<slug>` branch; the **verifier must re-run the reporter's repro steps**
  before the orchestrator merges.
- Out-of-focus `fix-accepted` bugs are NOT touched (the focus contract wins); list them in
  the status report so the founder can cut the next campaign around them.

## Validity escalation (`needs-human-review`)

- **Triggers:** repro fails on the reporter's exact steps; the issue references behavior/UI
  that does not exist; it describes intended behavior as a bug; it conflicts with another
  open/accepted issue, an existing RULE-NNN, or a shipped DD-NNN founder decision.
- **Action:** do NOT fix, do NOT close, do NOT argue in-thread. Add label
  **`needs-human-review`** + ONE structured comment: what was tried (repro attempts, env,
  commit sha), why it looks invalid OR what it conflicts with (link the conflicting
  issue/rule), and one neutral question to the reporter. Log to the run-log; a gate-ledger
  row only if it blocks the campaign. Then move to the next task.
- **Re-entry:** a collaborator removes `needs-human-review` and adds/keeps `fix-accepted` →
  the issue is back in the queue.

## Label bootstrap (per project, once)

```bash
gh label create grind-ok           --color 0e8a16 --description "swarm-consumable TODO"
gh label create fix-accepted       --color 1d76db --description "triaged bug, swarm may fix"
gh label create human-gate         --color d93f0b --description "swarm blocked, needs human answer"
gh label create needs-human-review --color fbca04 --description "suspected invalid/conflicting issue"
gh label create bug                --color b60205 --description "manual tester report" 2>/dev/null || true
# swarm-claim is reserved for scripts/grind/swarm-claim.sh
gh label create swarm-claim        --color 5319e7 --description "agent ownership board (reserved)"
```

## Etiquette

- Agents NEVER close a human-opened issue without a linking comment (what landed, where).
- The **`swarm-claim`** label stays reserved for the agent↔agent ownership board
  (`scripts/grind/swarm-claim.sh`) — never reuse it for TODOs or gates.
- Humans can request a pause by commenting **`PAUSE`** on the live swarm-claim issue; the
  orchestrator polls for it at each quota-gate poll (rate-limited by
  `GRIND_POLL_MIN_INTERVAL_SEC`) and treats it like the PAUSE sentinel (drain to savepoint,
  park — see /soft-pause).
