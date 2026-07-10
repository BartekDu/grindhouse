# The triple-write trap rule

**Origin:** P.i.w.o — hard-won traps kept being re-hit because the knowledge
lived only in a commit body nobody re-reads, or a `docs/lessons/` graveyard
nobody visits. The recurrence chain got engineered instead: *"trap recurs →
inline comment alerts → operator follows to `.md` → `.md` cites commit hash for
full archaeological history."*

**The pattern:** any finding worth >2 sentences of commit body lands in THREE
places, same PR:

1. **The commit body** — what + why, full detail.
2. **A `.md` next to the code it concerns** — NOT a central lessons graveyard;
   discovery-by-proximity is the point. Cites the commit hash.
3. **A greppable inline comment at the trap site:**
   `!!! UPPERCASE TRAP NAME !!!` + one line + pointer to the `.md`.

Live examples: `!!! GRIND ENV TRAP !!!` (two-python trap in
`scripts/grind/config.sh`), `!!! GRIND HOOK !!!` (hook markers), the
FENCE-SKIP trap in landable-guard.

## Scope honestly

Traps only — the rule is overkill for routine changes, and applying it to
everything would bury the real traps. A trap = something that WILL be re-hit
by a future agent/operator acting reasonably: env quirks, ordering
requirements, silent-failure layers, things that look safe but aren't.
