# CineMate handbook

This handbook is written for LLM coding agents (Claude Code, or any other AI agent) working
on the `cinemate` + `cinepi-raw` stack — a stable, curated, forward-looking reference to read
before making a change, not a narrative to skim once. A human maintainer can read it too, but
the audience it's optimized for is an agent that starts every session with no memory of the
last one and has to re-derive context from scratch. That's also why it's structured the way
it is: short pages, one topic each, a router at the top — cheap to load only the parts a given
task needs, instead of one long document.

It is not the archive — that is `system-review/` in the `cinemate` repo, a dated record of an
eleven-session audit (193 findings) with line-cited evidence. When a page here would restate a
finding, it links to `system-review/` instead of copying it. See
[`lessons/review-archive.md`](lessons/review-archive.md) for the map between the two.

This handbook is not published by mkdocs — `docs/` is the operator-facing site for humans
using the camera; this is for whatever is next to touch the source, human or agent, including
a future session of you with no memory of this one.

## Read once, before touching anything

- [`orientation/what-this-is.md`](orientation/what-this-is.md) — two programs, one Redis channel, no other interface
- [`orientation/the-traps.md`](orientation/the-traps.md) — the five things that will bite you
- [`orientation/entry-points.md`](orientation/entry-points.md) — where to go, and what else you must update

## Task → page

| I want to... | Read |
|---|---|
| Add or change a Redis key, controller method, or settings key | [`working/changing-a-control.md`](working/changing-a-control.md), then [`orientation/entry-points.md`](orientation/entry-points.md) |
| Change what the HDMI GUI or web GUI shows | [`working/changing-the-gui.md`](working/changing-the-gui.md), then [`architecture/gui-state-model.md`](architecture/gui-state-model.md) |
| Change the installer or a systemd service | [`working/changing-the-installer.md`](working/changing-the-installer.md) |
| Run or add tests, understand what needs a Pi | [`working/testing.md`](working/testing.md) |
| Run a deterministic hardware verification session | [`working/hardware-session.md`](working/hardware-session.md) |
| Understand how cinemate boots and threads | [`architecture/cinemate.md`](architecture/cinemate.md) |
| Understand cinepi-raw's capture loop and DNG/audio pipeline | [`architecture/cinepi-raw.md`](architecture/cinepi-raw.md) |
| Understand the Redis `cp_controls` contract between the two repos | [`architecture/redis-contract.md`](architecture/redis-contract.md) |
| Understand how the four UI surfaces relate | [`architecture/gui-state-model.md`](architecture/gui-state-model.md) |
| Match the existing code style before a PR | [`conventions/style.md`](conventions/style.md) |
| Understand the project's own design principles (and where it violates them) | [`conventions/philosophy.md`](conventions/philosophy.md) |
| Understand CI, and add a new automated check | [`conventions/checks-and-ci.md`](conventions/checks-and-ci.md) |
| Judge whether a claim needs hardware to settle | [`lessons/what-the-pi-taught-us.md`](lessons/what-the-pi-taught-us.md) |
| Find the original finding behind a citation like `F-204` | [`lessons/review-archive.md`](lessons/review-archive.md) |

## The one rule that generated this handbook

**Duplicated truth stops agreeing.** The system review that produced this handbook found the
same fact written down twice, drifting, thirty-nine separate times. That is why this handbook
is its own repo instead of a copy baked into an agent's skill prompt: a skill that carries its
own copy of this material drifts from the code within weeks, silently, and nothing would
catch it. This handbook is the one place; the `cinemate-dev` skill that assists development
work on this stack routes here rather than repeating any of it.

If you are updating this handbook because something drifted, also ask whether a check could
catch it next time — see [`conventions/checks-and-ci.md`](conventions/checks-and-ci.md)'s
closing section, "how to add a check."

## A note on paths in this handbook

This handbook lives in its own repository, sibling to `cinemate/`, `cinepi-raw/`, and
`libcamera/` in the local workspace. Paths like `system-review/deliverables/...`,
`src/module/...`, or `.github/workflows/checks.yml` that appear in these pages refer to
files **inside the `cinemate` or `cinepi-raw` repos**, not this one — they are not relative
links you can click through from here.

## A note on line numbers

Several source pages in `system-review/deliverables/` cite exact line numbers. This handbook
deliberately does not — line numbers rot the moment a file changes shape, and nothing
checks them. Where precision matters, this handbook names a function and a file; the shapes
are what matter, not the coordinates.
