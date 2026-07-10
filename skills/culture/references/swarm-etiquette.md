# Swarm etiquette — the ownership board

**Origin:** two agent swarms (different users/machines) on one repo can't see
each other's local locks; Fable's suggestion — coordinate through gh issues as
a backlog-ownership board — became `swarm-claim.sh` (2026-07-10).

**The medium:** one open gh issue per live swarm, labeled `swarm-claim`,
machine-parseable body: session id, machine, campaign branch, focus globs,
`window_end_epoch`. The script (`scripts/grind/swarm-claim.sh
{claim|check|renew|release}`) is the law; exit 2 on `check` = a live foreign
claim overlaps your globs.

## Team-player duties

- **Check before claiming.** Every campaign Step 0.
- **Foreign claims = your `forbidden_globs`.** Same discipline as your own
  focus contract.
- **Negotiate, don't bulldoze.** Overlap → narrow your globs, or comment on the
  conflicting issue and wait for agreement.
- **Comment before reclaiming a stale claim** (window_end + 6h grace passed) —
  the other swarm may have crashed, not finished; leave the archaeology.
- **Renew when chaining; release when stopping or soft-pausing.** A parked
  swarm that hoards globs is not a team player.
- **Degrade gracefully:** no gh / no remote / no perms → LOCAL_ONLY (exit 0);
  same-machine concurrency is lock.sh + the run-log table's job. The
  coordination layer must never block a solo repo.
