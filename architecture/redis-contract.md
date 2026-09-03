# The Redis contract

`cp_controls` is the entire interface between cinemate and cinepi-raw. There is no RPC, no
shared library, no other channel that matters day to day. Two further channels exist for
stats and histogram data, but the control surface is `cp_controls`.

## Two registries, neither enforced

| | cinemate | cinepi-raw |
|---|---|---|
| Mechanism | `ParameterKey` enum (`redis_controller.py`) | `#define CONTROL_KEY_*` macros (`cinepi_state.hpp`) |
| Enforced? | No — `set_value()` accepts any string | No — macros are plain strings |

Because dispatch on the cinepi-raw side is a handler map keyed by the published message name,
**the published message IS the key name** — the contract is exactly the set of keys both
sides agree to use, and nothing stops either side drifting from that set.

Both registries were extracted by static pattern matching, which cannot see dynamically
constructed keys. At least one such key is real and load-bearing: cinepi-raw publishes a
per-camera-port readiness key built at runtime, and cinemate glob-scans for it to learn when
each camera instance is up. It appears in neither registry and in neither side's docs.

## ClearHDR live knobs and phase-lock: two undocumented key families

Two key families exist as matched pairs on both sides — a `CONTROL_KEY_*`
macro in `cinepi_state.hpp`, a `ParameterKey` entry in `redis_controller.py`
— but aren't described anywhere else in this contract:

- **ClearHDR live knobs**, new since the `cinemate-v3.3.2` release
  (`cinepi_state.hpp` history: 2026-07-14/07-20) — imx585/imx708, applied
  while streaming, no process restart: `hdr_threshold_low`/`hdr_threshold_high`
  (HG→LG data-selection thresholds), `hdr_blend` (blend mode, driver menu
  index), `hdr_gain_adder` (LG gain adder menu index). See
  [`cinepi-raw.md`](cinepi-raw.md) for what each does to the image. `hdr`
  itself (`ParameterKey.HDR`, "1 = ClearHDR active") is cinemate-side only —
  it's set at process launch via `--hdr sensor`, not read back by
  cinepi-raw over Redis.
- **Phase-lock** (dynamic fps correction) — actually predates that release
  (2026-06-11, three weeks before the tag) but was never documented here
  either: `fps_phase_lock` (0/1), `pll_kp`/`pll_ki` (proportional/integral
  gain), `pll_deadband_us` (phase-error deadband). `CinePiController.__init__`
  applies one shared value to the single `fps_phase_lock` key, read from
  whichever camera's `settings.jsonc` `phase_lock` field it checks first
  (`cam0`, then `cam1`; default `true` on both) — so despite the per-camera
  setting, there is one Redis key behind it, not two independently
  switchable ones.

## Keys that look orphaned are not necessarily dead

Static analysis found roughly a dozen cinepi-raw-side keys with no reference anywhere in
cinemate's source — control handlers that can never fire, tuning knobs apparently never set,
telemetry apparently never read. **Hardware verification found none of them were actually
dead.** Two distinct live patterns explained them:

1. Several keys are read by cinepi-raw itself, once per process (re)start, as an
   **undocumented launch-config contract** — values seeded into Redis long before the
   observing session, persisted via Redis's own snapshotting, with nothing in either
   repo's tracked source setting them.
2. Two of them are **live per-frame telemetry** from the phase-lock controller, written on
   the order of once per frame with zero consumer on the cinemate side.

The lesson generalises past this specific finding — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md): static analysis
proves absence of *references*, never absence of *behaviour*. Before deleting a Redis key
because nothing in the source reads it, check what's actually resident in a running Redis
instance.

## Access patterns on the cinemate side

There are at least four distinct ways cinemate code touches Redis, which is one of the
clearer consistency problems in the codebase:

1. `set_value(ParameterKey.X.value, …)` — the intended path.
2. `set_value("raw_string", …)` — accepted, because `set_value` coerces either form.
3. Module-level string constants scattered across a few modules, bypassing the enum.
4. Reaching past the controller to the raw Redis client directly — bypasses the cache
   entirely, and at least one module (`usb_monitor.py`) constructs its own separate Redis
   client rather than using the injected controller.

If you're debugging "why doesn't this value update", check which of the four patterns is in
play before assuming `RedisController`'s cache is involved at all.

## `awb` is a trap

It looks like the white-balance control. It isn't reachable — cinemate drives colour through
`wb`/`wb_user` plus `cg_rb` and launch-time `--awb`/`--awbgains` flags, never through the
`awb` key. The `awb` handler on the cinepi-raw side is registered but effectively unreachable
from cinemate's normal operation.

## When you add or rename a key

See [`../orientation/entry-points.md`](../orientation/entry-points.md) and
[`../working/changing-a-control.md`](../working/changing-a-control.md) for the checklist.
`tools/redis_key_diff.py` runs in CI as a ratchet on the cross-repo side of this contract —
see [`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md).

## Further reading

- `system-review/deliverables/CODE-MAP-cinepi-raw.md` §5 and `CODE-MAP-cinemate.md` §6 — the line-cited originals.
- `system-review/findings/F-027.md` — the full orphaned-key analysis, reproducible with `system-review/harness/redis_key_diff.py`.
