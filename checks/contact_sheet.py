#!/usr/bin/env python3
"""contact_sheet: one still per scene, tiled into a single PNG.

Reviews a rendered video without watching it: pull the middle frame of
every scene (times come from the script's beats) — or evenly spaced
frames when no script is given — scale them down, and tile them with
ffmpeg into one image you can eyeball in seconds.

Usage:
    contact_sheet.py video.mp4 [--script script.json] [--cols N] [--out sheet.png]
    contact_sheet.py --self-test

Python stdlib plus ffmpeg/ffprobe on PATH. Written by: Devin (2026-11-25).
"""
import json
import math
import os
import subprocess
import sys
import tempfile

THUMB_W = 480          # each cell's width in pixels
GRID_PAD = 0.02        # seconds past the end a padded cell may seek to


def run(cmd):
    """Run a command, raising RuntimeError with its stderr on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}… failed: {(result.stderr or result.stdout).strip()[:300]}")
    return result


def probe_duration(path):
    """The video's length in seconds, via ffprobe."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]).stdout.strip()
    return float(out)


def scene_times(script_path, duration):
    """One timestamp per scene: the middle of its first-to-last beat span."""
    with open(script_path) as f:
        doc = json.load(f)
    times = []
    for scene in doc.get("scenes", []):
        beats = scene.get("beats") or []
        starts = [b["start"] for b in beats if isinstance(b.get("start"), (int, float))]
        ends = [b["end"] for b in beats if isinstance(b.get("end"), (int, float))]
        if not starts or not ends:
            continue
        lo, hi = min(starts), max(ends)
        times.append(min(max((lo + hi) / 2, 0.0), max(0.0, duration - 0.05)))
    return times or evenly_spaced(duration, 6)


def evenly_spaced(duration, count):
    """`count` timestamps spread across the video, never on the last frame."""
    if duration <= 0:
        return [0.0]
    return [duration * (i + 0.5) / count for i in range(count)]


def contact_sheet(video, times, out_path, cols=None):
    """Extract one frame per timestamp and tile them into `out_path`."""
    n = len(times)
    cols = cols or math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cells = rows * cols
    # Pad short of a full grid by repeating the last frame's time.
    padded = list(times) + [times[-1]] * (cells - n)
    with tempfile.TemporaryDirectory(prefix="contact-sheet-") as tmp:
        frames = []
        for i, t in enumerate(padded):
            frame = os.path.join(tmp, f"f_{i:03d}.png")
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", video,
                 "-frames:v", "1", "-vf", f"scale={THUMB_W}:-2", frame])
            frames.append(frame)
        run(["ffmpeg", "-y", "-v", "error", "-framerate", "1",
             "-start_number", "0", "-i", os.path.join(tmp, "f_%03d.png"),
             "-vf", f"tile={cols}x{rows}", "-frames:v", "1", out_path])
    return {"cells": cells, "used": n, "cols": cols, "rows": rows, "out": out_path}


def self_test():
    """Build a 3 s test video, sheet it two ways, check the PNGs exist."""
    failures = []

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            print("     " + str(detail))
            failures.append(name)

    with tempfile.TemporaryDirectory(prefix="contact-sheet-test-") as tmp:
        video = os.path.join(tmp, "clip.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "testsrc=size=640x360:rate=30:duration=3", "-pix_fmt", "yuv420p", video])
        duration = probe_duration(video)
        check("ffprobe reads the duration", 2.9 < duration < 3.1, duration)
        # Even spacing, no script.
        times = evenly_spaced(duration, 4)
        check("even spacing covers the middle", abs(times[0] - duration / 8) < 0.01
              and abs(times[-1] - duration * 7 / 8) < 0.01, times)
        sheet = os.path.join(tmp, "sheet.png")
        info = contact_sheet(video, times, sheet)
        check("the sheet is written", os.path.getsize(sheet) > 1000, info)
        # With a script: one still per scene at the beat-span middle.
        script = os.path.join(tmp, "s.script.json")
        with open(script, "w") as f:
            json.dump({"scenes": [
                {"id": "a", "beats": [{"start": 0.0, "end": 1.5, "caption": "x", "picture": "y"}]},
                {"id": "b", "beats": [{"start": 1.5, "end": 3.0, "caption": "x", "picture": "y"}]},
            ]}, f)
        stimes = scene_times(script, duration)
        check("scene times are the beat middles", len(stimes) == 2
              and abs(stimes[0] - 0.75) < 0.01 and abs(stimes[1] - 2.25) < 0.01, stimes)
        sheet2 = os.path.join(tmp, "sheet2.png")
        contact_sheet(video, stimes, sheet2, cols=2)
        check("a two-scene sheet is written", os.path.getsize(sheet2) > 1000, sheet2)
    print("\n" + ("all passed" if not failures else f"{len(failures)} failed"))
    return 1 if failures else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return self_test()
    video = argv[0]
    script = argv[argv.index("--script") + 1] if "--script" in argv else None
    out = argv[argv.index("--out") + 1] if "--out" in argv else "contact-sheet.png"
    cols = int(argv[argv.index("--cols") + 1]) if "--cols" in argv else None
    duration = probe_duration(video)
    times = scene_times(script, duration) if script else evenly_spaced(duration, 8)
    info = contact_sheet(video, times, out, cols)
    print(f"contact sheet: {info['used']} scene stills ({info['cols']}x{info['rows']}) -> {info['out']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"contact_sheet: {error}", file=sys.stderr)
        sys.exit(2)
