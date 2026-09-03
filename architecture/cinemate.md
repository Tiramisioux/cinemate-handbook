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

## The web app is one Flask process, three blueprints

`create_app()` (`src/module/app/__init__.py`), started from `run_application()`
only if `network_available()`, builds a single Flask + Socket.IO app and
registers three blueprints into it — this is one process, not three:

- `main_routes` — the browser mirror of the HDMI GUI (same `populate_values()`
  dict, see [`gui-state-model.md`](gui-state-model.md)) plus the MJPEG/HDMI
  preview stream route.
- `settings_editor_bp` (`src/module/app/settings_editor.py`) — edits
  `settings.jsonc` and `config.txt`, plus two read-mostly panes: RAW
  (`raw_files.py` — browse/download/delete/format takes) and Playback
  (`playback.py` — per-clip DNG/WAV frame serving for in-browser review,
  gated off whenever a recording is in progress).
- `api_v1` (`src/module/app/api.py`, gated by `system.web_api.enabled`) — the
  IoT/hotspot control surface. `/api/v1/cmd` is a thin adapter onto
  `CommandExecutor.handle_received_data()` — the same serialised Path A as
  CLI/serial — with its own rate limiter and a destructive-command
  allowlist gate; `/api/v1/get/<key>` reads `RedisController`'s cache
  directly by `ParameterKey`.

**The settings editor's `config.txt` writer has no confirm/revert window.**
`PUT /api/config-txt` writes the file and, if a `cinepi_controller.reboot` is
available, reboots 0.4s later — unconditionally, with no backup and no
timer. Contrast this with the recovery console below, which protects the
identical file behind a 300-second confirm-or-revert timer and an opt-in
`allow_config_txt` gate. A caller who knows the recovery console's safety
model would reasonably assume the settings editor works the same way; it
doesn't.

**The recovery console is a wholly separate process**, outside
`run_application()` entirely: `services/cinemate-recovery/cinemate-recovery.py`,
a dependency-free stdlib HTTP server on its own port (`:8080`, reachable over
the hotspot), run as its own systemd unit specifically so it survives cases
this main process can't even start — redis is down, cinemate's Python packages are missing or
broken, a bad `settings.jsonc`. There is no venv to plan around any more (see
[`../working/changing-the-installer.md`](../working/changing-the-installer.md)); this console
runs on system `python3` deliberately, the same as everything else. It edits the same two
files (plus systemd state and the journal) through that confirm/revert timer rather than
this process's
`RedisController`/`CinePiController` machinery, because those may not exist
in the failure modes it's designed for.

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

## Storage: RAW hotswap, standby promotion, and write-failure telemetry

`storage-automount.py` (a separate service, not `SSDMonitor` itself) owns
the on-disk convention: the active recording drive is always mounted at
`/media/RAW`; a second, third, … drive plugged in alongside it mounts as
standby at `/media/RAW1`, `/media/RAW2`, and so on. Pulling the active drive
mid-session promotes a standby with a live `mount --move` — the mount point
`/media/RAW` never disappears, only the block device under it changes.
`SSDMonitor._check_mount_status()` polls for exactly that: if it's still
mounted but the underlying device name changed, it treats it as a fresh
mount and re-syncs filesystem type and the recorder storage profile, rather
than assuming an unchanged device because the path didn't unmount. The
settings editor's RAW pane (`raw_files.py`) reads the filesystem directly
(`storage_summary()`, `list_takes()`) rather than through the live
`SSDMonitor` instance, so it can list and serve takes even when the monitor
itself is unhealthy.

**Write-failure telemetry** closes the loop on that promotion: `redis_listener.py`
tracks `hw_write_failures` from cinepi-raw's stats-channel `writeFailures`
counter and raises a live operator warning once failures exceed the current
take's running count — "not keep up (use exFAT or ext4)". `storage_profiles.py`
codifies why: NTFS is supported (it mounts and records) but explicitly
**not recommended** — `filesystem_is_recommended()` returns `False` for it,
because the Linux NTFS driver can drop frames under sustained 4K writes.
Both of these are live, code-enforced signals; nothing about either is a
theoretical footnote to plan around, it fires and warns during a real take.

## Dual-sensor recording: preview vs. record gate, and phase-lock

Two independent Redis keys control the two sensors on a dual-camera rig
(`cinepi_multi.py`'s `CinePiManager` can launch one or two `cinepi-raw`
processes, one per port): `ParameterKey.HDMI_PREVIEW_SOURCE` picks what's on
HDMI (`both` / `cam0` / `cam1` / `pip_cam0` / `pip_cam1`), and
`ParameterKey.RECORD_CAMS` — a genuinely separate gate — picks which
sensor(s) actually write frames this take. `CinePiController._resolve_record_cams()`
defaults `RECORD_CAMS` to follow the preview target (side-by-side records
both; a single-sensor preview records only that sensor) unless an explicit
`rec cam0`/`cam1`/`both` override is given, or `settings.jsonc`'s
`sensors.record_policy` is `always_both`. Switching the live preview
mid-take doesn't cut the sensor that's already recording: `_extend_record_gate_for_preview()`
unions the newly-derived gate into whatever's already running, so a switch
to the dual view joins the second sensor back-to-back rather than replacing
the first.

**Dynamic fps phase-lock** is a cinepi-raw-side closed-loop controller (see
[`redis-contract.md`](redis-contract.md) for its four keys); cinemate's only
role is seeding `fps_phase_lock` at `CinePiController` construction from
`settings.jsonc`'s per-camera `phase_lock` field (default `true`). It reads
only the first configured camera's value and writes one shared key — the
per-camera setting shape doesn't currently buy independent per-sensor
control.

## Further reading

- [`redis-contract.md`](redis-contract.md) — the cross-repo key contract in detail.
- [`gui-state-model.md`](gui-state-model.md) — how the four UI surfaces relate to this state.
- [`../orientation/entry-points.md`](../orientation/entry-points.md) — where to make a given change.
- `system-review/deliverables/CODE-MAP-cinemate.md` — the full line-cited source map this page distills, including the thread inventory and what remains untraced (`RedisListener`'s 2000+ lines, `cinepi_multi.py`'s process supervision).
