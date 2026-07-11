#!/usr/bin/env python3
"""Append one quota-usage row to a GLOBAL cross-project CSV log.

Runs the /usage TUI reader (claude_usage.py --json), parses the result, and
appends a single timestamped row to ~/.claude/quota_log.csv (expanduser).

Intended to be fired every 30 min by a background scheduler, INDEPENDENT of
any Claude Code project/session (so the log is global, not per-project):
  - Linux:   systemd user timer (units in ./systemd/, see SKILL.md)
  - Windows: Scheduled Task "ClaudeQuotaLog"

Columns:
    warsaw_time          - "Sat 2026-05-30 14:07 CEST" (timestamp, Warsaw tz)
    five_hour_pct_left   - int % of the 5-hour window remaining (or "" on parse fail)
    week_pct_left        - int % of the weekly window remaining (or "")
    five_hour_resets     - reset-time string from the /usage panel
    week_resets          - reset-time string from the /usage panel
    quota_tight          - True/False (5h<=20% or either weekly<=10% left)
    status               - "ok" or "error: <reason>"
    week_model           - per-model weekly bar's model name ("fable", ...)
    week_model_pct_left  - int % of the per-model weekly window remaining

Run:
    python3 log_quota.py            # appends one row
    python3 log_quota.py --print    # also echo the row to stdout
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
USAGE_SCRIPT = os.path.join(HERE, "claude_usage.py")
LOG_PATH = os.path.join(os.path.expanduser("~"), ".claude", "quota_log.csv")

HEADER = [
    "warsaw_time",
    "five_hour_pct_left",
    "week_pct_left",
    "five_hour_resets",
    "week_resets",
    "quota_tight",
    "status",
    # appended 2026-07-07: the per-model weekly bar ("Current week (Fable)")
    # is a SEPARATE limit from the all-models bar. Until this date the parser
    # overwrote week_pct_left with the model bar, so older rows' week% is the
    # MODEL limit whenever the panel showed one. Old rows simply lack these
    # two columns (csv.DictReader fills None).
    "week_model",
    "week_model_pct_left",
]


def warsaw_now_str() -> str:
    try:
        from zoneinfo import ZoneInfo
        w = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Warsaw"))
    except Exception:
        w = datetime.now(timezone.utc) + timedelta(hours=2)  # CEST fallback
    return w.strftime("%a %Y-%m-%d %H:%M %Z")


def read_usage() -> dict:
    """Run claude_usage.py --json and return the parsed dict (raises on failure)."""
    # capture BYTES, not text: the child reconfigures its stdout to UTF-8, but
    # on Windows subprocess text=True would decode with the locale (cp1252) and
    # choke on the box-drawing / euro bytes. Decode UTF-8 ourselves.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, USAGE_SCRIPT, "--json"],
        capture_output=True, timeout=120, env=env,
    )
    out = (proc.stdout or b"").decode("utf-8", "replace")
    err = (proc.stderr or b"").decode("utf-8", "replace")
    if proc.returncode != 0:
        raise RuntimeError(f"claude_usage rc={proc.returncode}: "
                           f"{(err or out).strip()[:200]}")
    data = json.loads(out)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data


def build_row() -> dict:
    try:
        d = read_usage()
        return {
            "warsaw_time": d.get("warsaw_time") or warsaw_now_str(),
            "five_hour_pct_left": d.get("five_hour_pct_left", ""),
            "week_pct_left": d.get("week_pct_left", ""),
            "five_hour_resets": (d.get("five_hour") or {}).get("resets", ""),
            "week_resets": (d.get("week_all") or {}).get("resets", ""),
            "quota_tight": d.get("quota_tight", ""),
            "status": "ok",
            "week_model": d.get("week_model") or "",
            "week_model_pct_left": d.get("week_model_pct_left", ""),
        }
    except Exception as e:  # log the failure as a row instead of dying silently
        return {
            "warsaw_time": warsaw_now_str(),
            "five_hour_pct_left": "",
            "week_pct_left": "",
            "five_hour_resets": "",
            "week_resets": "",
            "quota_tight": "",
            "status": f"error: {str(e)[:160]}",
            "week_model": "",
            "week_model_pct_left": "",
        }


def main() -> int:
    row = build_row()
    new_file = not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        if new_file:
            w.writeheader()
        w.writerow(row)
    if "--print" in sys.argv:
        print(LOG_PATH)
        print(",".join(str(row[h]) for h in HEADER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
