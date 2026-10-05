#!/usr/bin/env python3
"""grindjson.py — JSON Swiss-army for the /grind bash scripts.

Local git-bash has python but NOT jq, so all JSON state/audit/cost ops route
through here. Stdlib only. Subcommands:

  get   STATE DOTTED.PATH                  print a scalar (or JSON for dict/list); "" if absent
  set   STATE DOTTED.PATH JSON_VALUE       set a path (atomic write)
  incr  STATE DOTTED.PATH [BY]             integer increment (default +1, atomic)
  focus-globs STATE allowed|forbidden      print the focus glob list, one per line
  quota-parse                              read tool JSON on stdin -> "FH WK WM" (WM=-1 if absent; exit 1 if unparseable)
  quota-read READINGS MAX_AGE [HARD_STOP_AT] [STOP_BEFORE_WEEK_RESET_MIN]
                                           newest reading (any source) -> "FH WK WM AGE HS SRC"
                                           (exit 1 + "FAIL <reason>" when missing / stale / past the 5h reset)
  hard-stop HARD_STOP_AT                   print "0" or "hard_stop_at" (for the GRIND_QUOTA_TOOL adapter)
  next-window READINGS [HARD_STOP_AT] [STOP_BEFORE_WEEK_RESET_MIN]
                                           "CHAIN <epoch> <local-iso>" (next 5h reset) or "NO_CHAIN <reason>" (exit 3)
  resolve-until HH:MM|ISO                  absolute local ISO time of the next HH:MM (for state.json .run_opts)
  deadline [MINUTES]                       UTC time MINUTES (default 10) from now, for a brief's hard deadline
  wave-brief CC_BRIEF_PY                   advisory budget lines from cc-brief --latest --json (exit 0 always)
  cache-write FILE FH WK [WM]              write {five_hour_pct_left,week_pct_left,week_model_pct_left,ts}
  cache-read  FILE                         print "FH WK WM TS"
  audit-append FILE EVENT [DATA]           append a hash-chained audit line
  cost-record FILE TYPE DELTA              append {ts,type,delta_pct}
  cost-p90    FILE TYPE DEFAULT            print p90 delta_pct for TYPE (DEFAULT if <3 samples)
"""

import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta


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


# --- quota from statusline readings ------------------------------------------
# cc-statusline.py (cc-ledger) appends one JSON object per line to
# ~/.claude/tools/cc-quota.readings.jsonl: {"t": epoch, "five_hour_used": pct,
# "five_hour_resets_at": epoch, "week_used": pct, "week_resets_at": epoch, ...}
# plus an OPTIONAL "week_model_used" (per-model weekly bar). All date math is
# here, in Python, so the gate behaves the same under git-bash on Windows
# (no GNU date).


def _now():
    """Epoch seconds; GRIND_NOW pins it for tests."""
    v = os.environ.get("GRIND_NOW", "").strip()
    return float(v) if v else time.time()


def _epoch(v):
    """Epoch from a number, a numeric string or an ISO-8601 string; None if unparseable."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()  # naive = local time
    except ValueError:
        return None


def _hard_stop_epoch(spec, now):
    """GRIND_HARD_STOP_AT -> epoch. Accepts ISO / epoch, or HH:MM meaning that
    local time TODAY (resolve-until turns a launch-time HH:MM into an absolute
    ISO so later windows do not roll it to the next day). Comma-separated
    values: the earliest wins. None if empty or unparseable."""
    best = None
    for part in str(spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        e = None
        if len(part) <= 5 and ":" in part:
            try:
                hh, mm = (int(x) for x in part.split(":"))
                base = datetime.fromtimestamp(now)
                e = base.replace(hour=hh, minute=mm, second=0, microsecond=0).timestamp()
            except ValueError:
                e = None
        else:
            e = _epoch(part)
        if e is not None and (best is None or e < best):
            best = e
    return best


def _latest_reading(path, with_model=False):
    """Record with the greatest `t` from the tail of the readings file (concurrent
    sessions can interleave lines, so the last line is not always the newest).
    Corrupt or partial lines are skipped. Raises OSError if the file is missing.
    with_model=True: only records that carry "week_model_used" count."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 65536))
        lines = f.read().splitlines()
    best = None
    for ln in lines:
        try:
            o = json.loads(ln.decode("utf-8"))
            t = float(o["t"])
            float(o["five_hour_used"]), float(o["week_used"])
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            continue
        if with_model and o.get("week_model_used") is None:
            continue
        if best is None or t > float(best["t"]):
            best = o
    return best


def _left(used):
    """percent used -> integer percent left, rounded DOWN (conservative)."""
    return max(0, int(math.floor(100 - float(used))))


def _stop_reason(now, hard_stop_at, week_resets_at, before_min):
    hs = _hard_stop_epoch(hard_stop_at, now)
    if hs is not None and now >= hs:
        return "hard_stop_at"
    wr = _epoch(week_resets_at)
    if wr is not None and str(before_min or "").strip():
        try:
            if now >= wr - float(before_min) * 60:
                return "week_reset"
        except ValueError:
            pass
    return "0"


def _quota_read(argv):
    path, max_age = argv[0], float(argv[1])
    hard_stop_at = argv[2] if len(argv) > 2 else ""
    before_min = argv[3] if len(argv) > 3 else ""
    now = _now()
    try:
        r = _latest_reading(path)
    except OSError:
        return "FAIL no readings file " + path, 1
    if r is None:
        return "FAIL no valid reading in " + path, 1
    age = int(now - float(r["t"]))
    if age > max_age:
        return f"FAIL stale reading age={age}s (max {int(max_age)}s)", 1
    fr = _epoch(r.get("five_hour_resets_at"))
    if fr is not None and now >= fr:
        return "FAIL reading predates the 5h reset", 1
    fh, wk = _left(r["five_hour_used"]), _left(r["week_used"])
    wm = r.get("week_model_used")
    if wm is None:
        # The status line has no per-model bar; the probe (source=oauth) has. Carry the
        # newest fresh per-model value from the same week (resets_at jitters by ~1 s).
        m = _latest_reading(path, with_model=True)
        mr, rr = _epoch((m or {}).get("week_resets_at")), _epoch(r.get("week_resets_at"))
        if m is not None and now - float(m["t"]) <= max_age and (
                mr is None or rr is None or abs(mr - rr) <= 300):
            wm = m.get("week_model_used")
    try:
        wm = -1 if wm is None else _left(wm)
    except (ValueError, TypeError):
        wm = -1
    hs = _stop_reason(now, hard_stop_at, r.get("week_resets_at"), before_min)
    # who wrote it: "statusline" (cc-statusline.py) or "oauth" (cc-usage-probe.py); one safe word for the audit line
    src = "".join(c for c in str(r.get("source") or "") if c.isalnum() or c in "_-")[:16] or "statusline"
    return f"{fh} {wk} {wm} {max(age, 0)} {hs} {src}", 0


def _next_window(argv):
    path = argv[0]
    hard_stop_at = argv[1] if len(argv) > 1 else ""
    before_min = argv[2] if len(argv) > 2 else ""
    now = _now()
    try:
        r = _latest_reading(path)
    except OSError:
        r = None
    if r is None:
        return "NO_CHAIN no reading", 3
    fr = _epoch(r.get("five_hour_resets_at"))
    if fr is None:            # null in the contract: any 5h window open now has reset 5h from now
        fr = now + 5 * 3600
    while fr <= now:          # reading predates a reset: next one is 5h later
        fr += 5 * 3600
    start = fr + 120          # start just after the reset, never on it
    if _stop_reason(start, hard_stop_at, r.get("week_resets_at"), before_min) != "0":
        why = _stop_reason(start, hard_stop_at, r.get("week_resets_at"), before_min)
        return f"NO_CHAIN next window would start after {why}", 3
    iso = datetime.fromtimestamp(start).astimezone().isoformat(timespec="minutes")
    return f"CHAIN {int(start)} {iso}", 0


def _resolve_until(spec):
    now = _now()
    s = spec.strip()
    if len(s) <= 5 and ":" in s:
        hh, mm = (int(x) for x in s.split(":"))
        base = datetime.fromtimestamp(now)
        t = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if t.timestamp() <= now:
            t += timedelta(days=1)
        return t.astimezone().isoformat(timespec="minutes")
    e = _epoch(s)
    if e is None:
        raise ValueError(spec)
    return datetime.fromtimestamp(e).astimezone().isoformat(timespec="minutes")


def _wave_brief(tool):
    """Advisory lines from cc-ledger's cc-brief for the newest session of this
    project (Claude Code keeps it in ~/.claude/projects/<cwd with every
    non-alphanumeric as '-'>; falls back to the newest session anywhere)."""
    import re
    import subprocess
    if not os.path.isfile(tool):
        return ["wave-brief: skipped (no cc-brief at %s; advisory only)" % tool]
    pdir = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                        re.sub(r"[^A-Za-z0-9]", "-", os.getcwd()))
    cmd = [sys.executable, tool, "--latest"] + ([pdir] if os.path.isdir(pdir) else []) + ["--json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
        b = json.loads(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return ["wave-brief: skipped (cc-brief gave no JSON; advisory only)"]
    w = b.get("window") or {}
    head = "wave-brief (advisory): spent $%.2f (agents $%.2f over %s agents)" % (
        b.get("spent_usd") or 0, b.get("agents_usd") or 0, b.get("agents") or 0)
    if w:
        head += " | 5h %s%% used, resets in %s min" % (w.get("five_hour_used"), w.get("resets_in_min"))
        if w.get("usd_left") is not None:
            head += ", ~$%.0f left" % w["usd_left"]
    lines = [head]
    for a in b.get("big_agents") or []:
        if (a.get("requests") or 0) > 100:
            lines.append("  big agent: %s, %s requests, $%.2f -> split such tasks, paste excerpts into the brief"
                         % (a.get("label") or "?", a.get("requests"), a.get("usd") or 0))
    for f in (b.get("reread_files") or [])[:5]:
        lines.append("  re-read %sx: %s -> paste the needed excerpt into the next brief"
                     % (f.get("reads"), f.get("file")))
    return lines


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

    elif cmd == "quota-read":
        out, rc = _quota_read(argv[1:])
        print(out)
        sys.exit(rc)

    elif cmd == "hard-stop":
        print(_stop_reason(_now(), argv[1] if len(argv) > 1 else "", None, ""))

    elif cmd == "next-window":
        out, rc = _next_window(argv[1:])
        print(out)
        sys.exit(rc)

    elif cmd == "resolve-until":
        try:
            print(_resolve_until(argv[1]))
        except (ValueError, IndexError):
            print("")
            sys.exit(1)

    elif cmd == "deadline":
        m = float(argv[1]) if len(argv) > 1 else 10.0
        print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now() + m * 60)))

    elif cmd == "wave-brief":
        for ln in _wave_brief(argv[1] if len(argv) > 1 else ""):
            print(ln)

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
