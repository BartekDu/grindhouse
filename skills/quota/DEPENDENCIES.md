# Custom skills — dependencies + reproducibility

Backed up via the private `claude-config` repo (`git@github.com:BartekDu/claude-config.git`,
synced from `~/.claude` into `snapshot/skills/`). These are OUR custom skills, distinct
from gstack (which is reproduced by cloning, not backed up here).

## /quota (custom)
- `SKILL.md` + `claude_usage.py` (this dir). `claude_usage.py` reads the `/usage` TUI panel
  via a pseudo-terminal (no headless `/usage`). Dual backend: stdlib `pty` on Linux/macOS,
  pywinpty/ConPTY on Windows.
- **Runtime deps:** `pip install pyte` (all platforms) + `pip install pywinpty` (Windows only).
- **Background logger (optional):** Linux = systemd user timer, units in `./systemd/`
  (`claude-quota-log.{service,timer}`); Windows = `ClaudeQuotaLog` scheduled task.
- **Path note:** the old 4-place coupling is dead — THIS dir's copy is what `install.sh`
  ships to `~/.claude/skills/quota/`, grind's `config.sh` auto-resolves `GRIND_QUOTA_TOOL`
  (repo-vendored `.claude/skills/quota/` copy wins, else the installed skill; env override
  for anything else), and both background loggers invoke the installed copy. A wrong
  override still fails the gate CLOSED (POLL_FAILED, no grind can start).

## /grind (custom) — canonical home: the grindhouse repo (since 2026-07-10)
- Source of truth: `F:\code\grindhouse` (github.com/BartekDu/grindhouse, private) —
  `scripts/grind/*` (the law: quota-gate, scope-guard, landable-guard, lock, cost-table,
  value-gate, audit-verify, grindjson.py, swarm-claim.sh, grind-bootstrap.sh) + `skills/*`
  (all seven engine skills incl. THIS one). `install.sh` syncs to `~/.claude/skills`.
  Underline keeps a vendored downstream copy of `scripts/grind/` (lefthook wiring; PR #117).
  Pre-2026-07-10 docs saying "Underline branch feature/grind-skill is canonical" are historical.
- **Depends on:** `/quota` (this skill) + `claude_usage.py`; and gstack `/codex`, `/qa-only`.
- **Engine siblings (2026-07-10):** `/sprint` (scope-bound delivery), `/soft-pause`
  (drain-to-savepoint pause; quota-gate exit 7), `/grind-office` (read-only dashboard),
  `/culture` (framework) — all in `~/.claude/skills/`, all reusing the same
  `scripts/grind/*` law. Engine-v2 law upgrades: Underline PR #117.

## gstack skills (/codex, /qa-only, /autoplan, /review, ...) — NOT backed up here
- Reproduced by cloning: `git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack`
  then `cd ~/.claude/skills/gstack && ./setup --team` (installs the sibling skills under `~/.claude/skills/`).
- Vendoring them here would duplicate an upstream repo — clone instead.
