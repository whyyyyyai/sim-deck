# Build plan

Taken from two articles the owner shared (a Remotion motion-design pipeline, and a
2.5D explainer pipeline with a rulebook and contact sheets). We keep the useful
ideas and skip what needs paid services or a big GPU.

## Kept

- Code draws everything (Remotion scenes, shapes, the deck's own colours). No image generator.
- Live data drives the pictures (the feed).
- A rulebook checked before render, and a contact sheet of stills to review.
- The camera never sits still for long; the picture changes every 2 to 3 seconds.
- Captions burned in, one or two words at a time, timed to the narration.
- One command does the whole render locally.

## Skipped for now

- Paid voiceover (ElevenLabs). First video uses captions only; voice is a later choice for the owner.
- Blender and 3D sets. Too heavy for this machine (8 cores, 7 GB, no GPU).
- 18 variants per video (hooks × ratios × endings). One 16:9 cut first.

## Version 1: "What is comms-deck?" (about 60 s)

1. The crew: each seat appears in its colour, with its name and what it is.
2. A note: one agent sends another a note, and it lands in their inbox.
3. Waking up: an idle seat is woken by a note and starts working.
4. The chat screen: the owner reads and answers on workspace 5.
5. Context split: the dot box fills from live data, and working seats glow.
6. Close: "comms-deck: how the crew talks."

## Who does what

| Part | Who | Done when |
|---|---|---|
| Remotion project, scenes 1 to 6, render command | Claude | `video/` renders a 16:9 mp4 |
| Feed (`feed/sample-deck.py`), frames saved for a scene, private fields left out | Vibe | a saved frame file the scenes read |
| Rulebook check and contact sheet (`checks/`) | Devin | one command fails on a broken script and prints a contact sheet |
| Brief and script for video 1 | Claude drafts, owner approves | `briefs/001-comms-deck.md` |

## Needed from the owner

- `npm` isn't installed (Remotion needs it): `sudo pacman -S npm`.
