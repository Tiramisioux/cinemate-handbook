# Hardware log

A running, dated record of what was tested on real hardware, what worked, what didn't, and
why — as opposed to [`what-the-pi-taught-us.md`](what-the-pi-taught-us.md), which is the
curated, durable lessons distilled *from* this log. This file keeps growing; that one only
changes when a new entry teaches a genuinely new way to reason about the system.

**This log is meant to be appended to automatically.** Any skill or workflow that runs a
verification session, a test take, or a debugging session on real hardware should add an
entry here when the operator confirms a finding — see "How an entry gets added" below. Don't
let a hardware result live only in a chat transcript.

## Entry format

```
## YYYY-MM-DD — <one-line subject>

**Tested:** what was run, on which hardware/branch.
**Worked:** what behaved as expected, if anything.
**Did not work:** what failed, was contradicted, or surprised.
**Why:** the actual mechanism, once known — not just the symptom. If the mechanism isn't
established yet, say so explicitly rather than guessing.
**Confirmed by:** operator / session artifact / PI-### reference, so a later reader can trace
the claim back to evidence.
```

Keep entries factual and dated. If a later session corrects an earlier one, add a new entry
that says so and points back — don't edit history in place, the same way `system-review/`
itself never edits a closed finding, only appends a correction.

## How an entry gets added

The `cinemate-dev` skill's hardware workflow (starting a managed session, running a test
take, or verifying a specific finding on the Pi) appends an entry here once the operator
confirms the result — the operator's confirmation is what turns a raw observation into a
recorded finding, the same distinction `PI-VERIFICATION-QUEUE.md` drew between "ran" and
"verdict." See the skill's own instructions for exactly when it does this.

## History (seeded from the 2026-08 system review)

The entries below predate this file and are backfilled from `system-review/PI-RESULTS-2026-08-24.md`
and `PI-RESULTS-2026-08-25.md` in the `cinemate` repo, condensed to this format. Full
ran/observed/verdict detail for each lives in `system-review/PI-VERIFICATION-QUEUE.md`.

## 2026-08-23/24 — sixteen-item hardware verification pass (imx585 → imx477 mid-session)

**Tested:** all 16 items in the system review's verification queue, across a live production
unit (CM5, 4048 MB RAM, imx585 mono, later swapped to a working imx477) and a separate blank
Raspberry Pi OS Lite Bookworm card for clean-install testing.

**Worked:** dead-template deletion has real deployment effect (PI-001); the full pytest suite
passes identically on hardware and off (PI-002, 381 passed/241 subtests, zero skips); two
cinepi-raw patch files confirmed vestigial (PI-003); a clean install reaches a working,
recording camera after two installer fixes (PI-004); the meson hiredis/redis++ fallback path
is dead, not live (PI-005); the audio VU meter works end to end on the physical display
(PI-006, first half); `INSTALL_ALT_GPIO_BACKEND=0` does not crash the app — `apt` supplies the
GPIO package independently (PI-012); the Redis-listener-freeze fix, once merged, held under
the exact fault injection that first proved the defect (see 2026-08-25 entry below).

**Did not work / contradicted:** an analog pot starves explicit CLI `set iso` commands 100% of
the time it's connected and moving, not occasionally (PI-007); all eleven "orphaned" Redis
keys are actually live, not dead (PI-008); DNG timecode rounding at 24.5fps wraps at the
*lower* base, opposite the predicted direction (PI-010); cinepi-raw's cold-start ISO fallback
clamps analogue gain to the sensor's absolute maximum while writing a plausible-looking value
to Redis — a real, silent ~5.6x overexposure, though likely unreachable via the normal
autostart path (PI-011); the undrained log queue grows ~70x faster while recording than idle
(PI-013, direction confirmed, exact rate now known); GUI refresh cadence measured at ~7.5 Hz,
not the assumed ~12 fps (PI-015); available RAM at the sensor's true peak capture mode never
dropped below ~2970 MB of 4048 MB total — the resource argument an architecture decision
partly relied on does not hold on this (4 GB, not 2 GB as assumed) board (PI-016).

**Why:** see [`what-the-pi-taught-us.md`](what-the-pi-taught-us.md) for the mechanism behind
each of these — static analysis proving absence of references but not of behaviour (PI-008),
`apt` dependencies bypassing an installer flag (PI-012), and measuring instead of arguing from
assumed board specs (PI-016) are the three with the widest lessons.

**Confirmed by:** operator-run session, `PI-VERIFICATION-QUEUE.md` PI-001 through PI-016.

## 2026-08-25 — merged-`dev` verification and the F-283/F-284/F-286 fix round

**Tested:** cinemate `dev` and cinepi-raw `dev` (post-merge of the remediation PRs) run
together on the Pi for the first time; re-verification of the Redis-listener-freeze fix under
the identical fault injection PI-014 used; three desk diagnoses (console-handoff restart hang,
unreliable RAW-volume mount/unmount, dynamic-resolution tie-break) handed off for hardware
verification and fixing.

**Worked:** the Redis-listener fix closed the defect completely under the exact fault that
proved it existed — `/api/v1/status` correctly reflected new values after the fault, with the
exception now caught and logged instead of killing the thread; a real 12-bit capture at the
sensor's full resolution was recorded and verified directly from DNG metadata, confirming the
dynamic-resolution tie-break fix; the mount-recovery fix correctly falls through to the
cache-backed query instead of trusting an empty-but-successful `blkid` result.

**Did not work as first diagnosed:** all three desk diagnoses needed correction on hardware.
The restart-hang's root cause was an interactive authentication prompt, not the systemd
dependency-ordering flag first suspected — see
[`what-the-pi-taught-us.md`](what-the-pi-taught-us.md) for the full case. The mount/unmount
defect's cause was a silently-successful-but-empty probe result, not a timeout. The
sensor-mode fixture used for one fix's test data was a reconstruction from notes, not a
measurement, and was replaced with the real table before shipping.

**Why:** see the corresponding cases in
[`what-the-pi-taught-us.md`](what-the-pi-taught-us.md).

**Confirmed by:** operator-run session, `PI-RESULTS-2026-08-25.md`, PRs #135–#140 in the
`cinemate` repo.

## 2026-08-26 — F-283: removing `Conflicts=getty@tty1.service` is worse than the race it removes

**Tested:** the fourth and last of the mitigations recorded in
`cinemate-console-handoff.sh`'s comment — dropping `Conflicts=getty@tty1.service` from
`cinemate-autostart.service` entirely — re-run and settled decisively on hardware, after the
three timing-based attempts (`--job-mode=ignore-dependencies`, a deferred timer, a debounced
timer) had each been defeated.

**Worked:** the originally reported F-283 symptom stays fixed and is not in question. The
`sudo -n` fix on the script's `systemctl start` calls holds across every run in this
investigation, including the runs that failed for other reasons — `ExecStopPost` completes in
well under a second, `TimeoutStopSec` is never reached, and the unit never lands `failed`.
Restoring `Conflicts=` was also directly confirmed to do its intended job: getty@tty1 is
auto-stopped when cinemate-autostart starts.

**Did not work:** dropping `Conflicts=` broke a *fresh start*, not just a restart, which is
strictly worse than the bug it was meant to remove. Reverted immediately; the unit file on
`dev` is back to the original and that revert is the correct state.

**Why:** `Conflicts=` was the only thing stopping a getty on tty1 before the unit started.
Without it, a getty can still be alive on tty1 when cinemate-autostart starts, and the unit's
own `TTYVHangup=yes` then hangs up every process on that tty as part of its own startup —
including its own `ExecStartPre`. `camera-ready.sh` was observed killed by `SIGHUP`. The
lesson generalises past this case: `TTYVHangup=yes` makes a unit's tty ownership a
precondition of its own startup, so the exclusion that clears the tty cannot be removed
without replacing it with something that clears the tty first.

**Still open, unchanged:** the narrower race — an explicit `getty@tty1` start colliding with
`Conflicts=` during an in-flight restart, leaving the unit `inactive` (never `failed`, never
hung; a second restart recovers it). All four documented approaches rejected. A desk review on
2026-08-26 against `origin/dev` added three things to it. First, **two** call sites issue that
getty start, not one as `FINDINGS.md`'s F-283 entry records: `main.py`'s
`restore_local_console_prompt()` (a getty `restart`, plus a 2.5s sleep, inside the stop path)
and `cinemate-console-handoff.sh`'s own final line (a getty `start`) — so fixing only the
documented one would not close it. Second, the race is now reachable from the web GUI, because
B11.4 (`c29bcbf3`, on `dev`) rewired "Restart Cinemate" to issue a real
`systemd-run … systemctl restart cinemate-autostart`; landing `inactive` on that path takes
the GUI down with it, so recovery needs SSH. Third, all four rejected approaches change *when*
the getty start happens or remove the exclusion, and none asks whether it should be issued at
all — during the stop half of a restart it is not merely racy but pointless, since `Conflicts=`
kills any getty that does start. Untested at time of writing.

**Confirmed by:** operator, hardware, 2026-08-26; follows `92480883` (`fix(autostart):
document and scope the console-restore getty race`) on `cinemate` `dev`.

## 2026-08-26 — RAW pane format-drive button: full destructive checklist passed

**Tested:** the new `POST /settings-editor/api/raw/format` endpoint and its RAW-pane control,
on `cinemate` branch `feature/raw-pane-format-drive` (`e54e691b`, off `dev` `953477e8`).
Python-only change — delivered by `git pull --ff-only` plus a cinemate restart, no rebuild.
The full destructive checklist, on a scratch drive: format as exFAT, ext4 and NTFS from the
browser; a take recorded on the freshly formatted drive; a format attempted *while* recording;
a CLI `set iso 800` issued during an in-flight format; the CLI `format exfat` path re-run as a
regression check; and the interaction with `storage-automount.service` after the remount.

**Worked:** all six checks. All three filesystems format and remount from the browser, and the
pane re-renders the drive afterwards. A take records normally on the fresh drive and lists in
the pane. Formatting while recording is refused with 409 and leaves the recording undisturbed.
A concurrent CLI command reports `busy` during the format and dispatches normally again once it
finishes — the accepted trade-off of routing through the shared dispatch lock, confirmed to
*recover* rather than wedge. The CLI `format` path is unregressed. No mount fight with
`storage-automount.service` was observed via the browser path.

**Did not work:** nothing reported.

**Why:** the one non-obvious mechanism here is why the endpoint cannot trust its own dispatch
result, and that was established at the desk, not on hardware: `CommandExecutor._confirm_or_ok`
reads back a value only for commands whose setter is in `parameters.REGISTRY`, and
`format_drive` is not, so `handle_received_data("format <fs>")` returns `(True, "")` whether
mkfs succeeded or not. The endpoint therefore verifies against observable state instead —
which filesystem is mounted at the active root once `format_drive()` has remounted. The
hardware run is consistent with that design but did not independently prove it; no failure path
was exercised on the Pi, because nothing failed.

**Not established:** which fstype string NTFS actually reported (the endpoint accepts `ntfs`,
`ntfs3` and `fuseblk` precisely because this is driver-dependent) and how long a format held the
dispatch lock in practice. Neither was reported, and a later reader should not infer them.

**Confirmed by:** operator, 2026-08-26, reported as "worked flawlessly" against the six-item
checklist in [`Tiramisioux/cinemate#152`](https://github.com/Tiramisioux/cinemate/pull/152). No
`cinemate_dev.py` session artifact was captured — this entry rests on operator report alone,
not on a traceable artifact.

## 2026-08-26 — RP1 overclock: the clock is 333 MHz, and no rp1 node exists to read it from

**Tested:** the RP1 overclock and the pixel-rate chain on the dev CM5 (4 GB, kernel
`6.12.93+rpt-rpi-2712`, imx477 on cam0), across cinemate `dev`, cinepi-raw `dev` and
libcamera `cinemate` @ `3c7b9abd`.

**Worked:** with the overlay enabled and the stack rebuilt, the chain reports consistently
end to end — `clk_sys` 333333333 Hz, `config.txt` `rp1-overclock enabled`, and the running
`cinepi-raw` carrying `--max-pixel-rate 580.0`. cinepi-raw accepting that option is itself
proof it is the new build: boost program_options rejects an unrecognised option, so an old
binary could not be running with it in its cmdline.

**Did not work:** two assumptions behind the original auto-detecting implementation
(libcamera `0413c1351`), both falsified on this board before it ever shipped:

1. **There is no `rp1` node in `/proc/device-tree` at all** — not an empty one, none, and no
   `assigned-clock-rates` property anywhere in the tree (`find /proc/device-tree -name
   assigned-clock-rates` returns nothing). A device-tree walk for the RP1 clock can never
   succeed here.
2. **The overlay requests 300 MHz and the hardware delivers 333.33 MHz.** `pll_sys` and
   `clk_sys` both read `333333333`; `pll_sys_pri_ph` reads `166666666`, consistent with a
   third of the 1 GHz PLL core. Any lookup keyed on the requested `300000000` misses.

Either failure alone made the probe return the stock rate on every boot, silently discarding
an overclock the operator had enabled.

**Why:** the clock driver synthesises the nearest rate it can from the 1 GHz `pll_sys_core`,
and 1000/3 is 333.33 — the request is a target, not a promise. The missing device-tree node
is not explained yet: RP1 is a PCIe device on Pi 5 and its clock description evidently does
not surface under `/proc/device-tree` on this kernel. That mechanism is **unestablished** —
recorded as an observation, not a diagnosis.

**Not established, and a later reader should not infer it:**

- **That libcamera is *applying* the value.** The new IPA is confirmed *installed*: `strings`
  on the installed `ipa_rpi_pisp.so` finds `LIBCAMERA_RPI_MAX_PIXEL_RATE`, so all three layers
  are running new code. But no *behaviour* has been observed. libcamera's `Info` line is
  suppressed in normal operation (cinepi-raw calls `logSetTarget(LoggingTargetNone)` unless
  `--verbose`, and always for `--list-cameras`), and on an *overclocked* board the old and new
  builds are indistinguishable by design: the old one hardcoded 580, the new one is passed
  580. The distinguishing test is toggling the overclock **off** — the new IPA should drop to
  380. That test has not been run.
- Whether the ceiling changes what `--list-cameras` advertises. Untested; this is gate G2 in
  `dev-track/C5-link-frequency-regime/GATES.md`.
- Any imx585 or imx283 behaviour. Neither sensor was attached; the imx283 `link-frequency`
  overlay parameter (driver fork `257c9cf`) remains unbooted.

**Confirmed by:** operator, 2026-08-26, pasting the three-line regime check after rebuilding
the stack. Clock values independently read over SSH earlier the same session, in both regimes
(200000000 before the overlay was enabled, 333333333 after). No `cinemate_dev.py` artifact.

## 2026-08-26 — the pixel-rate ceiling does reach `--list-cameras`, and libcamera honours it

Completes the entry above, which left two things unestablished. Both are now settled.

**Tested:** imx585 mono on the dev CM5 with the RP1 overclock **enabled** (`clk_sys`
333333333 Hz), running `cinepi-raw --list-cameras` bare — no `--max-pixel-rate`, so libcamera
fell back to its own default of 380 MPix/s.

**Worked:**

```
0 : imx585 [3840x2160 MONO]
    Modes: 'R12_CSI2P' : 1928x1090 [75.00 fps - (0, 0)/3840x2160 crop]
                         3856x2180 [43.80 fps - (0, 0)/3840x2160 crop]
```

Against the same modes recorded when libcamera was hardcoded at 580 MPix/s (75.00 and 66.85):

| Mode | at 580 | at 380 | ratio |
|---|---|---|---|
| 1928x1090 | 75.00 | 75.00 | 1.00000 |
| 3856x2180 | 66.85 | 43.80 | 0.65520 |

`380/580 = 0.65517`. The wide mode scales with the ceiling to five decimal places —
`66.85 × 380/580 = 43.80`, exactly the observed figure.

**Two conclusions, both previously open:**

1. **libcamera is applying the value, not merely carrying it.** The install was confirmed by
   `strings` earlier; this is the behaviour. A build that ignored
   `LIBCAMERA_RPI_MAX_PIXEL_RATE` could not have produced 43.80 — that number only exists if
   the 380 default was actually used.
2. **The ceiling reaches mode enumeration.** `--list-cameras` output changes with it. This
   answers gate G2 **yes**, and it removes the reason for the cinemate-side fps clamping
   planned as C5.2–C5.4: libcamera already produces an honest mode table once it is given the
   right ceiling, so there is nothing left for Cinemate to correct.

**Why:** the bound constrains *line time*, not frame throughput — the IPA stretches each
mode's minimum line length to `width ÷ rate`. So it binds only where the sensor's own readout
is faster than the receiver can drain:

| Mode | actual line time | needed at 380 | verdict |
|---|---|---|---|
| 1928x1090 | 12.23 µs | 5.07 µs | sensor-limited, unaffected |
| 3856x2180 | 10.47 µs | 10.15 µs | **bound-limited**, sitting right on the limit |

That is also why the imx477 cannot exercise this feature at all: checked across all fifteen
of its modes, the tightest uses 56% of the budget at 380, so no imx477 mode is ever
bound-limited and its `--list-cameras` output is identical at any ceiling. An imx477 board
gains nothing from the RP1 overclock — not a fault, just no bottleneck to relieve.

The 43.8 fps figure independently reproduces the number in will127534's driver README
("without overclocking RP1 you will be limited to ~43.8 FPS @ 4K"), from a different
direction: his came from measurement, this one falls out of the line-time arithmetic.

**Not established:** that a take at 66.85 fps actually records cleanly at 580 on this board —
only the *advertised* ceiling has been observed, not sustained capture. The imx283
`link-frequency` overlay parameter (`257c9cf`) is still unbooted, and no non-default link
frequency has been selected on any sensor.

**Confirmed by:** operator, 2026-08-26, pasting the `--list-cameras` output and reporting "it
works!". Arithmetic checked against the previously recorded 580 figures in
`docs/overclocking.md`.

## 2026-08-26 — imx585 mono "black image": a broken CSI cable, masked by a week of stack rebuilds

**Tested:** imx585 mono on the dev CM5 (4 GB, kernel `6.12.93+rpt-rpi-2712`), cinemate `dev`
@ `4affc53`, cinepi-raw `dev` @ `4a85042`, libcamera `cinemate` @ `3c7b9abd`, driver `6.12.y`
@ `479117e`. Symptom: preview renders but shows nothing (black frame); resolution changes
still work in the GUI. Full remote bisect over SSH, then a physical swap by the operator.

**Worked (the bisect, in order — each step eliminated a layer):**

1. `journalctl` showed the real failure: `Camera frontend has timed out!` +
   `Dequeue timer of 1000000.00us has expired!` on `/dev/video4`, camera restart every ~2 s.
   The "black image" is cinepi-raw displaying while receiving zero frames.
2. RP1 overclock off (stock 200 MHz): identical failure → overclock exonerated.
3. dpkg archaeology of Aug 24 19:52–20:45 (kernel 6.12.96 installed → downgraded to 6.12.93,
   generic Debian 6.1 *headers* installed, imx585 module + dtbo rebuilt 20:45): all boot
   artifacts verified coherent at 6.12.93; module vermagic matches → kernel churn exonerated.
4. Raw kernel capture (`v4l2-ctl -d /dev/video4 --stream-mmap`) with cinemate stopped:
   `select timeout`, zero frames → libcamera + cinepi-raw + all Aug-26 rebuilds exonerated.
5. cam0_clk verified enabled at 24 MHz with the sensor as consumer; cam0_reg on; live DT node
   correct (`clocks`, `assigned-clocks`, mono-mode) → clock/power/DT exonerated.
6. CFE debugfs: `CSI2_CH_FE_FRAME_ID(0) = 0`, `MIPICFG_INTS = 0` → no lane activity at all
   (dead link, not marginal).

**Did not work:** the CSI FFC cable. I²C and the 24 MHz clock ran perfectly over it while the
data pairs were dead — the driver logged `Streaming started` on every attempt and meant it.

**Why:** I²C, INCK and the CSI-2 data pairs are separate conductors in the FFC; a cable can
fail data-only. Every software layer then reports success because every software layer *is*
succeeding. The one place the failure is visible is the receiver's frame counter and interrupt
status, which nothing logs. The rig had been rewired (dual → single) between last-known-good
(Aug 23/24 sixteen-item pass) and the failure; the Aug 24/26 kernel churn and rebuilds landed
in the same window and looked guilty but were not.

**Also observed, not yet closed (same session):**

- The earlier "no rp1 node in /proc/device-tree" claim needs narrowing: the sensor lives at
  `/proc/device-tree/axi/pcie@1000120000/rp1/i2c@88000/imx585@1a`, so an `rp1` node exists;
  what is absent is an `assigned-clock-rates` array for `clk_sys` readable there.
- cinemate `dev` now logs the regime (`RP1 regime: stock (clk_sys 200000000 Hz) -> 380
  MPix/s`) and passes `--max-pixel-rate` accordingly — the C5 coupling works end to end.
- ClearHDR halves each mode's advertised fps (1928×1090: 50 SDR → 25 HDR at stock clock;
  3856×2180: 43.8 → ~21.9). With user fps 25 at stock clock, dynamic resolution
  **silently swaps a selected 3856 HDR mode for the 1928 sibling** (`set resolution 3` →
  `sensor_mode 4`) — this presents to the operator as "4K modes are not loading". At 580
  (overclock on) 3856 HDR ≈ 33.4 fps and the swap does not trigger. The silent swap is a UX
  defect worth filing.
- 3856×2180 12-bit SDR loads correctly through the same-aspect live-reconfigure path
  (verified at the subdev: `3856x2180 Y12_1X12`), no relaunch, no timeouts.
- 12-bit ClearHDR renders black and 16-bit ClearHDR renders fine vertical stripes with
  `hdr_data_selection_threshold = {0,0}` — zeros live in Redis
  (`hdr_threshold_low/high = 0`) and cinepi-raw's launch-restore writes them over any driver
  default, so the driver-side INNO-MAKER defaults fix (`cb7c7a6`, local, unpushed) cannot
  take effect alone; the Redis state must be corrected too. Live-threshold fix attempted via
  `set hdr threshold low 4095` / `high 0` — **result not yet confirmed by the operator**.
- cinepi-raw's threshold-restore guard is `||` where the pair semantics demand both keys
  (`cinepi_controller.cpp` sync()): one key set + one empty writes a half-default pair.
  Separately, cinepi-raw maps `pair[0]=low, pair[1]=high` while the driver documents the
  array as `{TH_H, TH_L}` — a naming/order swap to reconcile before touching this code.

**Confirmed by:** operator, 2026-08-26 ("it works! it was the cable") after swapping the FFC;
all bisect steps observed directly over SSH in the same session. No `cinemate_dev.py`
artifact — diagnosis ran as ad-hoc SSH probes.

## 2026-08-26 — 16-bit ClearHDR records a constant fill pattern, not camera data

Continues the entry above (same session, after the cable was replaced and the link was
healthy). Refines two items that entry left open; does not contradict it.

**Tested:** imx585 **mono** on the dev CM5, RP1 overclock **enabled** (`clk_sys` 333333333),
cinemate `dev` @ `4affc53`, cinepi-raw `dev` @ `4a85042`, libcamera `cinemate` @ `3c7b9abd`,
driver `6.12.y` @ `479117e`. Six frames recorded in 3856×2180 16-bit ClearHDR, pulled and
parsed off-device.

**Worked:**

- **The overclock fixes the "4K modes won't load" complaint.** At stock clock 3856×2180
  advertises 43.80 fps SDR / ~21.9 HDR, so a user fps of 25 made dynamic resolution silently
  substitute the 1928 sibling. With the overlay active every mode advertises 25.00 fps
  (`RP1 regime: overclocked (clk_sys 333333333 Hz) -> 580 MPix/s`) and the swap stops.
- **Thresholds persist correctly.** `set hdr threshold low 4095` / `high 0` reach the sensor
  live (`hdr_data_selection_threshold: 4095, 0`) **and survive reboot** — they are stored in
  Redis and the launch-restore reads from Redis. The earlier assumption that a restart would
  re-stomp them to `{0,0}` was **wrong**; correcting it here.
- The sensor streams normally in ClearHDR: `wide_dynamic_range value=1`, VBLANK/VMAX updated
  every frame, no `Camera frontend has timed out`, no restart loop.

**Did not work — 16-bit ClearHDR carries no image data at all:**

Parsed from the DNG's own `StripOffsets` (offset 8, `Compression=1` uncompressed,
`3856x2180`, `BitsPerSample=16`, stride exactly `w*2` — no assumed geometry):

| Measure | Value |
|---|---|
| unique pixel values in frame | **6** — `128, 3200, 8204, 12300, 32780, 51212` |
| first row | `[12300, 128, 8204, 3200, 128, 51212, 128, 32780]` repeating every 8 px |
| mean abs vertical neighbour diff | **0.0** — every row byte-identical |
| pixel-block md5, frames 7/8/9 | **identical** (only DNG metadata differs) |

A 16-byte pattern replicated across all 16.8 MB, identical in every frame. Real sensor data
always carries per-pixel and per-frame noise, so this is a synthetic fill, not a dark frame,
not an exposure fault, and not a byte-swap (a swap of real data would still vary row to row
and frame to frame).

This also explains the operator's "finer stripes at 4K": the period is fixed in *sensor*
pixels, so a 3856-wide frame downscaled into the same 1272-wide preview shows the same 8-px
pattern at roughly half the apparent pitch. 12-bit ClearHDR renders black on the same rig —
probably the same root cause with a different fill, not established.

**Why:** **not established.** What is ruled out: the CSI link (SDR is clean on the same
cable), frame delivery (no timeouts, VBLANK moving), the data-selection thresholds (correct
`4095,0` on the sensor during the failing capture), and the `Needs16bitEndianSwap` path as a
*sufficient* explanation. Note the swap **is** armed here — the configure line reads
`Selected sensor format: 3856x2180-Y16_1X16 - Selected CFE format: 3856x2180-Y16`, so the
CFE output is plain `Y16`, not PISP1/COMP1-packed, and `bcdd7e17b`'s guard
(`packing != PISP1`) therefore does not suppress it. Whether the swap is *also* wrong here is
untested and now secondary: swapping cannot turn varying data into a constant.

**Also observed:** `set hdr gain adder 2` returns `ok` but the control still reads
`hdr_gain_adder_db value=1 (+6dB)` against `default=2` — the write does not reach the driver.
Separate defect from the thresholds, which do reach it. `analogue_gain` sits pinned at its
maximum (80).

**Next check that would settle the mechanism** — and a correction to how to run it.

`/dev/video4` is **`rp1-cfe-fe_image0`**, the PiSP *front-end* output. It cannot stream
unless the FE has been configured with a parameter buffer queued on `/dev/video7`
(`rp1-cfe-fe_config`), which only libcamera does. So `v4l2-ctl -d /dev/video4
--stream-mmap` returns `select timeout` **whether or not the sensor is healthy** — it is not
a libcamera bypass and proves nothing on its own. Confirmed this session: with a
known-good cable and SDR working, video4 still timed out and wrote 0 bytes.

**This retroactively invalidates one inference in the cable entry above.** That entry cites a
`v4l2-ctl -d /dev/video4` timeout as evidence that "libcamera + cinepi-raw + all Aug-26
rebuilds" were exonerated. That test could not have shown anything else. The cable conclusion
still stands on the *other* two legs — `MIPICFG_INTS = 0` and `CSI2_CH_FE_FRAME_ID(0) = 0`
(no lane activity at the receiver), plus the operator's confirmed fix by physical swap — but
the raw-capture leg should be struck.

The genuine bypass is **`/dev/video0` (`rp1-cfe-csi2_ch0`)**, the direct CSI-2 channel, which
skips the PiSP FE. It requires re-routing the media graph first, because `csi2:4` is linked
to `pisp-fe` by default (media device is `/dev/media2` on this build):

```
sudo systemctl stop cinemate-autostart
media-ctl -d /dev/media2 -l '"csi2":4->"pisp-fe":0[0]'
media-ctl -d /dev/media2 -l '"csi2":4->"rp1-cfe-csi2_ch0":0[1]'
media-ctl -d /dev/media2 -V '"csi2":4 [fmt:Y16_1X16/3856x2180]'
v4l2-ctl -d /dev/video0 --set-fmt-video=width=3856,height=2180,pixelformat='Y16 '
v4l2-ctl -d /dev/video0 --stream-mmap --stream-count=3 --stream-to=/tmp/raw0.bin
sudo systemctl start cinemate-autostart   # libcamera restores the links on configure
```

Real varying data in `/tmp/raw0.bin` localises the fault to libcamera/PiSP-BE; the same
constant fill localises it to the CFE or the sensor driver. Note the sensor keeps
`wide_dynamic_range=1` and the Y16 subdev format after cinemate exits, so the ClearHDR mode
survives the stop — verified this session.

**Confirmed by:** operator report ("4K 16b looks like stripes but finer stripes than
before"); DNG parse and cross-frame pixel hashes performed off-device on
`CINEPI_26-08-26_232134_F03_C00000_cam0` frames 2, 7, 8, 9. Analysis scripts were scratch
only, not retained.

## 2026-08-26 — `chip id mismatch: 477!=0` is an overlay/sensor mismatch, not a dead camera

**Tested:** the 4 GB CM5 (`free -m` → 4049 MB), kernel `6.12.93+rpt-rpi-2712`, cinemate and
cinepi-raw both clean on `dev` (`4affc53e` / `4a85042`). Found `cinemate-autostart` in
`ActiveState=failed`, `Result=exit-code`, with neither `:5000` nor `:8000` listening — the
camera stack fully down at session start.

**Worked:** everything downstream of the camera. `storage-automount` active, `/media/RAW`
mounted (477 GB NVMe, still NTFS from the previous session's format test), both repos clean.
After the operator rebooted, the stack came up healthy on its own: unit `active`, both ports
listening, imx585 streaming at 3856×2180 16-bit ClearHDR.

**Did not work:** `camera-ready.sh` timed out at 30/30 attempts and exited 1, taking the unit
down with it. `dmesg` showed `imx477 10-001a: chip id mismatch: 477!=0` followed by
`probe with driver imx477 failed with error -5`.

**Why:** `/boot/firmware/config.txt` had been changed to `dtoverlay=imx585,mono,cam0`, but the
running kernel had booted the *previous* overlay and was still probing `imx477` — an imx477
driver reading an imx585's chip-id register gets a mismatch. A sensor change in `config.txt`
does not take effect until reboot, and until then the failure presents as a total camera
failure several layers up. Two details worth remembering for a future desk diagnosis:

- **The `!=0` side of the mismatch reads like "nothing on the bus"** — a loose or reversed
  ribbon, or an unpowered sensor — which is the wrong first hypothesis. Compare the running
  overlay in `dmesg` against `config.txt` *before* touching cables. `i2cdetect` on the camera
  buses is not a useful tiebreaker here: it returned nothing on buses 4/6/10/11 in this state.
- **The journal's timestamps can jump hours mid-boot** and did here: 09:51 → 22:12 between
  "attempt 15" and "timeout after 30 attempts (30s)". That is NTP correcting a stale RTC, not
  a 12-hour hang. The script counts attempts monotonically, so trust the attempt count over
  the wall-clock delta.

**Confirmed by:** operator ("rebooting now" / "with imx585" / "mono"), and the post-reboot
state directly observed over SSH — `imx585 10-001a: Streaming started`, unit `active`, ports
`:5000` and `:8000` listening.

## 2026-08-26 — the imx585 HMAX/hdr_scale bug is real, and is NOT the cause of the ClearHDR fill pattern

A **falsification**, recorded because the hypothesis was well-evidenced enough that a future
session would otherwise re-derive and re-test it. Continues the "16-bit ClearHDR records a
constant fill pattern" entry above.

**Tested:** imx585 mono, dev CM5, overclock on. `imx585_update_hmax()` in the driver computes
`hdr_scale = clear_hdr ? 2 : 1` and applies it to **VMAX only** — the HMAX line reads
`u32 h = factor / supported_modes[i].hmax_div;` with no `hdr_scale` factor, inside a function
named `update_hmax`. dmesg confirmed the asymmetry directly:

```
Update minimum HMAX: base=660 lane_scale=1 hdr_scale=2
 mode 3856x2180 -> VMAX=4500 HMAX=660        <- VMAX scaled, HMAX not
```

Hypothesis: ClearHDR reads out high- and low-gain data per line, so the line period must
double; at HMAX=660 instead of 1320 the sensor cannot emit a valid line. Patched line 695 to
`factor * hdr_scale / hmax_div`, rebuilt via DKMS (`./setup.sh`), rebooted.

**Worked:** the patch does exactly what it claims. Post-reboot dmesg:
`mode 3856x2180 -> VMAX=4500 HMAX=1320`.

**Did not work — the hypothesis is FALSIFIED.** Recorded 6 frames of 16-bit ClearHDR and
hashed the pixel block (`tail -c +9 | head -c 16812160 | md5sum`):

| | pixel-block md5 |
|---|---|
| before patch (HMAX 660) | `31603865fe3aa83d793e50cce4fe201c` |
| after patch (HMAX 1320) | `31603865fe3aa83d793e50cce4fe201c` |

**Byte-for-byte identical.** Doubling the line period changed not one bit of output. Operator
independently reported "visually it is the same as before".

**Why this matters more than the fix would have:** the captured constant is now known to be
invariant across HMAX 660 vs 1320, across frames, across reboots, and across a driver
rebuild. Sensor line timing is therefore *irrelevant* to it. This is not sensor data being
mangled in transit — it is a buffer the capture path never writes, carrying a deterministic
fill. Any future theory must explain invariance under sensor reconfiguration.

**Also ruled out this round:** `do16BitEndianSwap()` (pisp.cpp:373) as the *source*. Its NEON
loop is correct — `ld1`/`rev16`/`st1` with `count = (width+7)/8` covers exactly `width*2`
bytes per row (482 iterations x 16 B = 7712 B at width 3856), stride-indexed per row. It is
armed for this mode (Y16 maps to `Packing::None`, so `bcdd7e17b`'s `!= PISP1` guard passes),
but an in-place byte swap of a constant yields another constant; it cannot create one.

**Should the HMAX patch be kept?** Probably not as-is. It is a genuine upstream defect
(`git log -L` traces the unscaled line to will127534's `0fe7af2`, so it has never been
correct), but it buys nothing observable here and it **halves the maximum ClearHDR frame
rate** — immediately after the rebuild, dynamic resolution swapped a requested 3856 HDR mode
down to 1928 because 4K HDR could no longer sustain 25 fps. Revert with
`git checkout imx585.c && ./setup.sh` unless a separate test shows it matters. Fix it upstream
on its own merits, not as a fix for this.

**Next hypothesis to test (cheapest first):** force the 16-bit ClearHDR mode down the COMP1
CFE path instead of plain Y16, by changing imx585's 16-bit `packing` from `U` to `P` in
`resources/sensors.json`. `pisp.cpp` `platformValidate` leaves a 16-bit + `Packing::None`
request untouched (plain uncompressed Y16, 2 B/px), while a CSI2/`P` request becomes
PISP1/COMP1 (`PC1M` for mono, 1 B/px) — an entirely different CFE output format. If COMP1
produces real data, the fault is localised to the uncompressed Y16 CFE path.

**Confirmed by:** operator applied the patch and rebuilt; dmesg HMAX value and both pixel-block
hashes observed directly over SSH, 2026-08-26.

## 2026-08-26 — the boundary is not ClearHDR: only the base HD SDR mode returns real data

**Supersedes the framing of the two entries above.** Those investigated "16-bit ClearHDR
records a fill pattern" as if ClearHDR were the variable. It is not. A resolution-matched
control set shows the failure is broader and the working set is much smaller than assumed.

**Tested:** imx585 mono, dev CM5, **no lens fitted** (bare sensor in room light — relevant,
see below). RP1 overclock on. Link frequency set to the over-spec 1039.5 MHz / 2079 Mbps
option. imx585 driver carrying the local HMAX `hdr_scale` patch. Six frames recorded per mode
via `rec f 6`, DNGs pulled and unpacked off-device (MIPI RAW12 for the 12-bit modes).

**Results:**

| Mode | unique values | mean\|dx\| | mean\|dy\| | verdict |
|---|---|---|---|---|
| **1928x1090 12b SDR** | **592** | 1156 | 780 | **real image** (mean 1823, pct 1/50/99 = 90/1511/3934) |
| 3856x2180 12b SDR | 1 | 0.00 | 0.00 | uniform 4095 fill |
| 3856x2180 12b ClearHDR | 3-4 | 184 | 0.5 | fill (values 0/12/192/200) |
| 1928x1090 & 3856x2180 16b ClearHDR | 6 | 22953 | 0.0 | fill (16-byte repeat) |

**Only 1928x1090 12-bit SDR — the smallest payload of any available mode — produces real
sensor data.** Every larger mode returns a fill pattern.

**Why saturation is ruled out for 4K SDR** (this is the load-bearing argument, and it needs
the no-lens detail): with no lens the bare sensor is flooded, so "everything clips to 4095"
is a plausible innocent explanation. It does not survive. 1928x1090 is the **2x2 binned**
mode — it collects roughly 4x the light per output pixel and should therefore clip *before*
the unbinned 4K mode. Observed is the exact inverse: the binned mode shows a normal histogram
while the unbinned mode is pinned at exactly 4095 with **zero** variance, unchanged across a
~5-stop exposure reduction (ISO 3200 -> 100, `analogue_gain` 80 -> 0, `exposure` 751). A real
saturated frame still varies at hot/dead pixels and edges. 4K SDR is a fill, not a clip.

**What this falsifies, beyond the HMAX patch already retracted above:**

- **HMAX / `hdr_scale`** — ClearHDR-only by construction, but 4K **SDR** fails identically
  with `hdr_scale = 1`. Doubly dead.
- **`do16BitEndianSwap`** — armed only for 16-bit; 4K 12-bit SDR fails too.
- **CCMP ratios, data-selection thresholds, `hdr_gain_adder`** — all ClearHDR-only, all
  cannot explain 4K SDR.
- Operator report "nothing happens in ClearHDR when I change ISO" is consistent and expected:
  a buffer holding no sensor data cannot respond to any sensor control.

**Why:** **not established.** The surviving shape is bandwidth/throughput: the one working
mode is the smallest payload, and every failure is either 4x the pixels (4K) or ~2x the
readout (ClearHDR) or both. That points back at the PiSP pixel-rate ceiling — and at the
subagent's observation that the bound is specified in **pixels**/s while the CSI2-to-ISP-FE
FIFO is a **byte** pipe, so a bound that is safe at 12 bpp is over-stated by 1.33x at 16 bpp.
Not proven; no test has yet varied bandwidth alone.

**Next test that would settle it:** drop `--max-pixel-rate` far below the current value
(e.g. 200) and re-shoot **4K 12-bit SDR**. Real data at a lower ceiling confirms a throughput
ceiling and localises it; unchanged fill refutes the bandwidth family outright and moves the
search to buffer allocation / DMA target. Do this from a clean baseline: revert the HMAX
patch (`git checkout imx585.c && ./setup.sh`) and return the link frequency to the in-spec
720 MHz first, so over-spec settings are not stacked on the measurement.

**Method note for future sessions:** the discriminator that made this tractable is cheap and
general — unpack the DNG and report unique-value count plus mean absolute row-to-row
difference. Real sensor data has hundreds of levels and non-zero vertical variation; every
failure mode here had <10 levels and ~0 vertical variation. It distinguishes "no data" from
"wrong data" from "clipped data" without needing a reference frame or a known scene. Beware
the naive inverse: a *legitimately* uniform frame (true clipping) also shows one level, which
is why the binning argument above, not the level count, is what settles 4K SDR.

**Confirmed by:** operator ("only HD SDR looks good" — the original report, which this
finally corroborates; "nothing happens in ClearHDR when i change iso"; "i have the sensor
without a lens"). All frames recorded and analysed over SSH, 2026-08-26, takes
`CINEPI_26-08-26_235123/235316/235620/235712/235808_*_cam0`.

## 2026-08-27 — the RP1 D-PHY tops out at 1500 Mbps/lane, and it clamps instead of refusing

**Tested:** imx585 **mono**, dev CM5 (4 GB, `6.12.93+rpt-rpi-2712`), **no lens** (bare sensor in
room light). cinemate `dev` @ `4affc53`, cinepi-raw `dev` @ `4a85042`, libcamera `cinemate` @
`3c7b9abd`, driver `6.12.y` @ `479117e` (HMAX patch **already reverted** before the session —
the tree was clean and `HMAX=440` under `hdr_scale=2`). The six-mode matrix re-shot at four link
frequencies: 1188, 1440, 1782, 2079 Mbps. Every take verified at `/dev/v4l-subdev2` before
recording, with dynamic resolution disabled and exposure forced short.

**Worked:**

- **The receiver's ceiling is exactly 1500 Mbps/lane, and above it the kernel warns and then
  *clamps* rather than refusing.** `rp1_cfe/dphy.c`: `if (mbps < 80 || mbps > 1500)
  dphy_err("DPHY: Datarate %u Mbps out of range\n", mbps);` — void, no return. The lookup loop
  runs `i < ARRAY_SIZE(table) - 1` and falls through to the last bucket `{1500, 0b111100}`. So
  1782 and 2079 are physically programmed with the 1500 Mbps calibration bin; 1440 lands
  correctly on bucket 37 `{1449}`. Verified byte-identical to upstream `rpi-6.12.y`, and the
  function has only ever had two commits, neither touching it. `dmesg` shows the warning on
  every configure at 1782 and 2079, and none at 1440 or 1188.
- **4K 12-bit SDR is fixed by lowering the rate.** Uniform-4095 fill at 2079; real at 1188,
  1440 and 1782. The old "Defect A" is rate-dependent, not a mode-validity property.
- **In-spec mono ClearHDR exists.** 4K 12-bit ClearHDR is real at **1440 Mbps with a stock RP1
  clock** (`clk_sys` 200000000, `RP1 regime: stock -> 380 MPix/s`), operator-confirmed. This
  kills the previous "12-bit ClearHDR has only ever produced fills on mono" conclusion.
- Defect C (`hdr_gain_adder` stomped at every startup) fixed by seed-if-absent in `main.py` and
  verified across two reboots. The decisive check is that Redis `hdr_threshold_low=4095`
  survives while `settings.jsonc` says `0` — pre-fix the unconditional seed overwrote it.

**Did not work:**

- **2079 Mbps degrades a working mode over minutes.** 1928×1090 12-bit SDR went **1090/1090 rows
  → 5 rows → 47 rows** in ~4 minutes with no physical change; everything below the last valid
  row is exactly 0, and the monitor showed a bright band at the top over black. Thermals were
  clean (48 °C, `throttled=0x0`) and the sensor's exposure/gain were verified moving throughout.
  1782 held full row counts through three ClearHDR sweeps plus a high-gain sequence over ~5
  minutes, so *being out of range is not sufficient* — 39% over clamps far worse than 19% over.
- Both 16-bit ClearHDR modes show stripes at 1440/stock. The only rate where the operator has
  agreed 16-bit ClearHDR works is 2079.
- HD 12-bit ClearHDR failed at every rate by measurement, **but the operator reports it working
  at 1440/stock** — unresolved, see below.

**Why:** **two independent defects, not one.** (a) The D-PHY clamp costs receiver margin and
explains the *stability* gradient (1440 clean, 1782 marginal-but-holding, 2079 truncating). It
cannot explain *which* modes fill, because the PHY config is mode-invariant: `imx585.c:1582-1587`
sets `link_freq_idx` once at probe as a read-only control, and `v4l2-common.c:482-493` ignores
the `mul` argument, so bit depth never enters the calculation — all six modes program the PHY
identically. The disqualifying counterexample is that at 2079 the *largest* payload (4K 16b HDR)
is real while 4K 12b SDR is 100% 4095. (b) The fills are sensor-side: they are byte-exact
deterministic, and two different resolutions (1928×1090 and 3856×2180) produced the *same*
`0c 80 c8` repeat across the whole strip. Changing link frequency reprograms the sensor's
`DATARATE_SEL`, which is why lowering the rate rescues 4K 12b SDR — not because the link got
cleaner.

**Method traps that cost real time this session — all three are general:**

- **A fill-vs-real statistical discriminator gives false REALs.** `discriminator.py` scored 4K
  12b ClearHDR REAL at 2079 (2180/2180 distinct rows, 567 uniques, populated ±1 neighbours) on a
  frame whose histogram was **frozen across a real ~5-stop exposure change** — value 3627 held
  22.82% → 22.81%, every top-10 count within 0.1%. **Exposure response is the reliable test, not
  frame statistics.** Even that was not sufficient for 16-bit: mode 5 responded (1.55× mean) yet
  the operator sees stripes. A `16384 = 2^14` unique count is a reliable *fill* tell for 16-bit
  modes here; the one operator-agreed working case showed 9400 instead.
- **Saturation reads as FILL.** With no lens the bare sensor floods, and an entire 1440 run was
  invalidated by `exposure` having silently reset to VMAX (2250 lines = 360°). Confirm `exposure`
  at the subdev before trusting any uniform frame.
- **Settings silently fail to re-apply after a resolution change.** A mode switch resets the
  sensor's exposure to VMAX while Redis keeps the old `shutter_a`, so re-issuing the same value
  is swallowed by `set_value`'s same-value dedup and the sensor is never reprogrammed. Workaround:
  set a different value, then the target. This is a real cinemate defect, not just a test artifact.
- `set resolution N` is remapped by dynamic resolution — disable it first or the cell labels in a
  mode matrix are wrong (`set resolution 0` landed on `sensor_mode=4` once).

**Open / contradicted, deliberately not resolved here:**

- **The overclock test is confounded.** The 1440-with-overclock run used fps 25 — exactly the
  advertised ClearHDR ceiling at that rate — while the 1440-stock run used fps 19. So mode 3's
  recovery may be the stock clock, the fps headroom, or both. The isolating test (1440 + overclock
  ON + fps 19) was not run and should be the next thing anyone does.
- Upstream's AppNote reading says binned ClearHDR is 16-bit-only and 12-bit binned HDR yields
  all-BLC frames; the operator reports that mode working at 1440/stock, and its measured mean
  (1177) is nowhere near black level (200). Resolve before porting the upstream gate `bb53099a`,
  which would disable that mode permanently.

**Confirmed by:** operator throughout, watching the HDMI monitor and the web preview — including
three calls that overrode the analysis tool ("2k and 4k sdr is now working but clear hdr modes
are not", "hdr 12 bit in 4K now worked!", "mode 4 shows stripes, mode 5 shows stripes as well").
All frames recorded over SSH and analysed off-device; takes and per-rate results in
`development/pi-test-takes/2026-08-27-phase4/` and
`development/imx585-mode-matrix-handoff/LIVE-RESULTS-2026-08-27.md`. D-PHY source claims verified
against `raspberrypi/linux` `rpi-6.12.y` and independently corroborated by the desk-analysis
session, which also cites the RP1 datasheet §8.2.

## 2026-08-27 (evening) — Mono ClearHDR byte-level forensics: 16-bit is a capture-path format bug, binned 12-bit is real sensor BLC

**Tested:** structured/overexposed mono takes pulled off /media/RAW and decoded byte-by-byte on
the desk (takes 19:07-19:08 @1782-era config and 20:13-20:14 @1440 default, old driver 479117e
loaded — NB the operator re-ran the 6.12.y revert at ~19:52, so the "innomaker similar results"
session and these takes ran DIFFERENT drivers; check dmesg `base=` vs `link_freq=` HMAX line to
know which driver is loaded before trusting any session).
**Worked:** 4K 12-bit CCMP HDR mono RECORDS REAL DATA (19:07 take: smooth companded values,
correct b=1 LinearizationTable). 12-bit unpacking, CCMP table attach, and DNG geometry all
correct in that mode.
**Did not work:**
- 16-bit mono (both takes, both rates): buffer contains a repeating 16-byte motif = PiSP
  COMP1-style compressed blocks in a buffer labeled/consumed as uncompressed R16, additionally
  scrambled by libcamera's 16-bit endian swap. Kernel rpi-6.12.y `cfe_fmts.h` shows why mono
  differs from color: Bayer 16-bit entries carry `csi_dt = 0` ("Avoid RP1 HW mismatch for
  16-bit modes") but the Y16 entry kept `csi_dt = MIPI_CSI2_DT_RAW16` — the 6.12.93 16-bit
  workaround was never applied to mono. Operator's hypothesis ("endian swap different for
  mono?") pointed here. Fix direction: align the Y16 entry with the Bayer16 entries and
  rebuild rp1-cfe; then mono 16-bit needs the 2200-row mode (OB prepend passes when csi_dt=0),
  i.e. pairs with upstream-main/innomaker driver.
- Binned 12-bit CCMP HDR mono: constant 200 = BLC pedestal across the frame WITH THE SCENE
  OVEREXPOSED — a working mode cannot output pedestal on a blown-out scene. AppNote §2 p.6 /
  bb53099a binned-ClearHDR gate CONFIRMED for mono at pixel level (color b=4 passed the
  2026-08-10 goldens, so it is mono-specific in practice).
**Why:** see above; two independent mechanisms, neither is the sensor driver, which is why both
driver generations "failed identically". The earlier "fill at 1440 / works at 1782" pattern is
now CONTAMINATED evidence: the 16-bit legs were the COMP1/swap bug (rate-independent), the new
1440 takes were saturation-constants (saturation reads as fill — trap re-confirmed), and mode
labels diverged from actual modes (Redis/table vs driver nearest-match; SensorBinning picked
b=4 for a 4K request; a "12-bit" launch got an R16 raw stream). 1440-vs-1782 for mono ClearHDR
is REOPENED, retest only after the fixes with a non-clipped structured scene + exposure
response.
**Also confirmed:** cinemate rp1_regime misclassifies stock clk_sys 333 MHz as overclocked and
passes --max-pixel-rate 580 with the overclock overlay commented out (journal 19:52:46) — clk_sys
cannot discriminate regimes on 6.12.93; the config.txt overlay line must be the authority.
Suspected (unverified): ccmpPreview "whites become black" = highlight overflow wrap
(decompanded 63265 × preview exposure gain > 65535) — check renderer clamping in
cinepi-raw ccmp_preview.hpp.
**Confirmed by:** operator (takes, overexposure statement, preview observations) + desk byte
analysis of the five DNGs (scratchpad session 2026-08-27); kernel table via raspberrypi/linux
rpi-6.12.y cfe_fmts.h.

## 2026-08-27 (night) — Mono ClearHDR VERIFIED WORKING end to end; milestone tagged

**Tested:** the full verification matrix on the mono rig after deploying the complete fix
stack in one configuration: rp1-cfe Y16 csi_dt=0 kernel patch (first compile AND first load —
built clean against 6.12.93 headers, loaded srcversion D0CCED8E6D1BA72AC1C26AA verified),
sensor driver `innomaker-v1.0`, branches `fix/mono-clearhdr-stack` in cinemate + cinepi-raw,
`--max-pixel-rate 380.0` (stock, from the fixed rp1_regime), `dtoverlay=imx585,cam0,mono,ccmp`,
link 1440 Mbps (overlay default, in-spec), overclock overlay commented. Modes recorded with a
structured scene at two shutter values each: 2K/4K 12-bit SDR, 4K 12-bit CCMP HDR, 16-bit
ClearHDR with log off and with log-encode 12.
**Worked: everything.** Operator: "big breakthrough… correct frames now in all modes."
Overseer byte verification of the decisive 16-bit linear pair (takes 223145/223201): 3840×2200
with OB rows sitting exactly at the 3200 pedestal, smooth scene gradients, no repeating motif,
and ~3-stop exposure response matching the shutter step (signal-above-pedestal 3432 vs 417).
The launch line simultaneously proved the rp1_regime fix (380 on stock), the mono AWB gating
(no --awb args), and the label/stream agreement (requested 3840:2200:16 = configured).
**Did not work:** nothing in the matrix.
**Why:** the three root causes in the two earlier 2026-08-27 entries, all now fixed: kernel
Y16 csi_dt (mono 16-bit garbage), stack-level mode/label divergence + preview stage refusing
mono formats (12-bit "black"/"inverted" symptoms), binned ClearHDR invalid on the sensor
(now gated out by the driver). Working config encoded into cinemate-install.sh + docs on
`fix/mono-clearhdr-stack` (commit 02b2bec8: innomaker-v1.0 default, ccmp overlay param,
scripts/patch-rp1-cfe.sh run automatically for imx585_mono). Milestone tag
`milestone-mono-clearhdr-2026-08-27` on both repos. Overclock/link-rate exploration
deliberately deferred to a follow-up session — 380/1440/stock is the verified baseline.
**Confirmed by:** operator (live preview + takes), overseer byte analysis (this session),
Sonnet round-3 verification results in `development/mono-clearhdr-fixes/`.

## 2026-08-29 — GPIO10 double-claim crashed cinemate at every boot; latent in the shipped config

**Tested:** diagnosis of a Pi (CM5, 4049 MB, kernel 6.12.93+rpt-rpi-2712, branch
`fix/mono-clearhdr-stack` at 02b2bec8) that failed to start cinemate on every boot.
`cinemate-autostart` sat in `failed`, `ExecStart` exiting 1 within ~3 s of launch.

**Worked:** disabling the rotary encoder in `settings.jsonc`
(`hardware_controls.rotary_encoders[0].enabled` true → false) restored a clean boot
immediately, with no code change and no reboot — operator confirmed "boot is confirmed, now
it works." Recovery from the `failed` unit state needed `systemctl reset-failed` then `start`,
not `restart` (see the console-handoff hang recorded elsewhere in this log).

**Did not work:** the camera would not start at all while that one flag was true. The
journal's stated reason named only the pin —
`GPIOPinInUse: pin GPIO10 is already in use by <gpiozero.Button object on pin GPIO10 ...>` —
and neither of the two `settings.jsonc` entries that collided, so the message gave no route
back to the setting that caused it.

**Why:** the shipped `settings.jsonc` assigns GPIO10 twice — `hardware_controls.buttons[1].pin
= 10` (press → `rec`) and `hardware_controls.rotary_encoders[0].button_pin = 10`. The pair is
present in committed history, not introduced by the operator; it is harmless only because the
encoder ships `enabled: false`. `ComponentInitializer` guarded `reserved_output_pins` but
never tracked pins its own inputs had claimed, so the encoder's `SmartButton` construction
reached gpiozero and raised. A settings-editor save at 11:34:52 on 2026-08-28 flipped that one
flag; the crash follows at 11:38. So a one-click UI toggle detonated a collision that had been
sitting in the default config all along — the kind of thing that reads as "the encoder is
broken" rather than "two entries share a pin."

The same editor save also corrupted `sensors.camN.log_encode` from boolean `false` to the
**strings** `"true"` (cam0) and `"false"` (cam1). That key's editor control carried
`data-type="string"`, and `readControlValue()` returns `el.value` verbatim for anything not
`bool`/`number`. A string fails silently in the footage-losing direction: `cinepi_multi` gates
on `if log_requested:`, and a non-empty string is truthy, so `"false"` read as log-ON; the
truthy branch then forwards anything that is not literally `True` as an explicit target, so
`"true"` matched no valid bit depth and recorded LINEAR with only a warning. "Off" meant
on-but-broken; "On" meant off-with-a-warning. That save also dropped the `system.web_api` and
`system.recovery` blocks and stripped every comment.

**Not yet verified on hardware:** the code fixes for both defects are on `dev` (cf31459e) and
`fix/mono-clearhdr-stack` (6d62f762) but were **not running on the Pi** when boot was
confirmed — it was still at 02b2bec8, 8 commits behind, with `_claim_pin` and
`normalize_log_encode` both absent. The confirmed finding is therefore the *mechanism* and the
*settings-level* fix; the duplicate-pin guard (skip-with-both-names instead of raising) and the
`log_encode` normalisation are so far only covered by unit tests — including a MockFactory
reproduction that raises the identical `GPIOPinInUse` string against pre-fix code. Both still
need a Pi run. Note the Pi's `settings.jsonc` still carries `"log_encode": "true"` for cam0, so
once it does pull, cam0 starts genuinely recording log rather than linear.

**Confirmed by:** operator (boot restored, this session); journald `cinemate-autostart` on the
unit; git history for the pin pair being pre-existing; offline gpiozero MockFactory
reproduction against the Pi's own `settings.jsonc` (this session).

## 2026-08-27/28 — RP1 overclock IS compatible with mono ClearHDR; the real limits are storage and a shutter-apply delay

**Tested:** the full overclock × CSI-2 link-rate × mode matrix on the dev CM5, imx585 mono,
`fix/mono-clearhdr-stack` in both repos, patched rp1-cfe, `innomaker-v1.0` driver. Seven cells
planned, six run (1188/1440/1782 Mbps × stock/overclocked), three modes each (4K 12-bit SDR,
4K 12-bit CCMP HDR, 16-bit ClearHDR) at two shutter angles ~3 stops apart, plus soaks.
Deliverable `development/mono-clearhdr-fixes/RATE-MATRIX-RESULTS.md`; overseer verification in
`OVERSEER-NOTES-R4.md`.

**Worked:** the question the campaign existed to answer — **the RP1 overclock (580 MPix/s)
runs mono ClearHDR cleanly at 1440 Mbps**, 8/8 takes byte-REAL across all three modes and both
log states. That combination had never been tested on the fixed stack. The whole in-spec
envelope (1188/1440 × stock/overclock) was clean: 32 takes, zero motif, zero truncation, zero
fill. 1782 Mbps (19% over the D-PHY spec, kernel logs `DPHY: Datarate 1782 Mbps out of range`
once per boot) was clean on 16/16 short takes at both clocks. Settled-frame exposure response
was exact — 8.1–8.5× measured for a commanded 8× shutter step, overseer-verified by pulling
frames and decoding them independently in cells 1, 2, 4 and 5.

**Did not work / surprised:**
- **No multi-minute soak was achievable at 16-bit.** A 12-bit 21 fps soak (~264 MB/s) ran
  2520/2520 frames clean, but every 16-bit soak (~355+ MB/s) stalled after ~15–22 s: the RAM
  pool (173 frames ≈ 2941 MB) fills and frames stop arriving — cleanly, no corruption, no
  telemetry loss. `/media/RAW` is NTFS via `fuseblk` on NVMe. So **1782 Mbps stays
  labelled-risk**: its minutes-scale behaviour is still unproven. 2079 Mbps was never reached.
- **The overclock buys no frame rate here.** Advertised fps was identical with it on or off at
  every link rate (21.99 @1440, 30.00 @1782). It raises the RP1 pixel-rate ceiling, which only
  matters when a mode approaches it — 3840×2200 does not.
- **A post-mode-switch shutter change lands ~12 frames into the *next* recording.** Byte-
  measured from within-take frame profiles: a step between frames 10 and 15, then a stable
  plateau — not a slow ramp. Even a 4.5 s pre-record settle did not help; SDR applies promptly.
  Practical rule adopted since: **sample frame ≥ 20 for any exposure verdict.**

**Why:** the link-rate/overclock question is answered and is not the limiting factor. The
limits are elsewhere — sustained write bandwidth on NTFS-over-FUSE, and a control-apply path
whose mechanism is still unidentified (the original "the shutter command lands late" wording
was later withdrawn as unsupported; the measurement stands, the mechanism does not).

**Confirmed by:** operator (live session, 2026-08-27 night → 08-28); worker deliverable
`RATE-MATRIX-RESULTS.md`; independent overseer re-verification — frame pulls decoded with
`tools/dng_inspect.py`, soak takes compared frame-10-vs-last, and the D-PHY clamp line quoted
from `dmesg` directly. Recommended default left unchanged at **1440 Mbps / stock clock**, and
the rig was restored to it at session end.

## 2026-08-30 — A threshold write outlives restarts and sensor power cycles via V4L2 control-cache replay

**Tested:** threshold semantics on the mono rig. Stack: cinemate `dev` @ bf4b68d, cinepi-raw
`dev` @ dad2247 (= #69 merge), both pulled and rebuilt on the Pi; driver `innomaker-v1.0`
@ 70bdb26 verified by source diff (not srcversion); kernel 6.12.93 + rp1-cfe Y16 patch; mono
16-bit linear ClearHDR (sensor_mode 4, 3840×2200); scene bare/lensless (operator-confirmed).
One boot, two managed stop→starts, raw-I2C readbacks of 0x36D0/0x36D4 after every threshold
command.

**Worked:** #69's fix holds — `set hdr threshold high 4095` lands EXP_TH_H=0x0FFF /
EXP_TH_L=0x0000 (the key swap is dead), and the prohibited pair (low=3000 accepted as a valid
intermediate, then high=500) is refused with the new warn line, registers byte-unchanged
across the refused write. That PR's pending hardware gate is closed.

**Did not work:** the prediction that a stop→start would restore EXP_TH_L=0. After the
refusal test, stop→start (with a true driver-level sensor power cycle in the journal:
power_off → power_on → Streaming started) came back 0x0BB8 (3000) — the earlier written
value — with Redis reseeded empty and no userspace write in the journal. Also found:
`systemctl restart cinemate-autostart` cancels itself (Conflicts=getty@tty1 + the ExecStopPost
console handoff starts getty, which kills the queued start job) — the stack silently stays
down; only stop-then-start works. journald runs `Storage=volatile`, so only the current boot
exists and every boot's evidence dies at power-off. And libcamera's on-rig tree is dirty at
the pinned SHA: colour `imx585.json` and `imx283.json` stripped (~4.3 KB,
alsc/denoise/lux/dpc/noise/geq removed) and installed; `imx585_mono.json` untouched — any
colour work must restore them first.

**Why:** the threshold persistence is V4L2 control-cache replay, confirmed at source after
the run: `imx585.c:2024` calls `__v4l2_ctrl_handler_setup()` at every stream start ("Apply
user controls after writing the base tables"), replaying every cached control value over the
register-table defaults; probe seeds DATASEL_TH `p_cur`/`p_new` to {0x0FFF, 0}
(`imx585.c:1749`), so an untouched boot replays a no-op — but any threshold ever written
persists for the module's lifetime, across cinepi-raw restarts and sensor power cycles,
invisible to Redis. The driver deliberately zeroes VMAX/HMAX/SHR before the replay
(`imx585.c:2019-2021`) but not the HDR controls. Two adjacent footguns surfaced while
confirming: the control's registered *default* is `.def = 0`, i.e. p_def = {0,0}, the
degenerate pair (only p_cur/p_new get the good seed — anything that "resets to default"
writes {0,0}); and a write cinepi-raw refuses still lands in Redis, which then disagrees
with the silicon until the next reseed.

**Confirmed by:** worker-session raw-I2C readbacks, journal greps, and SHAs pasted verbatim
in the session record (2026-08-30); overseer source confirmation against `imx585.c` @ 70bdb26,
which the worker's own on-Pi diff showed byte-identical to the DKMS build source. Scene state
operator-confirmed. README fix for the prohibited-pair example opened as cinepi-raw PR #70
(docs-only).

## 2026-08-30 — Control-cache replay closed end-to-end; pre-engage WDR toggles are cache-only

**Tested:** the mono rig with persistent journald via drop-in (Storage=persistent,
SystemMaxUse=500M) plus a single warm reboot, with raw-I2C register readbacks before and
after. No threshold key written all session. Stack unchanged from the previous entry
(cinemate bf4b68d / cinepi-raw dad2247 / driver 70bdb26), scene bare.

**Worked:** every pre-registered prediction. The cached EXP_TH_L=3000 survived to the
reboot (pre-reboot readback 0x0FFF/0x0BB8) and was gone after it (0x0FFF/0x0000, the
driver-default pair) — module reload clears the V4L2 control cache, closing the replay
mechanism end-to-end: entry confirmed at source in the previous entry (`imx585.c:2024` +
`:1749`), exit confirmed on hardware here. The previous session's boot survived as journal
boot -1 (the drop-in wins over the stock `Storage=volatile` conf, which was left untouched).
Real-boot signature reconfirmed: probe power pair + exactly 2 engages (Plymouth double
start), streaming at t=18.8 s — a full warm reboot to streaming costs ~19 s.

**Did not work:** nothing — no prediction failed.

**Why (new observation classified):** the worker flagged `HDR=1→0→1` journal toggles
preceding each engage (~335 ms at 0). These are cinemate's dual-probe mode enumeration and
are cache-only: the WDR s_ctrl handler (`imx585.c:1307`) only flips the driver's
`clear_hdr` flag, activates/deactivates the HDR knob controls, forces HCG off, and updates
gain limits — no `cci_write` in the path (the register-writing switch says "Handled above"
and breaks) — and both toggle bursts land while the sensor is unpowered (t=8.29–8.87 vs
power_on at t=10.27; t=16.30/16.56 between power_off 16.10 and power_on 17.85). They cannot
reach the silicon; WDMODE is only written from the register table during start_streaming,
as previously established.

**Confirmed by:** worker raw-I2C readbacks and journal excerpts pasted verbatim in the
session record (2026-08-30); overseer source citations against `imx585.c` @ 70bdb26. Related:
cinepi-raw PR #70 (README prohibited-pair example) merged 2026-08-30.

## 2026-08-31 — Colour rig bring-up: driver-independent kernel BUG on imx585 module reload

**Tested:** bring-up of the colour imx585 rig (4 GB CM5, kernel 6.12.93+rpt-rpi-2712,
exFAT NVMe, healthy 42.8 KB colour tuning file) to cinemate dev @ bf4b68d, cinepi-raw dev
@ 24fd76a (= mono's dad2247 + the #70 README fix), libcamera cinemate @ 3c7b9ab (a local
380→580 overclock-companion tweak and a stripped settings.jsonc were both STASHED with
labels, not discarded), then a driver switch attempted twice: innomaker-v1.0 @ 70bdb26, and
— operator's choice — 6.12.y at tip (cb7c7a6, which is the 2026-08-10 colour-golden 479117e
plus exactly one commit changing hdr_thresh_def from the prohibited {512,1024} to
{0x0FFF, 0}).

**Worked:** the survey and userspace upgrade. Both driver branches DKMS-build and install
cleanly, source-diff-verified. Boot-time probes succeed cleanly on both branches (verified
via lsmod on fresh boots before any manual intervention).

**Did not work:** `rmmod imx585` + `modprobe imx585` inside a booted session SEGFAULTS the
probe with a kernel BUG — reproduced twice, byte-for-byte identical, on BOTH driver
branches: `kernel BUG at drivers/media/mc/mc-entity.c:146!`, PC media_gobj_create+0xdc [mc],
call trace cfe_async_complete [rp1_cfe] → v4l2_async_nf_try_complete →
__v4l2_async_register_subdev → imx585_probe, firing immediately after "rp1-cfe … Registered
[rp1-cfe-fe_config] node id 7". Kernel left tainted (G D W O), module in an undefined
half-probed state. **The crash is driver-independent: the discriminating variable is
RELOAD, not driver source.** Worker's working theory, explicitly not source-verified:
rp1_cfe does not tear down its media-graph object state when the sensor unloads, so a
second probe re-registers a live node ID and trips the media-controller core's
duplicate-registration assertion.

**Why it matters beyond this rig:** this was, as far as the session record shows, the first
actual rmmod+modprobe cycle anyone had run on either rig — every "restart" up to here was
systemd stop/start, which never unloads the module. Any procedure written around an
`rmmod` + soak step was therefore invalid as designed, and was avoided by construction, not
by verification. **Method rule, both rigs: never manually rmmod/modprobe camera sensor
modules on a live system — module reset = reboot.** Open desk item: rp1-cfe remove/probe
paths + the mc-entity.c:146 assertion; check raspberrypi/linux for known reports; candidate
upstream bug report. Until that closes, no procedure may assume module reload works.

**Confirmed by:** worker session (dmesg captures of both crashes, dkms/source-diff
verification, clean-boot lsmod checks), pasted verbatim in the session record; operator at
the rig (authorized stopping their own manually-started session; performed the recovery
reboot; chose 6.12.y as the colour driver).

## 2026-08-31 — DEFINITIVE ClearHDR milestone: the shipped HDR blend default was the defect; all seven modes work on colour

**Tested:** the colour rig (`cinepi`), full state: CM5 Lite 4 GB, kernel
6.12.93+rpt-rpi-2712, exFAT NVMe at `/media/RAW`. `config.txt`: `camera_auto_detect=1`,
`dtoverlay=imx585,cam0,link-frequency=891000000`, `dtoverlay=rp1-overclock` — 1782 Mbps/lane,
RP1 overclock ON. Driver `imx585-v4l2-driver` branch `cinemate-7modes` @ e9d5759, DKMS
installed. cinepi-raw `dev` @ 24fd76a · cinemate `dev` @ bf4b68d + a local settings edit ·
libcamera `cinemate` @ 3c7b9abd + local tuning edits. Redis at test time: `hdr_blend=5`,
`hdr_gain_adder=1`, thresholds empty, `sensor_mode=6`, 3840×2200, 16-bit.

**Worked: the HDR blend menu at index 5.** It removes the white/magenta speckles and the flat
black-level-pedestal frames. The control is `hdr_data_blending_mode`, reaching the sensor as
`EXP_BK` **0x36e2**; cinemate settings key `image_capture.hdr.blend`, Redis key `hdr_blend`,
CLI `set hdr blend 5`. The menu has **eight** entries, valid indices 0–7 (`imx585.c`,
`hdr_data_blender_menu[]`, per AppNote §4.2 p.15) — index 8 does not exist and is
"Setting Prohibited":

| Index | High gain | Low gain |
|---|---|---|
| 0 | 1/2 | 1/2 |
| 1 | 3/4 | 1/4 |
| 2 | 7/8 | 1/8 |
| 3 | 15/16 | 1/16 |
| 4 | 1/2 | 1/2 |
| **5** | **1/16** | **15/16** |
| 6 | 1/8 | 7/8 |
| 7 | 1/4 | 3/4 |

Index 5 is the shipped default as of now.

**All seven modes work on the colour rig:**

| Mode | Depth | Type |
|---|---|---|
| 1920×1080 | 12-bit | SDR |
| 3840×2160 | 12-bit | SDR |
| 3840×2160 | 10-bit | SDR |
| 1920×1080 | 12-bit | HDR CCMP |
| 3840×2160 | 12-bit | HDR CCMP |
| 1920×1100 | 16-bit | HDR |
| 3840×2200 | 16-bit | HDR |

The 16-bit heights carry optical-black padding: 1080 + 2×10 and 2160 + 2×20. Both enumeration
runs came back as expected — `--list-cameras` (SDR): SRGGB10 3840×2160, SRGGB12 1920×1080 and
3840×2160; `--list-cameras --hdr sensor`: SRGGB12 1920×1080 and 3840×2160, SRGGB16 1920×1100
and 3840×2200. `dmesg` shows every mode at VMAX=4500, HMAX=550, `link_freq=891000000`,
`hdr_scale=2`. The subdev reports 3840×2200 SRGGB16. The binned 16-bit mode (1920×1100)
enumerated on hardware for the first time.

**Did not work / caveats:**
- The first `--list-cameras --hdr sensor` immediately after an SDR run failed with
  `sensor did not accept wide_dynamic_range=1 after retrying`. A retry succeeded. Real,
  reproducible-looking, not yet diagnosed.
- **Register-level confirmation was not captured.** That blend 5 reached `EXP_BK` 0x36e2 is
  inferred from the control path, not read back — `i2ctransfer` is refused while the driver
  holds the address, and closing that gap needs `-f`.
- 2079 Mbps/lane was not re-tested after the fix.
- The result was verified visually by the operator, not by pixel forensics.

**Why:** the shipped blend default was the cause. **This retires the light-history-dependent
clamp model ("Model M") and everything built on it** — its release levers, the mitigation
machinery those levers justified, and the register-level conclusions drawn while chasing it.
Those entries have been deleted from this log rather than annotated; if you meet the model
anywhere else, it is dead.

Still standing, unaffected: the RP1 D-PHY 1500 Mbps/lane spec ceiling; the mono-only finding
that binned 12-bit ClearHDR returns pure BLC on the mono variant (colour is fine and now
offers binned ClearHDR in both depths); and the rp1-cfe Y16 `csi_dt` kernel patch requirement
for mono 16-bit.

**Confirmed by:** operator at the rig, 2026-08-31 — visual confirmation across all seven modes,
plus the two `--list-cameras` runs and the `dmesg` mode lines quoted above.
