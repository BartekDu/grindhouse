# The contribution law

**Why this exists.** grindhouse is used commercially under a licence whose
consideration is contributing improvements back upstream, **anonymized**. That
obligation starts the moment the engine earns its keep — in practice, at once.
An obligation nobody can forget is an obligation encoded in scripts; this file
describes the encoding. (Constitution rule 3: *enforcement lives in scripts and
stable-ID registers, not prose* — so treat this page as the map, not the law.)

## The incident that created it (2026-08-14)

grindhouse installs **one way**: `install.sh` copies the repo into
`~/.claude/skills`. Nothing ever looked the other way. So a session that
improved a `SKILL.md`, a law script, or a **selftest case** *inside the live
install* produced work that was:

1. invisible to the canonical repo,
2. destroyed without warning by the next `install.sh`, and
3. never shared as a PR — a licence obligation missed silently.

Separately, nothing inspected what a contribution *carried*. The engine's own
tree holds 31 references to one client and 6 to another: proof that identifying
names ride along in this kind of prose by default, not by accident.

One-way sync with no back-pressure is a work shredder; an unexamined diff is a
client-data leak.

## The three gates

| Gate | Script | What it refuses |
|---|---|---|
| **Prevention** | `scripts/grind/mirror-hook` | A Claude Code `PreToolUse` hook. Any `Edit`/`Write` into a grindhouse-owned dir under `~/.claude/skills` is **denied at the tool boundary**, with the canonical path handed back. The wrong move becomes impossible instead of regrettable. Fails **open** — a broken guard must never brick editing. |
| **Detection** | `scripts/grind/mirror-guard` | `check` classifies every difference **by direction** — exit 1 = unshared work stranded in the mirror, exit 3 = the clone is merely ahead (just re-run `install.sh`), exit 0 = in sync. `import` rescues stranded edits into the clone and **refuses to clobber a newer clone file** without `--force`. `owns PATH` is the hook's decision function. Fails **closed** — a guard that cannot find canonical refuses. |
| **Delivery** | `scripts/grind/contribute` | The single command that ships work: mirror check → **anonymization** → selftest → commit → push → PR. Any red gate stops the push with the diff intact. |

Anonymization itself is `scripts/grind/anon-guard`: it scans **added lines
only** in the outgoing diff. Whole-tree scanning was rejected — the pre-existing
client references would fail every PR forever, and they are history, not this
gate's business.

## The denylist is the confidential part

`anon-guard`'s term list enumerates your clients, so it is **machine-local and
never committed**: `~/.claude/grindhouse.anon-terms`, seeded by `install.sh`
from the tracked, empty `scripts/grind/anon-terms.example`. Built-in patterns
(e-mail addresses, absolute user paths, credentials, private IP ranges and the
usual internal-only hostname suffixes) are always on and need no entry.

Committing a filled-in denylist would leak exactly what the gate protects.

### The `ANON-OK` waiver

A line carrying the literal marker `ANON-OK` is skipped, and **the waived count
is always printed** — a silent waiver would be a hole, a loud one is a review
prompt (`git diff <base>...HEAD | grep ANON-OK`).

It exists because dogfooding proved the gate could not ship its own tests:
`anon-guard`'s selftest cases must contain a fake token, a fake e-mail, a fake
user path and a private IP, or they test nothing. Use it for **synthetic
fixtures only** — never to push a real client name through.

## Daily shape

```bash
# improve the engine — ALWAYS in the clone, never in ~/.claude/skills
$EDITOR skills/grind/SKILL.md            # policy
$EDITOR scripts/grind/selftest           # a new law test case

bash scripts/grind/contribute --check    # dry run: every gate, nothing changed
bash scripts/grind/contribute -m "feat(grind): ..." feat/my-improvement
bash install.sh                          # re-sync the mirror after it lands
```

Edited the live install by mistake? Do not retype it:

```bash
bash scripts/grind/mirror-guard import   # mirror -> clone
```

## Generalizing a finding (what "anonymized" means here)

Every rule must still cite the incident that created it — **cite it
anonymously**. Replace the client with the *shape* of the problem, the path with
a placeholder, the ticket id with the pattern it illustrates:

> ~~"CF-012 broke the Underline mobile nav"~~
> "A prop rename silently passed review in a large React product repo, because…"

The incident keeps its evidentiary value; the client keeps its privacy.

## Open items

- **`LICENSE` is absent from this repo.** The permission and the contribute-back
  obligation are held verbally from the owner. Until the licence text is
  committed, the obligation these scripts enforce is undocumented for everyone
  who was not in that conversation — file it as its own PR.
- **PR destination.** `contribute` pushes to `$GRINDHOUSE_UPSTREAM` (default
  `origin`). If contributions are owed to a repo other than `origin`, set that
  remote and the variable.
