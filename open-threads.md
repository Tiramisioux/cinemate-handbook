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

### MODE_1C's `.top` is still 852, where this round's checker expects 784 — deferred 2026-09-27

**What:** `.top` was set to 852 (centred against the active area) on 2026-09-22 and had no
visible effect on the image, because `.top` is metadata rather than a live window for drive
mode 0x30 (see that date's entry in [`lessons/hardware-log.md`](lessons/hardware-log.md)).
This round's checker independently derives an expected value of 784 for the same field.
`.top` was tried at 784 while chasing the `veff` short-frame bug below and reverted once
`veff` turned out to be the actual cause — the revert settles nothing about which of 852/784
is correct, only that neither was the noise bug.

**Evidence:** the 2026-09-22 entry (852, no visible effect on drive mode 0x30); the
2026-09-27 `veff` entry in [`lessons/hardware-log.md`](lessons/hardware-log.md) (784 tried and
reverted alongside `.left`, neither implicated).

**Why deferred:** untested, not refuted — one build and one reboot would settle it, and
neither happened this session.

**What would settle it:** set `.top = 784`, build, reboot once, and stream MODE_1C. If the
picture is unchanged (consistent with `.top` being inert for this drive mode, per
2026-09-22), record that and pick either value as the checker-agreeing default. If it is not
inert, that itself corrects the 2026-09-22 finding and needs its own entry.

### The imx283 `ct_curve` is a two-point calibration — deferred 2026-09-27

**What:** `rpi.awb.ct_curve` — the table `cinepi_controller.initialize_wb_cg_rb_array()`
interpolates every white-balance preset's gains from (see
[`lessons/hardware-log.md`](lessons/hardware-log.md)'s 2026-09-27 entry) — has exactly two
measured points: tungsten, confirmed by eye, and daylight, measured on one scene through one
lens. Every preset between those two Kelvin values is an interpolation between two samples,
not a measurement.

**Evidence:** the gain sweep that fixed the magenta cast (`cg_rb = 1.42, 1.32`) was measured
and confirmed at one colour temperature only; the curve's shape at any other preset has not
been checked against a real subject.

**Why deferred:** needs a grey card and time on the bench, not a code change.

**What would settle it:** shoot a grey card across 2500–7000K through the same lens, measure
`AsShotNeutral` at each step, and rebuild `ct_curve` from the real samples instead of the
two-point interpolation.

### Thirteen `IMX283_ASPECT_MODE_1C` rows are still marked `.experimental`, and the `veff` fix reopens the question — deferred 2026-09-27

**What:** the thirteen `IMX283_ASPECT_MODE_1C()` rows
[`working/repository-and-tooling-traps.md`](working/repository-and-tooling-traps.md)'s
checker fix made newly resolvable were marked `.experimental` while MODE_1C's own `veff`
carried the wrong value (see [`lessons/hardware-log.md`](lessons/hardware-log.md)'s
2026-09-27 entry — MODE_1C read out 638 of 2176 lines). None have been retested since that
fix landed.

**Evidence:** the checker's `n/a`-resolver bug and the `veff` bug were found and fixed in the
same round; neither has been re-run against these thirteen rows since.

**Why deferred:** no further hardware time this session.

**What would settle it:** rerun `check_mode_table.py`/`ratio_audit.py` against the thirteen
rows now that both the checker's resolver and MODE_1C's `veff` are fixed, and stream each on
hardware. Promote whichever pass; whatever stays `.experimental` should name the reason it's
still there rather than carry the flag over by default.

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
