# sim-deck

Videos that document how our starship gets built. The starship is the
crew of agents that work together on this machine, and comms-deck is how
they talk. sim-deck turns that work into short explainer videos.

The first video: **what comms-deck is and how it works**.

Personal project. Code only: no notes, keys or machine data go in here.

## How a video gets made

1. **Brief.** A short text file says what the video explains and who it's for.
2. **Script.** Scenes, each with its narration line and the picture that goes with it.
3. **Data.** `feed/sample-deck.py` reads comms-deck's live state (seats, context
   split, who is working) as JSON frames, so scenes show the real deck and not mock-ups.
4. **Scenes.** [Remotion](https://www.remotion.dev) (React → video) draws each scene from the
   script and the data.
5. **Checks.** A rulebook is checked before anything renders: timing, every line has a
   picture, nothing private on screen. A contact sheet of stills is made for review.
6. **Render.** One command renders locally. A person watches it before it's posted.

See [PLAN.md](PLAN.md) for the build order and who does what.

## Layout

```
feed/       live deck data for the scenes (Vibe)
video/      the Remotion project (Claude)
checks/     the rulebook and the contact sheet (Devin)
briefs/     one brief per video
```

## Licence note

Remotion is free for individuals and small teams. This is a personal project, so
that's us. Check again if that ever changes.
