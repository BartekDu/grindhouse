---
name: culture
preamble-tier: 3
version: 1.0.0
description: |
  The development-culture framework — battle-tested working patterns harvested
  from mature projects (P.i.w.o, Underline) and generalized: stable-ID registers,
  Never-blocks, reset notes, agent/council conventions, AUTO/GATE triage, the
  savepoint contract, swarm etiquette, the triple-write trap rule. Two commands:
  `/culture seed` bootstraps a repo with the templates; `/culture audit` checks
  an existing repo for drift (missing Never-blocks, renumbered IDs, stale
  reset-note stacks, oversized append-only logs). Constitution: every rule cites
  the incident that created it; rules with no incident don't ship; a collapse
  pass retires rules that stopped paying rent. Agile but professional.
  Use when asked to "culture seed", "culture audit", "seed the conventions",
  "development culture", or "/culture [seed|audit]".
triggers:
  - culture seed
  - culture audit
  - development culture
  - seed the conventions
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - AskUserQuestion
---

# /culture — the development-culture framework

**Constitution (read this before seeding anything):**

1. **Every rule cites the incident that created it.** A rule with no incident is
   speculation — don't ship it. (Every pattern below carries its origin story;
   copy the story with the rule.)
2. **Rules die when they stop paying rent.** The collapse pass (below) retires
   rules with no hits, merges reset-notes-correcting-reset-notes into clean
   prose, and rotates oversized append-only logs. Process that only accumulates
   is bureaucracy — we are agile but professional; no German bureaucracy.
3. **Enforcement lives in scripts and stable-ID registers, not in prose the
   model can rationalize around.** Prose cites; scripts and registers define.
   (The load-bearing insight of the whole grind engine.)
4. **Knowledge is promoted to durable artifacts the moment it would otherwise
   be re-explained** — an agent file, a rulebook row, a reset note. Compaction
   eats everything else.

## The patterns (each has a reference file with the template + origin)

| Pattern | File | One-liner |
|---|---|---|
| Stable-ID registers | `references/registers.md` | R-NNN/CF-NNN/RULE-NNN/DD-NNN: never renumber, never delete — close with date+sha |
| Never-blocks | `references/never-blocks.md` | every CLAUDE.md section ends with `### Rules for agents` in **Never** form |
| Reset notes + collapse pass | `references/reset-notes.md` | policy changes documented; stacks periodically collapsed; logs rotated |
| Agent conventions | `references/agents.md` | promote-to-agent, council debate-vs-lens quiz, single-lens shape, codex-as-standing-member |
| AUTO / GATE / convention triage | `references/triage.md` | what runs silently vs what quizzes the founder vs what the agent just documents |
| Savepoint contract | `references/savepoints.md` | commit ≤10 min; pause and power cuts become cheap |
| Swarm etiquette | `references/swarm-etiquette.md` | gh-issue ownership board; foreign claims = your forbidden_globs |
| Triple-write trap rule | `references/triple-write.md` | traps land in commit body + adjacent .md + `!!! TRAP !!!` comment |

**Deliberately NOT in the framework** (documented as opt-in, with why):
per-PR mandatory codex (heavy for a solo founder — codex is mandatory only at
plan-level: sprint charters, EVOLVE designs, big councils); mandatory
finops-lens per plan review; the 6-layer config checklist (project-specific —
the meta-rule "a config var must exist at every layer in the same PR" travels,
the layer list doesn't); the slow-versionName scheme (good story — "don't write
checks the product can't cash", born from a 2-day 0.0.2→0.5.4 version race —
but adopt per-project, not globally).

## Recommended external tools (optional, per project)

Third-party add-ons a grindhouse project can adopt. All **optional** and **not part of grindhouse** —
install them yourself; attribution noted. Document whichever you adopt in the project's CLAUDE.md.

**caveman** — compressed comms, ~75% fewer tokens, full technical accuracy. By Julius Brussee
(`github.com/JuliusBrussee/caveman`).
```
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```
Toggle with `/caveman lite|full|ultra`; disable with "stop caveman".

**graphify** — turns a codebase into a knowledge graph; query architecture / call paths before
Read/Grep sweeps. External CLI (`graphifyy`).
```
uv tool install graphifyy      # or: pip install graphifyy
```
Then use the `/graphify` skill. Convention: if `graphify-out/graph.json` exists, treat structure
questions as a `graphify query` FIRST. Keep it fresh with a post-commit `graphify <repo> --update` hook.

**codex** — multi-AI second opinion (review / challenge / consult). The CLI is OpenAI's; the
`/codex` skill wrapper is gstack's.
```
npm install -g @openai/codex   # OpenAI Codex CLI
codex login                    # or set $OPENAI_API_KEY / $CODEX_API_KEY
```
That gives raw `codex exec` / `codex review`. For the `/codex review|challenge|consult` wrapper
(pass/fail gate, adversarial mode, session continuity) install **gstack** (its own tooling — see gstack docs).

## /culture seed <repo>

1. Read the repo's CLAUDE.md (create a stub if absent).
2. Quiz the founder (AskUserQuestion, house format) on which patterns to adopt —
   default-recommend: registers, Never-blocks, reset-notes, triage. Offer the
   rest. Never seed everything silently; adoption is a choice.
3. For each adopted pattern, append its template section to CLAUDE.md (from the
   reference file) WITH the origin story, and create the on-disk skeletons
   (e.g. an empty register dir with the header row, a RULEBOOK stub).
4. End the new CLAUDE.md sections with their own `### Rules for agents`
   Never-blocks (the pattern applies to itself).
5. Report what was seeded + what was offered and declined (a register row).

## /culture audit <repo>

Read-only drift check; output a findings table (stable IDs: `CU-NNN`):

- CLAUDE.md sections missing a `### Rules for agents` block.
- Register hygiene: renumbered/deleted IDs (diff gaps), closed rows missing
  date+sha, clusters with no progress line.
- Reset-note stacks ≥3 deep on one topic → flag for a collapse pass.
- Append-only logs > 64KB (PROGRESS.md hit 167KB in the wild before this rule)
  → flag for quarterly rotation with a pointer stub.
- Rules with zero references in the last N commits → retire candidates.
- Agent hygiene: `-v2`/`-extended` persona forks (should be additive updates).

Findings are proposals — the founder decides; `/culture audit` never edits.

## Rules for agents

- **Never** seed a rule without its incident story — no incident, no rule.
- **Never** renumber or delete a register ID anywhere, ever — close, don't erase.
- **Never** turn an audit into silent edits — findings are proposals.
- **Never** add process that doesn't name the failure it prevents — when the
  collapse pass finds a rule paying no rent, retire it loudly (reset note).
- **Always** copy the origin story with the pattern — a rule without its why
  becomes bureaucracy within a quarter.
