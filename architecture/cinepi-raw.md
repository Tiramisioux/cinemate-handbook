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
preserve or relocate the explanation, don't just delete it. cinemate's half of it is
`_buffered_frames_flushing()`, and it now gates two things rather than one: the record
trigger, and a deferred dynamic-resolution mode change that would relaunch cinepi-raw — the
relaunch is a SIGTERM, and firing it while the drain is still running truncates the take that
just ended.

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

## Output depth: why the sensor mode, not the pixel format, decides it

The single most misleading thing about the DNG writer is that **the Bayer
format's own bit count does not tell you how many bits are real.** On a Pi 5,
libcamera's PiSP pipeline handler cannot emit a raw stream in anything but an
unpacked 16-bit container — *"We cannot output CSI2 packed or non 16-bit output
from the frontend"* (`pipeline/rpi/pisp/pisp.cpp`) — so a 10-bit mode, a 12-bit
mode and a genuine 16-bit ClearHDR mode all arrive as `SRGGB16`. The sensor
mode's depth is the only thing left that says how many of those bits carry
signal, and the significant bits are **MSB-aligned**, so the container must be
shifted down by `container - sensor_depth` before packing.

On a Pi 4 / VC4 none of this applies: rows arrive at their native depth
(`SBGGR10`/`12` and their `_CSI2P` forms), already right-justified or
CSI2-packed, and must be left alone. That is why the rule tests `bf.bits == 16`
rather than treating it as a given.

`cinepi/dng_output_depth.hpp`'s `resolve_dng_output_depth()` is the whole rule,
pulled out as pure logic so the truth table over
`(container, sensor depth, trusted, packed, compressed)` can be tested without
a live `Camera` — the same split, for the same reason, as `ccmp_gate.hpp`. It
is the **single writer** of `dng_info.bits`/`white` on the linear path; the
CCMP decompand and CineMate Log override afterwards, in that order, and the log
path clears both pack flags outright because `log_lut_` owns the row
conversion. `tests/dng_output_depth_test.cpp` pins it.

Three properties of the rule are load-bearing:

- **The asymmetry.** Packing down further than the data justifies destroys real
  bits; packing down less just stores known-zero padding. Every guard fails
  toward the larger file, and an unrecognised depth (0, 8, 14, or anything a
  stray Redis write leaves behind) packs at 12 exactly as it always has rather
  than being derived into an untested file.
- **COMP1 keeps the 12-bit flag.** `dng_save()` dispatches on
  `bayer_format.compressed` *before* either pack flag, and its compressed
  branch reads the 12-bit flag to choose packed-12 over a 2 B/px verbatim
  write. Clearing it there would silently turn every COMP1 take into a 16-bit
  file. 10-bit is excluded from COMP1 instead — deliberately, because COMP1's
  dequantisation emits non-multiples of 64 in three of its four quantisation
  modes, so a 10-bit repack would discard detail a 12-bit one keeps, and that
  trade has never been measured. Reachable on imx519, which cinemate launches
  with packing `P` on Pi 5.
- **Everything downstream is already depth-generic.** Tag 258, `WhiteLevel`,
  `StripByteCounts`, the buffer sizing, the RAM pool and the per-channel black
  rescale all derive from `dng_info.bits` — which is why adding a depth is a
  decision plus a packer plus a branch, and nothing else.

Native 10-bit modes were written as 12-bit until 2026-09-15: a file
byte-identical in size to the same resolution at 12-bit, carrying two fewer
stops. At 3840×2160 the fix saves 2,073,600 B/frame, 16.7%. See that date's
entry in [`../lessons/hardware-log.md`](../lessons/hardware-log.md) for the
hardware confirmation, for how the MSB-alignment question was settled from
libcamera source rather than from a take, and for the in-file second opinion
(the IFD1 thumbnail is an ISP render that never touches the packing path) that
distinguishes "the packer is wrong" from "the shot was overexposed".

## The embedded thumbnail (IFD1)

Every DNG can carry a second image alongside the raw frame: an uncompressed 8-bit thumbnail
(mono or RGB) at the lores stream's own size, chained as a second IFD (IFD1) right after the
raw frame's IFD0. IFD0 itself is untouched by this — same bytes, same offset, same next-IFD
field left at 0 whenever the thumbnail is off or the lores stream is unavailable, which is what
makes "off" a genuine no-op rather than a smaller version of "on".

The geometry — width, height, samples per pixel, and the byte count that follows from them —
lives in one place, `cinepi/dng_thumbnail.hpp`'s `thumbnail_geometry()`. `setup_encoder()` calls
it to size the take's buffer reservation; `dng_save()` calls it again to get what it actually
writes into IFD1, so the two cannot silently drift apart the way two separately-computed copies
of the same formula once could. cinemate mirrors the same formula in Python,
`sensor_detect.thumbnail_plane_bytes()`, for its own `file_size` / minutes-remaining estimate —
see that function's docstring for the argument-order difference between the two.

Two Redis keys govern it, with different lifetimes:

- `thumbnail` (0 off, 1 mono, 2 colour) is a **per-take snapshot**: `setup_encoder()` reads
  `options_->thumbnail` once, at the first frame of each take, and holds it for the whole take
  even if the key changes mid-recording. This is deliberate, not an oversight — two encode
  workers racing a live value mid-take could otherwise write one take with a non-monotonic mix
  of thumbnail/no-thumbnail frames. A `set thumbnail` therefore always takes effect on the
  *next* take, never the current one.
- `thumbnail_size` (0–12, a right-shift of the lores plane) is **boot-seeded**: CineMate seeds
  it from `image_capture.thumbnail_size` before cinepi-raw launches, and cinepi-raw's own
  handler restarts the camera on any live change — a mid-take reconfigure would invalidate the
  buffer `setup_encoder()` already sized against this take's snapshot.

The shipped default is **colour at shift 1** — 640×360, 691,200 B per frame, +5.6% on a 4K
12-bit frame and +4.0% on 4K 16-bit ClearHDR. That figure moved twice on 2026-09-13 before it
settled, and the reasoning is worth keeping because the two sizes are not equivalent in kind: an
interim quarter-size default (320×180, 172,800 B) made colour cost *fewer* bytes than mono at
half size, which flattened the choice into a free one; half size restores a real trade-off, with
colour costing three times mono at the same size. Half won on what the thumbnail is actually
for — 320×180 is small for judging a take in the Playback pane, which is the pane's only path to
a picture. Mono (`set thumbnail mono`) is the lighter opt-in at a third of the bytes. Shift 0 (the full
lores plane, no downscale) in colour was measured at up to +89% per file, which is what
CineMate 3.4 actually shipped with until this was fixed. See the 2026-09-13 hardware-log entry
in [`../lessons/hardware-log.md`](../lessons/hardware-log.md) for the measurements this default
is built on, and the entry immediately above it (2026-09-05) for why
the mode toggle had stopped reading `options_->thumbnail` at all in the meantime.

### A fourth mode: colour JPEG

`thumbnail` 3 (`jpeg`) reads the same lores plane and converts it to RGB the same way colour
(2) does, then hands each row to libjpeg as a baseline JPEG (YCbCr 4:2:0, quality 85 —
`kThumbnailJpegQuality` in `dng_encoder.cpp`, chosen from the three quality settings actually
measured) instead of writing the raw bytes. `cinepi/dng_thumbnail.hpp` is still the single
source for this: `thumbnail_geometry()` grew a `compressed` field, and its tag emission moved
into a new pure function, `add_thumbnail_ifd1_entries()`, which `dng_save()` now calls for
every mode instead of building IFD1's tags inline the way it used to. IFD1's tag layout differs
only for mode 3: compression 7 instead of 1, photometric 6 (YCbCr) instead of 2 (RGB), and two
extra tags a JPEG-encoded strip needs (530 YCbCrSubSampling, 531 YCbCrPositioning). The three
uncompressed layouts (0, 1, 2) are byte-identical to what `dng_save()` wrote before this mode
existed.

`thumbnail_geometry()`'s `bytes` field means something different for mode 3. For the
uncompressed modes it is the strip's exact size, always. For JPEG it is a **reservation**, not
an estimate: the same uncompressed-worst-case number colour would need at that geometry, which
`setup_encoder()` sizes the take's buffer against and `dng_save()` checks the actual encoded
size against before ever writing the strip — skipping the thumbnail for that one frame (one
warning per take, IFD0's next-IFD field left at 0, same as `thumbnail=0`) if a pathological
frame somehow does not fit, rather than letting `write_pod()` throw and drop the whole frame.
cinemate's `sensor_detect.thumbnail_plane_bytes()` mirrors this reservation formula for modes
0–2, but for mode 3 it carries its own, separately-named **estimate** constant instead
(`THUMBNAIL_JPEG_BUDGET_BYTES_PER_PIXEL = 0.15`, deliberately above the measured 0.04–0.08 B/px
range) — the reservation and the file-size estimate are different quantities that happen to
share a source measurement, and conflating them would either waste buffer headroom on every
take or under-count `file_size` on every one that uses JPEG.

Colour JPEG is the smallest file of the four by a wide margin — measured 9–16 KB per frame at
the shipped 640×360 default, ~3–8 KB at 320×180, against 230,400 B / 57,600 B for mono at the
same sizes (FINDINGS.md §2b, `development/dng-thumbnail-cost/`) — but the highest CPU per
frame: the same YUV→RGB conversion colour already pays, plus the JPEG encode itself. That is
why it stays an opt-in (`set thumbnail jpeg`, or `image_capture.thumbnail: "jpeg"`) rather than
the default: processor headroom is this camera's stated constraint, and colour (2, uncompressed)
does not spend any of it. See `docs/settings-json.md`'s "DNG thumbnails" section (cinemate repo)
for the full four-way cost table and how-to-choose guidance.

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
being touched. Neither the static post-process file nor the dual-sensor one
Cinemate writes names the stage; `EnsureFirstPostProcessingStage` inserts it,
so it runs on defaults unless a file overrides it.

### The clamp zone, and why the preview needs a second correction (both bit depths)

Decompanding fixes the *transfer* but cannot un-clip, and the second half is
easy to mistake for the first. In 12-bit ClearHDR the HG/LG merge clamps
**digitally**, and the channels **converge** as it does — a blown area arrives
with R, G and B on very nearly the same code. An equal-code quad is exactly
what the preview renderer cannot pass through cleanly: under the shipping gains
and CCM, green solves NEGATIVE for one at *any* level, clamps to 0, and the
pixel is magenta. So the whole convergence zone renders magenta even though the
decompand is working perfectly, which is why "highlights magenta, mid-tones
correct" means the clip correction, **not** a missing decompand.

`ccmp_preview.hpp`'s `desaturateHighlight()` blends such a pixel to neutral so
blown reads as white. Two properties of its anchor are load-bearing and were
each wrong in a shipped build:

- **It anchors on the FLOOR of the clamp zone, not the peak code.** The zone is
  soft; its body sits 60–80 codes below the highest code the sensor emits. The
  ramp ends *at* the anchor, so anchoring near the peak leaves the body
  desaturated by nothing.
- **It is per binning.** The compander runs on `b*L` and divides back by `b`,
  so the same physical clamp lands on a different code per binning (~2900 at
  b=1, ~2582 at b=4). The anchor therefore lives in `CcmpAnchor::clip_code` in
  `ccmp_lut.hpp`, beside the `T1` anchor that is already per binning for the
  same reason. A single shared value fixes full res and leaves HD magenta.

`CcmpPreviewColour::sensor_clip_code` is only an override (0 = use the table's
anchor), exposed as `sensorClipCode` in the post-process file.

**Reading the stage's log line.** It prints `peak raw code`, `highest
uncorrected`, and a count of fully-desaturated quads. `highest uncorrected` is
the one that answers the question: with the anchor placed correctly it sits
just *under* the anchor (e.g. `highest uncorrected 2581` against `clip anchor
2582`); when it tracks the frame peak instead, the anchor is too high and blown
areas are still magenta. The peak alone cannot distinguish those two states —
see the 2026-09-06/07 entry in [`../lessons/hardware-log.md`](../lessons/hardware-log.md),
where it made two bad anchors look correct.

**16-bit is not unaffected — that was true at one gain, not in general.** The
same HG/LG merge clamp happens with no compander involved: 16-bit ClearHDR is
delivered linear, so there is nothing to decompand, but the sensor still
clamps digitally and the four Bayer samples of a blown quad still converge on
one code. Under the shipping white-balance gains that equal-code plateau
overshoots on R and B while G cannot move, and the highlight renders pink —
the same cast as 12-bit's magenta, from the same mechanism, just with no
compander in the middle. Confirmed 2026-09-13: two operator takes, 13 minutes
apart, same mode/blend/gain-adder/shutter, plateaued at raw code 54100 at
analogue gain code 71 and at 48600 at code 80 — **the clamp code moves with
gain**, so unlike 12-bit it cannot be a per-binning table entry; a table keyed
on the wrong axis would be right at one ISO and wrong at the next. See that
date's entry in [`../lessons/hardware-log.md`](../lessons/hardware-log.md) for
the full diagnosis, and the entry after it for the fix's hardware verdict.

Two different mechanisms were built to address the same defect, one per bit
depth, the difference following from whether there is a compander to re-render
through. Only one of the two is still in the tree:

- **12-bit** re-renders the lores frame from the raw Bayer through
  `CcmpPreviewRenderer` (decompand, then white balance, CCM and gamma), and
  `desaturateHighlight()` blends toward neutral using the **tabulated**
  per-binning anchor described above.
- **16-bit** has **no correction in the tree at all** — see the status note
  below. It keeps the ISP's own render, unmodified.

### Status as of 2026-09-15: read this before trusting anything above

This section is deliberately a status note rather than a rewrite, because the
work it describes is **parked, not finished**, and the next person to pick it
up needs to know what was tried as well as what survives.

**What is in the tree on `dev`/`main`:**

| | correction code | operator's verdict on the preview |
|---|---|---|
| **12-bit** ClearHDR | **present** — `CcmpPreviewRenderer`, `desaturateHighlight()`, `CcmpAnchor::clip_code`, `sensorClipCode` | *"doesn't really work now"* |
| **16-bit** ClearHDR | **absent** — reverted | *"works"* |

That is the inverse of what you would guess, and it is the single most
important fact on this page for anyone resuming this: **the mode with the
correction is the one that looks wrong, and the mode without it looks fine.**

An earlier version of this page described a 16-bit stack —
`clip_neutralise.hpp`'s `HighlightNeutraliser`, `clip_plateau.hpp`'s
`ClipPlateauDetector`, a per-frame measured anchor, a `clip_convergence.hpp`
quad test, and a "shadow mode" detector feeding the 12-bit path. **None of
those files exist any more.** They were backed out by five reverts and no
reference to them remains in `cinepi/`. If you are reading this page in a
cached form that still describes them, check the source first: the page was
wrong for some days before an unrelated change happened to read it.

**What the evidence supports, and what it does not.** The 2026-09-14 entries
in [`../lessons/hardware-log.md`](../lessons/hardware-log.md) establish that
the HG/LG merge clamps at a hard ceiling around 55–59% of the container, and
conclude that correcting the preview "can only choose what colour the plateau
is painted" — i.e. that this is a sensor-level limit, not a rendering one.
That conclusion predicts **both** modes looking wrong, so it does not by
itself explain the 12-bit/16-bit split in the table above. **That split is an
open question**, not a settled mechanism; do not assume the prior explanation
covers it. See the 2026-09-15 entry for the audit behind the table.

The 12-bit description that precedes this note (the decompand, the per-binning
`CcmpAnchor::clip_code`, the floor-of-the-clamp-zone anchoring, the log-line
falsifier) still describes code that is present and is still the right reading
of how that path is built. Whether it is doing any good is the open question.

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
