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

## ClearHDR: sensor HDR, live knobs, and the CCMP12 decompand

`--hdr off|auto|sensor|single-exp` (`cinepi_options.cpp`) selects sensor HDR
at launch. On imx585/imx708, `auto`/`sensor` is ClearHDR — it switches the
sensor to its 16-bit-linear HDR mode list, which requires a 12-bit camera
mode (`--mode ...:12:P`; AE/AWB gate on 12-bit sensor stats and stop working
above that).

`core/options.cpp`'s `set_subdev_hdr_ctrl()` walks every `/dev/v4l-subdevN`
looking for `V4L2_CID_WIDE_DYNAMIC_RANGE`, writes it, and **confirms the
readback** rather than trusting the write call alone. If the sensor hasn't
confirmed within 4 retries at 50ms, cinepi-raw now **throws and refuses to
launch** — `"imx585/imx708 ClearHDR: sensor did not accept
wide_dynamic_range=1 after retrying"` — rather than silently proceeding with
the sensor's WDR combiner still off. That silent-proceed case was the
invalid-combo defect (the driver serving a BLC pedestal fill while cinepi-raw
believed ClearHDR was engaged) the ClearHDR stabilization work closed; see
[`../lessons/hardware-log.md`](../lessons/hardware-log.md) for that
investigation if the failure mode is unfamiliar. This hard-refusal is new
behavior with no precedent in older builds — a rig that used to silently
record pedestal fill now hard-fails at launch instead.

Once launched, four knobs apply live over Redis with no restart —
`hdr_threshold_low`/`hdr_threshold_high` (HG→LG data-selection thresholds,
0..4095), `hdr_blend` (HG/LG blend mode, driver menu index) and
`hdr_gain_adder` (LG gain adder menu index) — handled in
`cinepi_controller.cpp`'s Redis callback map. Only the mode switch itself
(`--hdr`) needs a process restart, because it changes the sensor's mode
list; these four don't. See [`redis-contract.md`](redis-contract.md) for the
exact key names.

imx585's 12-bit ClearHDR path (the mono/binned variant) companders on-sensor:
the 16-bit-linear signal goes through a three-segment piecewise-linear curve
before a 12-bit code comes out. Written straight to a DNG as if linear, that
data renders with the mid-tones crushed magenta — the defect is the transfer
curve, not gain. `dng_encoder.cpp` embeds a `LinearizationTable` (built in
`ccmp_lut.cpp`, gated by `ccmp_gate.hpp`) that undoes this inside the file, so
a converter reading it sees linear data with no post step needed. The gate is
exactly "ClearHDR on AND a *trusted* 12-bit sensor mode" — 16-bit ClearHDR
never companded, and a 12-bit SDR mode never companded either, so gating on
bit depth alone would decompand data that was never companded. "Trusted"
matters because a mode-mismatch on this hardware has produced a 12-bit
request landing on the real 16-bit sensor mode; `ccmp_gate.hpp` refuses the
table rather than mislabel the file when that happened, and falls back to a
loud warning plus uncorrected (magenta) linear 12-bit output instead.

`ccmpPreviewStage.cpp` applies the same decompand to the lores buffer in
place, inserted at the front of the post-processing chain, ahead of both
preview stages — so HDMI, MJPEG, and the DNG thumbnail (which reads the lores
stream) all inherit the fix for free without any of those three consumers
being touched.

## CineMate Log (`--log-encode`)

`--log-encode [10|12]` (bare flag defaults to 12; the token grammar is parsed
once in `log_encode_arg.hpp`, unit-tested directly in
`tests/log_encode_arg_test.cpp`) re-encodes recorded DNGs through a log curve
(`log_lut.hpp`) at launch. It's resolved in `dng_encoder.cpp`, the one place
that already knows both the source bit depth and whatever CCMP decompand is
in play, because the two compose: a 16-bit ClearHDR or 12-bit SDR stream is a
valid log source directly, but 12-bit *companded* ClearHDR is only a valid
source via composition — decompand to 16-bit linear FIRST, then apply the
log curve; there is no such thing as a linear log curve fit to the companded
12-bit domain itself. Today only `--log-encode 10` has a composed spec for
the CCMP case; requesting `12` on a companded source refuses with an explicit
error rather than emit an unmeasured file.

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

`--max-pixel-rate` (`core/options.hpp`/`.cpp`, an upstream `rpicam-apps` option) is the other
RPi-fork dependency worth knowing: `Options::Parse()` sets
`LIBCAMERA_RPI_MAX_PIXEL_RATE` from it before `initCameraManager()` runs, the only channel
into the forked libcamera IPA's PiSP pixel-rate ceiling — nothing later can change it, and
cinepi-raw never computes the value itself. cinemate's `rp1_regime.py` derives it from
whichever RP1 clock regime the board actually booted at (passed, not probed — the
`rp1-overclock` overlay's requested 300MHz and the achieved 333.33MHz clock disagree, and a
CM5 on this kernel has no `/proc/device-tree` node to read the real clock from anyway) and
passes it down through `cinepi_multi.py`. Setting it above what the hardware can actually
drain corrupts wide sensor modes silently — the option's own help text says so.

## Further reading

- [`redis-contract.md`](redis-contract.md) — the key contract cinepi-raw and cinemate share.
- [`../working/testing.md`](../working/testing.md) — what's unit-testable here and how to run it.
- `system-review/deliverables/CODE-MAP-cinepi-raw.md` — the full line-cited source map this page distills, including what remains untraced (the DNG writer internals, `cinepi_sound.cpp`'s internals, the timing→DNG-tag metadata path).
