#!/usr/bin/env python3
"""Read Claude Code's REAL usage limits by driving the `/usage` TUI panel.

There is no headless `/usage` (it's a TUI dialog; `-p "/usage"` just treats it
as a chat prompt). So this spawns the same `claude` binary on your PATH inside
a pseudo-terminal, sends `/usage`, renders the panel with a terminal emulator
(pyte), and parses the percentages. It uses the same auth/config as running
`claude` in your shell (same binary, inherited environment).

PTY backend is picked per-OS:
  - Linux/macOS: stdlib `pty` + `select` (no extra deps beyond pyte)
  - Windows:     pywinpty / ConPTY (pip install pywinpty)

Output: JSON with the 5-hour, weekly (all-models), per-model weekly
("Current week (Fable)" etc. — a SEPARATE limit that usually exhausts first)
and credit usage, plus a `quota_tight` decision for the autonomy-gating rule.

Usage:
    python3 claude_usage.py            # human-readable
    python3 claude_usage.py --json     # machine-readable JSON only

Requires: pip install pyte   (plus pywinpty on Windows only)
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta

# Force UTF-8 stdout so the credits "€" + box chars survive on Windows, where
# the default console/redirect codec is cp1252 and mangles them to mojibake.
# (No-op on Linux, where UTF-8 is already the locale default.)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROWS, COLS = 64, 150
BOOT_TIMEOUT = 30.0   # max wait for the TUI prompt (poll, not fixed sleep —
                      # fixed 7s+6s sleeps broke on slow boots: the panel never
                      # rendered inside the window and whole days of the log
                      # turned into `could not parse` rows)
PANEL_TIMEOUT = 25.0  # max wait for the /usage panel to render
SETTLE = 1.2          # extra settle after the panel first appears
SUBMIT_WAIT = 0.5     # gap between typing "/usage" and pressing Enter (paste-detect guard)
PCT_RE = re.compile(r"(\d+)%\s*used")
# The panel suffixes reset times with the local tz in parens, e.g. "(Europe/Warsaw)"
# — strip whatever tz label appears so group(1) is just the clock time.
RESET_RE = re.compile(r"Resets\s+(.+?)\s*(?:\([\w/+-]+\))?\s*$")

# PAUSE thresholds (flat; no time/peak/weekend factor — the founder is Pro/Max and
# Anthropic permanently removed peak hours for Pro/Max on 2026-05-06).
FIVE_H_PAUSE_PCT = 20   # pause the chain when the 5h limit has <= this % left
WEEK_PAUSE_PCT = 10     # pause the chain when the weekly limit has <= this % left


def _drive(write_fn, screen) -> list[str]:
    """Shared TUI-driving choreography, backend-agnostic. POLLS the rendered
    screen instead of fixed sleeps.

    1. Wait for boot: the folder-trust dialog (fresh pty spawns get it even
       when the interactive session is already trusted) is confirmed with
       Enter; then poll for the input prompt, with a stable-screen fallback
       (~2s unchanged non-empty screen = call it booted).
    2. Type "/usage" ONE CHAR AT A TIME — writing the whole string at once
       trips the TUI's paste detection and the submit gets swallowed. Enter
       goes separately after SUBMIT_WAIT.
    3. Poll until the panel shows a "% used" bar (network fetch can be slow),
       resending /usage once halfway in case the keystrokes got eaten during
       a redraw. SETTLE after the first bar so the rest of the panel renders.
    """
    def lines() -> list[str]:
        return [ln.rstrip() for ln in screen.display]

    def on_screen(*pats: str) -> bool:
        return any(p in ln for ln in lines() for p in pats)

    def send_usage() -> None:
        for ch in b"/usage":
            write_fn(bytes([ch]))
            time.sleep(0.06)
        time.sleep(SUBMIT_WAIT)
        write_fn(b"\r")

    deadline = time.time() + BOOT_TIMEOUT
    prev = ""
    stable = 0
    while time.time() < deadline:
        if on_screen("trust this folder", "Quick safety check"):
            write_fn(b"\r")
            time.sleep(3.0)
            prev, stable = "", 0
            continue
        cur = "\n".join(lines())
        if on_screen("? for shortcuts", "│ >", "❯"):
            break
        stable = stable + 1 if (cur == prev and cur.strip()) else 0
        if stable >= 4:          # ~2s unchanged non-empty screen: call it booted
            break
        prev = cur
        time.sleep(0.5)
    time.sleep(0.5)

    send_usage()
    deadline = time.time() + PANEL_TIMEOUT
    resent = False
    while time.time() < deadline:
        if any(PCT_RE.search(ln) for ln in lines()):
            time.sleep(SETTLE)   # let the rest of the panel finish rendering
            break
        if not resent and time.time() > deadline - PANEL_TIMEOUT / 2:
            send_usage()
            resent = True
        time.sleep(0.5)
    return lines()


def _capture_windows(screen, stream) -> list[str]:
    """Windows backend: pywinpty / ConPTY. read() blocks when the TUI is idle,
    so we read on a daemon thread and poll the rendered screen on a clock."""
    from winpty import PtyProcess

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

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        return _drive(lambda b: p.write(b.decode("ascii")), screen)
    finally:
        stop.set()
        try:
            p.terminate(force=True)
        except Exception:
            pass


def _capture_posix(screen, stream) -> list[str]:
    """Linux/macOS backend: stdlib pty + select. Spawns `claude` on a real
    pseudo-terminal sized ROWSxCOLS and feeds its output into pyte."""
    import fcntl
    import pty
    import select
    import signal
    import struct
    import subprocess
    import termios

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
    env = dict(os.environ, TERM="xterm-256color")
    proc = subprocess.Popen(
        ["claude"], stdin=slave, stdout=slave, stderr=slave,
        env=env, start_new_session=True, close_fds=True,
    )
    os.close(slave)
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            try:
                r, _, _ = select.select([master], [], [], 0.2)
            except OSError:
                break
            if master not in r:
                continue
            try:
                data = os.read(master, 8192)
            except OSError:
                break
            if not data:
                break
            stream.feed(data)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        return _drive(lambda b: os.write(master, b), screen)
    finally:
        stop.set()
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        try:
            os.close(master)
        except OSError:
            pass


def capture_usage_screen() -> list[str]:
    # pyte is imported lazily so parse()/classify() stay importable without it
    # (the selftest exercises the parser on CI runners that have no pyte).
    import pyte

    screen = pyte.Screen(COLS, ROWS)
    stream = pyte.ByteStream(screen)
    if os.name == "nt":
        return _capture_windows(screen, stream)
    return _capture_posix(screen, stream)


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
