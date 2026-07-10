# Agent conventions

## Promote-to-agent rule

**Origin:** P.i.w.o, verbatim: *"If you find yourself in a conversation
re-explaining the same complex process… promote it to an agent file BEFORE the
session compacts."* Subagents are durable memory that survives compaction.

Triggers — any one:
- >100 words of process being re-explained that isn't captured anywhere;
- a named role invoked more than once ("the reviewer", "the stylist");
- about to spawn an ad-hoc agent with a long inline prompt.

## Agent hygiene

- **Never** create overlapping agents (`brewer-v2`, `brewer-extended`) — update
  the canonical one, additively.
- **Never** rewrite an agent file mid-task unless asked — treat personas like
  memory: additive updates only.
- Reuse before creating: a sprint staffing a "usual work" role takes the
  existing persona; only novel roles get new files (written BEFORE dispatch).

## Council shapes (from Underline §15)

**Multi-lens council** — MUST quiz the parent which mode before running:
- **debate**: parallel agents, ~6× tokens, surfaces contradictions — for real
  forks where perspectives genuinely conflict;
- **lens-pass**: single context wearing lenses sequentially, ~1× tokens — the
  DEFAULT. *"Do not skip the quiz; do not silently default to debate."*

**Single-lens specialist** — one charter, no quiz, ≤5 findings per category
(prioritize, don't dump nits), a fixed markdown output anchor, a declared token
cap, reads ONLY the plan + a small canonical file set — never the whole repo.

## Codex as standing external member (ratified 2026-07-10)

**Origin:** a retroactive codex run on a shipped Underline plan produced 15
findings (4 CRITICAL, 8 HIGH) in error classes that are structurally
Claude-blind: cross-doc coordination failures within one session,
multi-thousand-line internal-consistency checks, architectural-reframing
propagation.

**MANDATORY** codex pass on:
- every `/sprint` charter `PLAN.md` before wave 1;
- every `/semi-grind` EVOLVE feature design (locked convention 1);
- any council of ≥3 agents deciding a GATE-class question — codex sits as the
  standing external member, one consult per decision.

**FREE (no codex):** routine per-cluster/per-item fixes, mechanical AUTO work,
small PRs. Manual `/codex` always available. Per-PR mandatory codex was
evaluated and rejected — ~10–13 invocations + 3–5h founder gate time per
feature is solo-founder bureaucracy; ceremony only where the stakes are.
