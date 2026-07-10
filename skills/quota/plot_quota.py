#!/usr/bin/env python
"""View quota_log.csv in the terminal: codeburn-style block-bar chart or table.

Backs the /quota subcommands:
    /quota plot       -> python plot_quota.py            # two stacked block-bar panels (all)
                         python plot_quota.py 48          #   last 48 samples
    /quota plot bars  -> python plot_quota.py bars        # horizontal bars, latest-glance
                         python plot_quota.py bars 16     #   last 16 rows
    /quota log        -> python plot_quota.py rows        # table, last 20 rows
                         python plot_quota.py rows 40

Auto-refresh: every invocation first appends a FRESH sample to the CSV (via
log_quota.py -> nested /usage read, ~13s) unless the newest logged sample is
younger than REFRESH_MAX_AGE_MIN. Pass --no-refresh (or set QUOTA_NO_REFRESH=1)
for an instant, read-only view of already-logged data.

X-axis is TIME-PROPORTIONAL: each column is a fixed slice of wall-clock time,
so logging gaps (machine off, errors) appear as visible `·` gaps instead of
silently compressing. Midnights get a `┬` tick + weekday label; intermediate
hours get smaller ticks where they fit without label collisions.

Beauty is carried by Unicode block glyphs (they survive a markdown code fence).
Color (5h=cyan, weekly=magenta, reset=red) is a TTY-ONLY enhancement: emitted
only when stdout is an interactive terminal, auto-stripped when piped/relayed
(ANSI escapes render as literal garbage inside a chat code block). So the chart
reads correctly in monochrome and lights up when run directly in a terminal.

Reset markers: a 5h window reset (the `five_hour_resets` string changes, i.e.
the pct snaps back up) draws a vertical line across both panels — red `│` on a
TTY, dashed `╎` in monochrome so it's unmistakable without color.
"""
from __future__ import annotations
import csv, os, re, shutil, subprocess, sys
from datetime import date, datetime, time as dtime, timedelta, timezone

BRAKE = 20   # 5h pause threshold (mirrors FIVE_H_PAUSE_PCT in claude_usage.py)
WEEK_PAUSE_PCT = 10  # weekly pause floor (mirrors claude_usage.py)
WRESET_JUMP = 50  # weekly% jump that counts as a real reset (forecast string drifts; ignore it)
WINDOW_H = 5 # length of the 5-hour window
REFRESH_MAX_AGE_MIN = 5  # skip auto-refresh when newest sample is younger than this
LOOKBACK_DAYS = 10  # default history window; older samples silently dropped (--all / --days N override)

# mutated by CLI flags in main(); None => no lookback cap (show everything)
_lookback_days: float | None = LOOKBACK_DAYS

try:
    sys.stdout.reconfigure(encoding="utf-8")  # block glyphs + emoji survive on Windows
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
LOGGER = os.path.join(HERE, "log_quota.py")
LOG = os.path.join(os.path.expanduser("~"), ".claude", "quota_log.csv")
EIGHTHS = " ▁▂▃▄▅▆▇█"   # index 0..8, rising vertical eighths
ROWS = 5                # block-panel height in text rows (resolution = ROWS*8)
# Emoji squares carry REAL color through a chat code fence (unlike ANSI, which
# renders as literal escape garbage). Coarse (one fat cell each) but colored.
SQ5, SQW, SQR, SQE = "🟦", "🟪", "🟥", "⬜"

# ---- color guard (zero-dep, stdlib only) --------------------------------
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if os.name == "nt":
    os.system("")       # enable VT processing on Win10 conhost; no-op elsewhere
CYAN, MAG, RED, DIM = "38;5;51", "38;5;201", "38;5;196", "38;5;240"


def col(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if USE_COLOR else s


# ---- data ---------------------------------------------------------------
def load_all() -> list[dict]:
    if not os.path.exists(LOG):
        return []
    with open(LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def hhmm(warsaw_time: str) -> str:
    # "Sun 2026-05-31 12:41 CEST" -> "12:41" (grab the HH:MM token)
    for tok in warsaw_time.split():
        if ":" in tok:
            return tok
    return warsaw_time


def ymd(warsaw_time: str) -> str:
    m = _DATE_RE.search(warsaw_time)   # "...2026-05-31..." -> "2026-05-31"
    return m.group(0) if m else ""


def _clock_minutes(s: str):
    """'2:39am' / '9pm' -> minutes-of-day, or None when missing/unparsable."""
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", (s or "").strip().lower())
    if not m:
        return None
    h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
    return h * 60 + int(m.group(2) or 0)


def _reset_clock_shifted(a: str, b: str, tol_min: int = 20) -> bool:
    """True when two 5h reset-clock strings point at genuinely different
    times. The panel recomputes the clock at render time, so consecutive
    samples of the SAME window jitter by a minute ('2:39am' vs '2:40am',
    '9:40pm' vs '9:39pm') — a raw string != comparison flagged nearly every
    sample as a reset. Compare parsed minutes-of-day with tolerance instead;
    a real rollover moves the clock by hours."""
    ma, mb = _clock_minutes(a), _clock_minutes(b)
    if ma is None or mb is None:
        return False        # missing/unparsable — the pct snap is the signal
    d = abs(ma - mb)
    return min(d, 1440 - d) > tol_min


def _week_target_advanced(prev_s: str, s: str, prev_dt, dt) -> bool:
    """True when the parsed `week_resets` TARGET moved to a later date by 2+
    days — the unambiguous weekly-rollover signal that survives logging gaps
    (the pct-snap heuristic misses a reset when samples are missing around it
    or when little quota was used, which merged cycles into 500h monsters).
    The string's time-of-day drifts by minutes ('1:59pm' vs '2pm') and can
    even cross midnight, so require >= 2 days (real cycles are ~7 apart)."""
    if prev_dt is None or dt is None:
        return False
    a = parse_week_reset(prev_s or "", prev_dt)
    b = parse_week_reset(s or "", dt)
    if a is None or b is None:
        return False
    return (b.date() - a.date()).days >= 2


def ok_records(cap: bool = True) -> list[dict]:
    """ok rows -> [{t, date, five, week, reset, wreset}].

    `reset`  = 5h window rolled over at this sample (5h pct snapped up, or the
               reset clock moved by more than render jitter).
    `wreset` = weekly window rolled over here (weekly pct snapped up, or the
               `week_resets` target date advanced).
    `cap=False` bypasses the default 10-day lookback (weekly analysis needs the
    full history — a weekly cycle is ~7 days).
    """
    recs = []
    prev_fhr, prev_five = None, None
    prev_wk_at, prev_week, prev_dt = None, None, None
    for r in load_all():
        if r.get("status") != "ok" or not r.get("five_hour_pct_left", "").strip():
            continue
        five = int(r["five_hour_pct_left"]); week = int(r["week_pct_left"])
        fhr = r.get("five_hour_resets", "")
        wk_at = r.get("week_resets", "")
        d = ymd(r["warsaw_time"])
        try:
            dt = datetime.fromisoformat(f"{d}T{hhmm(r['warsaw_time'])}")
        except ValueError:
            dt = None
        reset = prev_five is not None and (
            five - prev_five >= 30 or _reset_clock_shifted(prev_fhr, fhr))
        wreset = prev_week is not None and (
            week - prev_week >= WRESET_JUMP
            or _week_target_advanced(prev_wk_at, wk_at, prev_dt, dt))
        wm = (r.get("week_model_pct_left") or "").strip()
        recs.append({"t": hhmm(r["warsaw_time"]), "date": d,
                     "five": five, "week": week, "reset": reset, "reset_at": fhr,
                     "wreset": wreset, "wreset_at": wk_at,
                     "wmodel": int(wm) if wm.isdigit() else None,
                     "wmodel_name": (r.get("week_model") or "").strip()})
        prev_fhr, prev_five = fhr, five
        prev_wk_at, prev_week, prev_dt = wk_at, week, dt
    return _apply_lookback(recs) if cap else recs


def _apply_lookback(recs: list[dict]) -> list[dict]:
    """Silently drop samples older than `_lookback_days` before the newest one.

    Anchored to the newest sample (not wall-clock now) so a logging gap — machine
    off for a week — still yields the last 10 days of DATA rather than an empty
    plot. `_lookback_days = None` (via --all) disables the cap.
    """
    if _lookback_days is None or not recs:
        return recs
    newest = max((d for d in (sample_dt(r) for r in recs) if d), default=None)
    if newest is None:
        return recs
    cutoff = newest - timedelta(days=_lookback_days)
    return [r for r in recs if (d := sample_dt(r)) is None or d >= cutoff]


def sample_dt(rec: dict):
    """Naive Warsaw-local datetime of a record from its date + HH:MM."""
    try:
        return datetime.fromisoformat(f"{rec['date']}T{rec['t']}")
    except ValueError:
        return None


def parse_reset_clock(s: str, after: datetime):
    """'5:40pm' / '7:40am' / '12:40pm' -> next datetime strictly after `after`."""
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", s.strip().lower())
    if not m:
        return None
    h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
    target = after.replace(hour=h, minute=int(m.group(2) or 0), second=0, microsecond=0)
    if target <= after:
        target += timedelta(days=1)
    return target


def fmt_dur(hours: float) -> str:
    mins = max(0, round(hours * 60))
    return f"{mins // 60}h{mins % 60:02d}m"


# ---- auto-refresh: append a fresh sample before plotting -----------------
def maybe_refresh() -> None:
    """Append a fresh sample via log_quota.py unless the log is already fresh.

    Costs one nested /usage read (~13s + a tiny slice of quota). Skipped when:
      - --no-refresh passed or QUOTA_NO_REFRESH env set
      - newest ok sample is < REFRESH_MAX_AGE_MIN minutes old (already fresh)
      - log_quota.py is missing
    """
    if os.environ.get("QUOTA_NO_REFRESH"):
        return
    recs = ok_records()
    if recs:
        newest = sample_dt(recs[-1])
        if newest is not None:
            age_min = (datetime.now() - newest).total_seconds() / 60.0
            if age_min < REFRESH_MAX_AGE_MIN:
                print(f"(log is fresh: newest sample {age_min:.0f}m old — skipping refresh)")
                return
    if not os.path.exists(LOGGER):
        print(f"(log_quota.py not found at {LOGGER} — plotting logged data only)")
        return
    print("refreshing: appending fresh sample (nested /usage read, ~13s) ...", flush=True)
    try:
        proc = subprocess.run([sys.executable, LOGGER], capture_output=True, timeout=180)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or b"").decode("utf-8", "replace").strip()
            print(f"(refresh failed rc={proc.returncode}: {err[:160]} — plotting logged data only)")
    except Exception as e:
        print(f"(refresh failed: {e} — plotting logged data only)")


# ---- time-proportional column layout -------------------------------------
def time_columns(recs: list[dict], width: int):
    """Place samples into `width` equal slices of wall-clock time.

    Returns (cols, t0, t1) where cols[x] is the latest record falling in slice x
    (reset flag accumulated across the slice), or None for slices with no data
    (a real logging gap — machine off, error rows). This keeps the x-axis
    honest: distance on screen == distance in time.
    """
    pts = [(sample_dt(r), r) for r in recs]
    pts = [(d, r) for d, r in pts if d is not None]
    if not pts:
        return None, None, None
    t0, t1 = pts[0][0], pts[-1][0]
    span = max(1.0, (t1 - t0).total_seconds())
    cols: list[dict | None] = [None] * width
    for d, r in pts:
        x = min(width - 1, int((d - t0).total_seconds() / span * width))
        cur = dict(r)
        cur["dt"] = d
        if cols[x] is not None:
            cur["reset"] = cur["reset"] or cols[x]["reset"]
        cols[x] = cur
    return cols, t0, t1


# ---- vertical block-bar panel (codeburn style) --------------------------
def render_panel(cols_data: list, key: str, series_code: str, title: str,
                 colw: int = 1) -> list[str]:
    w = len(cols_data)
    # grid[r][x] = (char, code|None) ; r=0 top row, r=ROWS-1 bottom row
    grid = [[(" ", None)] * w for _ in range(ROWS)]
    for x, rec in enumerate(cols_data):
        if rec is None:
            # logging gap: faint dot on the bottom row so "no data" reads
            # differently from "0%"
            grid[ROWS - 1][x] = ("·", DIM)
            continue
        v = rec[key]
        units = v / 100 * ROWS * 8
        for r in range(ROWS):
            k = ROWS - 1 - r                 # 0 = bottom
            cell = units - k * 8
            if cell >= 8:
                grid[r][x] = ("█", series_code)
            elif cell > 0:
                grid[r][x] = (EIGHTHS[min(8, max(1, round(cell)))], series_code)
    # reset markers: vertical line over empty cells of reset columns
    marker = "│" if USE_COLOR else "╎"
    for x, rec in enumerate(cols_data):
        if rec is not None and rec["reset"]:
            for r in range(ROWS):
                if grid[r][x][0] == " ":
                    grid[r][x] = (marker, RED)

    lines = [col(DIM, title)]
    for r in range(ROWS):
        label = "100 ┤" if r == 0 else (" 50 ┤" if r == ROWS // 2 else "    │")
        cells = "".join(col(code, ch * colw) if code else ch * colw for ch, code in grid[r])
        lines.append(col(DIM, label) + cells)
    return lines


def render_axis(n_buckets: int, t0: datetime, t1: datetime, colw: int) -> list[str]:
    """Time axis under a panel: `┬` + weekday label at every midnight, smaller
    `┬` + HH label at intermediate hours where they fit, absolute corner times.
    Tick positions use the SAME bucket mapping as time_columns so ticks line up
    with the bars above them."""
    total = n_buckets * colw
    span = max(1.0, (t1 - t0).total_seconds())

    def x_of(dt: datetime) -> int:
        b = min(n_buckets - 1, int((dt - t0).total_seconds() / span * n_buckets))
        return b * colw

    base = ["─"] * total
    lab = [" "] * total
    placed: list[tuple[int, int]] = []

    def place(pos: int, text: str) -> bool:
        pos = max(0, min(pos, total - len(text)))
        end = pos + len(text)
        for p, q in placed:                 # require >=1 space between labels
            if pos < q + 1 and p < end + 1:
                return False
        for i, ch in enumerate(text):
            lab[pos + i] = ch
        placed.append((pos, end))
        return True

    # 1. midnights: always tick, weekday label best-effort
    d = t0.date() + timedelta(days=1)
    while datetime.combine(d, dtime.min) <= t1:
        mid = datetime.combine(d, dtime.min)
        x = x_of(mid)
        base[x] = "┬"
        place(x, mid.strftime("%a"))
        d += timedelta(days=1)

    # 2. intermediate hour ticks: pick a step that keeps labels readable
    span_h = span / 3600.0
    step_h = next((s for s in (3, 6, 12, 24) if (span_h / s) * 5 <= total), 24)
    cur = t0.replace(minute=0, second=0, microsecond=0)
    while cur < t0 or cur.hour % step_h:
        cur += timedelta(hours=1)
    while cur <= t1:
        if cur.hour != 0:                   # midnights already handled
            x = x_of(cur)
            if base[x] == "─" and place(x, f"{cur.hour:02d}"):
                base[x] = "┬"
        cur += timedelta(hours=step_h)

    lines = [col(DIM, "  0 ┴" + "".join(base)),
             "     " + col(DIM, "".join(lab))]
    # absolute corner timestamps (weekday + HH:MM disambiguates multi-day spans)
    lt, rt = f"{t0:%a %H:%M}", f"{t1:%a %H:%M}"
    gap = max(1, total - len(lt) - len(rt))
    lines.append("     " + col(DIM, lt + " " * gap + rt))
    return lines


def show_chart(n: int | None) -> int:
    recs = ok_records()
    recs = recs[-n:] if n else recs
    recs = [r for r in recs if sample_dt(r)]   # need timestamps for a time axis
    if not recs:
        print("no ok rows in", LOG); return 1

    term_cols = shutil.get_terminal_size((120, 24)).columns
    avail = max(10, term_cols - 6)

    t0, t1 = sample_dt(recs[0]), sample_dt(recs[-1])
    span_s = max(60.0, (t1 - t0).total_seconds())

    # natural bucket duration ≈ the logger cadence (median gap between samples,
    # clamped to 5..60 min) so one bucket ≈ one sample when there are no gaps
    diffs = sorted((sample_dt(b) - sample_dt(a)).total_seconds()
                   for a, b in zip(recs, recs[1:]))
    period = diffs[len(diffs) // 2] if diffs else 1800.0
    period = max(300.0, min(3600.0, period))

    n_buckets = min(avail, max(1, int(span_s / period) + 1))
    colw = max(1, min(6, avail // n_buckets))   # widen bars to fill the terminal

    cols_data, t0, t1 = time_columns(recs, n_buckets)
    if cols_data is None:
        print("no plottable rows in", LOG); return 1

    marker = "│" if USE_COLOR else "╎"
    print()
    print(f"quota % left  —  {len(recs)} samples over {fmt_dur(span_s / 3600)}   "
          f"({marker} = 5h reset · `·` = no data · ┬ = midnight/hour)")
    print()
    for line in render_panel(cols_data, "five", CYAN, "5h window % left", colw):
        print(line)
    for line in render_axis(n_buckets, t0, t1, colw):
        print(line)
    print()
    for line in render_panel(cols_data, "week", MAG, "weekly % left", colw):
        print(line)
    for line in render_axis(n_buckets, t0, t1, colw):
        print(line)
    print()
    show_window_projection()
    cur = recs[-1]
    print()
    print(f"latest: {cur['t']}   " + _latest_str(cur))
    return 0


def _latest_str(cur: dict) -> str:
    """'5h=93%  week=36%  fable=3%' — per-model weekly shown when logged."""
    s = f"5h={cur['five']}%   week={cur['week']}%"
    if cur.get("wmodel") is not None:
        s += f"   {cur.get('wmodel_name') or 'model'}={cur['wmodel']}%"
    return s


# ---- current 5h window: burn-rate projection to next reset --------------
def show_window_projection() -> None:
    recs = ok_records()                       # full resolution for the fit
    if not recs:
        return
    # current window = samples since the most recent reset boundary
    start_i = max((i for i, r in enumerate(recs) if r["reset"]), default=0)
    win = recs[start_i:]
    now = win[-1]
    now_dt = sample_dt(now)
    reset_at = parse_reset_clock(now.get("reset_at", ""), now_dt) if now_dt else None

    print(col(DIM, "current 5h window"))
    if reset_at is None or now_dt is None:
        print("  (can't parse reset time — no projection)")
        return
    win_start = reset_at - timedelta(hours=WINDOW_H)
    h_to_reset = (reset_at - now_dt).total_seconds() / 3600.0

    # burn rate via least-squares slope of five% vs elapsed hours
    pts = [(sample_dt(r), r["five"]) for r in win if sample_dt(r)]
    slope = None
    if len(pts) >= 2:
        xs = [(d - pts[0][0]).total_seconds() / 3600.0 for d, _ in pts]
        ys = [v for _, v in pts]
        mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
        denom = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom else None

    nf = now["five"]
    print(f"  since {win_start:%H:%M} · resets {reset_at:%H:%M} (in {fmt_dur(h_to_reset)}) · "
          f"as of {now['t']} 5h={nf}%")

    if slope is None:
        print("  burn: need 2+ samples this window for a projection"); return
    burn = -slope                              # %/hour consumed (positive when draining)
    proj = max(0.0, min(100.0, nf + slope * h_to_reset))

    if burn <= 0.2:
        verdict = col(DIM, "≈flat — no brake risk this window")
        brake_h = None
    elif nf <= BRAKE:
        verdict = "⚠ ALREADY at/below brake (%d%%)" % BRAKE
        brake_h = 0.0
    else:
        brake_h = (nf - BRAKE) / burn          # hours until 20% at this burn
        if brake_h < h_to_reset:
            bt = now_dt + timedelta(hours=brake_h)
            verdict = (f"⚠ BRAKE RISK — hit {BRAKE}% at ~{bt:%H:%M} "
                       f"(~{fmt_dur(brake_h)} from now, ~{fmt_dur(h_to_reset - brake_h)} before reset)")
        else:
            verdict = (f"✓ SAFE — reach reset with ~{proj:.0f}% left "
                       f"(~{proj - BRAKE:.0f}% above the {BRAKE}% brake)")
    print(f"  burn ≈ {burn:.1f}%/h ({len(pts)} samples)   projected at reset ≈ {proj:.0f}%")
    print("  " + verdict)

    # horizontal gauge across the window: value trajectory + now/brake marks
    W = min(48, max(20, shutil.get_terminal_size((120, 24)).columns - 30))
    def val_at(hours_from_start: float) -> float:
        t_h = hours_from_start - (now_dt - win_start).total_seconds() / 3600.0
        if t_h <= 0:                            # past: interpolate actual samples
            tx = win_start + timedelta(hours=hours_from_start)
            lo = pts[0]
            for p in pts:
                if p[0] <= tx:
                    lo = p
                else:
                    hi = p
                    span = (hi[0] - lo[0]).total_seconds() / 3600.0
                    if span <= 0:
                        return lo[1]
                    f = (tx - lo[0]).total_seconds() / 3600.0 / span
                    return lo[1] + (hi[1] - lo[1]) * f
            return lo[1]
        return max(0.0, min(100.0, nf + slope * t_h))   # future: projected

    spark = []
    for x in range(W):
        v = val_at((x + 0.5) / W * WINDOW_H)
        lvl = max(0, min(8, round(v / 100 * 8)))
        spark.append(EIGHTHS[lvl])
    now_x = round((now_dt - win_start).total_seconds() / 3600.0 / WINDOW_H * W)
    mark = [" "] * W
    if 0 <= now_x < W:
        mark[now_x] = "n"
    if brake_h and 0 < brake_h < h_to_reset:
        bx = round((((now_dt - win_start).total_seconds() / 3600.0) + brake_h) / WINDOW_H * W)
        if 0 <= bx < W:
            mark[bx] = "╳"
    print("  100 " + "".join(spark))
    print("      " + "".join(mark))
    print("      " + f"{win_start:%H:%M}" + " " * max(1, W - 10) + f"{reset_at:%H:%M}")


# ---- weekly-cycle analysis (per-reset stats + derivatives) --------------
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_week_reset(s: str, ref: datetime):
    """'Jun 1, 2pm' / 'Jun 15, 1:59pm' -> datetime (year inferred from `ref`)."""
    m = re.match(r"([a-z]{3,})\.?\s+(\d{1,2}),?\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)",
                 s.strip().lower())
    if not m:
        return None
    mon = _MONTHS.get(m.group(1)[:3])
    if not mon:
        return None
    h = int(m.group(3)) % 12 + (12 if m.group(5) == "pm" else 0)
    year = ref.year + (1 if mon < ref.month else 0)
    try:
        return datetime(year, mon, int(m.group(2)), h, int(m.group(4) or 0))
    except ValueError:
        return None


def weekly_cycles(recs: list[dict]) -> list[list[dict]]:
    """Split records into weekly cycles, breaking BEFORE each `wreset` sample.

    Each cycle = the run of samples from one weekly reset until the next.
    """
    cycles, cur = [], []
    for r in recs:
        if r.get("wreset") and cur:
            cycles.append(cur)
            cur = []
        cur.append(r)
    if cur:
        cycles.append(cur)
    return cycles


def cycle_stats(cyc: list[dict], is_last: bool) -> dict | None:
    pts = [(sample_dt(r), r["week"]) for r in cyc if sample_dt(r)]
    if len(pts) < 1:
        return None
    t0, t1 = pts[0][0], pts[-1][0]
    dur_h = max(0.0, (t1 - t0).total_seconds() / 3600.0)
    weeks = [w for _, w in pts]
    start_w, end_w, min_w = weeks[0], weeks[-1], min(weeks)
    drained = start_w - min_w
    mean_burn_day = (drained / (dur_h / 24.0)) if dur_h > 0 else 0.0  # %/day

    # first derivative per consecutive pair: burn %/h (positive = draining)
    peak_burn_h = 0.0
    for (a_dt, a_w), (b_dt, b_w) in zip(pts, pts[1:]):
        dh = (b_dt - a_dt).total_seconds() / 3600.0
        if dh > 0:
            peak_burn_h = max(peak_burn_h, (a_w - b_w) / dh)

    # current burn = least-squares slope over the last ~6h of samples
    recent = [(d, w) for d, w in pts if (t1 - d).total_seconds() <= 6 * 3600]
    cur_burn_h = _slope_burn(recent)

    reset_at = parse_week_reset(cyc[-1].get("wreset_at", ""), t1)
    proj_at_reset = exhaust_at = None
    if is_last and reset_at and cur_burn_h is not None:
        h_left = (reset_at - t1).total_seconds() / 3600.0
        if h_left > 0:
            proj_at_reset = max(0.0, end_w - cur_burn_h * h_left)
            if cur_burn_h > 0.01:
                exhaust_at = t1 + timedelta(hours=end_w / cur_burn_h)

    return {"t0": t0, "t1": t1, "dur_h": dur_h, "start": start_w, "end": end_w,
            "min": min_w, "drained": drained, "mean_burn_day": mean_burn_day,
            "peak_burn_h": peak_burn_h, "cur_burn_h": cur_burn_h, "n": len(pts),
            "is_last": is_last, "reset_at": reset_at, "proj_at_reset": proj_at_reset,
            "exhaust_at": exhaust_at}


def _slope_burn(pts: list[tuple[datetime, float]]):
    """Least-squares burn rate (%/h, positive = draining) over (dt, week) pts."""
    if len(pts) < 2:
        return None
    xs = [(d - pts[0][0]).total_seconds() / 3600.0 for d, _ in pts]
    ys = [w for _, w in pts]
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if not denom:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return -slope


def render_signed(series: list[float | None], title: str, code: str,
                  colw: int = 1) -> list[str]:
    """Signed block panel: a zero baseline mid-row, positive bars rise, negative
    bars fall. Scaled by the max abs value across the series."""
    vals = [v for v in series if v is not None]
    scale = max((abs(v) for v in vals), default=1.0) or 1.0
    half = ROWS // 2                       # baseline row index (0 = top)
    up_rows, dn_rows = half, ROWS - half - 1
    grid = [[(" ", None)] * len(series) for _ in range(ROWS)]
    for x, v in enumerate(series):
        if v is None:
            grid[half][x] = ("·", DIM)
            continue
        mag = abs(v) / scale
        if v >= 0:
            units = mag * up_rows * 8
            for r in range(up_rows):
                k = up_rows - 1 - r
                cell = units - k * 8
                if cell >= 8:
                    grid[r][x] = ("█", code)
                elif cell > 0:
                    grid[r][x] = (EIGHTHS[min(8, max(1, round(cell)))], code)
        else:
            units = mag * dn_rows * 8
            for rr in range(dn_rows):
                cell = units - rr * 8
                row = half + 1 + rr
                if cell >= 8:
                    grid[row][x] = ("█", DIM)
                elif cell > 0:
                    grid[row][x] = (EIGHTHS[min(8, max(1, round(cell)))], DIM)
    # baseline
    for x in range(len(series)):
        if grid[half][x][0] == " ":
            grid[half][x] = ("─", DIM)
    lines = [col(DIM, f"{title}   (scale ±{scale:.1f}, ▔above=+ ▁below=−)")]
    for r in range(ROWS):
        tag = " 0 ┤" if r == half else "   │"
        cells = "".join(col(c, ch * colw) if c else ch * colw for ch, c in grid[r])
        lines.append(col(DIM, tag) + cells)
    return lines


def show_weekly(want_deriv: bool = True) -> int:
    recs = ok_records(cap=False)
    recs = [r for r in recs if sample_dt(r)]
    if not recs:
        print("no ok rows in", LOG); return 1
    cycles = weekly_cycles(recs)
    stats = [s for i, c in enumerate(cycles)
             if (s := cycle_stats(c, is_last=(i == len(cycles) - 1)))]

    print()
    print(f"weekly cycles — {len(stats)} reset window(s) over "
          f"{fmt_dur((sample_dt(recs[-1]) - sample_dt(recs[0])).total_seconds()/3600)}")
    print("(a cycle = weekly quota from one reset until the next)")
    print()
    hdr = (f"{'#':>2}  {'start':<16} {'dur':>7} {'beg%':>4} {'end%':>4} {'min%':>4} "
           f"{'used%':>5} {'avg/day':>7} {'peak/h':>6} {'now/h':>6} {'n':>4}")
    print(hdr)
    print("-" * len(hdr))
    for i, s in enumerate(stats):
        nb = f"{s['cur_burn_h']:.1f}" if s["cur_burn_h"] is not None else "  -"
        tag = "  ← now" if s["is_last"] else ""
        print(f"{i:>2}  {s['t0']:%a %m-%d %H:%M} {fmt_dur(s['dur_h']):>7} "
              f"{s['start']:>4} {s['end']:>4} {s['min']:>4} {s['drained']:>5} "
              f"{s['mean_burn_day']:>7.1f} {s['peak_burn_h']:>6.1f} {nb:>6} "
              f"{s['n']:>4}{tag}")

    # dynamic stats for the live cycle
    if stats and stats[-1]["is_last"]:
        s = stats[-1]
        print()
        print(col(DIM, "current weekly cycle — dynamic"))
        print(f"  in cycle {fmt_dur(s['dur_h'])} · used {s['drained']}% · "
              f"now at {s['end']}%")
        if s["cur_burn_h"] is not None:
            print(f"  current burn ≈ {s['cur_burn_h']:.2f}%/h "
                  f"({s['cur_burn_h']*24:.1f}%/day)")
        if s["reset_at"]:
            h_left = (s["reset_at"] - s["t1"]).total_seconds() / 3600.0
            print(f"  next weekly reset: {s['reset_at']:%a %m-%d %H:%M} "
                  f"(in {fmt_dur(h_left)})")
        if s["proj_at_reset"] is not None:
            verdict = ("✓ lands with headroom" if s["proj_at_reset"] > WEEK_PAUSE_PCT
                       else "⚠ projected to cross the %d%% weekly floor" % WEEK_PAUSE_PCT)
            print(f"  projected at reset ≈ {s['proj_at_reset']:.0f}%  ({verdict})")
        if s["exhaust_at"] is not None:
            print(f"  at this burn, weekly hits 0% ≈ {s['exhaust_at']:%a %m-%d %H:%M}")

    if want_deriv:
        _show_weekly_derivatives(recs)
    return 0


def _show_weekly_derivatives(recs: list[dict]) -> int:
    """First (burn %/h) and second (accel %/h²) derivative panels of weekly %,
    over the full logged timeline, on the same time-proportional x-axis as the
    main plot."""
    term_cols = shutil.get_terminal_size((120, 24)).columns
    avail = max(10, term_cols - 6)
    cols_data, t0, t1 = time_columns(recs, min(avail, max(1, len(recs))))
    if cols_data is None:
        return 1
    colw = max(1, min(6, avail // len(cols_data)))

    # per-column burn (first deriv) and accel (second deriv) from week series
    pts = [(c["dt"], c["week"]) if c else None for c in cols_data]
    d1: list[float | None] = [None] * len(pts)
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        if a and b:
            dh = (b[0] - a[0]).total_seconds() / 3600.0
            if dh > 0:
                d1[i] = (a[1] - b[1]) / dh        # burn %/h, +=draining
    d2: list[float | None] = [None] * len(pts)
    for i in range(1, len(d1)):
        a, b = pts[i - 1], pts[i]
        if d1[i] is not None and d1[i - 1] is not None and a and b:
            dh = (b[0] - a[0]).total_seconds() / 3600.0
            if dh > 0:
                d2[i] = (d1[i] - d1[i - 1]) / dh  # accel %/h²

    print()
    print("weekly burn — 1st derivative (burn %/h, +draining / −refilled)")
    for line in render_signed(d1, "d/dt week%", MAG, colw):
        print(line)
    for line in render_axis(len(cols_data), t0, t1, colw):
        print(line)
    print()
    print("weekly burn — 2nd derivative (acceleration %/h², +speeding up)")
    for line in render_signed(d2, "d²/dt² week%", RED, colw):
        print(line)
    for line in render_axis(len(cols_data), t0, t1, colw):
        print(line)
    return 0


# ---- emoji bars (color survives the chat relay) -------------------------
def emoji_bar(value: int, sq: str, cells: int = 10) -> str:
    filled = round(value / 100 * cells)
    return sq * filled + SQE * (cells - filled)


def show_emoji_bars(n: int) -> int:
    recs = ok_records()
    if not recs:
        print("no ok rows in", LOG); return 1
    recs = recs[-n:]
    print()
    print(f"quota — last {len(recs)} samples    {SQ5} 5h  /  {SQW} week    {SQR} reset")
    print()
    for i, r in enumerate(recs):
        flag = ""
        if r["reset"]:
            flag += f"  {SQR} reset"
        if i == len(recs) - 1:
            flag += "  ← now"
        wm = f"  {r['wmodel_name'][:5]} {r['wmodel']:3d}%" if r.get("wmodel") is not None else ""
        print(f"{r['t']}   5h {emoji_bar(r['five'], SQ5)} {r['five']:3d}%"
              f"    wk {emoji_bar(r['week'], SQW)} {r['week']:3d}%{wm}{flag}")
    cur = recs[-1]
    print()
    print(f"latest: {cur['t']}   " + _latest_str(cur))
    return 0


# ---- rows table (unchanged behavior) ------------------------------------
def show_rows(n: int) -> int:
    allrows = load_all()
    if not allrows:
        print("no rows in", LOG); return 1
    rows = allrows[-n:]
    print(f"\nlast {len(rows)} rows of {LOG}\n")
    print(f"{'warsaw_time':<26} {'5h%':>4} {'wk%':>4} {'mdl%':>4}  {'5h resets':<10} "
          f"{'wk resets':<12} status")
    print("-" * 84)
    for r in rows:
        st = r.get("status", "")
        st = st if st == "ok" else "ERR"
        print(f"{r.get('warsaw_time',''):<26} "
              f"{r.get('five_hour_pct_left',''):>4} "
              f"{r.get('week_pct_left',''):>4} "
              f"{r.get('week_model_pct_left') or '':>4}  "
              f"{r.get('five_hour_resets',''):<10} "
              f"{r.get('week_resets',''):<12} {st}")
    return 0


def main() -> int:
    global _lookback_days
    raw = sys.argv[1:]
    skip_refresh = "--no-refresh" in raw

    # lookback override: --all (no cap) or --days N / --days=N (default LOOKBACK_DAYS)
    if "--all" in raw:
        _lookback_days = None
    for i, a in enumerate(raw):
        if a == "--days" and i + 1 < len(raw) and raw[i + 1].lstrip("-").isdigit():
            _lookback_days = float(raw[i + 1])
        elif a.startswith("--days=") and a.split("=", 1)[1].lstrip("-").isdigit():
            _lookback_days = float(a.split("=", 1)[1])

    consumed = {"--no-refresh", "--all", "--days"}
    args = []
    skipnext = False
    for i, a in enumerate(raw):
        if skipnext:
            skipnext = False
            continue
        if a == "--days":
            skipnext = True
            continue
        if a in consumed or a.startswith("--days="):
            continue
        args.append(a)

    if not skip_refresh:
        maybe_refresh()
    a0 = args[0].lower() if args else ""
    if a0 in ("rows", "log", "table"):
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
        return show_rows(n)
    if a0 in ("bars", "bar", "emoji", "h"):   # emoji bars (color survives chat)
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 16
        return show_emoji_bars(n)
    if a0 in ("weekly", "week", "cycles", "resets"):
        # per-weekly-reset stats table + 1st/2nd derivative panels.
        # `weekly table` / `--no-deriv` suppresses the graphs (table only).
        want_deriv = "table" not in args and "--no-deriv" not in raw
        return show_weekly(want_deriv=want_deriv)
    # default: high-res block panels (`fine` accepted as an explicit alias).
    rest = args[1:] if a0 == "fine" else args
    n = int(rest[0]) if rest and rest[0].isdigit() else None
    return show_chart(n)


if __name__ == "__main__":
    raise SystemExit(main())
