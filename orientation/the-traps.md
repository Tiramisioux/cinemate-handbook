# The five things that will bite you

These hold regardless of which corner of the codebase you're changing. All five are cited
from the system review — see `F-###` links to [`review-archive.md`](../lessons/review-archive.md)
if you want the original evidence.

## 1. Reads do not come from Redis

`RedisController.get_value()` returns a local cache kept fresh by one background listener
thread. If that thread dies, every read keeps succeeding and every value is frozen —
**silently**. This was hardware-confirmed (`F-204`): one raising subscriber froze the HTTP
API and the SSE stream permanently, with zero staleness indicator anywhere. A fix landed
(wrapping the subscriber dispatch loop in `try`/`except`, matching the pattern
`cinepi_controller.py` already used) and was hardware re-verified to close it — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md). If you add a new
Redis-backed feature, ask what happens if the listener thread has already died before you
build on top of `get_value()`.

## 2. Two dispatch paths, and only one is serialised

CLI, serial, and the web API (`POST /api/v1/cmd`) funnel through one lock
(`CommandExecutor._dispatch_lock`). Six other modules — GPIO, analog pots, the rotary
encoder, the I²C board, storage pre-roll, and the GUI itself — call the controller directly
through `getattr` and take no lock at all. Hardware-confirmed as a real, everyday failure
(`F-285`): a live analog pot completely starved explicit CLI `set iso` commands for as long
as it kept moving. **Do not assume two inputs cannot arrive at once**, and if you're adding a
new input surface, decide up front whether it needs the dispatch lock.

## 3. Actions are dispatched by name, so a typo is silence

Button and menu actions in `settings.jsonc` are strings resolved with
`getattr(controller, name)`. A name that doesn't resolve produces no error, no log line,
nothing — just a control that silently does nothing when pressed. This has shipped at least
once (`set_log`). If you rename a controller method, grep `settings.jsonc` and the settings
editor's catalogue before you do — nothing else will catch it for you at this dispatch layer.

## 4. One process owns the display

DRM master is exclusive per GPU, and cinepi-raw holds it. The preview binds to a display at
process start and cannot rebind — that's why hot-plugging HDMI restarts the whole capture
process. The project has already engineered around this exclusivity once, routing a second
sensor's frames through SysV shared memory rather than sharing the display. If your change
introduces anything that wants its own DRM/KMS client, it will hit this wall; see
[`../architecture/gui-state-model.md`](../architecture/gui-state-model.md).

## 5. The web GUI has no state of its own

It consumes the HDMI GUI's value dictionary (`populate_values()`, 68 fields) verbatim over
Socket.IO, and those updates are emitted from inside the framebuffer draw loop. Add a field to
the HDMI GUI's dict and the browser gets it for free — but stop the GUI thread and the browser
freezes with it, because it has no independent source of truth. See
[`../architecture/gui-state-model.md`](../architecture/gui-state-model.md) for the full
surface-by-surface breakdown.
