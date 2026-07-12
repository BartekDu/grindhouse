#!/usr/bin/env python3
"""grindjson.py — JSON Swiss-army for the /grind bash scripts.

Local git-bash has python but NOT jq, so all JSON state/audit/cost ops route
through here. Stdlib only. Subcommands:

  get   STATE DOTTED.PATH                  print a scalar (or JSON for dict/list); "" if absent
  set   STATE DOTTED.PATH JSON_VALUE       set a path (atomic write)
  incr  STATE DOTTED.PATH [BY]             integer increment (default +1, atomic)
  focus-globs STATE allowed|forbidden      print the focus glob list, one per line
  quota-parse                              read tool JSON on stdin -> "FH WK WM" (WM=-1 if absent; exit 1 if unparseable)
  cache-write FILE FH WK [WM]              write {five_hour_pct_left,week_pct_left,week_model_pct_left,ts}
  cache-read  FILE                         print "FH WK WM TS"
  audit-append FILE EVENT [DATA]           append a hash-chained audit line
  cost-record FILE TYPE DELTA              append {ts,type,delta_pct}
  cost-p90    FILE TYPE DEFAULT            print p90 delta_pct for TYPE (DEFAULT if <3 samples)
"""

import hashlib
import json
import os
import sys
import time


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _atomic_write(p, text):
    tmp = f"{p}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, p)


def _iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main(argv):
    # On Windows, text-mode stdout translates \n -> \r\n; the trailing \r then
    # corrupts bash `read` / `$(( ))` consumers. Force LF-only stdout.
    try:
        sys.stdout.reconfigure(newline="\n")
    except (AttributeError, ValueError):
        pass
    if not argv:
        sys.exit("grindjson: no subcommand")
    cmd = argv[0]

    if cmd == "get":
        st = _load(argv[1])
        cur = st
        for k in argv[2].split("."):
            cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None:
            print("")
        elif isinstance(cur, (dict, list)):
            print(json.dumps(cur))
        else:
            print(cur)

    elif cmd == "set":
        st = _load(argv[1])
        path = argv[2].split(".")
        val = json.loads(argv[3])
        cur = st
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = val
        _atomic_write(argv[1], json.dumps(st, indent=2) + "\n")

    elif cmd == "incr":
        st = _load(argv[1])
        path = argv[2].split(".")
        by = int(argv[3]) if len(argv) > 3 else 1
        cur = st
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = int(cur.get(path[-1], 0) or 0) + by
        _atomic_write(argv[1], json.dumps(st, indent=2) + "\n")

    elif cmd == "focus-globs":
        st = _load(argv[1])
        key = argv[2] + "_globs"
        for g in st.get("focus", {}).get(key, []) or []:
            print(g)

    elif cmd == "quota-parse":
        try:
            o = json.loads(sys.stdin.read())
            fh, wk = o["five_hour_pct_left"], o["week_pct_left"]
        except (ValueError, KeyError, TypeError):
            print("")
            sys.exit(1)
        if fh is None or wk is None:
            print("")
            sys.exit(1)
        # week_model_pct_left = the per-model weekly bar (e.g. "Current week
        # (Fable)") — usually exhausts FIRST. -1 = unknown (older tool output);
        # quota-gate skips the model check when negative.
        wm = o.get("week_model_pct_left")
        wm = -1 if wm is None else int(wm)
        print(f"{int(fh)} {int(wk)} {wm}")

    elif cmd == "cache-write":
        _atomic_write(
            argv[1],
            json.dumps(
                {
                    "five_hour_pct_left": int(argv[2]),
                    "week_pct_left": int(argv[3]),
                    "week_model_pct_left": int(argv[4]) if len(argv) > 4 else -1,
                    "ts": int(time.time()),
                }
            ),
        )

    elif cmd == "cache-read":
        o = _load(argv[1])
        print(
            f"{o.get('five_hour_pct_left', '')} {o.get('week_pct_left', '')} "
            f"{o.get('week_model_pct_left', -1)} {o.get('ts', 0)}"
        )

    elif cmd == "audit-append":
        # One hash chain is shared by the orchestrator AND concurrent builder
        # worktrees (state anchors at the main root), so read-last + append must
        # be atomic — two unlocked appends reading the same `prev` fork the
        # chain and audit-verify reports it as tampering. flock is advisory but
        # every writer goes through here. (No fcntl on Windows → best effort.)
        p, event = argv[1], argv[2]
        data = argv[3] if len(argv) > 3 else ""
        try:
            import fcntl
        except ImportError:
            fcntl = None
        with open(p, "a+", encoding="utf-8", newline="\n") as f:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            lines = [ln for ln in f if ln.strip()]
            prev = json.loads(lines[-1]).get("hash", "GENESIS") if lines else "GENESIS"
            ts = _iso()
            h = hashlib.sha256(f"{prev}{ts}{event}{data}".encode()).hexdigest()
            f.write(
                json.dumps({"ts": ts, "event": event, "data": data, "prev": prev, "hash": h}) + "\n"
            )

    elif cmd == "cost-record":
        with open(argv[1], "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"ts": _iso(), "type": argv[2], "delta_pct": int(argv[3])}) + "\n")

    elif cmd == "cost-p90":
        p, t, default = argv[1], argv[2], int(argv[3])
        vals = []
        try:
            with open(p, encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    o = json.loads(ln)
                    if o.get("type") == t and isinstance(o.get("delta_pct"), (int, float)):
                        vals.append(o["delta_pct"])
        except FileNotFoundError:
            pass
        vals.sort()
        if len(vals) < 3:
            print(default)
        else:
            idx = (90 * len(vals) + 99) // 100
            idx = max(1, min(idx, len(vals)))
            print(int(vals[idx - 1]))

    else:
        sys.exit(f"grindjson: unknown subcommand {cmd!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
