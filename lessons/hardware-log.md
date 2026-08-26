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
