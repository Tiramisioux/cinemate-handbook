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
