# Never-blocks (`### Rules for agents`)

**Origin:** P.i.w.o CLAUDE.md — every section ends with a `### Rules for agents`
block written in `**Never**` form. Stated rationale, verbatim: *"Forces honesty
about what NOT to do, not just what to do. When adding a new section, you also
write the Rules block."* Applied consistently across ~16 sections in both
mature projects; the sections without one were where agents drifted.

**The pattern:** every CLAUDE.md section (and every SKILL.md) ends with:

```markdown
### Rules for agents

- **Never** <the specific failure this section exists to prevent>.
- **Never** <the tempting shortcut that recreates the incident>.
- **Always** <the one positive invariant worth stating> (use sparingly —
  Never-form forces sharper thinking).
```

## Laws

- Writing the section and writing its Rules block are ONE act — a section
  without a Rules block is unfinished.
- Each Never names a concrete failure, not a virtue ("**Never** run `gh secret
  set`" beats "**Always** handle secrets carefully").
- When an agent violates a Never, the fix is usually a script/hook, not a
  louder Never (constitution rule 3).
