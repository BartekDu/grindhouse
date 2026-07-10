# AUTO / GATE / internal-convention triage

**Origin:** Underline's `chief-stylist.md` boundary, generalized. It is what
lets an autonomous loop run fast without ever making the founder's taste calls.
The canonical example of the third category: CF-012 (`onBack` prop) — flagged
as a divergence, resolved as an engineering decoupling call, documented as
RULE-042, **not quizzed** (quizzing it would be handholding).

For every proposed change, stamp **exactly one**:

## AUTO — do it silently

Objective, mechanical, behavior-preserving, reduces a measurable count:
- hardcoded hex / magic literal → token; off-scale value → nearest scale;
- missing a11y role/label added; reduce-motion gated;
- a banned word → its **documented** swap; dead cast removed;
- mechanical wiring with no taste fork (route registered in both navigators).

A builder applies it; the value-gate passes on the count drop. No quiz.

## GATE — quiz the founder (or log the decision)

Anything needing judgment:
- layout / flow / hierarchy / IA restructure;
- changing what a feature DOES, or risking a downgrade;
- ANY new user-facing copy (routes through copy review, never invented inline);
- a rule candidate that encodes taste.

**When unsure → GATE.** Demoting a wrongly-AUTO'd taste fix after it ships is
expensive; a spare quiz costs a minute. Founder absent → log a `DD-NNN` and
continue on unblocked work (never hang an AskUserQuestion in an empty room).

## Internal convention — agent decides + documents

Zero user-facing impact = nothing for the founder to have taste about:
- the agent decides, documents it as a convention, ratifies a RULE — no quiz.
- Quizzing these violates "don't hand-hold; reserve pauses for real forks."

## Quiz house format (when GATE fires)

Preamble ABOVE the quiz, exactly four parts: **Impact** (cite severity + IDs) ·
**Scope** (screens/files) · **a key Insight** (the one non-obvious discovery) ·
**`Recommendation: <option> — because <one-line why>`** (in prose, not folded
into an option). Then 2–4 options, each with pros AND cons and an **ASCII
preview** (the founder is visual), recommended first, tagged "(Recommended)".
Pushback → REFRAME and re-ask; silence ≠ approval.
