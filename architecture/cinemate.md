# Architecture — cinemate

cinemate is a single Python process (`src/main.py`) that supervises the external C++
recorder (cinepi-raw) and paints an on-camera GUI. It does not capture frames itself — it
owns the *controls* and the *display*; cinepi-raw owns the *sensor and the writer*. The two
communicate exclusively through Redis: cinemate writes intent, cinepi-raw writes actuals, and
every UI surface is a view onto those keys (see
[`redis-contract.md`](redis-contract.md)).

## Boot: one long straight-line function

`run_application()` in `main.py` is around 400 lines that construct roughly twenty
components in a fixed, load-bearing order — later components take earlier ones as
constructor arguments. In rough sequence: load `settings.jsonc` → splash → detect the Pi
model → start the hotspot → build the six lowest-level components (`RedisController` first,
then `SensorDetect`, `SSDMonitor`, `USBMonitor`, `GPIOOutput`, `DmesgMonitor`) → seed Redis
defaults → start `ssd_monitor` → launch the `cinepi-raw` child → build `CinePiController` →
`StoragePreroll` → GPIO → `CommandExecutor` (the CLI/serial/HTTP dispatcher) → the serial
relay → the status broadcaster → analog controls → mount the controller → `RedisListener`
(the read side) → `BatteryMonitor` → `SimpleGUI` → the optional I²C OLED and quad rotary →
the web app (only if the network is available) → `Mediator` → mark the process ready for
systemd.

**`RedisController` is constructed first and injected into nearly everything.** It has the
widest fan-in of any object in the repo. If you're changing how state moves through the
system, you are almost certainly changing this object or its callers.

Process integrates with **systemd** as a notify-type service and negotiates with
**Plymouth** (the boot splash) for framebuffer ownership at startup — direct evidence that
framebuffer contention exists even before the main GUI starts, and is handled by *waiting for
the other party to exit*, not by sharing.

## Threads and shutdown

Long-lived components subclass `threading.Thread` and expose `run()`/`stop()` (see
[`../conventions/style.md`](../conventions/style.md) for the two threading shapes this
project uses). `cleanup()` is registered with `atexit` and also called from the SIGINT/SIGTERM
handler, guarded by a `cleanup_called` flag. On the way out it writes three Redis keys:
`is_recording=0`, `is_writing=0`, and the last `fps` — the only state deliberately persisted
across a restart.

**Historically, a handful of components with live threads were never told to stop** in
`cleanup()` (they were added to boot but not to teardown — the two functions are far apart
in the same file with no structural link between them). If you add a new long-lived thread to
`run_application()`, add its `stop()`/`join()` call to `cleanup()` in the same change — this
is the single most common omission pattern in this file's history.

## Control surfaces → dispatcher → controller

Two independent paths reach `CinePiController`, and only one of them is serialised. See
[`../orientation/the-traps.md`](../orientation/the-traps.md) #2 for why that matters, and
[`../working/changing-a-control.md`](../working/changing-a-control.md) for the practical
checklist when you're adding to either path.

**Path A — serialised.** CLI (stdin), serial (UART), and the web API all funnel through
`CommandExecutor.handle_received_data()`, which acquires `_dispatch_lock` with a timeout. On
timeout the command is dropped with a warning, not retried.

**Path B — not serialised.** GPIO buttons/switches, analog pots, and the I²C quad rotary
controller hold a `cinepi_controller` reference and call its methods directly via
`getattr(controller, method_name)`, with the method name coming from a string in
`settings.jsonc`. None of these touch `_dispatch_lock`.

Both GPIO and the quad rotary resolve **user-facing method names from config**, which has two
consequences worth internalising: `CinePiController`'s public method names are effectively a
user-facing API (renaming one silently breaks any camera whose `settings.jsonc` references
it), and a typo in that config produces a log line, not a visible error — see
[`../orientation/the-traps.md`](../orientation/the-traps.md) #3.

## State ownership

| State | Owner | Mechanism |
|---|---|---|
| Live camera state (fps, iso, shutter, wb, resolution, `is_recording`, …) | Redis | `RedisController`, keyed by the `ParameterKey` enum |
| Intent (what the operator asked for) | cinemate → Redis | `set_value()` from the controller or an input surface |
| Actuals (what the sensor/writer actually did) | cinepi-raw → Redis | read by `RedisListener` |
| User configuration | `settings.jsonc` | `config_loader.py`, read once at boot |
| Per-surface view state (VU smoothing, lock flags, layout) | Each UI surface | e.g. `SimpleGUI` instance attributes — never reach Redis at all |

`RedisController` is more than a thin client: it keeps a **local cache** primed at startup,
`get_value()` reads that cache (not Redis — see
[`../orientation/the-traps.md`](../orientation/the-traps.md) #1), a background listener
thread keeps the cache fresh, and `set_value()` writes Redis, publishes on `cp_controls`,
updates the cache, and short-circuits if the value is unchanged.

Several call sites bypass this object entirely — module-level string constants for specific
keys, and at least one call site that reaches past the controller to the raw Redis client.
`usb_monitor.py` additionally constructs its own Redis client rather than using the injected
controller. Treat "everything goes through `RedisController`" as the design intent, not an
invariant you can rely on while debugging.

## Further reading

- [`redis-contract.md`](redis-contract.md) — the cross-repo key contract in detail.
- [`gui-state-model.md`](gui-state-model.md) — how the four UI surfaces relate to this state.
- [`../orientation/entry-points.md`](../orientation/entry-points.md) — where to make a given change.
- `system-review/deliverables/CODE-MAP-cinemate.md` — the full line-cited source map this page distills, including the thread inventory and what remains untraced (`RedisListener`'s 2000+ lines, `cinepi_multi.py`'s process supervision).
