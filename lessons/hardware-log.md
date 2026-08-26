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

**Next check that would settle the mechanism:** capture the same scene straight off
`/dev/video4` with `v4l2-ctl --stream-mmap` in the 16-bit mode with cinemate stopped. That
path bypasses libcamera entirely, so real data there localises the fault to
libcamera/PiSP-BE; the same fill pattern there localises it to the CFE/driver.

**Confirmed by:** operator report ("4K 16b looks like stripes but finer stripes than
before"); DNG parse and cross-frame pixel hashes performed off-device on
`CINEPI_26-08-26_232134_F03_C00000_cam0` frames 2, 7, 8, 9. Analysis scripts were scratch
only, not retained.
