# /grind default profile — the learned rules, in one place

`/grind`, `/sprint` and `/semi-grind` cite this file instead of restating it.
Thresholds (floor, reserve, caps) live in `config.sh`; this file holds the
working rules learned from past campaigns. Each rule names the incident behind
it. A rule that stops paying rent is deleted here, nowhere else.

## Orchestrator session

- Run the orchestrator at `/effort high` and `/autocompact 200k`. The `Agent`
  tool has no `effort` parameter: every agent it starts inherits the session's
  effort, so the session setting IS the agent setting. A grind session left at
  `max` ran 58 Sonnet agents at `max` (session `6c5ee3ea`, 2026-09-27, about
  $240 of $655). Step 0 prints this; the founder types both commands.
- Workflow `agent()` calls do take `effort`: set it from the role table in
  grind `SKILL.md` § Model + effort (the one copy of that table).
- Per-model weekly bar: the statusline readings do not carry it today, so
  check `/usage` once by hand at Step 0. If that bar is near
  `GRIND_HARD_STOP_WEEK_MODEL_PCT`, set `--until` (or `GRIND_HARD_STOP_AT`).

## Every brief (builder, verifier, fixer)

- Paste `.claude/grind/rules.md` verbatim (the project's hard constraints;
  `bash $G/rules-init` creates the skeleton).
- One task = one commit within the savepoint limit (SKILL.md § Savepoints).
  Write the deadline into the brief as an absolute UTC time: `wave-brief`
  prints it (now + `GRIND_TASK_DEADLINE_MIN`). Agents without a clock target
  overran their slices.
- Builders report in the project's language (the language of its docs and
  commit bodies), so the founder reads reports without translating.
- Paste excerpts of files that `wave-brief` lists as re-read, instead of
  letting each agent open them again.

## Checks and gates the agents write

- Fail closed: a check script exits non-zero unless it saw every expected
  result, and the count of results equals the count of tasks. Incident
  (grind-05-10-2026, rysobot_v2): the bed-check returned rc 0 when every
  model errored, a false green.
- Every new check ships with a control case that MUST trigger it (a known-bad
  input). Incident (V-11): the test for rotation direction passed with the
  rotation reversed.
- The verifier reads the changed documents too, not only code and test
  output: duplicated sections, stale numbers, copy-paste leftovers. Incident
  (V-16): duplicated KARTA sections passed code-only verification.

## Waves

- Before each dispatch wave: `bash $G/quota-gate.sh`, then `bash $G/wave-brief`
  (advisory). An agent past 100 requests means its task was too big: split
  the next one like it.
- After a wave that changed the staffing (model or effort of a role), run
  `/ledger quality` before keeping the change.
- No A/B experiments on builders inside a production grind: one staffing per
  role per campaign. Experiments run on purpose-built tasks.
