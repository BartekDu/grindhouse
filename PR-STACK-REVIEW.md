# PR stack review — portability → correctness → quota → CI

**For:** Bartek · **From:** Maciej (+ Claude) · **Date:** 2026-07-11

This branch (`dev`) is the whole series in one place for a first read. The same
14 commits sit on four LOCAL stacked branches on my machine, one per PR below —
after your OK I push them and open the PRs with exactly these descriptions.
Nothing here touches `main`.

```
main
 └ portability-project-conf     3 commits   selftest 41/41
    └ correctness-worktree-law   6 commits   selftest 54/54
       └ linux-quota-tool        4 commits   selftest 59/59
          └ ci-selftest          1 commit    + GitHub Actions on ubuntu + windows
             └ dev               this file only
```

House rules followed: every fix cites its incident in the commit body; nothing
in `scripts/grind/*` got reimplemented — your soft-pause (exit 7), per-model
weekly gate, worktree law and swarm-claim are untouched and now covered by
tests. Review commit-by-commit; each is one decision.

---

## PR 1 — `portability-project-conf` → `main`

**feat(law): per-repo project.conf layer — de-couple the bundle from Underline**

The bundle called itself "canonical home" but only worked for one project:
value-gate accepted only Underline backlog ids (T24/SEC/LP/E/R), hygiene-check
hardcoded `db.sqlite3` + `graphify-out/*`, landable-guard knew only `dev|main`
and only `needs:/qa|/cso` gates, the branch model assumed `dev`. Running a
grind in ANY other repo meant the law rejecting legitimate work.

What lands:

- **`<repo>/.claude/grind/project.conf`** sourced by `config.sh` —
  `GRIND_BASE_BRANCH`, `GRIND_PROTECTED_BRANCHES`, `GRIND_EXTRA_IGNORES`,
  `GRIND_VALUE_EXTRA_RE`. **Underline behaves exactly as before** by dropping
  in `docs/examples/underline.project.conf` (included, commented).
- **`grind_base_branch()`** (lib.sh): origin/HEAD → dev|main|master → current;
  override via project.conf. SKILL.md branch model generalized to match.
- **value-gate** generic patterns: `#N`, `GH/ISSUE/PR N`, Jira-style `ABC-123`
  (covers `T24-3`, `SEC-12`, `R-007`), `TODO-x`, `T-NN`, semi-grind's
  `CF/TC/DD/RULE` ids, `tests +N` — plus the project regex hook. Work-item ids
  went case-sensitive (case-insensitive `[A-Z]+-[0-9]+` false-passed "utf-8").
- **landable-guard**: protected list from config; gate regex `needs:<anything>`
  — your `needs:/qa|/cso` regex let semi-grind's `needs:decision` gates push
  straight through the guard (real hole, PR 1 closes it).
- **hygiene-check**: generic required-ignores + grind's own volatile state
  (`.active`, `.lock/`, `.quota-cache.json`, `audit.log`,
  `cost-history.jsonl`) + `GRIND_EXTRA_IGNORES`; `-uall` so an untracked dir
  can't collapse past the exclusion.
- **NEW `verify-run`**: the verifier's non-interactive gate as a script —
  explicit `.claude/grind/verify-cmds` wins, else auto-detect by project type
  (npm/yarn/pnpm scripts, ruff/mypy/pytest, cargo, go, manage.py, make test).
  Exit 3 = no gates found = UNVERIFIED, never "green".
- **NEW `commit-msg-guard`**: conventional `<scope>: <subject>` enforced as a
  commit-msg hook, window-only, git-generated messages exempt — the contract
  lived only in prose outside Underline's lefthook.
- **NEW `scripts/grind/selftest`**: 41 assertions, throwaway repos, faked quota
  cache — zero network, zero Claude auth, zero quota spend. Covers YOUR
  features too (SOFT_PAUSE exit 7, per-model weekly stop, worktree law).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR 2 — `correctness-worktree-law` → PR 1

**fix(law): the law reaches worktrees; hooks v2; landable window-only**

Six commits, each an incident found by executing the law, not reading it:

1. **State anchors at the main worktree root.** Live repro: a builder worktree
   under `.claude/worktrees/grind-feat-*` committed a `forbidden_globs` file
   with message `wip` — every guard silent. `--show-toplevel` points at the
   worktree, where `.active`/`state.json` don't exist. Your worktree law
   forces builders INTO worktrees, i.e. exactly where the law didn't reach.
   `GRIND_MAIN_ROOT = dirname(git rev-parse --git-common-dir)`; one campaign =
   one state tree (focus, ledger, audit, lock, sentinels) from every worktree.
2. **Protected-branch push block is window-only.** One /grind run left a repo
   refusing every direct push to main forever. The open-gate check stays
   unconditional on purpose (self-quenching; a gated branch must not land by
   accident post-window).
3. **Hook wrapper v2.** v1 baked the absolute bundle path into every armed repo
   (moving `~/.claude/skills` = exit 127 on every commit machine-wide) and a
   pre-commit conflict still installed the other two hooks. v2 resolves the
   guardrail at runtime (repo-local → `$HOME` bundle), fails CLOSED during an
   active window / OPEN with a warning otherwise, installs all-or-nothing, and
   upgrades v1 hooks in place on the next bootstrap.
4. **Audit chain under flock.** Orchestrator + builders now share one chain;
   two unlocked appends reading the same `prev` fork it — audit-verify would
   report your own concurrency as tampering.
5. **Lock: age-only staleness.** The recorded holder pid is the one-shot
   lock.sh process — always dead by the next acquire — so pid-liveness
   silently reclaimed EVERY held lock (selftest caught a second acquire
   succeeding during a live window; two windows could run concurrently).
   Contract now: explicit release, or age > 6h (matches /soft-pause crash
   recovery). Plus `MERGE_HEAD` via `--git-path` (the old check used an
   undefined var and a path that's wrong in worktrees).
6. **Skill fixes:** /grind declares `CronCreate` (Window-end chains with it —
   undeclared means the chain dies silently at the end of window 1);
   /semi-grind Step 0 contract must include `RULEBOOK.md` + `<register-dir>/**`
   (scope-guard rejected the campaign's own ledgers mid-window — live repro).

Selftest grows to 54: worktree enforcement both ways, window-only landable,
v2 upgrade/all-or-nothing/missing-bundle fail modes, lock single-run, 8
concurrent audit appends.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR 3 — `linux-quota-tool` → PR 2

**feat(quota): one dual-backend tool; per-OS config; the 4-place coupling dies**

Merge of our two divergent forks of `claude_usage.py` into one file that is
better than either:

- **From yours:** poll-based drive (no fixed 7s+6s sleeps — slow boots turned
  whole days of the log into `could not parse` rows), halfway `/usage` resend,
  SETTLE after the first bar, the per-model weekly parser (`Current week
  (Fable)` is a SEPARATE limit that usually exhausts first), never-overwrite
  parse guard, full-screen debug dump on parse failure.
- **From mine:** dual PTY backend (stdlib `pty`+`select` on Linux/macOS,
  pywinpty on Windows), folder-trust-dialog handling, char-by-char typing
  (whole-string tripped the TUI paste detection on Linux and the submit was
  swallowed), tz-generic `Resets` regex.
- `pyte` imports lazily → `parse()`/`classify()` are importable on bare CI
  runners; the selftest feeds the parser a synthetic panel with a Fable bar.

**Measured on the real panel (Linux): 17.2s → 4.8s per read, and the Fable
weekly bar — which my Linux fork silently dropped — parses correctly.** Until
today my machine's gate was blind to the limit that binds first.

Also: per-OS python resolution in `config.sh` (msys/cygwin prefer `python`,
everything else `python3`; `python.exe` interop fallback kept);
`GRIND_QUOTA_TOOL` auto-resolves (repo-vendored → installed skill → env
override) — the `C:/Users/b/Desktop/...` default failed the gate CLOSED on
every machine that isn't that desktop. Linux systemd twin of your
`ClaudeQuotaLog` task ships in `skills/quota/systemd/`. SKILL.md /
DEPENDENCIES.md rewritten to the new path model: **this repo's copy IS the
executed tool**; `install.sh` ships it; nothing points at a desktop.

Selftest grows to 59 (tool resolution ×3, interpreter check, parser test).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR 4 — `ci-selftest` → PR 3

**ci: run the law selftest on ubuntu + windows for every push/PR**

The engine lived as two per-machine forks with no shared proof — the per-model
parser existed on Windows while Linux dropped the Fable bar; Linux carried
guard fixes Windows lacked. The selftest was built to need zero network / auth
/ quota, so CI is one step: checkout + `bash scripts/grind/selftest` on
`ubuntu-latest` and `windows-latest` (`shell: bash` = git-bash — the same
environment the law runs in on your machine; your LF `.gitattributes` is what
makes this possible). `fail-fast: false` so an OS-specific break reports both
platforms' truth; the flock check self-skips where `fcntl` is unavailable.

From this PR on, "works on my OS" stops being an argument anyone has to make.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## After this series (proposed, NOT started — your call)

**PR 5 — generalize the semi-grind/sprint/culture skill prose.** The law under
them is generic now, but `skills/semi-grind/SKILL.md` still hardcodes Underline
(authority order → `docs/design/underline-mobile-*`, `DESIGN_RULEBOOK.md`,
`chief-stylist` agents), and sprint/culture treat `/codex`/gstack as always
present. Same treatment as the law: parameterize, keep an Underline example.

**Then:** both machines run `bash install.sh` from this repo and the forks are
over — one canonical, CI-proven engine.
