# Open threads

Work that is **known, understood well enough to act on, and deliberately not done**. Every
entry was left open on purpose, by a decision someone can point at — not forgotten, not
blocked on mystery.

This exists because the failure mode of an agent with no memory of the last session is not
forgetting a bug; it is *rediscovering* one. Twice this stack has spent a session
re-investigating something an earlier session had already measured and chosen to defer. An
entry here should be enough to skip straight to the fix, or to decide the deferral still
stands.

It is not a backlog of everything that could be improved, and it is not
[`lessons/hardware-log.md`](lessons/hardware-log.md) — that is a dated record of what
hardware *did*, appended to and never edited. This page is the opposite: short, current, and
entries are **deleted** when they close.

## Entry format

```
### <one-line subject>  — deferred YYYY-MM-DD

**What:** the defect or question, concretely.
**Evidence:** measurements, file:line, or the artifact that shows it. Never "seems to".
**Why deferred:** the actual reason — scope, risk, needs hardware, needs a decision.
**What would settle it:** the cheapest next step, named precisely.
```

If an entry cannot state its evidence, it is not ready to be here; investigate or drop it.
When one closes, delete it and — if hardware taught something durable — add the lesson to
[`lessons/what-the-pi-taught-us.md`](lessons/what-the-pi-taught-us.md) instead.

---

## Sensor / driver

### MODE_1C's centred origin (924) is untested on hardware — deferred 2026-09-26, corrected from 2026-09-22

**What:** `IMX283_MODE_1C_WINDOW_LEFT` selects between two named candidates,
`_HW_CONFIRMED` (236, currently active) and `_CENTRED` (924 = `imx283_active_area.left` (108)
+ (5472-3840)/2). Whether 924 streams cleanly has never been tried on a camera.

**Evidence:** the 2026-09-22 finding below this one — that centring to 856 corrupts the frame
— is **retracted as evidence against centring**, though the measurement itself stands. 856 =
40 + (5472-3840)/2 is centred against `imx283_active_area.left = 40`, the value this same
branch chain later corrected to 108 for being left/top-swapped (`development/imx283-active-
size/ROUND2.md`, Defect 3a; see [`lessons/hardware-log.md`](lessons/hardware-log.md)'s
2026-09-26 entries). 924 is the value that actually follows from the corrected origin, was
derived and named this round (`imx283-v4l2-driver@812c058`), and remains untested — there was
no Pi access in that session.

**Why deferred:** needs a camera and a scene with a recognisable centre, and the old wrong
answer (856) cost a corrupted mode, so this is not a change to make unattended.

**What would settle it:** switch `IMX283_MODE_1C_WINDOW_LEFT` to `_CENTRED` and stream a
scene with a known centre in MODE_1C. If it corrupts the same way 856 did, record that failure
against 924 specifically — do not assume it inherits 856's result, they are centred against
different origins. If it streams cleanly, promote it and retire 236 to the historical
constant.

### `HTRIMMING_END` is written as `crop.left + crop.width + 1` — deferred, long-standing

**What:** mainline's imx283 writes `HTRIMMING_END = crop.left + crop.width`. This fork has
always written `+ 1`. Nobody has established which is right.

**Evidence:** `EXPERIMENTAL_CROPS.md` records it as an open divergence from WP-283-3 onward,
desk-checked and deliberately not changed.

**Why deferred:** the line runs for **every** mode, so a wrong guess moves the horizontal
window on every readout at once rather than on one experimental crop. It needs the datasheet's
exact start/end semantics (inclusive vs exclusive end) or a register read-back, not a
plausible-looking edit.

**What would settle it:** a chart take checked for a one-column miscentre or wrap, or the
datasheet. This was previously listed as a live candidate for an imx283 MODE_2 column
shortfall; that shortfall is now resolved and retracted (the actual cause was
`imx283_active_area`'s `.left`/`.top` being swapped, not this `+1` — see
[`lessons/hardware-log.md`](lessons/hardware-log.md)'s 2026-09-26 entry), so this question is
independent of that one and still needs its own evidence.

### Shading correction is preview-only; DNG lens-shading falloff is still uncorrected by design — deferred 2026-09-26

**What:** the libcamera-side fix (`feature/imx283-shading-tuning`) gives the ISP a real
`luminance_lut`, so the **preview** stops looking artificially flat-lit and starts showing
genuine corner falloff. It does nothing for the DNG: `rpi.alsc`'s table only feeds the ISP's
own processing path, and CineMate's raw DNG is the sensor's Bayer data captured before that
path runs.

**Evidence:** `src/ipa/rpi/controller/rpi/alsc.cpp` applies `luminanceLut` inside the IPA
pipeline; the DNG writer (`cinepi_raw.cpp`'s IFD builder) packs the sensor's raw frame
directly and never calls into libcamera's ISP processing.

**Why deferred:** correcting DNG-side shading needs a per-pixel gain map baked into (or shipped
alongside) the raw pipeline — a different mechanism from an IPA tuning file — and was out of
scope for this round.

**What would settle it:** decide whether DNG-side shading correction belongs in cinepi-raw
(bake a gain map into the unpack/pack step) or stays a post-process step done in the edit, and
update this entry once decided.

### 30 single-row imx283 mode classes remain unmeasured against Round 2's checks — deferred 2026-09-26

**What:** `check_mode_table.py` and `ratio_audit.py` were run against the aspect-ratio mode
families (`IMX283_ASPECT_MODE`/`IMX283_ASPECT_MODE_1C`) this round touched. Thirty single-row
mode classes elsewhere in the driver's mode table were not in that sweep and have not been
checked against either tool.

**Evidence:** `development/imx283-active-size/ROUND2.md`'s scope was explicitly the
aspect-ratio families; the single-row classes are separate table entries the audit scripts
were never pointed at this round.

**Why deferred:** no hardware access this session, and thirty rows is a sweep of its own
rather than something to fold into this round's close-out.

**What would settle it:** point `check_mode_table.py` and `ratio_audit.py` at the remaining
single-row classes and record the result here. Likely a quick pass — the tools now discover
their own rects (see [`working/repository-and-tooling-traps.md`](working/repository-and-tooling-traps.md)) —
but say so once actually run, not before.

### imx585 does not report its active-picture origin — deferred 2026-09-22

**What:** the imx283 driver now exposes `Mode Active Left` / `Mode Active Top`, and
cinepi-raw prefers them when emitting DNG `ActiveArea`. The imx585 does not implement the
pair, so it still falls back to the inference in `cinepi/cinepi_raw.cpp` — 16-bit mode,
vertical padding only, split evenly top and bottom.

**Why deferred:** operator instruction, 2026-09-22: do not touch the imx585. The inference is
correct for its RAW16 families and there was no imx585 attached to verify a change against.

**What would settle it:** an imx585 on the bench. The driver side is a near-copy of the
imx283's: report where the picture starts inside the transport frame, in that frame's own
pixels. Delete the inference branch once it does.

### `HTRIMMING_END` is written as `crop.left + crop.width + 1` — deferred, long-standing

**What:** mainline's imx283 writes `HTRIMMING_END = crop.left + crop.width`. This fork has
always written `+ 1`. Nobody has established which is right.

**Evidence:** `EXPERIMENTAL_CROPS.md` records it as an open divergence from WP-283-3 onward,
desk-checked and deliberately not changed.

**Why deferred:** the line runs for **every** mode, so a wrong guess moves the horizontal
window on every readout at once rather than on one experimental crop. It needs the datasheet's
exact start/end semantics (inclusive vs exclusive end) or a register read-back, not a
plausible-looking edit.

**What would settle it:** a chart take checked for a one-column miscentre or wrap, or the
datasheet. Note this is a live candidate for the MODE_2 column shortfall above — resolve the
two together.

### DNG `ActiveArea` is verified on the UHD mode only — deferred 2026-09-22

**What:** the `Mode Active Left`/`Mode Active Top` controls and cinepi-raw's `ActiveArea`
emission are proven end to end on `IMX283_MODE_1C` (3936x2176, 10-bit). The same path has
**not** been confirmed on the 2x2 full-frame mode (2784x1828, 12-bit), where the expected tags
are `DefaultCropOrigin 48 0`, `DefaultCropSize 2736 1824`, `ActiveArea 0 48 1824 2784`.

**Evidence:** a fresh UHD DNG carries `ActiveArea 0 96 2160 3936`, `DefaultCropOrigin 96 0`,
`DefaultCropSize 3840 2160` — matching the measured layout exactly. The control was read live
as `mode_active_left = 96, mode_active_top = 0`. The 2x2 take was in progress when the Pi
dropped off the network and the session was stopped.

**Why deferred:** hardware became unreachable mid-verification. The mechanism is the same code
path and the same control, and the 2x2 optical-black layout was already measured from a DNG
(columns 0–47 black, rows 1824–1827 zero), so this is confirmation rather than investigation.

**What would settle it:** switch to the 2x2 full-frame mode, record one short take, and read
the tags off a frame — three commands. Note the right-edge column shortfall above will still
be inside `ActiveArea` until that separate defect is fixed.

## CineMate

### Eight tests fail on `dev`, all in the imx585 ClearHDR area — deferred 2026-09-22

**What:** `python3 -m pytest _test/ -q -p no:randomly` on `dev` reports 8 failures. They are
pre-existing and unrelated to the crop-mode work; two others in the same area were fixed
2026-09-22 when the phantom-ClearHDR defect was repaired.

**Evidence:** the same 8 fail at `3e416c64`, before that repair, byte-for-byte. Verified by
checking out that commit in a worktree and re-running. They are:
`test_cinepi_controller_startup_sensor_mode::test_valid_mode_is_kept_unchanged`,
`test_clearhdr_probe_state::test_hdr_only_probe_marks_every_mode_hdr`,
`test_resolution_defaults::test_clearhdr_16bit_driver_binning_is_preserved`,
`test_sensor_database::test_imx585_clearhdr_modes_merged_and_ordered`,
`test_sensor_mode_geometry::test_geometry_on_continuation_line_is_attached_to_previous_mode`,
and three in `test_sensor_modes_endpoint`.

**Why deferred:** each needs deciding whether the test encodes a contract the code has
legitimately moved past, or a real regression. `test_hdr_only_probe_marks_every_mode_hdr`
asserts `_parse_cinepi_output(..., hdr=True)` marks every mode HDR, which the parser no
longer does — that one is likely a stale test. The `test_sensor_modes_endpoint` trio fail
with `KeyError: 'imx585'`, which is a different shape and may be a real fault in the
endpoint.

**What would settle it:** one pass per test, asking only "is the assertion still the contract
we want?". Do not fix them as a batch — they are not one defect.

### The HDMI preview outline is off by one pixel — deferred 2026-09-22

**What:** the white guide rectangle the HDMI GUI draws around the live preview does not
always hug the image exactly; the operator sees it about a pixel too large.

**Evidence:** `simple_gui._calculate_preview_guide_rect()` and `DrmPreview::Show()` use
identical integer arithmetic, and against the running mode's real crop they agree exactly
(image x=95..1823, outline hugging 95..1823). They diverge when the crop used to compute the
lores size differs from the running mode's by one aspect step: 5472/3080 instead of 3840/2160
flips the requested lores width 1280 → 1279, which moves the DRM fit by one pixel. Which
lookup supplies the wrong crop was **not** established — `res_modes[sensor_mode]` is keyed by
mode index, and the index set changes when the enabled aspect ratios change.

**Why deferred:** cosmetic, and the investigation was interrupted by a higher-priority
regression.

**What would settle it:** print the live process's `res_modes[sensor_mode]` alongside Redis
`width`/`height` while a mode is running, and see whether they describe the same mode. A
reconstruction built outside the process is not evidence — it does not apply the same
settings filters, and that produced a false positive once already.

### `sensor_mode` is a position in a filtered list, and the filter now changes — deferred 2026-09-22

**What:** Redis `sensor_mode` and `settings.jsonc`'s saved mode are an **index** into
`res_modes`, which is the *filtered* mode table. The aspect-ratio toggles change which modes
pass the filter, so the same index can mean a different mode after the operator flips a
toggle — or after a driver update changes the mode list.

**Evidence:** not observed misbehaving; found while investigating the preview outline above.
`SensorDetect.load_sensor_resolutions()` sets `res_modes = sensor_resolutions[camera_model]`,
and `get_resolution_info()` indexes it by `sensor_mode`. Reconstructing the table without
settings loaded gives 21 entries and a completely different index→mode mapping than the live,
filtered one — which is exactly how a stale index would present.

**Why deferred:** speculative until someone catches it selecting the wrong mode. Listed
because the aspect-ratio work made the filter operator-controllable, which raises the odds
considerably.

**What would settle it:** flip an aspect toggle that removes a mode earlier in the ordering,
restart, and see whether the camera comes back in the mode the operator left it in. If it
does not, the saved value needs to be a mode *identity* (width/height/depth/hdr) rather than a
position.

## Pi / runtime

### DNG disk workers cannot set their nice level — deferred 2026-09-22

**What:** every take logs `dng-dsk-N: failed to set nice level -5: Permission denied`, once
per worker. The disk-worker priority tuning CineMate passes via `--disk-nice -5` silently
does nothing.

**Evidence:** visible in the settings-editor console and `src/logs/system.log` on the CM5,
across all disk workers.

**Why deferred:** found in passing while fixing something else; not yet confirmed whether it
costs throughput.

**What would settle it:** `cinemate-autostart.service` runs as `pi`, and lowering a nice
value needs `RLIMIT_NICE` or `CAP_SYS_NICE`. The established pattern in this stack is the
`limits.d` drop-in the audio path already uses (`@audio - rtprio 80`, see
[`working/changing-the-installer.md`](working/changing-the-installer.md)) — never `setcap`.
Confirm it matters first by timing a take with and without the priority applied.

## Tooling

### `rpicam-jpeg` / `rpicam-still` reject their own default HDR option — deferred 2026-09-22

**What:** the `rpicam-*` binaries this fork installs refuse to run:

```
ERROR: *** Invalid HDR option provided:  ***
```

The message names an empty value, and `--hdr <anything>` is rejected as an unrecognised
option, so there is no way to satisfy it from the command line.

**Evidence:** reproduced on the CM5 with `rpicam-jpeg --mode 5568:3664:12 -o /tmp/x.jpg` and
with `--hdr off|0|auto`; all four fail identically. `cinepi-raw` itself is unaffected.

**Why deferred:** it blocks a convenient way to grab a single still for verification, but a
short `rec` take through `POST /api/v1/cmd` does the same job, so nothing is actually
unreachable.

**What would settle it:** the HDR option is validated against a set that an empty default
string does not belong to, and the `rpicam-*` apps never set it. Either give it a valid
default or skip validation when the app did not ask for HDR.
