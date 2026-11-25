#!/usr/bin/env python3
"""sim-deck sample: one read-only JSON frame of comms-deck's live state.

A frame is what a sim-deck video renders from: every seat's state, the
context split, the limit meters, and deck-level totals. Nothing here
writes, wakes or sends -- each frame only reads what the deck persists.

Modes:
  sim-deck-sample.py            print one frame (pretty JSON)
  sim-deck-sample.py --watch N  sample every N seconds, NDJSON on stdout
  sim-deck-sample.py --self-test

Pure stdlib. Reads the same env the deck does (COMMS_DECK_HOME for the
data, or the defaults), plus `comms-deck status --json` for the seats.
Written by: Vibe (2026-11-25) - sim-deck's deck-data side.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME_DECK = Path.home() / ".local" / "bin" / "comms-deck"
SEAT_COLOURS = {"claude": 208, "grok": 45, "codex": 141, "gravity": 213,
                "vibe": 50, "devin": 117, "alice": 229, "lumo": 155,
                "mystra": 176}
FALLBACK_COLOUR = 245

argv0 = sys.argv[0] if sys.argv[0:] else ""


def seat_colour(seat):
    return SEAT_COLOURS.get(seat, FALLBACK_COLOUR)


def list_tail(path, n=5):
    """The last n JSON lines of a JSONL file, oldest first; missing -> []."""
    try:
        return [json.loads(line) for line in path.read_text().splitlines()[-n:] if line.strip()]
    except (OSError, ValueError):
        return []


def context_window(d):
    """(tokens, size) from a usage file's data, or (None, None)."""
    cw = d.get("context_window") or {}
    used, size = cw.get("context_tokens"), cw.get("context_window_size")
    if not isinstance(used, (int, float)) or used <= 0:
        pct, size0 = cw.get("used_percentage"), cw.get("context_window_size")
        if not (isinstance(pct, (int, float)) and pct > 0
                and isinstance(size0, (int, float)) and size0 > 0):
            return None, None
        used = size0 * pct / 100
        size = size0
    return float(used), (float(size) if isinstance(size, (int, float)) and size > 0 else None)


def deck_home():
    return Path(os.environ.get("COMMS_DECK_HOME") or
                Path.home() / ".local/share/comms-deck")


def seat_status():
    """The deck's own seat view (status --json on test's shape), or []."""
    try:
        r = subprocess.run([str(HOME_DECK), "status", "--json"],
                           capture_output=True, text=True, timeout=10)
        return (json.loads(r.stdout) if r.returncode == 0 else {}).get("seats", {})
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def frame():
    """One sample. Everything read-only; suitable to render scene by scene."""
    data = deck_home()
    seats = {}
    usage_dir = data / "usage"
    status_seats = seat_status()
    names = sorted(set(status_seats) | {p.stem for p in usage_dir.glob("*.json")})
    for seat in names:
        d = (usage_dir / f"{seat}.json")
        try:
            usage = (json.loads(d.read_text()).get("data") or {})
        except (OSError, ValueError):
            usage = {}
        used, window = context_window(usage)
        rl = usage.get("rate_limits") or {}
        five = rl.get("five_hour") or {}
        seven = rl.get("seven_day") or {}
        st = {}
        for name, row in (("five_hour", five), ("seven_day", seven)):
            if isinstance(row.get("used_percentage"), (int, float)):
                st[name] = round(row["used_percentage"], 1)
        seats[seat] = {
            "colour": seat_colour(seat),
            "state": status_seats.get(seat, {}).get("state", "unknown"),
            "waiting": status_seats.get(seat, {}).get("waiting", 0),
            "context_tokens": used,
            "context_window": window,
            "context_pct": (round(100 * used / window, 1) if used and window else None),
            "limits": st,
        }
    # the context pool: shares of the total, the dot box's own arithmetic
    pool = {s: v["context_tokens"] for s, v in seats.items() if v["context_tokens"]}
    total = sum(pool.values())
    split = {s: round(100 * t / total, 2) for s, t in pool.items()} if total else {}
    return {
        "t": time.time(),
        "machine": os.uname().nodename,
        "seats": seats,
        "context_split": split,
        "context_total": total or None,
        "working": sorted(s for s, v in seats.items() if v["state"] == "busy"),
        "protocol": 1,  # the frame's shape version, for sim-deck's renderer
    }


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        f = frame()
        assert f["protocol"] == 1 and isinstance(f["seats"], dict)
        f2 = frame()
        assert abs(f2["t"] - f["t"]) < 5
        for seat, v in f["seats"].items():
            assert isinstance(v["colour"], int) and 0 <= v["colour"] <= 255
            assert isinstance(v["state"], str) and v["state"]  # agents: busy/idle/away; app seats may say "no chat yet"
            p = v["context_pct"]
            assert p is None or 0 <= p
        if f["context_split"] and f["seats"]:
            assert abs(sum(f["context_split"].values()) - 100.0) < 1.0, f["context_split"]
            biggest = max(f["context_split"], key=f["context_split"].get)
            assert biggest in f["seats"]
        print("sim-deck-sample: frames sample ok")
        return
    if args and args[0] == "--watch":
        n = float(args[1]) if len(args) > 1 else 1.0
        out = sys.stdout
        while True:
            out.write(json.dumps(frame(), separators=(",", ":")) + "\n")
            out.flush()
            time.sleep(n)
    else:
        print(json.dumps(frame(), indent=1))


if __name__ == "__main__":
    main()
