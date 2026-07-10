#!/usr/bin/env python
"""Read Claude Code's REAL usage limits by driving the `/usage` TUI panel.

There is no headless `/usage` (it's a TUI dialog; `-p "/usage"` just treats it as
a chat prompt). So this spawns the same `claude.exe` on your PATH inside a
pseudo-terminal (pywinpty / ConPTY), sends `/usage`, renders the panel with a
terminal emulator (pyte), and parses the percentages. It uses the same auth/
config as running `claude` in PowerShell (same binary, inherited environment).

Output: JSON with the 5-hour + weekly + credit usage, the Warsaw off-hours flag,
and a `quota_tight` / `proceed_autonomously` decision for the autonomy-gating
rule (off-hours AND tight quota AND no real gate -> just proceed).

Usage:
    python claude_usage.py            # human-readable
    python claude_usage.py --json     # machine-readable JSON only

Requires: pip install pywinpty pyte
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta

import pyte
from winpty import PtyProcess

# Force UTF-8 stdout so the credits "€" + box chars survive on Windows, where
# the default console/redirect codec is cp1252 and mangles them to mojibake.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROWS, COLS = 64, 150
BOOT_TIMEOUT = 30.0   # max wait for the TUI prompt (poll, not fixed sleep)
PANEL_TIMEOUT = 25.0  # max wait for the /usage panel to render
SETTLE = 1.2          # extra settle after the panel first appears
PCT_RE = re.compile(r"(\d+)%\s*used")
RESET_RE = re.compile(r"Resets\s+(.+?)\s*(?:\(Europe/Warsaw\))?\s*$")

# PAUSE thresholds (flat; no time/peak/weekend factor — founder is Pro/Max and
# Anthropic permanently removed peak hours for Pro/Max on 2026-05-06).
FIVE_H_PAUSE_PCT = 20   # pause the chain when the 5h limit has <= this % left
WEEK_PAUSE_PCT = 10     # pause the chain when the weekly limit has <= this % left


def capture_usage_screen() -> list[str]:
    """Drive the TUI. pywinpty read() blocks when the TUI is idle, so we read
    on a daemon thread and POLL the rendered screen instead of fixed sleeps.

    Fixed sleeps (the old 7s+6s) broke whenever boot was slow (auto-update
    check, cold start, busy machine): the panel never rendered inside the
    window and whole days of the log turned into `could not parse` rows.
    Now we wait until the input prompt is actually up (max BOOT_TIMEOUT),
    send /usage, and wait until a `NN% used` bar actually renders (max
    PANEL_TIMEOUT, with one resend halfway in case the keystrokes got eaten
    during a redraw)."""
    screen = pyte.Screen(COLS, ROWS)
    stream = pyte.ByteStream(screen)
    p = PtyProcess.spawn("claude", dimensions=(ROWS, COLS))
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            try:
                data = p.read(8192)
            except (EOFError, OSError):
                break
            if data:
                stream.feed(data.encode("utf-8", "replace")
                            if isinstance(data, str) else data)

    def text() -> str:
        return "\n".join(screen.display)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        # 1. wait for the input prompt (screen shows the shortcuts hint or the
        #    bordered input box) — or the screen going stable as a fallback
        deadline = time.time() + BOOT_TIMEOUT
        prev = ""
        stable = 0
        while time.time() < deadline:
            cur = text()
            if "? for shortcuts" in cur or "│ >" in cur or "❯" in cur:
                break
            stable = stable + 1 if (cur == prev and cur.strip()) else 0
            if stable >= 4:          # ~2s unchanged non-empty screen: call it booted
                break
            prev = cur
            time.sleep(0.5)
        time.sleep(0.5)

        # 2. send /usage, poll for the panel; resend once halfway if nothing
        p.write("/usage\r")          # written to the pty, so MSYS can't mangle the /
        deadline = time.time() + PANEL_TIMEOUT
        resent = False
        while time.time() < deadline:
            if PCT_RE.search(text()):
                time.sleep(SETTLE)   # let the rest of the panel finish rendering
                break
            if not resent and time.time() > deadline - PANEL_TIMEOUT / 2:
                p.write("/usage\r")
                resent = True
            time.sleep(0.5)
        return [ln.rstrip() for ln in screen.display]
    finally:
        stop.set()
        try:
            p.terminate(force=True)
        except Exception:
            pass


def classify(label: str) -> str | None:
    low = label.lower()
    if ("5-hour" in low or "5 hour" in low or "five" in low
            or "current session" in low):
        return "five_hour"
    if "week" in low:
        # per-model weekly bars are SEPARATE limits ("Current week (Fable)"
        # runs out long before "Current week (all models)") — mapping them
        # all to week_all made the model bar overwrite the all-models bar
        for model in ("sonnet", "opus", "fable", "haiku"):
            if model in low:
                return f"week_{model}"
        return "week_all"
    if "credit" in low:
        return "credits"
    return None


def parse(lines: list[str]) -> dict:
    """Walk the rendered panel. A label line precedes a `NN% used` bar line;
    a `Resets ...` line follows it. Map each to a known section by label text,
    falling back to positional order for the three top bars."""
    out: dict[str, dict] = {}
    last_label = None
    positional = ["five_hour", "week_all", "week_sonnet"]
    pos_i = 0
    pending_key = None
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = PCT_RE.search(s)
        if m:
            key = classify(last_label or "") or (
                positional[pos_i] if pos_i < len(positional) else None)
            if pos_i < len(positional) and key == positional[pos_i]:
                pos_i += 1
            if key and "pct_used" in out.get(key, {}):
                key = None      # never overwrite an already-parsed section
            if key:
                out.setdefault(key, {})["pct_used"] = int(m.group(1))
                pending_key = key
            continue
        r = RESET_RE.match(s)
        if r and pending_key:
            out[pending_key]["resets"] = r.group(1).strip()
            pending_key = None
            continue
        # credit euro line e.g. "EUR1.41 / EUR45.00 spent"
        if pending_key == "credits" and "/" in s and "spent" in s.lower():
            out["credits"]["detail"] = s
            continue
        # a non-bar, non-reset line is a candidate label for the NEXT bar
        if "%" not in s and not s.lower().startswith("resets"):
            last_label = s
    return out


def warsaw_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Warsaw"))
    except Exception:
        return datetime.now(timezone.utc) + timedelta(hours=2)  # CEST fallback


def main() -> int:
    want_json = "--json" in sys.argv
    lines = capture_usage_screen()
    sections = parse(lines)

    if "five_hour" not in sections and "week_all" not in sections:
        # full screen dump to a side file — the CSV truncates the error to
        # ~160 chars, which made these failures undiagnosable for weeks
        dump = os.path.join(os.path.expanduser("~"), ".claude",
                            "quota_usage_last_error.txt")
        try:
            with open(dump, "w", encoding="utf-8") as f:
                f.write(datetime.now().isoformat() + "\n")
                f.write("\n".join(lines))
        except Exception:
            dump = None
        err = {"error": "could not parse /usage panel",
               "debug_dump": dump,
               "raw": [l for l in lines if l.strip()][:40]}
        print(json.dumps(err, indent=2, ensure_ascii=False))
        return 2

    five_used = sections.get("five_hour", {}).get("pct_used")
    week_used = sections.get("week_all", {}).get("pct_used")
    five_left = None if five_used is None else 100 - five_used
    week_left = None if week_used is None else 100 - week_used

    # per-model weekly bar ("Current week (Fable)" etc.) — a SEPARATE limit
    # from the all-models bar; the panel shows one for the tier in use
    week_model_name = None
    week_model = None
    for k in sections:
        if k.startswith("week_") and k != "week_all":
            week_model_name = k.removeprefix("week_")
            week_model = sections[k]
            break
    model_used = (week_model or {}).get("pct_used")
    model_left = None if model_used is None else 100 - model_used

    # PAUSE trigger (the autonomy stop-loss). Flat thresholds, NO time/peak/
    # weekend factor: the founder is on Pro/Max and Anthropic permanently removed
    # peak hours for Pro/Max on 2026-05-06, so there is no burn-rate adjustment.
    #   quota_tight = 5h <= 20% left  OR  weekly <= 10% left (all-models OR
    #                 the per-model weekly — whichever limit binds first)
    # When true, the agent PAUSES before the next task and waits for "go".
    quota_tight = ((five_left is not None and five_left <= FIVE_H_PAUSE_PCT)
                   or (week_left is not None and week_left <= WEEK_PAUSE_PCT)
                   or (model_left is not None and model_left <= WEEK_PAUSE_PCT))

    w = warsaw_now()  # display only — not a gate factor
    result = {
        "warsaw_time": w.strftime("%a %Y-%m-%d %H:%M %Z"),
        "five_hour": sections.get("five_hour"),
        "week_all": sections.get("week_all"),
        "week_model": week_model_name,
        "week_model_usage": week_model,
        "credits": sections.get("credits"),
        "five_hour_pct_left": five_left,
        "week_pct_left": week_left,
        "week_model_pct_left": model_left,
        "quota_tight": quota_tight,
    }

    if want_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Time:     {result['warsaw_time']}")
        print(f"5-hour:   {five_used}% used  ({five_left}% left)"
              f"  resets {sections.get('five_hour', {}).get('resets', '?')}")
        print(f"Week:     {week_used}% used  ({week_left}% left)"
              f"  resets {sections.get('week_all', {}).get('resets', '?')}")
        if week_model:
            print(f"Week ({week_model_name}): {model_used}% used"
                  f"  ({model_left}% left)"
                  f"  resets {week_model.get('resets', '?')}")
        if sections.get("credits"):
            print(f"Credits:  {sections['credits'].get('pct_used','?')}% used"
                  f"  {sections['credits'].get('detail','')}")
        verdict = "PAUSE — wait for go" if quota_tight else "OK — proceed"
        print(f"quota_tight={quota_tight}  ->  {verdict}"
              f"   (pause if 5h<={FIVE_H_PAUSE_PCT}% or week<={WEEK_PAUSE_PCT}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
