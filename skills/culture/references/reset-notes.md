# Reset notes + the collapse pass

**Origin:** Underline/P.i.w.o CLAUDE.mds are peppered with `### Reset note
(<date>)` blocks (the codex policy change, the version-race reset from a 2-day
0.0.2→0.5.4 auto-bump incident, the stale `platform/` diagram). Rationale,
verbatim: *"Don't pretend the past didn't happen — reset notes acknowledge the
artifact (e.g. orphan tags, deprecated files) so future readers understand the
state they're seeing."*

**The pattern:** when any policy changes, write next to the policy:

```markdown
### Reset note (<YYYY-MM-DD>)
- What changed: <old → new, one line>
- Why: <the incident or data that forced it>
- Historical artifacts: <what still exists that doesn't fit, and what to do
  with it — leave / migrate / ignore>
```

## The collapse pass (the missing half — added 2026-07-10)

The wild exposed two failure modes the original pattern lacked an answer for:
reset-notes-correcting-reset-notes (Underline §10 documented a diagram for a
tree that *"never existed"*), and append-only logs without rotation
(PROGRESS.md at 167KB, TODOS.md at 43KB).

Quarterly (or when `/culture audit` flags it):

1. **Collapse stacks:** any topic with ≥3 reset notes → rewrite the section as
   clean current-state prose + ONE summary reset note listing the dates it
   absorbed. History stays in git; prose stays readable.
2. **Rotate logs:** append-only files >64KB → move to
   `<name>-archive-<quarter>.md`, leave a pointer stub + the last 20 entries.
3. **Retire dead rules:** rules with zero hits since the last pass → mark
   retired with a reset note saying so. Loudly, not silently.
