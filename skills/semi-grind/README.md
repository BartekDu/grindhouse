# /semi-grind — semi-supervised standardization campaign loop

**What it is.** The third autonomy mode for this repo, sitting between **interactive**
(founder prompts every step — too slow) and **`/grind`** (autonomous to the quota floor;
logs gates and moves on; too unsupervised for taste). `/semi-grind` runs agentic
cross-cutting **discovery** + autonomous **mechanical** fixes, but **BLOCKS on a founder
`AskUserQuestion` quiz** for every real taste / product / IA fork, ratifies the answer as a
stable `RULE-NNN`, and proceeds. It is governed by a living **waved register**
(`consistency-findings.md`: TC clusters + CF-NNN findings, never-renumbered, sha-stamped
status) and a living **rulebook** (`DESIGN_RULEBOOK.md`).

**It reuses, never reimplements, `/grind`'s guardrails.** Every hard guardrail —
`scripts/grind/{quota-gate.sh,scope-guard,landable-guard,value-gate,lock.sh,hygiene-check,
audit-verify,config.sh}` + the installed git hooks — is called verbatim (the hooks key off
`.claude/grind/.active`, not the skill/branch name). `/grind` itself is **untouched and stays
unattended-only**. The delta `/semi-grind` adds: the quiz-surface (orchestrator-only), the
AUTO/GATE/internal-convention classifier, the register governor, the rulebook governor, and
the EVOLVE-to-feature path.

**When to use:** a cross-cutting quality problem spanning multiple screens/wedges with a MIX
of mechanical + taste fixes, and a **semi-present** founder (reachable for a few quizzes, not
every step). **When NOT:** a closed task list (do-and-stop), a fully away-from-keyboard /
cron-resumed-into-empty-room burn (`/grind`), a one-line PR (`/review`), or plan-level
architecture (`/autoplan`).

## Spec

The runnable playbook + full contract live in
**`docs/process/semi-supervised-standardization-2026-06-09/`**:

- `PROCESS.md` — the formal process doc (roles, state machine, ID schemes, AUTO/GATE rule,
  quiz-gate contract, the full loop, the EVOLVE branch). Read once per cold start.
- `GRIND-INTEGRATION.md` — the standalone-vs-mode-vs-both analysis; the founder locked
  **Option C** (standalone skill reusing `scripts/grind/*`, `/grind` untouched).
- `SKILL-DRAFT.md` — the draft this `SKILL.md` was hardened from.
- `SEED.md` — the operator's first-hand account of the seed run.

## Live precedent

The seed campaign ran 2026-06-09 on branch **`grind-09-06-2026`** → **PR #64**:

- 58 CF findings → 8 triage clusters (TC-1..TC-8) in
  `docs/design/standardization-2026-06-08/consistency-findings.md`.
- Quizzes ratified **RULE-038..042** in `DESIGN_RULEBOOK.md` (cross-wedge switch on every tab
  root, one account surface, account-feature parity, shared-tabs-mirror, cross-domain routes +
  back-affordance convention).
- **TC-1** `✅ COMPLETED`; **TC-3** → RULE-039/040/041; **TC-4** mostly AUTO (route wiring +
  dead-cast removal) + the CF-012 `onBack` internal-convention call (documented, NOT quizzed);
  **TC-2** `🔄 EVOLVED → in design` ("Waiting for it",
  `docs/design/waiting-for-it-2026-06-09/`, GATE-pending after its own design workflow + codex).

Locked founder conventions (2026-06-09 quiz) baked into the skill: (1) codex+finops on the
EVOLVE branch only; (2) quizzes/DD-NNN stay out of `landable-guard`, flagged loudly at
window-end; (3) absent-founder fallback = degrade to grind's log-a-gate-and-continue;
(4) reuse the `grind-DD-MM-YYYY` branch prefix; (5) re-run `quota-gate.sh` on every
post-quiz/cron resume.
