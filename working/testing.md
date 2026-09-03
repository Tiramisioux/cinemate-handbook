# Testing — what runs where

## cinemate: the whole suite is portable

`_test/` (905 tests, 405 subtests, a few seconds, nine `pip` packages, no Raspberry Pi) runs
the same way locally and in CI — reconfirmed directly against `origin/dev`. A 2026-08-23
hardware pass (system-review's PI-002) matched the off-hardware run exactly at the time: 381
passed / 241 subtests, zero skips either way. The suite has since grown roughly 2.5x without a
repeat hardware pass, so treat "identical on the Pi" as confirmed at that earlier count, not
today's — but nothing about *how* tests get added has changed, including the newer
drift-guard tests (`test_installed_files_drift.py`, which checks `installed_files.py`'s
`INSTALLED_FILES` list against the Makefile's own `install` target): still no camera, no live
Redis, no GPIO. **There is no hardware-only subset today.** Keep it that way: a test that needs
hardware cannot run in CI, and CI is the only thing that actually runs these tests at all.

The house pattern is `unittest`, with hardware-only modules (`gpiozero`, `sugarpie`, `smbus`,
`grove.i2c`) stubbed via `sys.modules.setdefault` before the import under test. **Be careful
with this pattern**: `sys.modules` is process-wide and nothing cleans a stub up afterward, so
a stub installed by one test can silently decide what that module means for every test that
runs after it in the same process. Collection order currently matters for this reason — see
the comment in `.github/workflows/checks.yml`'s `pytest` job.

**Write a test that fails against the unfixed code, and check that it does.** Every fix in
the remediation that followed the system review was verified in both directions. A test that
passes against broken code is worse than no test.

## cinepi-raw: only pure, self-contained logic is unit-testable

No `libcamera`, no Redis, no DMA/mmap buffers, no recorder threads — anything touching those
needs a live take, not a unit test (see "What genuinely needs a Pi" below). What *is*
testable: header-only pure functions and value logic — the DNG pixel packing/unpacking
helpers in `dng_encoder.cpp`, the phase-lock core, the CCMP/log-LUT math. Eight of these
already have tests under `tests/` (check `cinepi/meson.build`'s `test(...)` targets for the
current count — CCMP12 work has added to it before), following one consistent pattern:

- **Logic under test lives in a header** that a test translation unit can `#include` with no
  libcamera. If the logic you want to test is `static inline` inside a `.cpp` file, lift it
  into a pure header first (only `<cstdint>`/`<cstddef>`-style includes) — this is the same
  extraction that made the existing tests possible.
- **A tiny built-in harness, no framework.** A `CHECK(cond, msg)` macro and a `main()` that
  reports failures and returns non-zero on any. Do not add gtest, catch2, or any new
  dependency.
- **Wired into `cinepi/meson.build`** as its own `test()` target, next to the existing ones.
- **Each test file documents its own direct `g++`/`c++` build line** in a header comment, so
  it can be compiled standalone without going through `meson setup` at all.

That last property is exactly what CI relies on: because the project's `meson.build` requires
libcamera unconditionally at configure time, cinepi-raw's CI compiles and runs each pure test
target directly with `g++` — one project header plus the standard library — bypassing `meson
setup` entirely. See [`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md).

To run the canonical, more thorough form on the Pi itself:

```
meson test -C /home/pi/cinepi-raw/build <name> --print-errorlogs
```

(drop `<name>` to run everything; `meson compile -C /home/pi/cinepi-raw/build` to build
without running). If `meson` doesn't pick up a newly added `test()`, force a reconfigure once
with `meson setup --reconfigure /home/pi/cinepi-raw/build`.

## What genuinely needs a Pi

Not a hedge — a specific, recurring list, because these categories have concretely produced
wrong desk conclusions before (see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md)):

- Whether a Redis key that looks orphaned in source is actually written by something outside
  the tracked source (an installer step, a first-boot seed, another process).
- Whether two input paths racing actually produce an observable bad outcome, not just a
  theoretical one.
- DRM/framebuffer composition and plane ownership.
- Timing: GUI refresh cadence, log-queue growth rate, boot time.
- Memory and CPU headroom under real recording load, at the sensor's true peak mode.
- Anything about a *clean install* — sudoers defaults, first-boot package resolution, apt-vs-pip
  overlap — that an already-running production unit cannot exercise.

**Nothing static can settle any of the above.** If you find yourself asserting one of these
categories from reading the code alone, stop and write down the specific experiment that
would confirm or refute it instead — see
[`hardware-session.md`](hardware-session.md) for how to actually run one.

## Further reading

- `system-review/deliverables/SKILL-PAYLOAD.md` §7 — the verification section this page distills.
- [`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md) — what's automated and where it runs.
