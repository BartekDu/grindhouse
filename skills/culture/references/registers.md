# Stable-ID registers

**Origin:** P.i.w.o's audit tree — 240 `R-NNN` rows across S1–S4 — and
Underline's standardization campaign (58 `CF-NNN` → 8 `TC-N` clusters → PR #64).
Renumbering once broke cross-references between sessions; the fix became law.

**The pattern:** any multi-session structured work (audit, refactor, QA
campaign, standardization, sprint) gets a dedicated register dir with stable,
never-renumbered IDs.

## ID families

| Prefix | Meaning |
|---|---|
| `R-NNN` | risk (audits) |
| `F-NNN` | finding |
| `CF-NNN` | consistency finding |
| `TC-N` | triage cluster (a fix wave, groups CFs) |
| `RULE-NNN` | ratified rulebook entry |
| `DD-NNN` | decision — surfaced / answered / deferred |
| `CU-NNN` | culture-audit finding |

## Laws

- **Never renumber. Never delete.** Close with `**Status: closed** (<date>,
  <commit sha>)`. Statuses: `closed` / `partial → TC-x` / `✅ COMPLETED` /
  `🔄 EVOLVED → in design` (an EVOLVED cluster closes only when its feature
  lands AND its mechanical baseline is wired).
- **Bidirectional anchors:** cluster→CFs and CF→cluster links; a CF may belong
  to more than one cluster.
- **Single atomic writer** per register file (Underline: chief-stylist). Two
  sessions writing one register = corruption; route through the owner.
- **Progress line at the top** of the register, mirrored into the live task
  board so the founder glances "done / here / next" without holding state.

## Dir skeleton (CLAUDE.md §15.2 shape)

```
<register-dir>/
  BRIEFING.md    what + why (frozen)
  PLAN.md        the charter (frozen after review)
  RESUME.md      operator-voice "where we are / next / open gates"
  state.json     canonical machine state (atomic writes only)
  run-log.md     append-only timestamped events
  <topic>.md     the register itself (## Triage clusters + ## Findings)
```

## Rulebook row format

```
RULE-NNN | <domain> | <the rule, one bold sentence> | source: <TC/CF/quiz-date/file cite>
```

Retired rules get `**Status: retired** (<date>, superseded by RULE-MMM)` — the
row stays.
