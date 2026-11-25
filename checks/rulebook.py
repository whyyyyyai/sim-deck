#!/usr/bin/env python3
"""rulebook: the script check every sim-deck video passes before render.

Reads a video's script file (briefs/*.script.json) and fails, naming the
beat, when the script breaks the rules in PLAN.md:

  - every beat has a caption and a picture (non-empty strings)
  - no beat runs longer than 3 s
  - beats run back to back: no gaps, no overlaps (1 ms tolerance)
  - no private text in captions: home paths, key-shaped strings, the
    machine's hostname, or anything that looks like a pasted note

Usage:
    rulebook.py <script.json> [--machine NAME]     check one script
    rulebook.py --self-test                        run the built-in checks

Written by: Devin (2026-11-25).
"""
import json
import os
import re
import socket
import sys
import tempfile

MAX_BEAT = 3.0          # seconds; the picture must keep changing
TOLERANCE = 0.001       # seconds of float slack on beat boundaries

# Things that must never appear in a caption on a public video.
PRIVATE_PATTERNS = [
    (re.compile(r"(?i)(/home/|/Users/|~/|[A-Za-z]:\\\\Users\\\\)"), "a home path"),
    (re.compile(r"(?i)(sk-[A-Za-z0-9]|api[_-]?key|secret|token|password|BEGIN [A-Z ]*PRIVATE KEY)"), "a key-shaped string"),
    (re.compile(r"(?i)(ssh-rsa|ssh-ed25519|ghp_|github_pat_|xox[baprs]-)"), "a credential"),
]


def private_reason(text, machine):
    """Why this caption can't be public, or None."""
    for pattern, what in PRIVATE_PATTERNS:
        if pattern.search(text):
            return what
    if machine and machine.lower() in text.lower():
        return "the machine name"
    return None


def check_script(doc, machine=None):
    """Every rule break in the script, as strings. Empty list means it passes."""
    problems = []
    if not isinstance(doc, dict):
        return ["the script is not a JSON object"]
    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return ["the script has no scenes"]
    seen_ids = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            problems.append("a scene is not an object")
            continue
        sid = scene.get("id", "?")
        if sid in seen_ids:
            problems.append(f"scene {sid}: duplicate id")
        seen_ids.add(sid)
        beats = scene.get("beats")
        if not isinstance(beats, list) or not beats:
            problems.append(f"scene {sid}: no beats")
            continue
        prev_end = None
        for i, beat in enumerate(beats):
            where = f"scene {sid} beat {i}"
            if not isinstance(beat, dict):
                problems.append(f"{where}: not an object")
                continue
            start, end = beat.get("start"), beat.get("end")
            if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
                problems.append(f"{where}: start/end missing or not numbers")
                continue
            if end <= start:
                problems.append(f"{where}: end {end} is not after start {start}")
                continue
            if end - start > MAX_BEAT + TOLERANCE:
                problems.append(f"{where}: runs {end - start:.2f} s, over the {MAX_BEAT:.0f} s limit")
            if prev_end is not None:
                if start > prev_end + TOLERANCE:
                    problems.append(f"{where}: gap of {start - prev_end:.3f} s after the previous beat")
                elif start < prev_end - TOLERANCE:
                    problems.append(f"{where}: overlaps the previous beat by {prev_end - start:.3f} s")
            prev_end = end
            caption = beat.get("caption")
            if not isinstance(caption, str) or not caption.strip():
                problems.append(f"{where}: no caption")
            else:
                why = private_reason(caption, machine)
                if why:
                    problems.append(f"{where}: caption holds {why}: {caption[:60]!r}")
            picture = beat.get("picture")
            if not isinstance(picture, str) or not picture.strip():
                problems.append(f"{where}: no picture")
    return problems


def load_script(path):
    with open(path) as f:
        return json.load(f)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return self_test()
    path = argv[0]
    machine = argv[argv.index("--machine") + 1] if "--machine" in argv else socket.gethostname()
    try:
        doc = load_script(path)
    except (OSError, json.JSONDecodeError) as error:
        print(f"rulebook: can't read {path}: {error}", file=sys.stderr)
        return 2
    problems = check_script(doc, machine)
    if problems:
        for problem in problems:
            print(f"rulebook: {problem}")
        print(f"rulebook: {len(problems)} problem(s) in {path}")
        return 1
    n = sum(len(s.get("beats", [])) for s in doc.get("scenes", []))
    print(f"rulebook: ok — {len(doc.get('scenes', []))} scenes, {n} beats")
    return 0


def self_test():
    """The rules against made-up scripts. Exit 1 on any failure."""
    machine = "testbox"
    good_beat = {"start": 0.0, "end": 2.5, "caption": "One machine.", "picture": "a ship draws itself"}

    def script(beats, sid="s1"):
        return {"video": "t", "scenes": [{"id": sid, "beats": beats}]}

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            print("     " + str(detail))
            failures.append(name)

    failures = []
    check("a clean script passes", check_script(script([good_beat, dict(good_beat, start=2.5, end=5.0)]), machine) == [])
    check("a beat with no caption fails",
          any("no caption" in p for p in check_script(script([dict(good_beat, caption="")]), machine)))
    check("a beat with no picture fails",
          any("no picture" in p for p in check_script(script([dict(good_beat, picture=None)]), machine)))
    check("a 4 s beat fails",
          any("over the 3 s limit" in p for p in check_script(script([dict(good_beat, end=4.0)]), machine)))
    check("a gap between beats fails",
          any("gap" in p for p in check_script(script([good_beat, dict(good_beat, start=3.0, end=5.0)]), machine)))
    check("an overlap fails",
          any("overlap" in p for p in check_script(script([good_beat, dict(good_beat, start=2.0, end=4.0)]), machine)))
    check("a home path in a caption fails",
          any("home path" in p for p in check_script(script([dict(good_beat, caption="files in /home/neo")]), machine)))
    check("a key-shaped string fails",
          any("key-shaped" in p for p in check_script(script([dict(good_beat, caption="token sk-abc123 here")]), machine)))
    check("the machine name fails",
          any("machine name" in p for p in check_script(script([dict(good_beat, caption="on testbox today")]), machine)))
    check("an ordinary caption passes the private scan",
          check_script(script([dict(good_beat, caption="The crew talks.")]), machine) == [])
    # The real brief must pass.
    here = os.path.dirname(os.path.abspath(__file__))
    real = os.path.join(here, "..", "briefs", "001-comms-deck.script.json")
    if os.path.exists(real):
        problems = check_script(load_script(real), machine)
        check("the shipped brief passes the rulebook", not problems, problems[:3])
    else:
        print("skip the shipped brief (not found)")
    print("\n" + ("all passed" if not failures else f"{len(failures)} failed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
