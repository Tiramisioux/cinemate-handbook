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

### WP-585-10 is the default branch's tip and has never been compiled — deferred 2026-09-27

**What:** `cinemate-modes` tip `18c1eb2` adds the 1920- and 2048-wide sensor-window crop
families — 19 new 16-bit Clear HDR entries, plus the SDR and 10-bit families, 96 entries in
`supported_modes[]` where the base branch had 43. It was pushed to `cinemate-modes`, which on
the same day became both the repo's default branch and what `cinemate-install.sh` pins
(`IMX585_DRIVER_REPO_REF`). **No build has ever run against it**, on any host, and no take has
been recorded in any new mode. A fresh clone or a fresh install gets it.

**Evidence:** G2 and G3 pass in software — `tools/replay_mode_table_audit.py` and
`tools/check_window_alignment.py` in the driver repo, run against the pushed tip, report 96
entries and the one pre-existing warning below. G1 (DKMS build) and G4 (hardware) are UNRUN and
were reported as such; the orchestrating host is macOS with no kernel tree, and
`pi@cinepi.local` refused ssh (`publickey,password`). Write-up:
`development/imx585-window-crops-1920-2048/RESULTS.md`.

**Why deferred:** the operator asked for the push knowing both gates were open, twice told.
Desk verification went as far as it can go without a compiler.

**What would settle it:** `free -g`, then `git pull && sudo ./setup.sh` in
`/home/pi/imx585-v4l2-driver`, then `cinepi-raw --list-cameras`. Expect 19 new 16-bit rows (10
at the 1920 window, 9 at 2048). A build failure is the *good* outcome — the three
`static_assert`s exist to catch a mis-ordered table at compile time. Then one take at
1920x1080 1x1 and one at 2048x1080 1x1, checking the DNGs for Bayer-phase shift and a
leading optical-black band. `cinemate-7modes` is untouched at `bd57617` if it has to be
reverted.

### Two entries advertise 3840x2072, so one of them is unreachable — deferred 2026-09-27

**What:** in `supported_modes[]`, index 5 (SDR 1.85:1, window 3840x2072) and index 67 (RAW16
1.89:1, window 3840x2032, which advertises `2032 + 40` = 2072) both advertise **3840x2072**.
`v4l2_find_nearest_size()` takes the first, so the second can never be selected — it appears
in `--list-cameras` and is dead. This is the WP-585-5 / WP-585-8 failure mode.

**Evidence:** `tools/replay_mode_table_audit.py` reports it as its only warning. It is
**pre-existing**, not introduced by WP-585-10 — confirmed by running the same replay against
`git show experimental-cropped-modes-v2:imx585.c`, which reports 43 entries and the same single
warning. Two collisions that WP-585-10 *did* introduce (1920x1080 and 2048x856, both RAW16)
were found the same way and removed before the push.

**Why deferred:** it belongs to WP-585-6, which is merged, and fixing it means deciding which
of the two ratios loses its entry — a framing decision, not a mechanical one.

**What would settle it:** decide whether 1.85:1 SDR or 1.89:1 RAW16 keeps 3840x2072, drop the
other, and re-run the audit to zero. Neither is reachable today, so no capture regresses.

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

### Nobody has confirmed the 16-bit Clear HDR fix reached the camera — deferred 2026-09-27

**What:** 16-bit Clear HDR modes were absent from the settings pane; the cause was a
parse-time drop, fixed on `dev` by `0e6899e7` (2026-09-25). Whether the camera is *running*
that commit was never established, so the original symptom may still be live on the unit.

**Evidence:** the fix is verified against the operator's own capture. Replaying
`development/todo-2026-09-20/captures/{plain,hdr}-probe-extracted.txt` through current `dev`
with the shipped `settings.jsonc` yields 4 sixteen-bit rows (3840x2200@21, 1920x1120@57,
1280x760@83, 1920x1100@30) where the live API at capture time returned 31 rows,
`available.bit_depths: [10,12]`, and no 16-bit mode at all. `_available_mode_categories()`
derives that from `sensor_modes_unfiltered`, so even the unfiltered table had none — which
rules out every filter-side explanation. `pi@cinepi.local` refused ssh from two sessions, so
the deployed commit was never read.

**Why deferred:** needs Pi access, and the fix being two days old at the time makes "the unit
is simply behind `dev`" the most likely answer — a deploy, not a code change.

**What would settle it:** on the camera, `git -C /home/pi/cinemate log --oneline | grep -c
0e6899e7`. If 0, deploy `dev` and re-check the settings pane. If 1 and 16-bit is still missing,
there is a second gate nobody has found — read the live `settings.jsonc` first, since a
non-empty `aspect_ratios`, a narrowed `k_steps` or an `enabled_modes` entry for imx585 would
each hide the same rows *after* the parse and look identical to the operator. Then use the
offline replay in [`working/testing.md`](working/testing.md) to localise it.

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

**Largely addressed, 2026-09-27 — kept open only for the hardware check.** The mechanism this
entry asked for now exists. `_remember_sensor_mode()` (`cinepi_controller.py`) writes a
per-sensor `SENSOR_MODE_MEMORY` entry carrying both the index and a *signature* of the mode
(width/height/depth/hdr), and `_get_stored_sensor_mode_for_current_sensor()` prefers the saved
index **only while its signature still matches**, resolving by stored geometry otherwise —
i.e. the saved value is now a mode identity with a position as a fast path, which is exactly
what the line below asks for. Landed in `3a6606ce` and `ce0ac5c1`. Read by desk inspection
while fixing a stale test that asserted the valid-mode path writes nothing at all; it writes
the memory key, which is the point.

**What would settle it:** the experiment is unchanged and still unrun — flip an aspect toggle
that removes a mode earlier in the ordering, restart, and see whether the camera comes back in
the mode the operator left it in. Delete this entry when it does.

### Only the aspect ratios a sensor can actually produce should be offered — deferred 2026-09-27

**What:** `available_aspect_ratios()` in `sensor_detect.py` returns an entry for **every** ratio
in the canonical table whenever the camera has any mode with a known aspect, because the
`best_mode` search has no tolerance gate — only a nearest-match. Ratios with nothing within
`ASPECT_RATIO_TOLERANCE` come back `exact: false` and the settings pane draws them dashed and
italic rather than omitting them. The operator's request is that they not appear at all.

**Evidence:** `available_aspect_ratios()`'s loop keeps a `best_mode` for each table entry and
`continue`s only when the camera has no aspect-bearing mode whatsoever; `exact` is computed
afterwards and never filters. Operator report 2026-09-27, "I should only see the aspect ratios
offered by the sensor".

**Why deferred:** a peer session was committing into this exact matcher while the batch ran —
`75a3ab4b` ("Default a fresh camera to its full frame plus 1.78-or-closest") and `ce0ac5c1`
("Keep a saved mode selection across a driver geometry change") landed mid-investigation. Two
agents rewriting one matcher is how this stack loses work.

**What would settle it:** decide whether "offered" means `exact` only, or `exact` plus the
full-frame entry (which is deliberately `exact: true` while being off-table — see
`full_frame_ratio()`), then gate the result. Check `_default_ratio_ids()`'s guarantee that no
camera loses its whole table still holds afterwards, and that the pane's "zero available ratios"
no-op path is reachable.

### The resolution dropdown and the settings-editor mode table can disagree — deferred 2026-09-27

**What:** the web GUI's dropdown is fed `get_available_resolutions()` (post-filter) while the
settings editor's table is the unfiltered driver catalogue from
`/settings-editor/api/sensor-modes`. Some divergence is by design — `enabled_modes`,
aspect-ratio matching, `k_steps`, `bit_depths`, `min_mode_width` all narrow the dial
deliberately — but the operator reports a mismatch they cannot account for, and at least one
parser defect behind it was never confirmed fixed.

**Evidence:** operator report 2026-09-27. `development/todo-2026-09-20/SENSOR-MODE-FINDINGS.md`
Finding 3: a continuation line's own crop annotation (`(0, 0)/3840x2160 crop binning 1x1`)
contains a `WxH`-shaped substring the parser reads as a second mode's resolution. Never fixed —
that worker was stopped mid-correction. Finding 1 from the same document (16-bit ClearHDR modes
dropped by the slice-and-reparse) **is** now fixed: `detect_camera_model()` passes
`hdr=True, clear_hdr_section=True` and `_parse_cinepi_output` carries
`line_hdr = current_hdr or current_bit_depth == 16`.

**Why deferred:** same peer-session collision as the entry above.

**What would settle it:** re-run the offline reproduction against the surviving captures in
`development/todo-2026-09-20/captures/` — they are verified free of the SSH wrapper's echoed
command line and need no camera — and diff parsed mode counts against
`sensors-modes-api-response.json` taken at the same moment.

### Per-sensor `config.txt` knowledge lives in bash where Python cannot read it — deferred 2026-09-27

**What:** which `camera_auto_detect` value and which extra overlay parameters a sensor needs is
written only in `cinemate-install.sh`'s `resolve_sensor_overlay()` `case` statement.
`boot_config.py` and `templates/settings_editor.html` need the same facts and each carried their
own copy, which had silently drifted both ways (see
[`lessons/hardware-log.md`](lessons/hardware-log.md), 2026-09-27).

**Evidence:** the drift itself, found by diffing the installer's output against
`_render_camera_section()`'s: `auto_detect` hardcoded `1` for every sensor, `ccmp` never emitted.
Both fixed, and `_test/test_boot_config_installer_parity.py` now gates the agreement — but by
comparing two copies, not by removing the duplication.

**Why deferred:** the durable home is `resources/sensors.json`, which both sides already read for
link frequencies via `sensor_database.py`. Moving it there needs the installer to gain a
`python3 -c` JSON-reading shim, which touches its own tests and its idempotency guarantees —
larger than the branch that found this should carry.

**What would settle it:** add `camera_auto_detect` and an overlay-parameter list to each sensor's
`sensors.json` entry, read them from both sides, and keep the parity test as the ratchet while
the bash side migrates.

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

### The Pi's libcamera checkout carries work that exists nowhere else — deferred 2026-09-27

**What:** `/home/pi/libcamera` has tracked modifications that are not on any branch, in any
repo, on any other machine. A sync worker stopped rather than fast-forward over them, which
was the right call and is how they were found at all.

**Evidence** (reported by the sync worker on 2026-09-27; the Pi went off the network before
this could be re-verified first-hand, so treat the line counts as reported, not measured):

| path | state |
|---|---|
| `src/ipa/rpi/controller/controller.cpp` | genuine uncommitted edit — a live 580 MHz overclock |
| `src/ipa/rpi/pisp/data/imx585.json` | ~1008-line uncommitted rewrite |
| `src/ipa/rpi/pisp/data/imx283.json` | working tree matches the trunk; only the *index* holds a stale staged blob |
| `src/ipa/rpi/vc4/data/imx283.json` | staged content already matches the trunk |

**Why it matters more than it looks:** the imx283 tuning landed this round is safe — the
working tree already matches `tiramisioux/cinemate`. The other two are not. The overclock in
`controller.cpp` is presumably what makes the current link rates work, and losing it would
change behaviour in a way nobody would connect back to a `git checkout`. Neither file is
backed up anywhere.

**Why deferred:** committing somebody's live tuning work without knowing what it is, or why
it was never committed, is not a decision a sync pass gets to make.

**What would settle it:** on the Pi, `git -C /home/pi/libcamera diff` each file and decide
per file — commit to a branch on the fork, or discard deliberately. Until then the Pi is the
only copy, and `git checkout`/`git pull` there can destroy it silently. Note the stale index
entry on `pisp/data/imx283.json` separately: `git checkout-index` or a plain `git add` of the
already-correct working-tree file clears it without touching content.

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
