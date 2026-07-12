---
name: quota
description: |
  Check real Claude usage limits (5-hour + weekly %) by reading the actual
  /usage panel, and decide whether to PAUSE an autonomous task chain. Use as a
  pre-task precaution during a "go" run, or when asked "how much quota is left",
  "check usage", "am I near the limit". Subcommands: `/quota log` (recent logged
  rows table), `/quota plot` (ASCII chart of logged history).
---

# /quota — usage precaution for autonomous "go" runs

Reads the REAL `/usage` numbers (there is no headless `/usage`; the tool drives
the TUI through a pseudo-terminal — same `claude` binary, same auth; stdlib
`pty` on Linux/macOS, pywinpty/ConPTY on Windows) and tells you whether to keep
running the task chain or PAUSE.

## Subcommands — dispatch on the argument FIRST

| Invocation        | Action                                                                 |
| ----------------- | ---------------------------------------------------------------------- |
| `/quota` (no arg)  | Live reading + PAUSE decision (spawns nested session, ~13s).            |
| `/quota log`       | Last N (default 20) logged rows as a table. Auto-refreshes first (see below). |
| `/quota plot`      | **Default.** High-res stacked block-bar panels (5h + weekly) on a **time-proportional x-axis** (gaps in logging show as `·`), midnight `┬` ticks with weekday labels + intermediate hour ticks, vertical lines marking 5h resets. Plus a **current-window burn projection**: burn rate, projected % at next reset, and a SAFE / BRAKE-RISK verdict (when you'd cross the 20% pause floor). **Shows the last 10 days by default** — older samples are silently dropped (`--all` for full history, `--days N` for a different cap). `last N samples` (the positional int) still trims further. Auto-refreshes first (see below). |
| `/quota plot bars` | Colored emoji bars (🟦 5h / 🟪 week / 🟥 reset), last N (default 16). Coarser, but color survives the chat relay. (`emoji` = alias.) Auto-refreshes first. |
| `/quota plot weekly` | **Weekly-reset analysis.** Segments the full history into weekly cycles (one cycle = from a weekly-quota reset until the next — detected by a ≥50-point upward snap, not the drifting forecast string), prints a per-cycle stats table (duration, begin/end/min %, used %, avg burn/day, peak + current burn/h, sample count), a **dynamic block** for the live cycle (current burn, next-reset ETA, projected % at reset, projected exhaustion time), and **1st + 2nd derivative panels** of the weekly burn (burn %/h and acceleration %/h²) over the timeline. Add `table` (or `--no-deriv`) for the table only. (`week` / `cycles` / `resets` = aliases.) Ignores the 10-day cap (cycles are ~7 days). Auto-refreshes first. |

**Auto-refresh:** every `log` / `plot` / `bars` invocation FIRST appends a fresh
sample to the global CSV (one nested /usage read, ~13s) — unless the newest
logged sample is < 5 min old, in which case it's skipped (no double-spend).
An OPTIONAL background logger (Linux: systemd user timer `claude-quota-log.timer`,
units in `./systemd/`; Windows: the `ClaudeQuotaLog` scheduled task) can log
every 30 min; the skill and the logger share the same CSV. Pass `--no-refresh`
(or set `QUOTA_NO_REFRESH=1`) for an instant, read-only view of logged data.

```bash
python3 ~/.claude/skills/quota/plot_quota.py rows        # /quota log  (last 20)
python3 ~/.claude/skills/quota/plot_quota.py rows 40     # /quota log 40
python3 ~/.claude/skills/quota/plot_quota.py             # /quota plot (block panels, last 10 days)
python3 ~/.claude/skills/quota/plot_quota.py --all       # /quota plot (full logged history)
python3 ~/.claude/skills/quota/plot_quota.py --days 30   # /quota plot (last 30 days)
python3 ~/.claude/skills/quota/plot_quota.py 48          # /quota plot (block panels, last 48 samples)
python3 ~/.claude/skills/quota/plot_quota.py bars        # /quota plot bars (emoji, last 16)
python3 ~/.claude/skills/quota/plot_quota.py bars 20     # /quota plot bars 20
python3 ~/.claude/skills/quota/plot_quota.py weekly      # /quota plot weekly (cycle table + derivative panels)
python3 ~/.claude/skills/quota/plot_quota.py weekly table # /quota plot weekly (table only, no graphs)
python3 ~/.claude/skills/quota/plot_quota.py --no-refresh  # read-only, instant (no nested session)
```

(Windows git-bash: swap `python3` for `python`. If the repo vendors its own copy
at `.claude/skills/quota/`, prefer that path.)

**Color note:** the default block-panel chart reads in monochrome through chat
(ANSI color only lights up cyan/magenta/red on a real terminal; reset markers
show as dashed `╎` in mono, red `│` on a TTY). For color *in chat*, use
`/quota plot bars` — emoji squares are real colored glyphs that survive a code
fence (the trade-off is coarser ~10%/cell bars). Paste output as-is.

Run the command, paste its output, and state the latest line
(`5h=NN%  week=NN%`). Then STOP — do not also run the live reading below.

Everything past here is the **no-arg** live-reading path.

## The model it serves
- **"go"** = the founder's authorization to run a chain of tasks autonomously.
  NOT re-confirmed between tasks — don't nag "go?" again.
- Before **each meaningful task**, poll this (precaution). Sub-steps within a
  task reuse the last reading.
- **`quota_tight` true** (5h `<= 20%` left OR week `<= 10%` left) → **PAUSE**:
  don't start the task, surface the number, wait for "go".
- A **real gate** (unauthorized shared-state landing, security/data trade-off,
  taste call, ambiguous scope) → stop regardless of quota.
- **"pause" / interrupt** → finish the current task, then wait for "go".

No time/peak/weekend factor: founder is Pro/Max and Anthropic permanently removed
peak hours for Pro/Max on 2026-05-06. Flat thresholds.

## Two threshold regimes (INTENTIONAL, not drift)

The same reader (`claude_usage.py`) feeds two different regimes:

| Regime | Where | Thresholds | Why different |
|---|---|---|---|
| **Interactive precaution** (this skill) | `quota_tight` in the tool | 5h ≤ 20 OR week ≤ 10 | a present founder wants early warning + headroom to decide |
| **Autonomous law** (grind engine) | `scripts/grind/config.sh` via `quota-gate.sh` | floor 10 / weekly 10 / model-weekly 10 / reserve +5 | an autonomous run is SUPPOSED to run deeper — the floor is the product, and the gate (not the model) enforces it |

They also cache separately (`.claude/grind/.quota-cache.json` vs this skill's
5-min CSV freshness rule). Do not "unify" them — the difference is the design.
The gate reads `week_model_pct_left` too (since 2026-07-10; it was blind before
and a Fable grind could exhaust the model week unseen).

## Path model (the 4-place coupling is dead)

The copy in this repo (`skills/quota/claude_usage.py`) IS the executed tool:
`install.sh` puts it at `~/.claude/skills/quota/claude_usage.py`, grind's
`config.sh` auto-resolves `GRIND_QUOTA_TOOL` (repo-vendored
`.claude/skills/quota/` copy at the main root wins, else the installed skill;
env/project.conf override for anything else — a wrong path still fails the
gate CLOSED: POLL_FAILED), and the background loggers invoke the installed
copy via `log_quota.py`. One source, one install step, no desktop copies.

## Run
```bash
python3 ~/.claude/skills/quota/claude_usage.py --json    # Windows git-bash: python
```
~13s; spawns a short nested `claude` session (the only way — `/usage` has no
headless output). Deps: `pyte` (all platforms; Linux/macOS use stdlib `pty`)
plus `pywinpty` on Windows only.

Parse `five_hour_pct_left`, `week_pct_left`, `week_model_pct_left`,
`quota_tight`. If `quota_tight`, PAUSE + surface, e.g. `5h 18% left — paused
before task 6`.

**Per-model weekly limits:** the /usage panel shows a SEPARATE weekly bar for
the model tier in use (`Current week (Fable)` next to `Current week (all
models)`) — different numbers, and the model bar usually runs out first.
`week_pct_left` = all-models; `week_model_pct_left` + `week_model` = the
model-specific bar. `quota_tight` fires when EITHER weekly (or the 5h) is at
the floor. When surfacing, name the binding limit: `fable week 3% left` reads
very differently from `week 3% left` (other models may still have plenty).

## Rules for agents
- **Poll before each meaningful task** during a "go" run — under-polling is the
  real risk; the ~13s cost is acceptable.
- **Never** re-poll per micro-step (sub-steps reuse the last reading).
- **`quota_tight` → PAUSE + wait for go.** Never run the chain into the limit.
- **Never** skip a REAL gate just because quota is fine.
- **Never** fabricate numbers — if the panel won't parse, say so.
- Thresholds live in the tool: `FIVE_H_PAUSE_PCT=20`, `WEEK_PAUSE_PCT=10`.
- Tool: `~/.claude/skills/quota/claude_usage.py` (a repo may vendor its own
  copy at `.claude/skills/quota/` — prefer that when present). Deps: `pyte`
  (+ `pywinpty` on Windows only).
- **`log` / `plot` subcommands auto-refresh** — they append one fresh sample
  (nested /usage read, ~13s) to `~/.claude/quota_log.csv` via `log_quota.py`,
  then plot. Skipped automatically when the newest sample is < 5 min old, so
  rapid re-invocations never double-spend. Dispatch on the arg before the
  no-arg live path. The optional background logger: Linux = the systemd user
  timer `claude-quota-log.timer` (units in `./systemd/`; enable with
  `cp systemd/claude-quota-log.* ~/.config/systemd/user/ &&
  systemctl --user daemon-reload && systemctl --user enable --now
  claude-quota-log.timer`), Windows = the `ClaudeQuotaLog` scheduled task.
  Both run `log_quota.py` every 30 min; each sample is a small real quota
  spend — leave it off unless the plots' history matters.
- **Never run the no-arg live path AND a plot in the same turn** — the plot's
  auto-refresh already produced a fresh number; reuse it.
