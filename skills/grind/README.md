# /grind + /semi-grind — global install

These two skills are installed **machine-globally** (`~/.claude/skills/grind/`,
`~/.claude/skills/semi-grind/`) so they're invocable from any repo on this machine.
`/quota` is likewise global and self-contained.

## How "global" works

- **`scripts/grind/`** here is the bundled **guardrail library** (the law: `quota-gate.sh`,
  `scope-guard`, `landable-guard`, `value-gate`, `hygiene-check`, `lock.sh`, `config.sh`,
  `lib.sh`, `cost-table`, `audit-verify`, `grindjson.py`). `/semi-grind` reuses it verbatim.
- **`grind-bootstrap.sh`** is the entrypoint both SKILL.md files `source` at Step 0. It:
  1. exports `$G` = repo-local `<repo>/scripts/grind` when present (so **Underline keeps its
     own committed copy + lefthook wiring**), else this global bundle;
  2. arms the `scope-guard` (pre-commit) + `landable-guard` (pre-push) hooks for the cwd repo
     — idempotent; already-wired repos (lefthook `grind-*`, or a `!!! GRIND HOOK !!!`-marked
     git hook) are left untouched; a foreign existing hook is **never clobbered** (returns
     `HOOK_CONFLICT` with a manual-wire instruction instead).
- State (`.claude/grind/`) is always **per-repo** (cwd-relative), created by `lock.sh acquire`.

## Source of truth / divergence

### Reset note (2026-07-10)

- What changed: canonical home moved **Underline → the `grindhouse` repo**
  (`F:\code\grindhouse`, github.com/BartekDu/grindhouse, private). It holds the
  guardrail library AND all seven engine skills (grind, semi-grind, sprint,
  soft-pause, culture, grind-office, quota).
- Why: the engine outgrew being a subfolder of one product repo — it is now a
  machine-global skill network used across projects; a product repo as canonical
  made every law change a product PR.
- Historical artifacts: Underline's committed `scripts/grind/` remains as a
  **vendored downstream copy** (its lefthook wiring needs it; PR #117 carries the
  v2 law). Older docs saying "Underline is canonical" describe the pre-2026-07-10
  state.

Sync direction: **grindhouse → everywhere** — edit in `F:\code\grindhouse`, then:

```bash
bash /f/code/grindhouse/install.sh          # → ~/.claude/skills (this bundle)
cp -f /f/code/grindhouse/scripts/grind/*  /f/code/Underline/scripts/grind/   # re-vendor Underline
# (grind-bootstrap.sh IS in grindhouse; it is still never vendored into product repos)
```
