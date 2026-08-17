# Gate ids, and why they carry a campaign

**Rule:** never hand-pick a gate id. Run `bash $G/gate-id mint` and use what it prints.

```
G-<NN>-<campaign>        G-07-secops, G-13-qa-test-expansion
G-<NN>                   legacy, pre-2026-08-17. Still valid, never rewritten
```

## The incident this pays for

Two campaigns ran in one repository on 2026-08-17. Each logged a gate. Each read the shared ledger,
computed `max+1`, and minted **`G-13`**. Their rows landed in different sections of the file, so the
merge was **clean** — no conflict, nothing red, two gates with one id.

That is not bad luck. **A counter shared between writers who cannot see each other has no correct
implementation.** Both processes read the same state and both are right about what they read. The
only fix is to stop sharing the counter.

Three things went wrong in sequence, and the third is the expensive one:

1. Both campaigns minted `G-13`.
2. The duplicate merged cleanly, so nothing caught it.
3. The renumbering that followed **reverted silently in five files** — resolving a cherry-pick
   conflict fixes the commit being resolved, not the same lines in the commits still queued behind
   it. An id is cheap to change before it is cited and expensive after; commit messages, code
   comments and reports all point at it.

## Why the suffix, and why you do not choose it

`NN` is now **per campaign**, because state moved to `.claude/grind/campaigns/<campaign>/` — one
campaign owns one ledger and is its only writer, so `max+1` is sound again.

The suffix comes from the **resolved campaign**, which is derived from the worktree. It is not a name
an agent invents. Two agents asked to pick a slug will both pick `qa`; git already guarantees
worktree names are unique, so the machine should answer this and not the model.

Resolution order, from `config.sh`:

1. `$GRIND_CAMPAIGN` — explicit, also settable in `project.conf`
2. `<worktree>/.claude/grind-campaign` — a marker written when the worktree is created
3. exactly one campaign exists — unambiguous, no marker needed
4. no `campaigns/` directory — legacy flat tree, unchanged
5. **several campaigns and nothing names one — refuse.** The guards fail closed rather than pick.

Step 5 matters more than it looks. Anchoring state per-worktree was tried once and gave builders an
*empty* state, which silently disarmed the guards — an out-of-focus `wip` commit passed clean inside
a builder worktree. Guessing which campaign's law applies is the same failure wearing a different
hat, so an unresolvable campaign blocks the push and says so.

## What the checker does and does not flag

`bash $G/gate-id check` runs in `landable-guard`, so a duplicate blocks a push.

It flags **one thing**: the same id declared as a *registry row* twice **in the same file**.

It deliberately does not flag:

| Not a duplicate | Why |
|---|---|
| A registry row plus a `## G-07 — …` detail heading | Every documented gate has both |
| An id repeated in a grouped sub-table further down | That is prose restating the registry |
| An id inside a ```` ``` ```` fence | The ledger documents its own row format in one |
| The same id in the ledger *and* in `GATES.md` | Separate registers, separate lifecycles, both start at G-01 |

Each of those was a false positive at some point while this was written, and a false positive is not
a harmless over-report: a check that blocks every push gets deleted, and then the real duplicate
merges clean again. All four are pinned by cases in `selftest`.

## Migrating a repository that already has bare ids

Do nothing. Legacy `G-01 … G-NN` stay exactly as they are — `mint` counts them when choosing the next
number, so it will not hand back one that is already in use, and `check` treats them as ordinary
declarations. New gates get suffixed ids; old ones are never rewritten, because rewriting a cited id
is the step that failed silently last time.
