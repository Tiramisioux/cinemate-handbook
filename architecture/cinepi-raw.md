# Architecture — cinepi-raw

cinepi-raw is a fork of `rpicam-apps`. Upstream supplies the camera plumbing (`core/`,
`preview/`, `encoder/`, `apps/`); the fork adds `cinepi/`, which is the actual product: a
capture loop that writes CinemaDNG frames, a supervised audio child process, and preview
stages that composite one or two sensors to HDMI. It takes all its runtime direction from
Redis, on the same `cp_controls` channel cinemate publishes to — see
[`redis-contract.md`](redis-contract.md).

## Three binaries, not one

`cinepi/meson.build` produces three executables:

- **`cinepi-raw`** — the main binary: capture, DNG encoding, the preview stages, the
  controller, the Redis bridge.
- **`cinepi-audio-capture`** — a separate, standalone executable, ALSA-only. See "Audio" below.
- A set of unit-test targets (`meson test`), pure-C++ and libcamera-free — see
  [`../working/testing.md`](../working/testing.md).

`apps/meson.build` also builds several inherited upstream binaries (`rpicam-still`, `-vid`,
etc.) whose relevance to a CineMate install is a standing open question, not a settled fact.

## The capture loop

`main()` builds a `CinePIRecorder` app (a subclass of the upstream `RPiCamApp`), parses
options — including a hardcoded `/media/RAW` destination — and enters `event_loop`, which is
the whole program. Each iteration: check for a config change (splitting the current take
first if recording), block for a frame with a timeout, recover from a stalled camera by
stopping and restarting it, process metadata and stats into Redis, handle the recording
start/stop edge, check the RAM guard, encode the frame, and show the preview.

**The RAM guard is a hard stop, not a warning.** If the DNG encoder's buffer fills, recording
is force-stopped and a warning is logged — this is the mechanism referenced whenever
resource-headroom arguments come up (see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md)'s note on
measuring before arguing from resources).

**A load-bearing comment worth knowing about, even paraphrased:** the encoder explains why
nothing is dropped when a take starts while the previous take is still flushing — cinemate
blocks the record trigger while the previous take's write buffer is still draining, so by the
time a new start edge arrives, the RAM buffer is already empty. That is a real cross-repo
interlock, and it is documented only in that one comment — if you touch either side of it,
preserve or relocate the explanation, don't just delete it.

## Frame lifecycle

`libcamera` delivers a completed request → `event_loop` reads metadata and stats into Redis
→ the frame is handed to the DNG encoder, which queues it, runs it through a thread pool,
writes to a per-take disk buffer through a second thread pool, and produces CinemaDNG files
in the take folder. A single atomic counter tracks frames from capture through written-to-disk
— this is what both the RAM guard and cinemate's write-buffer indicator ultimately read.

The DNG writer itself has been substantially rewritten across recent history — don't trust a
cached mental model of its internals; read the current file if you're changing pixel packing
or metadata behavior. See [`../working/testing.md`](../working/testing.md) for what part of
this *is* unit-testable (the packing helpers) and what genuinely needs a live take.

## Audio — a supervised child process, not a thread

This is the part most likely to surprise a newcomer: **audio capture happens in a separate
process**, not a thread inside the main binary. The main binary's audio supervisor locates the
`cinepi-audio-capture` executable (checking a few candidate paths in order) and launches it,
then tears it down with a **pattern-based `pkill`** rather than tracking the exact child PID —
fine on a single-camera rig, less obviously safe with two `cinepi-raw` instances running.
`cinepi-audio-capture` itself depends only on ALSA and runs at an elevated real-time priority,
above the DNG encode threads.

The VU-meter contract back to cinemate (`audio_vu`) is a hand-duplicated key name on both
sides — see [`redis-contract.md`](redis-contract.md).

## Preview and display ownership

Three preview stages self-register: an MJPEG preview, a dual-HDMI composite stage, and a
shared-context stage. **DRM master is exclusive per GPU**, and cinepi-raw's own dual-HDMI
code states the constraint and its workaround explicitly: a second `cinepi-raw` process (for
a second sensor) is forced to `--nopreview` and instead publishes its frame into shared
memory for the primary process to composite — it never touches DRM itself. See
[`../orientation/the-traps.md`](../orientation/the-traps.md) #4 and
[`gui-state-model.md`](gui-state-model.md) for how this bears on the on-camera GUI, which
reaches the display through a different kernel interface (the legacy fbdev node) and was
hardware-confirmed to hold its own DRM plane independent of cinepi-raw's preview.

## Dependency on the forked libcamera

Not audited in depth by the system review — noted, not traced. cinepi-raw uses Raspberry-Pi
vendor controls (`controls::rpi::ScalerCrops`, `controls::rpi::StatsOutputEnable`) that are
not part of upstream libcamera and tie the build to the RPi fork; the zoom/crop path depends
on `ScalerCrops` semantics surviving any libcamera version bump.

## Further reading

- [`redis-contract.md`](redis-contract.md) — the key contract cinepi-raw and cinemate share.
- [`../working/testing.md`](../working/testing.md) — what's unit-testable here and how to run it.
- `system-review/deliverables/CODE-MAP-cinepi-raw.md` — the full line-cited source map this page distills, including what remains untraced (the DNG writer internals, `cinepi_sound.cpp`'s internals, the timing→DNG-tag metadata path).
