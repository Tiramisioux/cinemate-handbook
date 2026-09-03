# What this is

Read this first. Everything else in the handbook assumes it.

## Two programs, one camera

**cinepi-raw** (C++, a fork of `rpicam-apps`) is the capture engine. It drives the sensor,
writes CinemaDNG frames, owns the HDMI preview, and runs a second process for audio.

**cinemate** (Python) is everything else: the on-camera GUI, a web GUI, a settings editor, a
CLI, GPIO/rotary/I²C inputs, storage management, and the installer.

## One Redis channel, no other interface

They communicate over Redis, publishing on a channel called `cp_controls`. That channel is
the entire contract between them — see [`architecture/redis-contract.md`](../architecture/redis-contract.md)
for the key set and the drift it has already accumulated. There is no RPC, no shared library,
no other channel that matters day to day.

**Neither repository's revision is pinned to the other's, in practice.** `versions.env` exists
so a tested pairing can be recorded, and `cinemate-install.sh` sources it — but both values ship
empty by default, no pairing has ever been filled in, and the day-to-day update path
(`cinemate-update.sh`) doesn't read `versions.env` at all; it just fast-forwards whatever branch
is already checked out. So "which cinepi-raw goes with which cinemate" still isn't answered on a
running system. Their `dev` branches can differ by thousands of lines, including keys in that
shared contract — so when you're debugging a cross-repo symptom, check out `dev` on both sides
before trusting either one's behavior in isolation.

## The rest of this handbook, in one sentence each

- [`the-traps.md`](the-traps.md) — the five things that will bite you regardless of what you're changing.
- [`entry-points.md`](entry-points.md) — for a given change, where the primary edit goes and what else you must update.
- [`../architecture/`](../architecture/) — how each program is built internally, and the shape of the contract between them.
- [`../conventions/`](../conventions/) — how code here is written, what the project believes about itself, and what CI checks for you.
- [`../working/`](../working/) — task-shaped how-to pages for the changes you'll actually make.
- [`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) — how to reason about what you can settle by reading versus what needs the real device.

## Where the deep material lives

This handbook is deliberately thin. The eleven-session system review that produced it did the
heavy lifting — see [`../lessons/review-archive.md`](../lessons/review-archive.md) for the map
into `system-review/deliverables/` if you need more depth than a handbook page gives you.
